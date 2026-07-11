from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.utils.audio_utils import cleanup_audio_paths, preprocess_audio_with_ffmpeg

logger = logging.getLogger(__name__)

_model = None


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


def get_whisper_model():
    global _model
    if _model is not None:
        return _model

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

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
    _model = WhisperModel(settings.whisper_model, device=device, compute_type=compute_type)
    return _model


def transcribe_speech(
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    wav_path = preprocess_audio_with_ffmpeg(audio_bytes, filename, content_type)
    try:
        model = get_whisper_model()
        segments, info = model.transcribe(
            str(wav_path),
            language=None,
            beam_size=settings.whisper_beam_size,
            best_of=1,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": settings.whisper_vad_silence_ms},
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
        language = getattr(info, "language", None) or "unknown"
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

    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No speech was detected in the recording")

    return {"success": True, "text": text, "language": language}
