import os
import signal
import sys
import threading
import time

from .config import (
    MIN_RECORD_SECONDS,
    MIN_VALID_FILE_SIZE,
    RECORDINGS_DIR,
)
from .deepgram_client import DeepgramClient
from .gpio_controller import GPIOController
from .recorder import Recorder
from .state_manager import DeviceState, StateData
from .storage import save_transcript_files
from .webapp import run_web


class FieldNotesDevice:
    def __init__(self) -> None:
        os.makedirs(RECORDINGS_DIR, exist_ok=True)

        self.state = StateData()
        self.gpio = GPIOController()
        self.recorder = Recorder()
        self.lock = threading.Lock()
        self.last_recording_duration = None

        mic_ok, mic_msg = self.recorder.check_microphone()
        print(f"[MIC] {mic_msg}")
        if not mic_ok:
            self.state.set_error(mic_msg)

        self.deepgram = None
        try:
            self.deepgram = DeepgramClient()
            print("[DG] Deepgram client ready")
        except Exception as exc:
            print(f"[DG] Deepgram unavailable: {exc}")

        self.gpio.record_button.when_pressed = self.handle_record_pressed
        self.gpio.record_button.when_released = self.handle_record_released
        self.gpio.upload_button.when_pressed = self.handle_upload_pressed
        self.gpio.skip_button.when_pressed = self.handle_skip_pressed
        self.gpio.spare_button.when_pressed = self.handle_spare_pressed

        self.gpio.show_state(self.state.state)

    def set_state(self, new_state: DeviceState) -> None:
        self.state.set_state(new_state)
        print(f"[STATE] -> {new_state.value}")
        self.gpio.show_state(new_state)

    def set_error(self, message: str) -> None:
        print(f"[ERROR] {message}")
        self.state.set_error(message)
        self.gpio.show_state(DeviceState.ERROR)

    def clear_error(self) -> None:
        self.state.clear_error()
        self.set_state(DeviceState.IDLE)

    def validate_pending_file(self, filepath: str, duration: float) -> tuple[bool, str]:
        if duration < MIN_RECORD_SECONDS:
            return False, f"Recording too short ({duration:.2f}s)"

        if not filepath:
            return False, "No file path returned"

        if not os.path.exists(filepath):
            return False, "Recorded file not found"

        size = os.path.getsize(filepath)
        if size < MIN_VALID_FILE_SIZE:
            return False, f"File too small ({size} bytes)"

        return True, ""

    def handle_record_pressed(self) -> None:
        with self.lock:
            print("[BUTTON] Record pressed")

            if self.state.state == DeviceState.ERROR and self.state.last_error:
                print("[INFO] Device is in error state. Fix issue or press Spare to clear.")
                return

            if self.state.state != DeviceState.IDLE:
                print(f"[INFO] Ignoring record press in {self.state.state.value}")
                return

            try:
                filepath = self.recorder.start()
                self.state.pending_file = filepath
                print(f"[AUDIO] Recording started: {filepath}")
                self.set_state(DeviceState.RECORDING)
            except Exception as exc:
                self.set_error(f"Failed to start recording: {exc}")

    def handle_record_released(self) -> None:
        with self.lock:
            print("[BUTTON] Record released")

            if self.state.state != DeviceState.RECORDING:
                print(f"[INFO] Ignoring record release in {self.state.state.value}")
                return

            try:
                filepath, duration = self.recorder.stop()
                ok, reason = self.validate_pending_file(filepath, duration)
                if not ok:
                    print(f"[WARN] Invalid recording: {reason}")
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
                    self.state.pending_file = None
                    self.last_recording_duration = None
                    self.set_state(DeviceState.IDLE)
                    return

                print(f"[AUDIO] Saved recording: {filepath}")
                print(f"[AUDIO] Duration: {duration:.2f}s")
                print(f"[AUDIO] Size: {os.path.getsize(filepath)} bytes")

                self.state.pending_file = filepath
                self.last_recording_duration = duration
                self.set_state(DeviceState.PENDING)

            except Exception as exc:
                self.set_error(f"Failed to stop recording: {exc}")

    def handle_upload_pressed(self) -> None:
        with self.lock:
            print("[BUTTON] Upload pressed")

            if self.state.state != DeviceState.PENDING:
                print(f"[INFO] Ignoring upload press in {self.state.state.value}")
                return

            if not self.state.pending_file or not os.path.exists(self.state.pending_file):
                self.set_error("No pending WAV file to upload")
                return

            if self.deepgram is None:
                self.set_error("Deepgram client not configured")
                return

            try:
                self.set_state(DeviceState.UPLOADING)

                print(f"[DG] Uploading {self.state.pending_file}")
                started = time.time()
                result = self.deepgram.transcribe_file(self.state.pending_file)
                processing_time_seconds = time.time() - started

                transcript = self.deepgram.extract_transcript(result)

                print(f"[DG] Transcript: {transcript}")
                print(f"[DG] Processing time: {processing_time_seconds:.2f}s")

                txt_path, json_path = save_transcript_files(
                    self.state.pending_file,
                    transcript,
                    result,
                    self.last_recording_duration,
                    processing_time_seconds,
                )

                print(f"[FILE] Saved transcript text: {txt_path}")
                print(f"[FILE] Saved transcript json: {json_path}")

                self.state.last_transcript = transcript
                self.state.pending_file = None
                self.last_recording_duration = None
                self.set_state(DeviceState.IDLE)

            except Exception as exc:
                self.set_error(f"Upload failed: {exc}")

    def handle_skip_pressed(self) -> None:
        with self.lock:
            print("[BUTTON] Skip pressed")

            if self.state.state != DeviceState.PENDING:
                print(f"[INFO] Ignoring skip press in {self.state.state.value}")
                return

            try:
                if self.state.pending_file and os.path.exists(self.state.pending_file):
                    os.remove(self.state.pending_file)
                    print(f"[FILE] Deleted {self.state.pending_file}")

                self.state.pending_file = None
                self.last_recording_duration = None
                self.set_state(DeviceState.IDLE)

            except Exception as exc:
                self.set_error(f"Failed to skip/delete file: {exc}")

    def handle_spare_pressed(self) -> None:
        with self.lock:
            print("[BUTTON] Spare pressed")

            if self.state.state == DeviceState.ERROR:
                mic_ok, mic_msg = self.recorder.check_microphone()
                print(f"[MIC] {mic_msg}")
                if mic_ok:
                    self.clear_error()
                else:
                    self.set_error(mic_msg)
            else:
                print("[INFO] No action assigned")

    def cleanup(self) -> None:
        print("[SYS] Cleaning up")
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.gpio.cleanup()


def main() -> None:
    device = FieldNotesDevice()

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("[WEB] Serving on http://<your-pi-ip>:5000")

    def shutdown_handler(signum, frame):
        print(f"[SYS] Signal {signum} received")
        device.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print("[SYS] Device ready")
    print("[SYS] Green = idle, Yellow = recording/uploading, Green+Yellow = pending, Red = error")
    print("[SYS] Hold Record to capture audio")

    try:
        while True:
            time.sleep(0.1)
    finally:
        device.cleanup()


if __name__ == "__main__":
    main()
