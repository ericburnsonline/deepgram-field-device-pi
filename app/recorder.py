import os
import re
import shutil
import subprocess
import time
from typing import Optional

from .config import (
    RECORDINGS_DIR,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_FORMAT,
    AUDIO_DEVICE,
    I2S_MIC_KEYWORDS,
    USB_MIC_KEYWORDS,
)


class Recorder:
    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.started_at: Optional[float] = None
        self.selected_device: Optional[str] = None
        self.selected_device_label: Optional[str] = None

    def _build_filename(self) -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        return os.path.join(RECORDINGS_DIR, f"note-{ts}.wav")

    def _run_arecord_list(self) -> str:
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return (result.stdout or "") + (result.stderr or "")

    def _parse_capture_devices(self, text: str) -> list[dict]:
        devices = []
        for line in text.splitlines():
            m = re.match(
                r"^card\s+(\d+):\s+([^\[]+)\[([^\]]+)\],\s+device\s+(\d+):\s+([^\[]+)\[([^\]]+)\]",
                line.strip(),
            )
            if not m:
                continue

            card_num = m.group(1)
            card_short = m.group(2).strip()
            card_long = m.group(3).strip()
            device_num = m.group(4)
            dev_short = m.group(5).strip()
            dev_long = m.group(6).strip()

            label = f"{card_short} {card_long} {dev_short} {dev_long}".strip()
            devices.append(
                {
                    "card": card_num,
                    "device": device_num,
                    "plughw": f"plughw:{card_num},{device_num}",
                    "label": label,
                    "search": label.lower(),
                }
            )
        return devices

    def _find_by_keywords(self, devices: list[dict], keywords: list[str]) -> Optional[dict]:
        for keyword in keywords:
            keyword = keyword.lower()
            for device in devices:
                if keyword in device["search"]:
                    return device
        return None

    def _choose_device(self, devices: list[dict]) -> Optional[dict]:
        # Prefer I2S first
        chosen = self._find_by_keywords(devices, I2S_MIC_KEYWORDS)
        if chosen:
            return chosen

        # Then fall back to USB mic
        chosen = self._find_by_keywords(devices, USB_MIC_KEYWORDS)
        if chosen:
            return chosen

        return None

    def check_microphone(self) -> tuple[bool, str]:
        if shutil.which("arecord") is None:
            return False, "arecord not found. Install with: sudo apt install alsa-utils"

        try:
            output = self._run_arecord_list()
        except Exception as exc:
            return False, f"Failed to run 'arecord -l': {exc}"

        if "List of CAPTURE Hardware Devices" not in output:
            return False, "No capture devices detected. Run: arecord -l"

        devices = self._parse_capture_devices(output)
        if not devices:
            return False, "No usable capture devices parsed from arecord output"

        # Explicit override wins
        if AUDIO_DEVICE:
            self.selected_device = AUDIO_DEVICE
            self.selected_device_label = f"manual override ({AUDIO_DEVICE})"
        else:
            selected = self._choose_device(devices)
            if not selected:
                labels = ", ".join(d["label"] for d in devices)
                return False, f"No preferred microphone found. Devices seen: {labels}"
            self.selected_device = selected["plughw"]
            self.selected_device_label = selected["label"]

        try:
            test = subprocess.run(
                [
                    "arecord",
                    "-D", self.selected_device,
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
            return False, f"Configured device '{self.selected_device}' could not be tested: {exc}"

        if test.returncode != 0:
            return False, (
                f"Configured device '{self.selected_device}' failed. "
                f"Error: {test.stderr.strip()}"
            )

        try:
            if os.path.exists("/tmp/mic_check.wav"):
                os.remove("/tmp/mic_check.wav")
        except Exception:
            pass

        return True, f"Microphone OK on {self.selected_device} ({self.selected_device_label})"

    def start(self) -> str:
        if self.process is not None:
            raise RuntimeError("Recording already in progress")

        if not self.selected_device:
            raise RuntimeError("No microphone selected")

        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        self.current_file = self._build_filename()

        cmd = [
            "arecord",
            "-D", self.selected_device,
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
