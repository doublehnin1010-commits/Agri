from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.core.config import BACKEND_DIR, settings
from app.utils.audio_utils import cleanup_audio_paths, preprocess_audio_with_ffmpeg


logger = logging.getLogger(__name__)

_model = None
_EXCESSIVE_REPETITION_RE = re.compile(r"(.)\1{7,}")
_MYANMAR_CHARACTER_RE = re.compile(r"[\u1000-\u109f\uaa60-\uaa7f\ua9e0-\ua9ff]")
_MYANMAR_INITIAL_PROMPT = "ဤအသံသည် မြန်မာဘာသာစကားဖြင့် ပြောထားသော အသံဖြစ်သည်။"


def _resolve_device() -> str:
    configured = (settings.whisper_device or "auto").strip().lower()
    if configured != "auto":
        return configured

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _resolve_compute_type(device: str) -> str:
    configured = (settings.whisper_compute_type or "auto").strip().lower()
    if configured != "auto":
        return configured
    return "float16" if device == "cuda" else "int8"


def _resolve_model_source() -> str:
    configured = settings.whisper_model.strip()
    if not configured:
        raise RuntimeError("WHISPER_MODEL must not be empty")

    candidate = Path(configured)
    if not candidate.is_absolute():
        candidate = BACKEND_DIR / candidate

    if candidate.is_dir():
        required_files = ("config.json", "model.bin", "tokenizer.json")
        missing = [name for name in required_files if not (candidate / name).is_file()]
        if missing:
            raise RuntimeError(
                f"Local Whisper model is incomplete at '{candidate}'. Missing: {', '.join(missing)}"
            )
        return str(candidate)

    # Values such as "small" remain valid faster-whisper model identifiers.
    return configured


def get_whisper_model():
    global _model
    if _model is not None:
        return _model

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Speech transcription is not installed. Run: pip install faster-whisper",
        ) from exc

    device = _resolve_device()
    compute_type = _resolve_compute_type(device)
    logger.info(
        "Loading Faster-Whisper model '%s' on %s with %s compute",
        settings.whisper_model,
        device,
        compute_type,
    )
    model_source = _resolve_model_source()
    _model = WhisperModel(
        model_source,
        device=device,
        compute_type=compute_type,
        local_files_only=settings.whisper_local_files_only,
    )
    return _model


def _clean_transcript(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).strip()


def _is_invalid_transcript(text: str) -> bool:
    return not text or "\ufffd" in text or bool(_EXCESSIVE_REPETITION_RE.search(text))


def _uses_expected_script(text: str, language: str | None) -> bool:
    if language != "my":
        return True
    return bool(_MYANMAR_CHARACTER_RE.search(text))


def transcribe_speech(
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    wav_path = preprocess_audio_with_ffmpeg(audio_bytes, filename, content_type)
    try:
        model = get_whisper_model()
        requested_language = (language or "").strip().lower()
        whisper_language = {
            "my-mm": "my",
            "myanmar": "my",
            "burmese": "my",
            "en-us": "en",
            "english": "en",
            "auto": "",
        }.get(requested_language, requested_language) or None

        segments, info = model.transcribe(
            str(wav_path),
            language=whisper_language,
            task="transcribe",
            beam_size=settings.whisper_beam_size,
            temperature=0.0,
            condition_on_previous_text=False,
            initial_prompt=_MYANMAR_INITIAL_PROMPT if whisper_language == "my" else None,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": settings.whisper_vad_silence_ms},
        )
        raw_text = _clean_transcript(
            " ".join(segment.text.strip() for segment in segments if segment.text)
        )
        detected_language = getattr(info, "language", None) or whisper_language or "unknown"
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Faster-Whisper transcription failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not transcribe audio. Please try again.",
        ) from exc
    finally:
        cleanup_audio_paths(wav_path)

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No speech was detected in the recording.",
        )
    if _is_invalid_transcript(raw_text):
        logger.warning("Rejected likely Whisper hallucination: %r", raw_text)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The Myanmar speech was unclear. Please speak again slowly and closer to the microphone.",
        )
    if not _uses_expected_script(raw_text, whisper_language):
        logger.warning("Rejected non-Myanmar script from Burmese transcription: %r", raw_text)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recording was not recognized as Myanmar script. Please speak again clearly in Myanmar.",
        )

    logger.info("Whisper output (%s): %s", detected_language, raw_text)
    return {"success": True, "text": raw_text, "language": detected_language}
