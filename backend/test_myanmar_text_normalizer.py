from unittest.mock import patch

from app.services.myanmar_text_normalizer import (
    _clear_normalization_cache,
    contains_myanmar_unicode,
    looks_like_romanized_myanmar,
    normalize_myanmar_text,
)


def setup_function() -> None:
    _clear_normalization_cache()


def test_myanmar_unicode_is_returned_without_llm_call() -> None:
    text = "ငါးမရ ရေချိုးပြန်"
    with patch("app.services.myanmar_text_normalizer.invoke_text") as generate:
        assert normalize_myanmar_text(text) == text
        generate.assert_not_called()


def test_normal_english_is_unchanged_without_llm_call() -> None:
    with patch("app.services.myanmar_text_normalizer.invoke_text") as generate:
        assert normalize_myanmar_text("hello world") == "hello world"
        generate.assert_not_called()


def test_known_romanized_myanmar_is_normalized_without_llm_call() -> None:
    with patch(
        "app.services.myanmar_text_normalizer.invoke_text",
    ) as invoke:
        assert normalize_myanmar_text("mì je taun ca pa le") == "ငါးမရ ရေချိုးပြန်"
        assert normalize_myanmar_text("mì je taun ca pa le") == "ငါးမရ ရေချိုးပြန်"
        invoke.assert_not_called()


def test_romanized_myanmar_is_normalized_and_cached() -> None:
    with patch(
        "app.services.myanmar_text_normalizer.invoke_text",
        return_value="နေကောင်းလား",
    ) as invoke:
        assert normalize_myanmar_text("nay kaung lar") == "နေကောင်းလား"
        assert normalize_myanmar_text("nay kaung lar") == "နေကောင်းလား"
        invoke.assert_called_once()


def test_common_ascii_phonetic_phrase_is_detected() -> None:
    assert looks_like_romanized_myanmar("mingalar par")
    assert not looks_like_romanized_myanmar("hello world")
    assert contains_myanmar_unicode("မင်္ဂလာပါ")


def test_low_confidence_model_output_falls_back_to_original() -> None:
    with patch(
        "app.services.myanmar_text_normalizer.invoke_text",
        return_value="This may mean hello",
    ):
        assert normalize_myanmar_text("nay kaung lar") == "nay kaung lar"
