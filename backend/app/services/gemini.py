from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_QUOTA_HTTP_CODES = {403, 429}
_QUOTA_HINTS = (
    "quota",
    "rate limit",
    "rate_limit",
    "resource_exhausted",
    "resource has been exhausted",
    "billing",
    "exceeded",
)


class GeminiQuotaError(RuntimeError):
    """Raised when a Gemini API key hits quota or rate limits."""


class GeminiKeyRotator:
    def __init__(self) -> None:
        self._preferred_index = 0

    def keys_in_try_order(self) -> list[str]:
        keys = settings.gemini_api_keys_list()
        if not keys:
            return []
        return [keys[(self._preferred_index + offset) % len(keys)] for offset in range(len(keys))]

    def remember_success(self, api_key: str) -> None:
        keys = settings.gemini_api_keys_list()
        if api_key in keys:
            self._preferred_index = keys.index(api_key)


_key_rotator = GeminiKeyRotator()


def validate_gemini_config() -> None:
    keys = settings.gemini_api_keys_list()
    if not keys:
        raise RuntimeError("GEMINI_API_KEYS must contain at least one API key")
    if not settings.gemini_model.strip():
        raise RuntimeError("GEMINI_MODEL must not be empty")


def _is_quota_error(http_code: int, payload: dict[str, Any]) -> bool:
    if http_code in _QUOTA_HTTP_CODES:
        return True

    error = payload.get("error")
    if not isinstance(error, dict):
        return False

    status = str(error.get("status", "")).lower()
    message = str(error.get("message", "")).lower()
    if status == "resource_exhausted":
        return True
    return any(hint in message for hint in _QUOTA_HINTS)


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini returned no candidates")

    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        raise RuntimeError("Gemini returned empty content")

    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text_parts.append(str(part["text"]))

    text = "\n".join(text_parts).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")
    return _strip_thinking(text)


def _call_gemini(api_key: str, prompt: str, system_instruction: str | None) -> str:
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": settings.gemini_temperature,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    request = Request(
        (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={api_key}"
        ),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings.gemini_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": {"message": raw}}

        if _is_quota_error(exc.code, payload):
            message = payload.get("error", {}).get("message", raw)
            raise GeminiQuotaError(str(message)) from exc
        message = payload.get("error", {}).get("message", raw)
        raise RuntimeError(f"Gemini generation failed: {message}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini generation failed") from exc

    if "error" in payload:
        if _is_quota_error(0, payload):
            message = payload.get("error", {}).get("message", "Gemini quota exceeded")
            raise GeminiQuotaError(str(message))
        message = payload.get("error", {}).get("message", "Gemini generation failed")
        raise RuntimeError(str(message))

    return _extract_text(payload)


def generate_gemini_text(prompt: str, *, system_instruction: str | None = None) -> str:
    keys = _key_rotator.keys_in_try_order()
    if not keys:
        raise RuntimeError("No Gemini API keys configured")

    last_quota_error: GeminiQuotaError | None = None
    for index, api_key in enumerate(keys, start=1):
        try:
            text = _call_gemini(api_key, prompt, system_instruction)
            _key_rotator.remember_success(api_key)
            if index > 1:
                logger.info("Gemini request succeeded after rotating to key %s/%s", index, len(keys))
            return text
        except GeminiQuotaError as exc:
            last_quota_error = exc
            logger.warning("Gemini key %s/%s hit quota or rate limit; trying next key", index, len(keys))
            continue

    raise RuntimeError("All Gemini API keys are exhausted or rate limited") from last_quota_error


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)
