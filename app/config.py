import os
from dotenv import load_dotenv

load_dotenv()

# LEDs
RED_LED_PIN = 17
YELLOW_LED_PIN = 27
GREEN_LED_PIN = 22

# Buttons
RECORD_BUTTON_PIN = 20
UPLOAD_BUTTON_PIN = 12
SKIP_BUTTON_PIN = 21
SPARE_BUTTON_PIN = 16

# Audio
ARECORD_DEVICE = "plughw:1,0"
#ARECORD_DEVICE = "default"
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_FORMAT = "S16_LE"
MIN_RECORD_SECONDS = 0.5
MIN_VALID_FILE_SIZE = 1024

# Deepgram
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3")
DEEPGRAM_LANGUAGE = os.getenv("DEEPGRAM_LANGUAGE", "en")

# Storage
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")

# Web
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
WEB_DEBUG = False
