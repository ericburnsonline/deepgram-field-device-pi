import os
import requests
from urllib.parse import urlencode

from .config import DEEPGRAM_API_KEY, DEEPGRAM_MODEL, DEEPGRAM_LANGUAGE


class DeepgramClient:
    def __init__(self) -> None:
        if not DEEPGRAM_API_KEY:
            raise RuntimeError("DEEPGRAM_API_KEY not set")

        self.api_key = DEEPGRAM_API_KEY

    def transcribe_file(self, filepath: str) -> dict:
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        params = {
            "model": DEEPGRAM_MODEL,
            "smart_format": "true",
            "language": DEEPGRAM_LANGUAGE,
        }

        url = f"https://api.deepgram.com/v1/listen?{urlencode(params)}"

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }

        with open(filepath, "rb") as f:
            response = requests.post(url, headers=headers, data=f, timeout=120)

        response.raise_for_status()
        return response.json()

    @staticmethod
    def extract_transcript(result: dict) -> str:
        try:
            return result["results"]["channels"][0]["alternatives"][0]["transcript"] or ""
        except Exception:
            return ""
