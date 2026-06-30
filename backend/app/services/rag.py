from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from app.core.config import settings
from app.db.chroma import get_collection
from app.services.llm import generate_answer, safe_json_from_llm
from app.services.guardrails import (
    validate_question,
    create_guardrailed_answer,
    create_no_result_answer,
    is_answer_valid,
    is_context_relevant,
)

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

{
    "intent": "<intent>",
    "language": "<my|en>"
}

Only return valid JSON.
Do not include markdown.
Do not answer the user's question.
""".strip()



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

    prompt = f"""
Classify this user message for Myanmar Proverbs AI Tutor.

User message:
{question}

Return JSON exactly in this shape:
{{
  "intent": "role | translate_previous_to_myanmar | proverb_only | proverb_question",
  "language": "my | en"
}}
"""
    try:
        result = safe_json_from_llm(
            generate_answer(prompt, system_instruction=INTENT_CLASSIFIER_SYSTEM_INSTRUCTION)
        )
    except Exception:
        return fallback

    intent = result.get("intent")
    language = result.get("language")
    if intent not in {"role", "translate_previous_to_myanmar", "proverb_only", "proverb_question"}:
        intent = fallback["intent"]
    if language not in {"my", "en"}:
        language = fallback["language"]

    return {"intent": intent, "language": language}


def _infer_builtin_intent(question: str) -> str | None:
    normalized = _normalize_search_text(question)
    compact = _compact_search_text(normalized)
    plain_compact = re.sub(r"\s+", "", unicodedata.normalize("NFC", normalized))

    # ==========================
    # Greeting
    # ==========================
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", normalized):
        return "greeting"

    if any(
        text in plain_compact
        for text in [
            "မင်္ဂလာပါ",
            "ဟယ်လို",
            "ဟိုင်း",
        ]
    ):
        return "greeting"

    # ==========================
    # Role
    # ==========================
    if re.search(r"\b(who|what)\s+(are|r)\s+(you|u)\b", normalized):
        return "role"

    if re.search(
        r"\b(your|ur)\s+(role|job|purpose|name|capabilit(?:y|ies))\b",
        normalized,
    ):
        return "role"

    if re.search(
        r"\bwhat\s+(is|does)\s+(this\s+)?(system|app|application)\b",
        normalized,
    ):
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

    # ==========================
    # Translate to Myanmar
    # ==========================
    if re.search(
        r"\btranslate\b.*\b(burmese|myanmar)\b",
        normalized,
    ):
        return "translate_previous_to_myanmar"

    if any(
        text in plain_compact
        for text in [
            "မြန်မာလို",
            "မြန်မာလိုပြန်",
            "ဗမာလို",
            "ဗမာလိုပြန်",
        ]
    ):
        return "translate_previous_to_myanmar"

    # ==========================
    # Translate to English
    # ==========================
    if re.search(
        r"\btranslate\b.*\benglish\b",
        normalized,
    ):
        return "translate_previous_to_english"

    if any(
        text in normalized
        for text in [
            "english",
            "in english",
            "explain in english",
        ]
    ):
        return "translate_previous_to_english"

    # ==========================
    # Thanks
    # ==========================
    if re.search(
        r"\b(thanks|thank you|thx|ty)\b",
        normalized,
    ):
        return "thanks"

    if any(
        text in plain_compact
        for text in [
            "ကျေးဇူး",
            "ကျေးဇူးတင်ပါတယ်",
            "ကျေးဇူးပါ",
        ]
    ):
        return "thanks"

    # ==========================
    # Goodbye
    # ==========================
    if re.search(
        r"\b(bye|goodbye|see you|see ya)\b",
        normalized,
    ):
        return "goodbye"

    if any(
        text in plain_compact
        for text in [
            "နောက်မှတွေ့မယ်",
            "သွားပြီ",
            "တာ့တာ",
            "ဘိုင်",
        ]
    ):
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
               f"I’m {settings.app_name}. I find Myanmar proverbs from the dataset and explain them in a simple, friendly way.\n"
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
            "meaning_simple_mm": "You’re welcome! I’m happy to help.",
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

    if target_language == "en":
        translated_meaning = _teacher_style_meaning({"proverb": proverb, "meaning": meaning}, "en")
    else:
        translated_meaning = _teacher_style_meaning({"proverb": proverb, "meaning": meaning}, "my")

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
    col = get_collection()
    col.upsert(ids=[proverb_id], documents=[doc], metadatas=[metadata])
    return {"id": proverb_id, **normalized}


def list_proverbs(limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
    col = get_collection()
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
    col = get_collection()
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

    if new_id != proverb_id:
        col.delete(ids=[proverb_id])

    col.upsert(ids=[new_id], documents=[doc], metadatas=[metadata])
    return {"id": new_id, **normalized}


def delete_proverb(proverb_id: str) -> bool:
    col = get_collection()
    existing = col.get(ids=[proverb_id], include=["metadatas"])
    metadatas = existing.get("metadatas") or []
    if not metadatas or not metadatas[0]:
        return False

    col.delete(ids=[proverb_id])
    return True


def delete_all_proverbs() -> int:
    col = get_collection()
    result = col.get(limit=100000, include=["metadatas"])
    ids = result.get("ids") or []
    if not ids:
        return 0

    col.delete(ids=ids)
    return len(ids)


def upsert_proverbs(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """
    rows: [{keyword, proverb, meaning, example}]
    """
    col = get_collection()
    inserted = 0
    skipped = 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for r in rows:
        try:
            normalized = _normalize_row(r)
        except ValueError:
            skipped += 1
            continue

        proverb_id, doc, metadata = _build_chroma_record(normalized)
        ids.append(proverb_id)
        documents.append(doc)
        metadatas.append(metadata)

    if ids:
        col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        inserted = len(ids)

    return inserted, skipped


def retrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.rag_top_k
    if not query or not query.strip():
        return []

    language = _language_from_question(query)
    search_queries = _build_search_queries(query, language)

    lexical_results: list[dict[str, Any]] = []
    semantic_results: list[dict[str, Any]] = []
    for search_query in search_queries:
        lexical_results.extend(_retrieve_lexical_context(search_query, top_k=k))
        semantic_results.extend(_retrieve_semantic_context(search_query, top_k=k))

    if not semantic_results and not lexical_results:
        return []

    merged = []
    seen_proverbs: set[str] = set()

    for item in lexical_results + semantic_results:
        proverb_text = str(item.get("proverb") or "")
        if not proverb_text or proverb_text in seen_proverbs:
            continue
        seen_proverbs.add(proverb_text)
        merged.append(item)

    return merged[:k]


def _build_search_queries(query: str, language: str) -> list[str]:
    queries = [query]
    rewritten_query = rewrite_query(query, language)
    if rewritten_query and rewritten_query.strip() and rewritten_query.strip() != query.strip():
        queries.append(rewritten_query)
    return queries


def rewrite_query(query: str, language: str) -> str:
    """Rewrite a user query into a semantic search phrase or keywords."""
    if not query or not query.strip():
        return query

    if language == "en":
        prompt = f"""
Translate the following English user sentence into a short Myanmar semantic search phrase or keyword list that captures the meaning.
Keep it brief and focused on the intent and topic, not the exact words.
Return only the rewritten query.

User sentence:
{query}

Rewritten query:
"""
    else:
        prompt = f"""
Rewrite the following Myanmar user sentence into a short semantic search phrase or keyword list that captures the meaning.
Keep it brief and focused on the intent and topic, not the exact words.
Return only the rewritten query.

User sentence:
{query}

Rewritten query:
"""
    try:
        rewritten = generate_answer(prompt).strip()
        return rewritten or query
    except Exception:
        return query


def _retrieve_semantic_context(query: str, top_k: int) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []

    try:
        col = get_collection()
        result = col.query(
            query_texts=[query],
            n_results=top_k,
            include=["metadatas", "distances"]
        )

        if not result or not result.get("metadatas") or not result["metadatas"][0]:
            return []

        metadatas = result["metadatas"][0]
        distances = result.get("distances", [[]])[0]
        
        matches: list[dict[str, Any]] = []
        for idx, md in enumerate(metadatas):
            if not md:
                continue
            distance = distances[idx] if idx < len(distances) else 1.0
            item = _context_item_from_metadata(md, distance)
            item["similarity"] = max(0.0, 1.0 - min(distance, 1.0))
            if item["similarity"] < settings.rag_semantic_threshold:
                continue
            matches.append(item)

        return matches[:top_k]
    except Exception:
        return []


def _retrieve_lexical_context(query: str, top_k: int) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return []

    col = get_collection()
    result = col.get(limit=100000, include=["metadatas"])
    metadatas = result.get("metadatas") or []
    matches: list[tuple[float, dict[str, Any]]] = []

    for md in metadatas:
        if not md:
            continue
        score = _lexical_distance(normalized_query, md)
        if score is None:
            continue
        if score > 1.0 - settings.rag_min_lexical_similarity:
            continue
        matches.append((score, _context_item_from_metadata(md, score)))

    matches.sort(key=lambda item: item[0])
    if matches and matches[0][0] <= 0.05:
        matches = [item for item in matches if item[0] <= 0.05]

    return [item for _, item in matches[:top_k]]


def _lexical_distance(normalized_query: str, metadata: dict[str, Any]) -> float | None:
    fields = [
        metadata.get("keyword"),
        metadata.get("proverb"),
        metadata.get("meaning"),
        metadata.get("example"),
    ]
    searchable = _normalize_search_text(" ".join(str(field or "") for field in fields))
    if not searchable:
        return None

    query_variants = _search_text_variants(normalized_query)
    searchable_variants = _search_text_variants(searchable)

    if _has_variant_substring_match(query_variants, searchable_variants):
        return 0.0

    proverb_keyword_score = _proverb_keyword_similarity(query_variants, metadata)
    searchable_compacts = [_compact_search_text(text) for text in searchable_variants]
    tokens = [
        token
        for variant in query_variants
        for token in variant.split()
        if len(token) > 1
    ]
    token_score = 0.0
    if tokens:
        matched = sum(
            1
            for token in tokens
            if any(token in text or _compact_search_text(token) in compact for text, compact in zip(searchable_variants, searchable_compacts))
        )
        token_score = matched / len(tokens)

    ngram_score = max(
        _ngram_similarity(_compact_search_text(query), _compact_search_text(searchable_text))
        for query in query_variants
        for searchable_text in searchable_variants
    )
    best_similarity = max(proverb_keyword_score, token_score, ngram_score)

    if best_similarity == 0.0:
        return None

    return 1.0 - best_similarity


def _has_variant_substring_match(query_variants: list[str], searchable_variants: list[str]) -> bool:
    for query in query_variants:
        if not query:
            continue
        compact_query = _compact_search_text(query)
        for searchable in searchable_variants:
            if not searchable:
                continue
            if query in searchable or searchable in query:
                return True
            compact_searchable = _compact_search_text(searchable)
            if compact_query in compact_searchable or compact_searchable in compact_query:
                return True
    return False


def _proverb_keyword_similarity(query_variants: list[str], metadata: dict[str, Any]) -> float:
    compact_queries = [_compact_search_text(query) for query in query_variants if query]
    if not compact_queries:
        return 0.0

    fields = [
        metadata.get("keyword"),
        metadata.get("proverb"),
    ]
    searchable = _normalize_search_text(" ".join(str(field or "") for field in fields))
    searchable_variants = _search_text_variants(searchable)
    tokens = []
    for variant in searchable_variants:
        for token in variant.split():
            compact_token = _compact_search_text(token)
            if len(compact_token) >= 4:
                tokens.append(token)
    tokens = list(dict.fromkeys(tokens))
    if not tokens:
        return 0.0

    matched = sum(
        1
        for token in tokens
        if any(
            _compact_search_text(token) in compact_query
            or _has_meaningful_prefix_overlap(_compact_search_text(token), compact_query)
            for compact_query in compact_queries
        )
    )
    if not matched:
        return 0.0

    return max(0.65, matched / len(tokens))


def _has_meaningful_prefix_overlap(left: str, right: str, min_length: int = 4) -> bool:
    common_length = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        common_length += 1
    shorter_length = min(len(left), len(right))
    return common_length >= min_length and common_length / shorter_length >= 0.75


def _normalize_search_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = _apply_myanmar_normalization_replacements(normalized)
    normalized = re.sub(r"[၊။!?.,;:\"'`(){}\[\]<>/\\|+=_*&^%$#@~`-]", " ", normalized)
    return " ".join(normalized.split())


def _apply_myanmar_normalization_replacements(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _search_text_variants(text: str) -> list[str]:
    variants = {text}
    variants.add(_strip_optional_myanmar_marks(text))
    return [variant for variant in variants if variant]


def _strip_optional_myanmar_marks(text: str) -> str:
    # Keep medial marks because they can change word identity completely.
    return re.sub(r"[\u1037\u1038\u1039\u103a]", "", text)


def _compact_search_text(text: str) -> str:
    compact = _apply_myanmar_normalization_replacements(text)
    compact = _strip_optional_myanmar_marks(compact)
    return re.sub(r"\s+", "", compact)


def _ngram_similarity(query: str, searchable: str, n: int = 3) -> float:
    if not query or not searchable:
        return 0.0
    if len(query) < n:
        return 1.0 if query in searchable else 0.0

    query_ngrams = {query[i : i + n] for i in range(len(query) - n + 1)}
    if not query_ngrams:
        return 0.0

    matched = sum(1 for ngram in query_ngrams if ngram in searchable)
    return matched / len(query_ngrams)


def _context_item_from_metadata(metadata: dict[str, Any], score: float | None) -> dict[str, Any]:
    return {
        "keyword": metadata.get("keyword"),
        "proverb": metadata.get("proverb"),
        "meaning": metadata.get("meaning"),
        "example": metadata.get("example"),
        "score": score,
    }


def _dedupe_context(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("proverb") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _answer_from_best_source(sources: list[dict[str, Any]], language: str = "my") -> dict[str, Any]:
    best = sources[0]
    return create_guardrailed_answer(
        proverb=best.get("proverb"),
        meaning_simple_mm=_teacher_style_meaning(best, language),
        example_mm=best.get("example"),
        sources=sources,
    )


def _build_answer_prompt(context_json: str, user_question: str, language: str) -> str:
    if language == "en":
        return f"""
You are a Myanmar Proverbs AI Tutor.

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
{context_json}

User Question:
{user_question}

Answer in English only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}
"""

    return f"""
You are a Myanmar Proverbs AI Tutor.

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
{context_json}

User Question:
{user_question}

Answer in Burmese only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}
"""


def rag_answer(user_question: str, previous_answer: dict[str, Any] | None = None) -> dict[str, Any]:
    user_intent = _classify_user_intent(user_question)
    intent = user_intent["intent"]
    response_language = (
        "my"
        if intent == "translate_previous_to_myanmar"
        else "en"
        if intent == "translate_previous_to_english"
        else user_intent["language"]
    )

    # Guardrail 1: Validate the question
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

    # Guardrail 2: Retrieve context
    sources = retrieve_context(user_question, top_k=settings.rag_top_k)

    if not sources:
        return _no_result_answer(response_language)

    if not is_context_relevant(sources):
        return _no_result_answer(response_language)

    if intent == "proverb_only":
        best = sources[0]
        return {
            "proverb": best.get("proverb"),
            "meaning_simple_mm": _teacher_style_meaning(best, response_language),
            "example_mm": best.get("example"),
        }

    context_json = json.dumps(sources, ensure_ascii=False, indent=2)
    prompt = _build_answer_prompt(context_json, user_question, response_language)

    try:
        raw = generate_answer(prompt)
        answer = safe_json_from_llm(raw)
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
