from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings
from app.db.chroma import get_vectorstore
from app.services.guardrails import (
    create_guardrailed_answer,
    create_no_result_answer,
    is_answer_valid,
    is_context_relevant,
    validate_question,
)
from app.services.rag_service import arun_rag_chain, parse_rag_answer
from app.services.retriever_service import (
    _compact_search_text,
    _normalize_search_text,
    aretrieve_context,
    invalidate_metadata_cache,
)


def _row_id(keyword: str | None, proverb: str) -> str:
    raw = f"{keyword or ''}||{proverb}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _normalize_row(row: dict[str, Any]) -> dict[str, str | None]:
    keyword = (row.get("keyword") or "").strip() or None
    proverb = (row.get("proverb") or "").strip()
    meaning = (row.get("meaning") or "").strip() or None
    example = (row.get("example") or "").strip() or None
    if not proverb:
        raise ValueError("proverb is required")
    return {"keyword": keyword, "proverb": proverb, "meaning": meaning, "example": example}


def _language_from_question(question: str) -> str:
    normalized = (question or "").strip()
    if not normalized:
        return "my"

    myanmar_chars = len(re.findall(r"[\u1000-\u109F]", normalized))
    latin_chars = len(re.findall(r"[A-Za-z]", normalized))

    if myanmar_chars > latin_chars:
        return "my"
    return "en"


def _classify_user_intent(question: str) -> dict[str, Any]:
    fallback = {
        "intent": "proverb_question",
        "language": _language_from_question(question),
    }
    if not question or not question.strip():
        return fallback

    builtin_intent = _infer_builtin_intent(question)
    if builtin_intent:
        return {
            "intent": builtin_intent,
            "language": fallback["language"],
        }

    return fallback


async def _aclassify_user_intent(question: str) -> dict[str, Any]:
    fallback = {
        "intent": "proverb_question",
        "language": _language_from_question(question),
    }
    if not question or not question.strip():
        return fallback

    builtin_intent = _infer_builtin_intent(question)
    if builtin_intent:
        return {
            "intent": builtin_intent,
            "language": fallback["language"],
        }

    return fallback


def _infer_builtin_intent(question: str) -> str | None:
    normalized = _normalize_search_text(question)
    compact = _compact_search_text(normalized)
    plain_compact = re.sub(r"\s+", "", unicodedata.normalize("NFC", normalized))

    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", normalized):
        return "greeting"

    if any(text in plain_compact for text in ["မင်္ဂလာပါ", "ဟယ်လို", "ဟိုင်း"]):
        return "greeting"

    if re.search(r"\b(who|what)\s+(are|r)\s+(you|u)\b", normalized):
        return "role"

    if re.search(r"\b(your|ur)\s+(role|job|purpose|name|capabilit(?:y|ies))\b", normalized):
        return "role"

    if re.search(r"\bwhat\s+(is|does)\s+(this\s+)?(system|app|application)\b", normalized):
        return "role"

    if re.search(r"\bhow\s+can\s+(you|u)\s+help\b", normalized):
        return "role"

    if any(
        text in plain_compact
        for text in [
            "မင်းဘယ်သူလဲ",
            "ဘယ်သူလဲ",
            "ဘာအလုပ်",
            "ဘာလုပ်နိုင်လဲ",
            "ဒီစနစ်ကဘာလဲ",
            "ဒီappကဘာလဲ",
            "ဒီapplicationကဘာလဲ",
        ]
    ):
        return "role"

    if re.search(r"\btranslate\b.*\b(burmese|myanmar)\b", normalized):
        return "translate_previous_to_myanmar"

    if any(text in plain_compact for text in ["မြန်မာလို", "မြန်မာလိုပြန်", "ဗမာလို", "ဗမာလိုပြန်"]):
        return "translate_previous_to_myanmar"

    if re.search(r"\btranslate\b.*\benglish\b", normalized):
        return "translate_previous_to_english"

    if any(text in normalized for text in ["english", "in english", "explain in english"]):
        return "translate_previous_to_english"

    if re.search(r"\b(thanks|thank you|thx|ty)\b", normalized):
        return "thanks"

    if any(text in plain_compact for text in ["ကျေးဇူး", "ကျေးဇူးတင်ပါတယ်", "ကျေးဇူးပါ"]):
        return "thanks"

    if re.search(r"\b(bye|goodbye|see you|see ya)\b", normalized):
        return "goodbye"

    if any(text in plain_compact for text in ["နောက်မှတွေ့မယ်", "သွားပြီ", "တာ့တာ", "ဘိုင်"]):
        return "goodbye"

    return None


def _no_result_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "Sorry, I could not find a matching proverb in my proverb database.",
            "example_mm": None,
            "sources": [],
        }

    return create_no_result_answer()


def _teacher_style_meaning(source: dict[str, Any], language: str = "my") -> str | None:
    meaning = (source.get("meaning") or "").strip()
    if not meaning:
        return None

    proverb = (source.get("proverb") or "").strip()

    if language == "en":
        if "teacher" in proverb.lower() and "student" in proverb.lower():
            return "A student can become more skilled or successful than the teacher."
        return f" {meaning}"

    if "ဆရာ့ထက်" in proverb and "တပည့်" in proverb:
        return "ကလေးတို့ရေ၊ တပည့်က ကြိုးစားလို့ ဆရာထက် ပိုတော်လာတဲ့အခါ ဒီစကားပုံကို သုံးတာပါ။"

    return f"ကလေးတို့ရေ၊ ဒီစကားပုံက {meaning} "


def _looks_teacher_styled(meaning: str | None, language: str) -> bool:
    normalized_meaning = (meaning or "").strip()
    if not normalized_meaning:
        return False
    if language == "en":
        return normalized_meaning.startswith(("In simple words", "This proverb means"))
    return bool(re.match(r"^(ကလေးတို့ရေ|ဆိုလိုတာက|လွယ်လွယ်ပြောရရင်)", normalized_meaning))


def _role_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": (
                f"I'm {settings.app_name}. I find Myanmar proverbs from the dataset and explain them in a simple, friendly way.\n"
                f"မြန်မာလိုပြောရရင် ကျွန်ုပ်က {settings.app_name} ဖြစ်ပါတယ်။ "
                f"မြန်မာစကားပုံအချက်အလက်စုစုဆောင်းမှု (Dataset) ထဲကနေ ရှာဖွေပေးပြီး၊ အဓိပ္ပာယ်ကို လွယ်ကူရှင်းလင်းစွာ ရှင်းပြပေးသွားမှာ ဖြစ်ပါတယ်။"
            ),
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": (
            f"ကျွန်ုပ်သည် {settings.app_name} ဖြစ်ပါသည်။ "
            "မြန်မာစကားပုံများကို အချက်အလက်စုစုဆောင်းမှု (Dataset) ထဲမှ ရှာဖွေပေးပြီး၊ အဓိပ္ပာယ်ကို လွယ်ကူရှင်းလင်းစွာ ရှင်းပြပေးသွားမည် ဖြစ်ပါသည်။ "
            "ဤစနစ်သည် မိမိမေးမြန်းသော မေးခွန်းနှင့် ကိုက်ညီသည့် စကားပုံကို ရှာဖွေကာ "
            "ကျွမ်းကျင်သူတစ်ဦးကဲ့သို့ နားလည်လွယ်အောင် ပြန်လည်ဖြေကြားပေးမည် ဖြစ်ပါသည်။"
        ),
        "example_mm": None,
        "sources": [],
    }


def _greeting_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "Hello! I can help you find a Myanmar proverb and explain it in a simple way.",
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": "မင်္ဂလာပါ။ ကျွန်ုပ်သည် မြန်မာစကားပုံများကို ရှာဖွေပေးပြီး အဓိပ္ပာယ်ကို လွယ်ကူရှင်းလင်းစွာ ရှင်းပြပေးသွားမည် ဖြစ်ပါသည်။",
        "example_mm": None,
        "sources": [],
    }


def _thanks_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "You're welcome! I'm happy to help.",
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": "ရပါတယ်ခင်ဗျာ။ အကူအညီပေးခွင့်ရလို့ ဝမ်းသာပါတယ်။",
        "example_mm": None,
        "sources": [],
    }


def _goodbye_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "Goodbye! Feel free to come back if you want help with Myanmar proverbs.",
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": "သွားလိုက်ပါဦးမယ်။ နောက်နောင်လည်း မြန်မာစကားပုံတွေအတွက် အကူအညီလိုရင် ပြန်လည်လာရောက်ဖို့ ဖိတ်ခေါ်ပါတယ်။",
        "example_mm": None,
        "sources": [],
    }


def _translate_previous_answer(previous_answer: dict[str, Any], target_language: str) -> dict[str, Any]:
    proverb = (previous_answer.get("proverb") or "").strip() or None
    if not proverb:
        return _no_result_answer(target_language)

    meaning = (previous_answer.get("meaning_simple_mm") or "").strip()
    example = (previous_answer.get("example_mm") or previous_answer.get("example") or "").strip()

    translated_meaning = _teacher_style_meaning({"proverb": proverb, "meaning": meaning}, target_language)

    return {
        "proverb": proverb,
        "meaning_simple_mm": translated_meaning,
        "example_mm": example or None,
        "sources": previous_answer.get("sources", []),
    }


def _build_chroma_record(row: dict[str, str | None]) -> tuple[str, str, dict[str, Any]]:
    keyword = row["keyword"]
    proverb = row["proverb"]
    meaning = row["meaning"]
    example = row["example"]
    doc = f"keyword: {keyword or ''}\nproverb: {proverb}\nmeaning: {meaning or ''}\nexample: {example or ''}"
    metadata = {
        "keyword": keyword,
        "proverb": proverb,
        "meaning": meaning,
        "example": example,
    }
    return _row_id(keyword, proverb), doc, metadata


def add_proverb(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_row(row)
    proverb_id, doc, metadata = _build_chroma_record(normalized)
    vectorstore = get_vectorstore()
    vectorstore.add_documents(
        [Document(page_content=doc, metadata=metadata)],
        ids=[proverb_id],
    )
    invalidate_metadata_cache()
    return {"id": proverb_id, **normalized}


def list_proverbs(limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
    col = get_vectorstore()._collection
    result = col.get(limit=max(1, min(limit, 5000)), offset=max(0, offset), include=["metadatas"])
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []

    items: list[dict[str, Any]] = []
    for proverb_id, metadata in zip(ids, metadatas):
        if not metadata:
            continue
        items.append(
            {
                "id": proverb_id,
                "keyword": metadata.get("keyword"),
                "proverb": metadata.get("proverb") or "",
                "meaning": metadata.get("meaning"),
                "example": metadata.get("example"),
            }
        )

    return items


def update_proverb(proverb_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    col = get_vectorstore()._collection
    existing = col.get(ids=[proverb_id], include=["metadatas"])
    metadatas = existing.get("metadatas") or []
    if not metadatas or not metadatas[0]:
        raise ValueError("Proverb not found")

    current = metadatas[0]
    merged = {
        "keyword": updates.get("keyword", current.get("keyword")),
        "proverb": updates.get("proverb", current.get("proverb")),
        "meaning": updates.get("meaning", current.get("meaning")),
        "example": updates.get("example", current.get("example")),
    }
    normalized = _normalize_row(merged)
    new_id, doc, metadata = _build_chroma_record(normalized)

    vectorstore = get_vectorstore()
    if new_id != proverb_id:
        vectorstore.delete(ids=[proverb_id])

    vectorstore.add_documents(
        [Document(page_content=doc, metadata=metadata)],
        ids=[new_id],
    )
    invalidate_metadata_cache()
    return {"id": new_id, **normalized}


def delete_proverb(proverb_id: str) -> bool:
    col = get_vectorstore()._collection
    existing = col.get(ids=[proverb_id], include=["metadatas"])
    metadatas = existing.get("metadatas") or []
    if not metadatas or not metadatas[0]:
        return False

    get_vectorstore().delete(ids=[proverb_id])
    invalidate_metadata_cache()
    return True


def delete_all_proverbs() -> int:
    col = get_vectorstore()._collection
    result = col.get(limit=100000, include=["metadatas"])
    ids = result.get("ids") or []
    if not ids:
        return 0

    get_vectorstore().delete(ids=ids)
    invalidate_metadata_cache()
    return len(ids)


def upsert_proverbs(rows: list[dict[str, Any]]) -> tuple[int, int]:
    vectorstore = get_vectorstore()
    inserted = 0
    skipped = 0

    ids: list[str] = []
    documents: list[Document] = []

    for row in rows:
        try:
            normalized = _normalize_row(row)
        except ValueError:
            skipped += 1
            continue

        proverb_id, doc, metadata = _build_chroma_record(normalized)
        ids.append(proverb_id)
        documents.append(Document(page_content=doc, metadata=metadata))

    if ids:
        vectorstore.add_documents(documents, ids=ids)
        inserted = len(ids)
        invalidate_metadata_cache()

    return inserted, skipped


def _answer_from_best_source(sources: list[dict[str, Any]], language: str = "my") -> dict[str, Any]:
    best = sources[0]
    return create_guardrailed_answer(
        proverb=best.get("proverb"),
        meaning_simple_mm=_teacher_style_meaning(best, language),
        example_mm=best.get("example"),
        sources=sources,
    )


def rag_answer(user_question: str, previous_answer: dict[str, Any] | None = None) -> dict[str, Any]:
    return asyncio.run(arag_answer(user_question, previous_answer=previous_answer))


async def arag_answer(user_question: str, previous_answer: dict[str, Any] | None = None) -> dict[str, Any]:
    user_intent = await _aclassify_user_intent(user_question)
    intent = user_intent["intent"]
    response_language = (
        "my"
        if intent == "translate_previous_to_myanmar"
        else "en"
        if intent == "translate_previous_to_english"
        else user_intent["language"]
    )

    is_valid, _error_msg = validate_question(user_question)
    if not is_valid:
        return _no_result_answer(response_language)

    if intent == "translate_previous_to_myanmar" and previous_answer:
        return _translate_previous_answer(previous_answer, "my")

    if intent == "translate_previous_to_english" and previous_answer:
        return _translate_previous_answer(previous_answer, "en")

    if intent == "greeting":
        return _greeting_answer(response_language)

    if intent == "thanks":
        return _thanks_answer(response_language)

    if intent == "goodbye":
        return _goodbye_answer(response_language)

    if intent == "role":
        return _role_answer(response_language)

    if intent == "proverb_only":
        sources = await aretrieve_context(user_question, top_k=settings.rag_top_k)
        if not sources or not is_context_relevant(sources):
            return _no_result_answer(response_language)
        best = sources[0]
        return {
            "proverb": best.get("proverb"),
            "meaning_simple_mm": _teacher_style_meaning(best, response_language),
            "example_mm": best.get("example"),
        }

    try:
        chain_result = await arun_rag_chain(user_question, language=response_language)
    except (ValueError, RuntimeError):
        sources = await aretrieve_context(user_question, top_k=settings.rag_top_k)
        if not sources:
            return _no_result_answer(response_language)
        return _answer_from_best_source(sources, response_language)

    sources = chain_result.get("sources") or []
    if not sources:
        return _no_result_answer(response_language)

    if not is_context_relevant(sources):
        return _no_result_answer(response_language)

    try:
        answer = parse_rag_answer(chain_result.get("text") or "")
    except (ValueError, RuntimeError):
        return _answer_from_best_source(sources, response_language)

    if not is_answer_valid(answer):
        if not answer.get("proverb"):
            return _no_result_answer(response_language)
        return _answer_from_best_source(sources, response_language)

    best = sources[0]
    source_meaning = (best.get("meaning") or "").strip()
    answer_meaning = (answer.get("meaning_simple_mm") or "").strip()
    if answer_meaning == source_meaning:
        answer["meaning_simple_mm"] = _teacher_style_meaning(best, response_language)
    elif response_language == "en" and not answer_meaning.startswith("In simple words"):
        answer["meaning_simple_mm"] = _teacher_style_meaning(best, response_language)
    elif response_language == "my" and not _looks_teacher_styled(answer_meaning, response_language):
        answer["meaning_simple_mm"] = _teacher_style_meaning(best, response_language)

    if "sources" not in answer or not answer["sources"]:
        answer["sources"] = sources

    return create_guardrailed_answer(
        proverb=answer.get("proverb"),
        meaning_simple_mm=answer.get("meaning_simple_mm"),
        example_mm=answer.get("example_mm"),
        sources=answer.get("sources", []),
    )
