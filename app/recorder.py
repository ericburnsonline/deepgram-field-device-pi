import os
import shutil
import subprocess
import time
from typing import Optional

from .config import (
    RECORDINGS_DIR,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_FORMAT,
    ARECORD_DEVICE,
)


class Recorder:
    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.started_at: Optional[float] = None

    def _build_filename(self) -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        return os.path.join(RECORDINGS_DIR, f"note-{ts}.wav")

    def check_microphone(self) -> tuple[bool, str]:
        if shutil.which("arecord") is None:
            return False, "arecord not found. Install with: sudo apt install alsa-utils"

        try:
            result = subprocess.run(
                ["arecord", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception as exc:
            return False, f"Failed to run 'arecord -l': {exc}"

        output = (result.stdout or "") + (result.stderr or "")
        if "List of CAPTURE Hardware Devices" not in output:
            return False, "No capture devices detected. Run: arecord -l"

        try:
            test = subprocess.run(
                [
                    "arecord",
                    "-D", ARECORD_DEVICE,
                    "-f", AUDIO_FORMAT,
                    "-r", str(AUDIO_SAMPLE_RATE),
                    "-c", str(AUDIO_CHANNELS),
                    "-d", "1",
                    "/tmp/mic_check.wav",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except Exception as exc:
            return False, f"Configured device '{ARECORD_DEVICE}' could not be tested: {exc}"

        if test.returncode != 0:
            return False, (
                f"Configured device '{ARECORD_DEVICE}' failed. "
                f"Run 'arecord -l' and update ARECORD_DEVICE in app/config.py. "
                f"Error: {test.stderr.strip()}"
            )

        try:
            if os.path.exists("/tmp/mic_check.wav"):
                os.remove("/tmp/mic_check.wav")
        except Exception:
            pass

        return True, f"Microphone OK on {ARECORD_DEVICE}"

    def start(self) -> str:
        if self.process is not None:
            raise RuntimeError("Recording already in progress")

        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        self.current_file = self._build_filename()

        cmd = [
            "arecord",
            "-D", ARECORD_DEVICE,
            "-f", AUDIO_FORMAT,
            "-r", str(AUDIO_SAMPLE_RATE),
            "-c", str(AUDIO_CHANNELS),
            self.current_file,
        ]

        self.process = subprocess.Popen(cmd)
        self.started_at = time.time()
        return self.current_file

    def stop(self) -> tuple[Optional[str], float]:
        if self.process is None:
            return None, 0.0

        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

        duration = 0.0
        if self.started_at:
            duration = time.time() - self.started_at

        self.process = None
        self.started_at = None
        return self.current_file, duration
