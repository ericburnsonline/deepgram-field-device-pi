from gpiozero import LED, Button

from .config import (
    RED_LED_PIN,
    YELLOW_LED_PIN,
    GREEN_LED_PIN,
    RECORD_BUTTON_PIN,
    UPLOAD_BUTTON_PIN,
    SKIP_BUTTON_PIN,
    SPARE_BUTTON_PIN,
)
from .state_manager import DeviceState


class GPIOController:
    def __init__(self) -> None:
        self.red = LED(RED_LED_PIN)
        self.yellow = LED(YELLOW_LED_PIN)
        self.green = LED(GREEN_LED_PIN)

        self.record_button = Button(RECORD_BUTTON_PIN, pull_up=True, bounce_time=0.05)
        self.upload_button = Button(UPLOAD_BUTTON_PIN, pull_up=True, bounce_time=0.05)
        self.skip_button = Button(SKIP_BUTTON_PIN, pull_up=True, bounce_time=0.05)
        self.spare_button = Button(SPARE_BUTTON_PIN, pull_up=True, bounce_time=0.05)

    def show_state(self, state: DeviceState) -> None:
        self.red.off()
        self.yellow.off()
        self.green.off()

        if state == DeviceState.IDLE:
            self.green.on()
        elif state == DeviceState.RECORDING:
            self.yellow.on()
        elif state == DeviceState.PENDING:
            self.green.on()
            self.yellow.on()
        elif state == DeviceState.UPLOADING:
            self.yellow.on()
        elif state == DeviceState.ERROR:
            self.red.on()

    def cleanup(self) -> None:
        self.red.off()
        self.yellow.off()
        self.green.off()
