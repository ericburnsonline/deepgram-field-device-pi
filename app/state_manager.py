from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PENDING = "pending"
    UPLOADING = "uploading"
    ERROR = "error"


@dataclass
class StateData:
    state: DeviceState = DeviceState.IDLE
    pending_file: Optional[str] = None
    last_error: Optional[str] = None
    last_transcript: Optional[str] = None

    def set_state(self, new_state: DeviceState) -> None:
        self.state = new_state

    def set_error(self, message: str) -> None:
        self.last_error = message
        self.state = DeviceState.ERROR

    def clear_error(self) -> None:
        self.last_error = None
        if self.state == DeviceState.ERROR:
            self.state = DeviceState.IDLE
