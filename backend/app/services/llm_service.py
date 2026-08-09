from __future__ import annotations

import asyncio
import http.client
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from app.core.config import settings


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)
logger = logging.getLogger(__name__)
_gemini_key_cooldowns: dict[str, float] = {}
_gemini_key_disabled: set[str] = set()

DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are Burmese Proverbs Hub, a Myanmar Proverbs Educational Assistant.

Strict rules:
1. Use ONLY the retrieved Myanmar Proverbs dataset context.
2. Do not use Gemini's own knowledge about Myanmar proverbs.
3. Do not generate new proverbs, guess missing meanings, or modify existing proverbs.
4. Gemini explains. Dataset provides knowledge.
5. If the context is empty or not relevant, return exactly:
ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။
6. Stay focused on Myanmar traditional proverbs only.
""".strip()

_llms: dict[str, ChatOllama] = {}


def get_llm(model: str | None = None) -> ChatOllama:
    """Return a shared ChatOllama singleton for the requested model."""

    model_name = (model or settings.utility_model).strip()
    if not model_name:
        raise RuntimeError("OLLAMA_MODEL must not be empty")
    if model_name == settings.embedding_model.strip():
        raise RuntimeError("Embedding model must not be used for chat generation")

    if model_name not in _llms:
        is_chat_model = model_name == settings.chat_model
        num_predict = settings.chat_num_predict if is_chat_model else settings.utility_num_predict
        num_ctx = settings.chat_num_ctx if is_chat_model else settings.utility_num_ctx
        temperature = settings.chat_temperature if is_chat_model else settings.utility_temperature
        _llms[model_name] = ChatOllama(
            model=model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
        )
    return _llms[model_name]


def get_chat_llm() -> ChatOllama:
    return get_llm(settings.chat_model)


def get_utility_llm() -> ChatOllama:
    return get_llm(settings.utility_model)


def configure_llm() -> None:
    """Eagerly initialize the chat model."""

    get_utility_llm()
    if not _use_gemini_chat():
        get_chat_llm()


def generate_answer(prompt: str, *, system_instruction: str | None = None) -> str:
    return generate_utility_response(prompt, system_instruction=system_instruction)


def generate_chat_response(prompt: str, *, system_instruction: str | None = None) -> str:
    instruction = system_instruction or DATASET_ONLY_SYSTEM_INSTRUCTION
    if _use_gemini_chat():
        return _invoke_gemini_text(prompt, system_instruction=instruction)
    return invoke_text(prompt, system_instruction=instruction, model=settings.chat_model)


def generate_utility_response(
    prompt: str,
    *,
    system_instruction: str | None = None,
    reasoning: bool | None = None,
) -> str:
    return invoke_text(
        prompt,
        system_instruction=system_instruction,
        model=settings.utility_model,
        reasoning=reasoning,
    )


async def agenerate_chat_response(prompt: str, *, system_instruction: str | None = None) -> str:
    instruction = system_instruction or DATASET_ONLY_SYSTEM_INSTRUCTION
    if _use_gemini_chat():
        return await asyncio.to_thread(_invoke_gemini_text, prompt, system_instruction=instruction)
    return await ainvoke_text(prompt, system_instruction=instruction, model=settings.chat_model)


async def agenerate_utility_response(prompt: str, *, system_instruction: str | None = None) -> str:
    return await ainvoke_text(prompt, system_instruction=system_instruction, model=settings.utility_model)


def invoke_text(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    reasoning: bool | None = None,
) -> str:
    """Invoke ChatOllama and return plain text."""

    messages: list[SystemMessage | HumanMessage] = []
    if system_instruction:
        messages.append(SystemMessage(content=system_instruction))
    messages.append(HumanMessage(content=prompt))

    selected_model = (model or settings.utility_model).strip()
    started_at = time.perf_counter()
    invoke_options = {"reasoning": reasoning} if reasoning is not None else {}
    response = get_llm(selected_model).invoke(messages, **invoke_options)
    return _response_text(response, selected_model, started_at)


async def ainvoke_text(prompt: str, *, system_instruction: str | None = None, model: str | None = None) -> str:
    """Async invoke ChatOllama and return plain text."""

    messages: list[SystemMessage | HumanMessage] = []
    if system_instruction:
        messages.append(SystemMessage(content=system_instruction))
    messages.append(HumanMessage(content=prompt))

    selected_model = (model or settings.utility_model).strip()
    started_at = time.perf_counter()
    response = await get_llm(selected_model).ainvoke(messages)
    return _response_text(response, selected_model, started_at)


def _response_text(response: Any, model: str, started_at: float) -> str:
    content = response.content
    if isinstance(content, str):
        text = _strip_thinking(content).strip()
    else:
        text = _strip_thinking(str(content)).strip()

    usage = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    prompt_tokens = usage.get("input_tokens") or response_metadata.get("prompt_eval_count")
    logger.info(
        "Ollama inference | Model: %s | Time: %.1f ms | Prompt Tokens: %s | Response Length: %s",
        model,
        (time.perf_counter() - started_at) * 1000,
        prompt_tokens,
        len(text),
    )
    return text


def _use_gemini_chat() -> bool:
    return settings.chat_provider.strip().lower() == "gemini"


def _invoke_gemini_text(prompt: str, *, system_instruction: str | None = None) -> str:
    api_keys = _available_gemini_api_keys()
    if not api_keys:
        configured_count = len(_gemini_api_keys())
        if configured_count:
            raise RuntimeError("All configured Gemini API keys are currently unavailable or cooling down.")
        raise RuntimeError("Gemini API key is not configured. Set GEMINI_API_KEY or GEMINI_API_KEYS in backend/.env.")

    models = _gemini_chat_models()
    if not models:
        raise RuntimeError("GEMINI_CHAT_MODEL must not be empty.")

    started_at = time.perf_counter()
    body = json.dumps(_gemini_text_request_body(prompt, system_instruction)).encode("utf-8")
    errors: list[str] = []
    raw = ""
    selected_model = models[0]
    succeeded = False

    for model_index, model in enumerate(models, start=1):
        model_path = urllib.parse.quote(model, safe="")
        url = f"{settings.gemini_chat_base_url.rstrip('/')}/models/{model_path}:generateContent"
        model_at_capacity = False
        model_unavailable = False
        for key_index, api_key in enumerate(api_keys, start=1):
            for attempt in range(settings.gemini_chat_max_retries + 1):
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Accept": "application/json", "Content-Type": "application/json", "X-goog-api-key": api_key},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=settings.gemini_chat_timeout_seconds) as response:
                        raw = response.read().decode("utf-8")
                    selected_model = model
                    succeeded = True
                    break
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")
                    message = f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} HTTP {exc.code}: {_gemini_error_message(detail)}"
                    errors.append(message)
                    _remember_gemini_key_failure(api_key, exc.code, detail)
                    if exc.code == 503 and attempt < settings.gemini_chat_max_retries:
                        delay = settings.gemini_chat_retry_base_seconds * (2 ** attempt)
                        logger.warning("Gemini chat is temporarily unavailable; retrying %s in %.1fs.", message, delay)
                        time.sleep(delay)
                        continue
                    if exc.code == 503:
                        model_at_capacity = True
                    if exc.code == 404 or (exc.code == 429 and "quota exceeded for metric" in detail.lower()):
                        model_unavailable = True
                    break
                except urllib.error.URLError as exc:
                    errors.append(f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} network error: {getattr(exc, 'reason', exc)}")
                    _cooldown_gemini_key(api_key, 30.0)
                    break
                except http.client.RemoteDisconnected as exc:
                    errors.append(f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} network error: {exc}")
                    _cooldown_gemini_key(api_key, 30.0)
                    break
                except TimeoutError:
                    errors.append(f"model {model_index}/{len(models)} key {key_index}/{len(api_keys)} timeout")
                    _cooldown_gemini_key(api_key, 30.0)
                    break
            if succeeded or model_at_capacity or model_unavailable:
                break
        if succeeded:
            break
        if model_index < len(models):
            logger.warning("Gemini chat model %s failed; trying fallback model %s.", model, models[model_index])

    if not succeeded:
        raise RuntimeError(f"Gemini chat failed for all configured API keys. Details: {'; '.join(errors)}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini chat returned invalid JSON.") from exc

    text = _extract_gemini_text(data)
    logger.info(
        "Gemini chat inference | Model: %s | Time: %.1f ms | Response Length: %s",
        selected_model,
        (time.perf_counter() - started_at) * 1000,
        len(text),
    )
    return text


def _gemini_chat_models() -> list[str]:
    models: list[str] = []
    for configured in (settings.gemini_chat_model, settings.gemini_chat_fallback_model):
        model = configured.strip()
        if model and model not in models:
            models.append(model)
    return models


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

    # A 503 is model capacity pressure; another model is useful, another key is not.
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


def _gemini_text_request_body(prompt: str, system_instruction: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    return body


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

    text = _strip_thinking("\n".join(text_parts)).strip()
    if text:
        return text

    prompt_feedback = data.get("promptFeedback", {})
    blocked_reason = prompt_feedback.get("blockReason") if isinstance(prompt_feedback, dict) else None
    if blocked_reason:
        raise RuntimeError(f"Gemini blocked the chat prompt: {blocked_reason}")
    raise RuntimeError("Gemini chat completed but did not return text.")


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


def invoke_chain(chain, inputs: dict[str, Any]) -> str:
    """Run a LangChain runnable and return plain text."""

    result = chain.invoke(inputs)
    if isinstance(result, str):
        return _strip_thinking(result).strip()
    return _strip_thinking(str(result)).strip()


def get_str_output_parser() -> StrOutputParser:
    return StrOutputParser()


def safe_json_from_llm(text: str) -> dict[str, Any]:
    cleaned = _strip_thinking(text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return JSON")

    return json.loads(cleaned[start : end + 1])


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)
