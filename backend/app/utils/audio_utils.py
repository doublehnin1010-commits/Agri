from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".mp4"}
SUPPORTED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/aac",
    "audio/x-m4a",
    "audio/ogg",
    "video/webm",
    "video/mp4",
}


def validate_audio_upload(filename: str | None, content_type: str | None, size_bytes: int) -> str:
    max_bytes = settings.speech_max_upload_mb * 1024 * 1024
    if size_bytes <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio upload is too large. Maximum size is {settings.speech_max_upload_mb} MB.",
        )

    suffix = Path(filename or "recording.webm").suffix.lower() or ".webm"
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(extension.lstrip(".") for extension in SUPPORTED_AUDIO_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Supported formats: {supported}.",
        )

    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_content_type and normalized_content_type not in SUPPORTED_AUDIO_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio MIME type.",
        )

    return suffix


def preprocess_audio_with_ffmpeg(audio_bytes: bytes, filename: str | None, content_type: str | None) -> Path:
    suffix = validate_audio_upload(filename, content_type, len(audio_bytes))
    configured_path = settings.ffmpeg_path.strip() or "ffmpeg"
    ffmpeg_path = configured_path if os.path.isfile(configured_path) else shutil.which(configured_path)
    if not ffmpeg_path:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "FFmpeg is not available on the server. Install FFmpeg and add it to PATH, "
                "or set FFMPEG_PATH to the full ffmpeg executable path."
            ),
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="speech_"))
    input_path = temp_dir / f"input_{uuid4().hex}{suffix}"
    output_path = temp_dir / "output.wav"
    input_path.write_bytes(audio_bytes)

    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.ffmpeg_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        cleanup_audio_paths(temp_dir)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Audio preprocessing timed out. Please try a shorter recording.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        cleanup_audio_paths(temp_dir)
        logger.warning("FFmpeg failed: %s", exc.stderr.strip())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process this audio file. Please try again.",
        ) from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        cleanup_audio_paths(temp_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio preprocessing produced no usable audio.",
        )

    return output_path


def cleanup_audio_paths(path: Path | str) -> None:
    target = Path(path)
    try:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            target.unlink(missing_ok=True)
            parent = target.parent
            if parent.name.startswith("speech_"):
                shutil.rmtree(parent, ignore_errors=True)
    except Exception:
        logger.exception("Failed to clean temporary audio path %s", target)
