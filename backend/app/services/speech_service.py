from __future__ import annotations

import base64
import json
import logging
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.utils.audio_utils import cleanup_audio_paths, preprocess_audio_with_ffmpeg


logger = logging.getLogger(__name__)

_EXCESSIVE_REPETITION_RE = re.compile(r"(.)\1{7,}")
_MYANMAR_CHARACTER_RE = re.compile(r"[\u1000-\u109f\uaa60-\uaa7f\ua9e0-\ua9ff]")
_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)
_gemini_key_cooldowns: dict[str, float] = {}
_gemini_key_disabled: set[str] = set()

GEMINI_STT_PROMPT = """
You are an advanced Speech-to-Text transcription engine for a Myanmar educational AI assistant.

Your task is to accurately transcribe the user's speech into text.

## Rules

1. Transcribe exactly what the speaker says.
2. Return ONLY the transcribed text.
3. Do NOT answer the user's question.
4. Do NOT explain, summarize, or translate.
5. Do NOT add punctuation that changes the meaning.
6. Preserve Myanmar Unicode correctly.
7. Never convert Myanmar words into Romanized text.
8. If the speaker uses both Myanmar and English, preserve both languages exactly as spoken.
9. If the speaker is asking about a Myanmar proverb, transcribe the proverb exactly.
10. Do not guess missing words. If a word is unclear, transcribe the remaining speech as accurately as possible.

## Educational Context

The audio is expected to contain:

* Myanmar proverbs
* Questions about proverb meanings
* Requests for explanations
* Requests for English meanings
* Requests for related proverbs
* Educational conversations

Common vocabulary includes:

* စကားပုံ
* အဓိပ္ပာယ်
* ရှင်းပြပါ
* ဥပမာ
* ဘာကိုဆိုလိုတာလဲ
* ဆက်စပ်စကားပုံ
* အင်္ဂလိပ်အဓိပ္ပာယ်
* သင်ခန်းစာ
* Generate Image
* Illustration

## Output Format

Return plain text only.

Never return JSON.
Never return Markdown.
Never return explanations.
Return only the transcription.
""".strip()


def _normalize_requested_language(language: str | None) -> str | None:
    requested = (language or "").strip().lower()
    return {
        "my-mm": "my",
        "myanmar": "my",
        "burmese": "my",
        "en-us": "en",
        "english": "en",
        "auto": "",
    }.get(requested, requested) or None


def _clean_transcript(text: str) -> str:
    cleaned = unicodedata.normalize("NFC", text).strip()
    cleaned = re.sub(r"^```(?:text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return " ".join(cleaned.split()).strip()


def _is_invalid_transcript(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\ufffd" in stripped or _EXCESSIVE_REPETITION_RE.search(stripped):
        return True
    if stripped.startswith("{") or stripped.startswith("["):
        return True
    if re.search(r"(?im)^\s*(transcription|transcript|output)\s*:", stripped):
        return True
    return False


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
    requested_language = _normalize_requested_language(language)
    try:
        wav_bytes = Path(wav_path).read_bytes()
        raw_text = _clean_transcript(_invoke_gemini_audio_transcription(wav_bytes))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gemini speech transcription failed")
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
        logger.warning("Rejected invalid Gemini STT output: %r", raw_text)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The speech was unclear. Please speak again slowly and closer to the microphone.",
        )
    if not _uses_expected_script(raw_text, requested_language):
        logger.warning("Rejected non-Myanmar script from Myanmar transcription: %r", raw_text)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recording was not recognized as Myanmar script. Please speak again clearly in Myanmar.",
        )

    detected_language = requested_language or "unknown"
    logger.info("Gemini STT output (%s): %s", detected_language, raw_text)
    return {"success": True, "text": raw_text, "language": detected_language}


def _invoke_gemini_audio_transcription(audio_bytes: bytes) -> str:
    api_keys = _available_gemini_api_keys()
    if not api_keys:
        configured_count = len(_gemini_api_keys())
        if configured_count:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="All configured Gemini API keys are currently unavailable or cooling down.",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured. Set GEMINI_API_KEY or GEMINI_API_KEYS in backend/.env.",
        )

    models = _gemini_stt_models()
    if not models:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_STT_MODEL must not be empty.",
        )

    started_at = time.perf_counter()
    body = json.dumps(_gemini_audio_request_body(audio_bytes)).encode("utf-8")
    if len(body) >= 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The processed audio is too large for Gemini inline transcription. Please record a shorter clip.",
        )
    errors: list[str] = []
    last_status_code = status.HTTP_502_BAD_GATEWAY

    raw = ""
    selected_model = models[0]
    succeeded = False
    for model_index, model in enumerate(models, start=1):
        model_path = urllib.parse.quote(model, safe="")
        url = f"{settings.gemini_chat_base_url.rstrip('/')}/models/{model_path}:generateContent"
        model_at_capacity = False
        model_unavailable = False
        for key_index, api_key in enumerate(api_keys, start=1):
            for attempt in range(settings.gemini_stt_max_retries + 1):
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Accept": "application/json", "Content-Type": "application/json", "X-goog-api-key": api_key},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=settings.gemini_stt_timeout_seconds) as response:
                        raw = response.read().decode("utf-8")
                    selected_model = model
                    succeeded = True
                    break
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")
                    last_status_code = exc.code
                    message = f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} HTTP {exc.code}: {_gemini_error_message(detail)}"
                    errors.append(message)
                    _remember_gemini_key_failure(api_key, exc.code, detail)
                    if exc.code == 503 and attempt < settings.gemini_stt_max_retries:
                        delay = settings.gemini_stt_retry_base_seconds * (2 ** attempt)
                        logger.warning("Gemini STT is temporarily unavailable; retrying %s in %.1fs.", message, delay)
                        time.sleep(delay)
                        continue
                    if exc.code == 503:
                        model_at_capacity = True
                    if exc.code == 404 or (exc.code == 429 and "quota exceeded for metric" in detail.lower()):
                        model_unavailable = True
                    break
                except urllib.error.URLError as exc:
                    last_status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                    errors.append(f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} network error: {getattr(exc, 'reason', exc)}")
                    _cooldown_gemini_key(api_key, 30.0)
                    break
                except TimeoutError:
                    last_status_code = status.HTTP_504_GATEWAY_TIMEOUT
                    errors.append(f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} timeout")
                    _cooldown_gemini_key(api_key, 30.0)
                    break
            if succeeded:
                break
            if model_at_capacity or model_unavailable:
                # Capacity, retirement, and project quota errors belong to the
                # model/project. Rotating keys only adds latency.
                break
        if succeeded:
            break
        if model_index < len(models):
            logger.warning(
                "Gemini STT model %s failed (%s); trying fallback model %s.",
                model,
                errors[-1] if errors else "unknown upstream error",
                models[model_index],
            )
    else:
        logger.error("Gemini STT failed for all models. %s", "; ".join(errors))
        if last_status_code in {401, 403}:
            detail = "Gemini rejected the configured API keys. Check that they are valid Gemini API keys with API access enabled."
        elif last_status_code == 429:
            detail = "Gemini transcription quota is exhausted. Please wait for quota reset or use a project with available quota."
        elif last_status_code == 400:
            detail = "Gemini rejected the audio transcription request. Check the server log for the upstream error."
        elif last_status_code == 404:
            detail = "The configured Gemini STT models are not available for this API project."
        else:
            detail = "Gemini STT is temporarily unavailable. Please try again shortly."
        raise HTTPException(
            status_code=last_status_code if last_status_code in {429, 503, 504} else status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini STT returned invalid JSON.",
        ) from exc

    text = _extract_gemini_text(data)
    logger.info(
        "Gemini STT inference | Model: %s | Time: %.1f ms | Response Length: %s",
        selected_model,
        (time.perf_counter() - started_at) * 1000,
        len(text),
    )
    return text


def _gemini_stt_models() -> list[str]:
    models: list[str] = []
    for configured in (settings.gemini_stt_model, settings.gemini_stt_fallback_model):
        model = configured.strip()
        if model and model not in models:
            models.append(model)
    return models


def _gemini_audio_request_body(audio_bytes: bytes) -> dict[str, Any]:
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": GEMINI_STT_PROMPT},
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": encoded_audio,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
        },
    }


def _extract_gemini_text(data: dict[str, Any]) -> str:
    text_parts: list[str] = []
    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        if text_parts:
            break

    text = "\n".join(text_parts).strip()
    if text:
        return text

    prompt_feedback = data.get("promptFeedback", {})
    blocked_reason = prompt_feedback.get("blockReason") if isinstance(prompt_feedback, dict) else None
    if blocked_reason:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini blocked the transcription prompt: {blocked_reason}",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Gemini STT completed but did not return text.",
    )


def _gemini_api_keys() -> list[str]:
    raw_values = [settings.gemini_api_keys, settings.gemini_api_key]
    keys: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for key in re.split(r"[\n,;]+", raw or ""):
            normalized = key.strip().strip('"').strip("'")
            if normalized and normalized not in seen:
                keys.append(normalized)
                seen.add(normalized)
    return keys


def _available_gemini_api_keys() -> list[str]:
    now = time.monotonic()
    keys: list[str] = []
    for key in _gemini_api_keys():
        if key in _gemini_key_disabled:
            continue
        cooldown_until = _gemini_key_cooldowns.get(key, 0.0)
        if cooldown_until > now:
            continue
        _gemini_key_cooldowns.pop(key, None)
        keys.append(key)
    return keys


def _remember_gemini_key_failure(api_key: str, status_code: int, detail: str) -> None:
    detail_lower = detail.lower()
    if status_code == 429:
        _cooldown_gemini_key(api_key, _retry_delay_seconds(detail) or 60.0)
        return

    if status_code == 400 and "user location is not supported" in detail_lower:
        _gemini_key_disabled.add(api_key)
        _gemini_key_cooldowns.pop(api_key, None)
        logger.warning("Disabled a Gemini API key for this server run because its location is not supported.")
        return

    # A 503 is model-level capacity pressure, so cooling down a key does not help.
    if status_code in {500, 502, 504, 408, 409}:
        _cooldown_gemini_key(api_key, 30.0)


def _cooldown_gemini_key(api_key: str, delay_seconds: float) -> None:
    delay = max(1.0, min(delay_seconds, 300.0))
    _gemini_key_cooldowns[api_key] = time.monotonic() + delay


def _retry_delay_seconds(detail: str) -> float | None:
    match = _RETRY_DELAY_RE.search(detail)
    if not match:
        return None
    try:
        return float(match.group(1)) + 1.0
    except ValueError:
        return None


def _should_try_next_gemini_key(status_code: int) -> bool:
    return status_code in {400, 401, 403, 408, 409, 429, 500, 502, 503, 504}


def _gemini_error_message(raw: str) -> str:
    try:
        data = json.loads(raw)
        error = data.get("error", {})
        message = error.get("message") if isinstance(error, dict) else None
        if isinstance(message, str) and message.strip():
            return message.strip()[:500]
    except json.JSONDecodeError:
        pass
    return raw.strip()[:500] or "No error details were returned."
