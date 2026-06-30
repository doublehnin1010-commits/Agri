from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
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

    _model = WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    return _model


def _normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    code = language.strip().lower().split("-", 1)[0]
    if code in {"my", "en"}:
        return code
    return None


def transcribe_audio_bytes(audio_bytes: bytes, filename: str, language: str | None) -> str:
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")

    suffix = Path(filename or "recording.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(audio_bytes)
        temp_path = temp_file.name

    try:
        model = _get_model()
        whisper_language = _normalize_language(language)
        segments, _info = model.transcribe(
            temp_path,
            language=whisper_language,
            beam_size=5,
            vad_filter=True,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not transcribe audio. Please try again.",
        ) from exc
    finally:
        Path(temp_path).unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No speech was detected in the recording")

    return transcript
