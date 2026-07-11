from __future__ import annotations

from app.services.speech_service import transcribe_speech


def transcribe_audio_bytes(audio_bytes: bytes, filename: str, _language: str | None = None) -> str:
    return transcribe_speech(audio_bytes, filename, None)["text"]
