import os
import time
from typing import Callable

from .config import RECORDINGS_DIR, TRANSCRIPTS_DIR
from .storage import save_transcript_files


def _base_name_from_wav(wav_path: str) -> str:
    filename = os.path.basename(wav_path)
    if filename.lower().endswith(".wav"):
        return filename[:-4]
    return filename


def _transcript_paths_for_wav(wav_path: str) -> tuple[str, str]:
    base = _base_name_from_wav(wav_path)
    txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.txt")
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
    return txt_path, json_path


def find_queued_recordings() -> list[str]:
    """
    A queued recording is a WAV file that does not have both matching
    transcript files yet.
    """
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

    queued = []

    for filename in sorted(os.listdir(RECORDINGS_DIR)):
        if not filename.lower().endswith(".wav"):
            continue

        wav_path = os.path.join(RECORDINGS_DIR, filename)
        txt_path, json_path = _transcript_paths_for_wav(wav_path)

        if not os.path.exists(txt_path) or not os.path.exists(json_path):
            queued.append(wav_path)

    return queued


def has_queued_recordings() -> bool:
    return len(find_queued_recordings()) > 0


def process_queued_recordings(
    deepgram_client,
    log: Callable[[str], None] = print,
) -> tuple[int, int]:
    """
    Reprocess queued WAV files.

    Returns:
        (success_count, failure_count)
    """
    queued = find_queued_recordings()

    if not queued:
        log("[QUEUE] No queued recordings found")
        return 0, 0

    log(f"[QUEUE] Found {len(queued)} queued recording(s)")

    success_count = 0
    failure_count = 0

    for wav_path in queued:
        log(f"[QUEUE] Processing {wav_path}")

        try:
            started = time.time()
            result = deepgram_client.transcribe_file(wav_path)
            processing_time = time.time() - started
            transcript = deepgram_client.extract_transcript(result)

            txt_path, json_path = save_transcript_files(
                audio_path=wav_path,
                transcript=transcript,
                raw_result=result,
                duration_seconds=None,
                processing_time_seconds=processing_time,
            )

            log(f"[QUEUE] Saved TXT:  {txt_path}")
            log(f"[QUEUE] Saved JSON: {json_path}")
            success_count += 1

        except Exception as exc:
            log(f"[QUEUE] ERROR processing {wav_path}: {exc}")
            failure_count += 1

    log(f"[QUEUE] Done. Success: {success_count}, Failed: {failure_count}")
    return success_count, failure_count
