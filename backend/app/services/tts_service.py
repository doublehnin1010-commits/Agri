from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.core.config import settings


_MYANMAR_TEXT_RE = re.compile(r"[\u1000-\u109f]")


def _select_voice(text: str, language: str | None) -> str:
    requested_language = (language or "").strip().lower()
    if requested_language.startswith("my") or _MYANMAR_TEXT_RE.search(text):
        return settings.edge_tts_myanmar_voice
    return settings.edge_tts_english_voice


async def synthesize_speech(text: str, language: str | None = None) -> bytes:
    normalized_text = " ".join(text.split()).strip()
    if not normalized_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text is required for speech synthesis.",
        )
    if len(normalized_text) > settings.tts_max_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"TTS text must be at most {settings.tts_max_characters} characters.",
        )

    try:
        import edge_tts
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Edge TTS is not installed. Run: pip install edge-tts",
        ) from exc

    audio = bytearray()
    try:
        communicate = edge_tts.Communicate(
            normalized_text,
            _select_voice(normalized_text, language),
            rate=settings.edge_tts_rate,
        )
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                audio.extend(chunk["data"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Edge TTS could not synthesize speech. Check the internet connection and voice name.",
        ) from exc

    if not audio:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Edge TTS returned no audio.",
        )
    return bytes(audio)
