import json
import os
import time

from .config import TRANSCRIPTS_DIR, DEEPGRAM_MODEL, DEEPGRAM_LANGUAGE


def ensure_dirs() -> None:
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def transcript_base_name_from_audio(audio_path: str) -> str:
    base = os.path.basename(audio_path)
    if base.lower().endswith(".wav"):
        base = base[:-4]
    return base


def save_transcript_files(
    audio_path: str,
    transcript: str,
    raw_result: dict,
    duration_seconds: float | None = None,
    processing_time_seconds: float | None = None,
) -> tuple[str, str]:
    ensure_dirs()
    base = transcript_base_name_from_audio(audio_path)

    txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.txt")
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")

    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(transcript.strip() + "\n")

    confidence = None
    language = None
    model = DEEPGRAM_MODEL or "unknown"

    try:
        channel = raw_result.get("results", {}).get("channels", [{}])[0]
        alt = channel.get("alternatives", [{}])[0]

        confidence = alt.get("confidence")

        language = (
            channel.get("detected_language")
            or alt.get("detected_language")
            or raw_result.get("results", {}).get("detected_language")
            or raw_result.get("metadata", {}).get("language")
            or DEEPGRAM_LANGUAGE
            or "unknown"
        )
    except Exception:
        language = DEEPGRAM_LANGUAGE or "unknown"

    try:
        metadata = raw_result.get("metadata", {})
        model = (
            metadata.get("model_info", {}).get("name")
            or metadata.get("model")
            or metadata.get("models", [None])[0]
            or DEEPGRAM_MODEL
            or "unknown"
        )
    except Exception:
        model = DEEPGRAM_MODEL or "unknown"

    payload = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "audio_file": audio_path,
        "audio_filename": os.path.basename(audio_path),
        "transcript": transcript,
        "confidence": confidence,
        "language": language,
        "model": model,
        "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
        "processing_time_seconds": round(processing_time_seconds, 2) if processing_time_seconds is not None else None,
        "deepgram_result": raw_result,
    }

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(payload, jf, indent=2)

    return txt_path, json_path


def list_recent_transcripts(limit: int = 10) -> list[dict]:
    ensure_dirs()

    items = []
    for filename in os.listdir(TRANSCRIPTS_DIR):
        if not filename.endswith(".json"):
            continue

        full_path = os.path.join(TRANSCRIPTS_DIR, filename)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            payload["_file"] = full_path
            items.append(payload)
        except Exception:
            continue

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]
