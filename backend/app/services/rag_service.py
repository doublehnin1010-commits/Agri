from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app.core.config import settings
from app.services.llm_service import (
    agenerate_chat_response,
    agenerate_utility_response,
    generate_chat_response,
    generate_utility_response,
    get_llm,
    get_chat_llm,
    get_str_output_parser,
    safe_json_from_llm,
)
from app.services.retriever_service import get_retriever


logger = logging.getLogger(__name__)


INTENT_CLASSIFIER_SYSTEM_INSTRUCTION = """
You classify intent for Myanmar Proverbs AI Tutor.

Return JSON only. Do not answer the user.
Use semantic understanding instead of exact phrase matching.

Valid intents:

- greeting:
  The user greets the assistant.
  Examples:
  "မင်္ဂလာပါ"
  "Hello"
  "Hi"

- role:
  The user asks who the assistant is, what the system does, or what it can help with.
  Examples:
  "မင်းဘယ်သူလဲ"
  "What can you do?"
  "ဒီ system ကဘာလဲ"

- proverb_question:
  The user asks for a proverb, the meaning of a proverb, an explanation, or a proverb related to a situation, feeling, topic, or event.
  Examples:
  "ငါးနဲ့ပတ်သက်တဲ့ စကားပုံ"
  "ဦးလှကို လူတွေက ကဲ့ရဲ့နေကြတယ်"
  "ဒီအခြေအနေနဲ့ လိုက်ဖက်တဲ့ စကားပုံရှိလား"
  "ချီးမွမ်း ခုနှစ်ရက် ကဲ့ရဲ့ ခုနှစ်ရက် ဆိုတာဘာလဲ"

- proverb_only:
  The user wants only the proverb without any explanation.
  Examples:
  "စကားပုံပဲပြော"
  "Only proverb"
  "Which proverb fits?"

- proverb_list:
  The user asks for multiple proverbs related to a topic, concept, person, value, category, or keyword.
  Include a topic field.
  Examples:
  "Show me proverbs about teachers." -> {"intent":"proverb_list","topic":"teacher"}
  "Tell me proverbs related to education." -> {"intent":"proverb_list","topic":"education"}
  "Give me proverbs about honesty." -> {"intent":"proverb_list","topic":"honesty"}

- proverb_detail:
  The user refers to one proverb from a previously returned proverb list.
  Include a selection field.
  Examples:
  "Explain number 2." -> {"intent":"proverb_detail","selection":"2"}
  "Tell me about the first proverb." -> {"intent":"proverb_detail","selection":"1"}
  "Explain this proverb." -> {"intent":"proverb_detail","selection":"current"}

- translate_previous_to_myanmar:
  The user asks to translate or explain the previous answer in Myanmar/Burmese.
  Examples:
  "မြန်မာလိုပြန်ရှင်းပေး"
  "Translate to Burmese"

- translate_previous_to_english:
  The user asks to translate or explain the previous answer in English.
  Examples:
  "Explain in English"
  "Translate to English"

- thanks:
  The user expresses gratitude.
  Examples:
  "ကျေးဇူးတင်ပါတယ်"
  "Thanks"
  "Thank you"

- goodbye:
  The user ends the conversation.
  Examples:
  "Bye"
  "Goodbye"
  "နောက်မှတွေ့မယ်"

- unrelated:
  The user's request is not related to Myanmar proverbs.
  Examples:
  "Write Python code"
  "What is cloud computing?"
  "Solve this math problem"

Valid languages:

- my:
  The response should be in Myanmar/Burmese.

- en:
  The response should be in English.

Output format:

For proverb_list:
{
    "intent": "proverb_list",
    "topic": "..."
}

For proverb_detail:
{
    "intent": "proverb_detail",
    "selection": "..."
}

For all other intents:
{
    "intent": "<intent>",
    "language": "<my|en>"
}

Only return valid JSON.
Do not include markdown.
Do not answer the user's question.
""".strip()

DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are Burmese Proverbs Hub, a Myanmar Proverbs Educational Assistant.

Strict rules:
1. Your ONLY knowledge source is the retrieved Myanmar Proverbs dataset context.
2. All Myanmar proverbs, meanings, explanations, and lessons MUST come ONLY from the provided dataset.
3. Do not use Gemini's own knowledge about Myanmar proverbs.
4. Do not generate new proverbs. Do not guess missing meanings. Do not modify existing proverbs.
5. Gemini is only responsible for explaining and presenting retrieved information clearly.
6. If the requested proverb or information cannot be found in the provided dataset, return this exact Myanmar sentence:
ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။
7. This chatbot is designed only for Myanmar traditional proverbs.
8. Explain like a teacher teaching a student. Use simple Myanmar language.
""".strip()

ANSWER_PROMPT_EN = ChatPromptTemplate.from_messages(
    [
        ("system", DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """You are a Myanmar Proverbs AI Tutor.

Use ONLY the retrieved dataset context below.
Never use outside knowledge, general facts, programming, science, history, politics, or any topic outside Myanmar proverbs.
Never guess or invent proverbs or meanings.
If there is no exact proverb match, choose the closest meaning from the context only.
Return the best matching proverb with a warm, natural English explanation.
Explain like a kind teacher answering children.
Do not copy the source meaning word-for-word.
The meaning_simple_mm value must start with "In simple words," or "This proverb means".
Use simple, friendly language and 1-2 short sentences.
If the context does not contain a relevant proverb, return null for proverb and the standard not-found message.

Context:
{context}

User Question:
{question}

Answer in English only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

ANSWER_PROMPT_MY = ChatPromptTemplate.from_messages(
    [
        ("system", DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """You are a Myanmar Proverbs AI Tutor.

Use ONLY the retrieved dataset context below.
Never use outside knowledge, general facts, programming, science, history, politics, or any topic outside Myanmar proverbs.
Never guess or invent proverbs or meanings.
If there is no exact proverb match, choose the closest meaning from the context only.
Return the best matching proverb with a warm, natural Burmese explanation.
Explain like a kind teacher answering children.
Do not copy the source meaning word-for-word.
The meaning_simple_mm value must start with "ကလေးတို့ရေ၊" or "ဆိုလိုတာက".
Use simple, friendly language and 1-2 short sentences.
If the context does not contain a relevant proverb, return null for proverb and the standard not-found message.

Context:
{context}

User Question:
{question}

Answer in Burmese only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

FAST_DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are Burmese Proverbs Hub, a Myanmar Proverbs Educational Assistant.
Use only the provided Myanmar Proverbs dataset context.
Gemini explains. Dataset provides knowledge. Never reverse this relationship.
Do not use outside knowledge. Do not invent proverbs or meanings. Do not modify existing proverbs.
If no relevant context exists, return null for proverb and the exact not-found message:
ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။
Return JSON only. If context is empty or irrelevant, set proverb to null.
""".strip()

ANSWER_PROMPT_EN = ChatPromptTemplate.from_messages(
    [
        ("system", FAST_DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """Context JSON:
{context}

Question: {question}

Answer in English. Pick the best context item only. Use 1-2 short teacher-friendly sentences.
meaning_simple_mm must start with "In simple words," or "This proverb means".
Return exactly this JSON:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

ANSWER_PROMPT_MY = ChatPromptTemplate.from_messages(
    [
        ("system", FAST_DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """Context JSON:
{context}

Question: {question}

Answer in simple Burmese. Pick the best context item only.
meaning_simple_mm must contain three labeled sections exactly:
အဓိပ္ပါယ်:
သင်ခန်းစာ:
ဥပမာ:
The meaning and lesson must be based only on the selected context item's meaning.
The example must be based on the selected context item's meaning or stored example.
Return exactly this JSON:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

_rag_chain = None
_answer_chains: dict[tuple[str, str], Any] = {}

def _format_sources_as_context(sources: list[dict[str, Any]]) -> str:
    context_items = []
    for index, source in enumerate(sources[: settings.rag_top_k], start=1):
        context_items.append(
            {
                "id": index,
                "proverb": source.get("proverb"),
                "meaning": source.get("meaning"),
                "english_meaning": source.get("english_meaning"),
                "example": source.get("example"),
            }
        )
    return json.dumps(context_items, ensure_ascii=False, separators=(",", ":"))


def _select_answer_prompt(language: str) -> ChatPromptTemplate:
    return ANSWER_PROMPT_EN if language == "en" else ANSWER_PROMPT_MY


def _documents_to_sources(documents: list[Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for doc in documents:
        metadata = doc.metadata or {}
        sources.append(
            {
                "keyword": metadata.get("keyword"),
                "keywords": metadata.get("keywords"),
                "category": metadata.get("category"),
                "proverb": metadata.get("proverb"),
                "meaning": metadata.get("meaning"),
                "english_meaning": metadata.get("english_meaning"),
                "example": metadata.get("example"),
                "score": metadata.get("score"),
                "similarity": metadata.get("similarity"),
            }
        )
    return sources


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def select_chat_model(question: str, *, language: str = "my", intent: str | None = None) -> str:
    """Select the final answer model, favoring the fast model for low-latency chat."""

    if settings.fast_response_mode and settings.fast_chat_model.strip():
        return settings.fast_chat_model
    return settings.chat_model


def _get_answer_chain(language: str, model: str | None = None):
    model_name = model or settings.chat_model
    key = (language, model_name)
    if key not in _answer_chains:
        _answer_chains[key] = _select_answer_prompt(language) | get_llm(model_name) | get_str_output_parser()
    return _answer_chains[key]


def _render_answer_prompt(language: str, *, context: str, question: str) -> tuple[str | None, str]:
    messages = _select_answer_prompt(language).format_messages(context=context, question=question)
    system_parts: list[str] = []
    human_parts: list[str] = []
    for message in messages:
        content = str(message.content)
        if getattr(message, "type", "") == "system":
            system_parts.append(content)
        else:
            human_parts.append(content)
    system_instruction = "\n\n".join(system_parts).strip() or None
    prompt = "\n\n".join(human_parts).strip()
    return system_instruction, prompt


def _generate_answer_text(language: str, *, context: str, question: str, model: str) -> str:
    if settings.chat_provider.strip().lower() == "gemini":
        system_instruction, prompt = _render_answer_prompt(language, context=context, question=question)
        return generate_chat_response(prompt, system_instruction=system_instruction)
    return _get_answer_chain(language, model).invoke(
        {
            "context": context,
            "question": question,
        }
    )


async def _agenerate_answer_text(language: str, *, context: str, question: str, model: str) -> str:
    if settings.chat_provider.strip().lower() == "gemini":
        system_instruction, prompt = _render_answer_prompt(language, context=context, question=question)
        return await agenerate_chat_response(prompt, system_instruction=system_instruction)
    return await _get_answer_chain(language, model).ainvoke(
        {
            "context": context,
            "question": question,
        }
    )


def _build_rag_chain():
    retriever = get_retriever()

    def _prepare_generation_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
        question = inputs["question"]
        language = inputs.get("language") or "my"
        documents = retriever.invoke(question)
        sources = _documents_to_sources(documents)
        return {
            "question": question,
            "language": language,
            "sources": sources,
            "context": _format_sources_as_context(sources),
        }

    def _run_generation(inputs: dict[str, Any]) -> dict[str, Any]:
        model = select_chat_model(inputs["question"], language=inputs["language"])
        text = _generate_answer_text(
            inputs["language"],
            context=inputs["context"],
            question=inputs["question"],
            model=model,
        )
        return {
            "sources": inputs["sources"],
            "text": text,
        }

    return RunnablePassthrough() | RunnableLambda(_prepare_generation_inputs) | RunnableLambda(_run_generation)


def get_rag_chain():
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = _build_rag_chain()
    return _rag_chain


def run_rag_chain(question: str, language: str = "my") -> dict[str, Any]:
    """Run the LangChain RAG pipeline and return sources plus raw LLM text."""

    return asyncio.run(arun_rag_chain(question, language=language))


async def arun_rag_chain(question: str, language: str = "my") -> dict[str, Any]:
    """Async RAG pipeline using cached retriever and prompt chains."""

    total_start = time.perf_counter()
    retrieve_start = time.perf_counter()
    documents = await get_retriever().ainvoke(question)
    sources = _documents_to_sources(documents)
    retrieve_ms = _elapsed_ms(retrieve_start)

    generation_start = time.perf_counter()
    model = select_chat_model(question, language=language)
    text = await _agenerate_answer_text(
        language,
        context=_format_sources_as_context(sources),
        question=question,
        model=model,
    )
    generation_ms = _elapsed_ms(generation_start)
    logger.info(
        "RAG timing | Model: %s | Retrieval: %.1f ms | LLM Generation: %.1f ms | Total Request: %.1f ms",
        model,
        retrieve_ms,
        generation_ms,
        _elapsed_ms(total_start),
    )

    return {
        "sources": sources,
        "text": text,
    }


def parse_rag_answer(text: str) -> dict[str, Any]:
    return safe_json_from_llm(text)


def classify_intent(question: str) -> dict[str, Any]:
    prompt = f"""
Classify this user message for Myanmar Proverbs AI Tutor.

User message:
{question}

Return JSON exactly in this shape:
{{
  "intent": "role | translate_previous_to_myanmar | proverb_only | proverb_question | proverb_list | proverb_detail",
  "language": "my | en",
  "topic": "optional topic for proverb_list",
  "selection": "optional selection for proverb_detail"
}}
"""
    raw = generate_utility_response(prompt, system_instruction=INTENT_CLASSIFIER_SYSTEM_INSTRUCTION)
    return safe_json_from_llm(raw)


async def aclassify_intent(question: str) -> dict[str, Any]:
    prompt = f"""
Classify this user message for Myanmar Proverbs AI Tutor.

User message:
{question}

Return JSON exactly in this shape:
{{
  "intent": "role | translate_previous_to_myanmar | proverb_only | proverb_question | proverb_list | proverb_detail",
  "language": "my | en",
  "topic": "optional topic for proverb_list",
  "selection": "optional selection for proverb_detail"
}}
"""
    raw = await agenerate_utility_response(prompt, system_instruction=INTENT_CLASSIFIER_SYSTEM_INSTRUCTION)
    return safe_json_from_llm(raw)
