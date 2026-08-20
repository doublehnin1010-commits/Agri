from __future__ import annotations

import logging
import json
import re
from typing import Any

from app.core.config import settings
from app.services.llm_service import (
    AGRICULTURE_SYSTEM_INSTRUCTION,
    agenerate_chat_response,
    agenerate_multimodal_response,
    safe_json_from_llm,
)
from app.services.retriever_service import aretrieve_context

logger = logging.getLogger(__name__)

OUT_OF_DOMAIN_MY = "ဒီစနစ်က စိုက်ပျိုးရေး၊ သီးနှံ၊ မြေဩဇာ၊ ရောဂါပိုးမွှား၊ ရေသွင်းရေထုတ် စတဲ့ မေးခွန်းများအတွက်သာ ဖြေကြားပေးပါတယ်။"
OUT_OF_DOMAIN_EN = "This assistant only answers agriculture, farming, crop, soil, fertilizer, irrigation, pest, and plant disease questions."
GEMINI_UNAVAILABLE_MY = "စိုက်ပျိုးရေးမေးခွန်းဖြစ်ပေမယ့် လက်ရှိ Gemini ဖြင့် အဖြေထုတ်ပေးရာမှာ ပြဿနာရှိနေပါတယ်။ ခဏကြာပြီး ပြန်မေးကြည့်ပါ။"
GEMINI_UNAVAILABLE_EN = "This is an agriculture question, but Gemini is currently unavailable. Please try again later."
IMAGE_NEEDS_BETTER_MY = "ပုံက အနည်းငယ်မရှင်းလင်းတဲ့အတွက် အတိအကျ ခန့်မှန်းပေးဖို့ ခက်ပါတယ်။\n\nထိခိုက်နေတဲ့ အရွက်/အပင်အစိတ်အပိုင်းကို ပိုနီးကပ်ပြီး ရှင်းလင်းတဲ့ပုံတစ်ပုံ ထပ်တင်ပေးပါ။"
IMAGE_NEEDS_BETTER_EN = "The image is not clear enough to make a useful estimate. Please upload a sharper, closer photo showing the affected plant part."
IMAGE_NOT_AGRICULTURE_MY = "ဒီပုံမှာ စိုက်ပျိုးရေးနှင့် သက်ဆိုင်သော အရာကို မတွေ့ရပါ။ အပင်၊ အရွက်၊ အသီး၊ မြေ သို့မဟုတ် ပိုးမွှားပုံကို တင်ပေးပါ။"
IMAGE_NOT_AGRICULTURE_EN = "I could not identify an agriculture-related subject in this image. Please upload a crop, leaf, fruit, soil, or pest photo."

AGRICULTURE_EN_TERMS = {
    "agriculture", "farming", "farm", "farmer", "crop", "crops", "rice", "paddy", "wheat", "corn", "maize",
    "bean", "beans", "pea", "peas", "sesame", "tomato", "potato", "onion", "vegetable", "fruit", "seed", "seeds",
    "soil", "fertilizer", "fertiliser", "compost", "manure", "nitrogen", "phosphorus", "potassium", "npk",
    "irrigation", "water", "watering", "drainage", "harvest", "harvesting", "cultivation", "planting", "sowing",
    "plant", "plants", "leaf", "leaves", "yellow", "disease", "pest", "insect", "fungus", "weed", "weeds",
    "herbicide", "pesticide", "fungicide", "nursery", "transplant", "yield", "organic", "mulch", "greenhouse",
}

AGRICULTURE_MY_TERMS = [
    "စိုက်ပျိုး", "စိုက်ခင်း", "လယ်", "ယာ", "တောင်သူ", "သီးနှံ", "စပါး", "ပဲ", "နှမ်း", "ပြောင်း", "ခရမ်းချဉ်",
    "ဟင်းသီးဟင်းရွက်", "အသီး", "မျိုးစေ့", "မြေ", "မြေဆီ", "မြေဩဇာ", "ဓာတ်မြေဩဇာ", "သဘာဝမြေဩဇာ",
    "ရေသွင်း", "ရေထုတ်", "ရေလောင်း", "ရိတ်သိမ်း", "ပျိုး", "စိုက်", "အပင်", "အရွက်", "အရွက်ဝါ", "ရောဂါ",
    "ပိုး", "ပိုးမွှား", "မှို", "ပေါင်း", "ပေါင်းသတ်", "ပိုးသတ်", "အထွက်နှုန်း", "စိုက်နည်း", "စိုက်ပျိုးနည်း",
]

OUT_OF_DOMAIN_EN_TERMS = {
    "html", "css", "javascript", "python", "programming", "code", "website", "football", "movie", "politics",
    "bank", "crypto", "recipe", "capital", "weather", "math", "physics", "phone", "computer", "windows",
}

OUT_OF_DOMAIN_MY_TERMS = ["ပရိုဂရမ်", "ကုဒ်", "ဝက်ဘ်ဆိုက်", "နိုင်ငံရေး", "ဘောလုံး", "ရုပ်ရှင်", "သင်္ချာ", "ကွန်ပျူတာ"]


def _language_from_question(question: str) -> str:
    myanmar_chars = len(re.findall(r"[\u1000-\u109F]", question or ""))
    latin_chars = len(re.findall(r"[A-Za-z]", question or ""))
    return "my" if myanmar_chars > latin_chars else "en"


def _is_agriculture_question(question: str) -> bool:
    normalized = (question or "").lower()
    words = set(re.findall(r"[a-z0-9]+", normalized))
    has_myanmar = bool(re.search(r"[\u1000-\u109F]", question or ""))
    has_agri = bool(words & AGRICULTURE_EN_TERMS) or any(term in question for term in AGRICULTURE_MY_TERMS)
    has_other = bool(words & OUT_OF_DOMAIN_EN_TERMS) or any(term in question for term in OUT_OF_DOMAIN_MY_TERMS)
    if has_other and not has_agri:
        return False
    if has_agri:
        return True
    if has_myanmar:
        return True
    return False


async def classify_user_intent(question: str) -> dict[str, Any]:
    language = _language_from_question(question)
    return {"intent": "agriculture_question" if _is_agriculture_question(question) else "out_of_domain", "language": language}


def _source_from_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": item.get("document_id"),
        "filename": item.get("filename") or item.get("source"),
        "file_type": item.get("file_type"),
        "chunk_id": item.get("chunk_id"),
        "page_number": item.get("page_number"),
        "source": item.get("source") or item.get("filename"),
        "score": item.get("score"),
        "similarity": item.get("similarity"),
        "preview": (item.get("content") or "")[:300],
    }


def _format_context(items: list[dict[str, Any]]) -> str:
    parts = []
    for index, item in enumerate(items, start=1):
        source = item.get("source") or item.get("filename") or "uploaded document"
        page = item.get("page_number")
        page_text = f", page {page}" if page else ""
        parts.append(f"[Source {index}: {source}{page_text}]\n{item.get('content') or ''}")
    return "\n\n".join(parts)


async def _gemini_agriculture_answer(user_question: str, language: str, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    context = _format_context(sources or [])
    if context:
        prompt = f"""
User question:
{user_question}

Retrieved agriculture document context:
{context}

Answer the agriculture question. Use the retrieved context first. If the context is weak or incomplete, you may add general agriculture knowledge, but clearly keep the answer practical and avoid pretending that unsupported details came from the uploaded documents. Return plain text.
""".strip()
    else:
        prompt = f"""
User question:
{user_question}

No relevant uploaded document context was found. This is still an agriculture question, so answer using general agriculture knowledge. Keep the answer practical, concise, and in the user's language. Return plain text.
""".strip()

    try:
        text = await agenerate_chat_response(prompt, system_instruction=AGRICULTURE_SYSTEM_INSTRUCTION)
    except Exception:
        logger.exception("Gemini agriculture fallback failed")
        return {"answer": GEMINI_UNAVAILABLE_MY if language == "my" else GEMINI_UNAVAILABLE_EN, "sources": [], "language": language, "error": "gemini_failed"}

    return {"answer": text.strip(), "sources": [_source_from_item(item) for item in (sources or [])], "language": language}


async def arag_answer(user_question: str, previous_answer: dict[str, Any] | None = None, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    language = _language_from_question(user_question)
    if not _is_agriculture_question(user_question):
        return {"answer": OUT_OF_DOMAIN_MY if language == "my" else OUT_OF_DOMAIN_EN, "sources": [], "language": language, "intent": "out_of_domain"}

    try:
        sources = await aretrieve_context(user_question, top_k=settings.rag_top_k)
    except Exception:
        logger.exception("RAG retrieval failed")
        sources = []

    return await _gemini_agriculture_answer(user_question, language, sources)


async def arag_image_answer(
    user_question: str,
    image_bytes: bytes,
    mime_type: str,
) -> dict[str, Any]:
    language = _language_from_question(user_question)
    analysis_prompt = f"""
Analyze this image for an agriculture question. The user's question is:
{user_question or "Please describe what you see in this agriculture image."}

Return JSON only with these fields:
{{
  "is_agriculture": true or false,
  "image_quality": "good" or "poor",
  "agriculture_subject": "crop, leaf, stem, fruit, flower, soil, insect, damage, or other",
  "visible_symptoms": ["short observable symptom"],
  "possible_causes": ["possible disease, pest, or non-disease cause"],
  "search_description": "concise searchable agriculture description"
}}

Only describe visible evidence. Do not claim a diagnosis is certain. Mark image_quality poor if it is dark, blurry, distant, or does not show the relevant area.
""".strip()
    try:
        analysis = safe_json_from_llm(
            await agenerate_multimodal_response(
                analysis_prompt,
                image_bytes,
                mime_type,
                system_instruction=AGRICULTURE_SYSTEM_INSTRUCTION,
            )
        )
    except Exception:
        logger.exception("Gemini image analysis failed")
        return {"answer": GEMINI_UNAVAILABLE_MY if language == "my" else GEMINI_UNAVAILABLE_EN, "sources": [], "language": language, "error": "gemini_failed"}

    if analysis.get("image_quality") == "poor":
        return {"answer": IMAGE_NEEDS_BETTER_MY if language == "my" else IMAGE_NEEDS_BETTER_EN, "sources": [], "language": language, "image_analysis": analysis}
    if not analysis.get("is_agriculture"):
        return {"answer": IMAGE_NOT_AGRICULTURE_MY if language == "my" else IMAGE_NOT_AGRICULTURE_EN, "sources": [], "language": language, "image_analysis": analysis}

    search_description = str(analysis.get("search_description") or " ".join(analysis.get("visible_symptoms") or [])).strip()
    retrieval_query = " ".join(part for part in [user_question, search_description] if part).strip()
    try:
        sources = await aretrieve_context(retrieval_query, top_k=settings.rag_top_k)
    except Exception:
        logger.exception("Image question RAG retrieval failed")
        sources = []

    context = _format_context(sources)
    final_prompt = f"""
User question:
{user_question or "Please explain what may be happening in this image."}

Image analysis based on visible evidence:
{json.dumps(analysis, ensure_ascii=False)}

Retrieved agriculture document context:
{context or "No relevant uploaded document context was found."}

Answer in the user's language. Use this structure when appropriate:
🔎 ဖြစ်နိုင်ခြေရှိသော အခြေအနေ
🌱 တွေ့ရတဲ့ လက္ခဏာများ
💡 လုပ်ဆောင်နိုင်တာများ
⚠️ သတိပြုရန်

Use phrases such as "ဖြစ်နိုင်ပါတယ်" or "ပုံအရ တွေ့ရတဲ့ လက္ခဏာများအရ". Never present image identification as certain. Ground treatment instructions in the retrieved documents; if relevant guidance is missing, say so clearly and do not invent treatment instructions. Keep the answer simple for farmers.
""".strip()
    try:
        text = await agenerate_multimodal_response(
            final_prompt,
            image_bytes,
            mime_type,
            system_instruction=AGRICULTURE_SYSTEM_INSTRUCTION,
        )
    except Exception:
        logger.exception("Gemini image agriculture answer failed")
        return {"answer": GEMINI_UNAVAILABLE_MY if language == "my" else GEMINI_UNAVAILABLE_EN, "sources": [], "language": language, "error": "gemini_failed"}

    return {
        "answer": text.strip(),
        "sources": [_source_from_item(item) for item in sources],
        "language": language,
        "image_analysis": analysis,
    }


def rag_answer(user_question: str, previous_answer: dict[str, Any] | None = None, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    import asyncio
    return asyncio.run(arag_answer(user_question, previous_answer=previous_answer, memory=memory))
