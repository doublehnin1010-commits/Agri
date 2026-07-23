import base64
import io
import urllib.error

import pytest
from fastapi import HTTPException

from app.services import speech_service


MYANMAR_TEXT = "\u1005\u1000\u102c\u1038\u1015\u102f\u1036"


def test_gemini_audio_request_body_contains_prompt_and_inline_wav():
    body = speech_service._gemini_audio_request_body(b"wav-bytes")
    parts = body["contents"][0]["parts"]

    assert "Transcribe exactly what the speaker says" in parts[0]["text"]
    assert parts[1]["inlineData"]["mimeType"] == "audio/wav"
    assert base64.b64decode(parts[1]["inlineData"]["data"]) == b"wav-bytes"
    assert body["generationConfig"]["temperature"] == 0


def test_extract_gemini_text_returns_plain_text():
    data = {"candidates": [{"content": {"parts": [{"text": MYANMAR_TEXT}]}}]}

    assert speech_service._extract_gemini_text(data) == MYANMAR_TEXT


def test_extract_gemini_text_reports_blocked_prompt():
    data = {"promptFeedback": {"blockReason": "SAFETY"}}

    with pytest.raises(HTTPException) as exc:
        speech_service._extract_gemini_text(data)

    assert exc.value.status_code == 502
    assert "blocked" in exc.value.detail


def test_invalid_transcript_rejects_json_or_labels():
    assert speech_service._is_invalid_transcript('{"text": "hello"}')
    assert speech_service._is_invalid_transcript("Transcript: hello")
    assert not speech_service._is_invalid_transcript(MYANMAR_TEXT)


def test_gemini_stt_models_include_distinct_fallback(monkeypatch):
    monkeypatch.setattr(speech_service.settings, "gemini_stt_model", "primary-model")
    monkeypatch.setattr(speech_service.settings, "gemini_stt_fallback_model", "fallback-model")

    assert speech_service._gemini_stt_models() == ["primary-model", "fallback-model"]


def test_gemini_503_does_not_cool_down_api_key():
    api_key = "capacity-test-key"
    speech_service._gemini_key_cooldowns.pop(api_key, None)

    speech_service._remember_gemini_key_failure(api_key, 503, "high demand")

    assert api_key not in speech_service._gemini_key_cooldowns


def test_gemini_503_switches_models_without_rotating_keys(monkeypatch):
    calls: list[str] = []

    def overloaded(request, timeout):
        calls.append(request.full_url)
        payload = b'{"error":{"message":"high demand"}}'
        raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", {}, io.BytesIO(payload))

    monkeypatch.setattr(speech_service, "_available_gemini_api_keys", lambda: ["key-1", "key-2"])
    monkeypatch.setattr(speech_service.settings, "gemini_stt_model", "primary-model")
    monkeypatch.setattr(speech_service.settings, "gemini_stt_fallback_model", "fallback-model")
    monkeypatch.setattr(speech_service.settings, "gemini_stt_max_retries", 0)
    monkeypatch.setattr(speech_service.urllib.request, "urlopen", overloaded)

    with pytest.raises(HTTPException) as exc:
        speech_service._invoke_gemini_audio_transcription(b"wav-bytes")

    assert exc.value.status_code == 503
    assert len(calls) == 2
    assert "primary-model" in calls[0]
    assert "fallback-model" in calls[1]
