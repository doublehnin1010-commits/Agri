import io
from unittest.mock import patch
import urllib.error

from app.services import llm_service


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}'


def test_gemini_api_keys_supports_comma_separated_rotation():
    with (
        patch("app.services.llm_service.settings.gemini_api_keys", " key-a, key-b ; key-a "),
        patch("app.services.llm_service.settings.gemini_api_key", "key-c"),
    ):
        assert llm_service._gemini_api_keys() == ["key-a", "key-b", "key-c"]


def test_gemini_text_rotates_to_next_key_after_rate_limit():
    llm_service._gemini_key_cooldowns.clear()
    llm_service._gemini_key_disabled.clear()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.headers["X-goog-api-key"])
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {},
                io.BytesIO(b'{"error":{"message":"quota exceeded"}}'),
            )
        return _FakeResponse()

    with (
        patch("app.services.llm_service.settings.gemini_api_keys", "key-a,key-b"),
        patch("app.services.llm_service.settings.gemini_api_key", ""),
        patch("app.services.llm_service.settings.gemini_chat_model", "gemini-test"),
        patch("urllib.request.urlopen", side_effect=fake_urlopen),
    ):
        assert llm_service._invoke_gemini_text("hello") == "ok"

    assert calls == ["key-a", "key-b"]


def test_gemini_skips_keys_that_are_cooling_down_or_disabled():
    llm_service._gemini_key_cooldowns.clear()
    llm_service._gemini_key_disabled.clear()
    llm_service._cooldown_gemini_key("key-a", 60)
    llm_service._gemini_key_disabled.add("key-b")

    with (
        patch("app.services.llm_service.settings.gemini_api_keys", "key-a,key-b,key-c"),
        patch("app.services.llm_service.settings.gemini_api_key", ""),
    ):
        assert llm_service._available_gemini_api_keys() == ["key-c"]

    llm_service._gemini_key_cooldowns.clear()
    llm_service._gemini_key_disabled.clear()


def test_gemini_disables_location_unsupported_key():
    llm_service._gemini_key_cooldowns.clear()
    llm_service._gemini_key_disabled.clear()

    llm_service._remember_gemini_key_failure(
        "key-a",
        400,
        '{"error":{"message":"User location is not supported for the API use."}}',
    )

    assert "key-a" in llm_service._gemini_key_disabled
    llm_service._gemini_key_disabled.clear()


def test_gemini_text_uses_fallback_model_after_503():
    llm_service._gemini_key_cooldowns.clear()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if "primary-model" in request.full_url:
            raise urllib.error.HTTPError(
                request.full_url,
                503,
                "Unavailable",
                {},
                io.BytesIO(b'{"error":{"message":"high demand"}}'),
            )
        return _FakeResponse()

    with (
        patch("app.services.llm_service.settings.gemini_api_keys", "key-a,key-b"),
        patch("app.services.llm_service.settings.gemini_api_key", ""),
        patch("app.services.llm_service.settings.gemini_chat_model", "primary-model"),
        patch("app.services.llm_service.settings.gemini_chat_fallback_model", "fallback-model"),
        patch("app.services.llm_service.settings.gemini_chat_max_retries", 0),
        patch("urllib.request.urlopen", side_effect=fake_urlopen),
    ):
        assert llm_service._invoke_gemini_text("hello") == "ok"

    assert len(calls) == 2
    assert "primary-model" in calls[0]
    assert "fallback-model" in calls[1]
