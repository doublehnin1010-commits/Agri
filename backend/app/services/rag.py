from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.core.config import settings
from app.db.chroma import get_collection
from app.services.ollama import generate_answer, safe_json_from_llm
from app.services.guardrails import (
    validate_question,
    create_guardrailed_answer,
    create_no_result_answer,
    is_answer_valid,
)


PROVERB_KEYWORD_STOPWORDS = {
    "စကား",
    "စကားပုံ",
}

PROVERB_ONLY_PATTERNS = (
    "ဘယ်လိုစကားပုံ",
    "ဘာစကားပုံ",
    "စကားပုံက ဘာ",
    "စကားပုံဘာ",
    "proverb only",
)

ROLE_QUESTION_PATTERNS = (
    "မင်းကဘယ်သူလဲ",
    "မင်းက ဘယ်သူလဲ",
    "နင်ကဘယ်သူလဲ",
    "နင်က ဘယ်သူလဲ",
    "သင်ကဘယ်သူလဲ",
    "သင်က ဘယ်သူလဲ",
    "ဘယ်သူလဲ",
    "ဒီsystem ကဘာအလုပ်လုပ်သလဲ",
    "ဒီ system ကဘာအလုပ်လုပ်သလဲ",
    "ဒီစနစ်ကဘာအလုပ်လုပ်သလဲ",
    "ဘာအလုပ်လုပ်သလဲ",
    "who are you",
    "what are you",
    "your role",
    "what is this system",
    "what does this system do",
)

TRANSLATE_TO_MYANMAR_PATTERNS = (
    "မြန်မာလို",
    "မြန်မာဘာသာ",
    "myanmar လို",
    "in myanmar",
    "translate to myanmar",
    "explain in myanmar",
    "ပြန်ရှင်းပြ",
    "မြန်မာလိုရှင်းပြ",
    "မြန်မာလို ပြန်ရှင်းပြ",
)

TEACHER_STYLE_PREFIXES = (
    "ကလေးတို့ရေ",
    "ဆိုလိုတာက",
    "လွယ်လွယ်ပြောရရင်",
)

MYANMAR_SYNONYM_GROUPS = (
    ("တော်", "ထူးချွန်", "အစွမ်းထက်", "ထက်မြက်", "ပညာအရည်အသွေး", "ကျွမ်းကျင်"),
    ("ကဲ့ရဲ့", "အပြစ်တင်", "အပြင်တင်", "ဝေဖန်", "မကောင်းပြော", "အတင်းပြော"),
    ("ချီးမွမ်း", "ချီးမွန်း", "ချီးကျူး", "ကောင်းချီးပေး"),
    ("ဆရာ", "ဆရာ့", "သင်ပေးသူ", "လက်ဦးဆရာ"),
    ("တပည့်", "တပည့်", "ကျောင်းသား", "သင်ယူသူ"),
    ("ကုသိုလ်", "ကောင်းမှု", "လှူဒါန်း", "အကျိုးပြု"),
    ("ဝမ်း", "စားဝတ်နေရေး", "ဝမ်းရေး", "စားရေး"),
)

MYANMAR_NORMALIZATION_REPLACEMENTS = (
    ("ဉ", "ဥ"),
    ("ဿ", "သ"),
    ("၏", "ရဲ့"),
    ("၍", "ပြီး"),
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


def _asks_for_translation_to_myanmar(question: str) -> bool:
    normalized_question = _normalize_search_text(question)
    compact_question = _compact_search_text(normalized_question)

    for pattern in TRANSLATE_TO_MYANMAR_PATTERNS:
        normalized_pattern = _normalize_search_text(pattern)
        if normalized_pattern in normalized_question:
            return True
        if _compact_search_text(normalized_pattern) in compact_question:
            return True

    return False


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
        return f"In simple words, this proverb means: {meaning}"

    if "ဆရာ့ထက်" in proverb and "တပည့်" in proverb:
        return "ကလေးတို့ရေ၊ တပည့်က ကြိုးစားလို့ ဆရာထက် ပိုတော်လာတဲ့အခါ ဒီစကားပုံကို သုံးတာပါ။"

    return f"ကလေးတို့ရေ၊ ဒီစကားပုံက {meaning} လို့ ဆိုလိုတာပါ။"


def _looks_teacher_styled(meaning: str | None) -> bool:
    normalized_meaning = (meaning or "").strip()
    return any(normalized_meaning.startswith(prefix) for prefix in TEACHER_STYLE_PREFIXES)


def _role_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": (
                "I’m Myanmar Proverbs AI Tutor. I find proverbs from the dataset and explain them in a simple, friendly way."
            ),
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": (
            "ကလေးတို့ရေ၊ ကျွန်ုပ်က မြန်မာစကားပုံတွေကို ရှာပေးပြီး "
            "အဓိပ္ပါယ်ကို လွယ်လွယ်ကူကူ ရှင်းပြပေးတဲ့ Myanmar Proverbs AI Tutor ပါ။ "
            "ဒီစနစ်က မေးခွန်းနဲ့ သက်ဆိုင်တဲ့ စကားပုံကို ဒေတာထဲကနေ ရှာပြီး "
            "ဆရာတစ်ယောက်လို နားလည်လွယ်အောင် ပြန်ဖြေပေးတာပါ။"
        ),
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
    synonym_score = _synonym_similarity(normalized_query, searchable)

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
    best_similarity = max(proverb_keyword_score, synonym_score, token_score, ngram_score)

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
            if len(compact_token) >= 4 and compact_token not in PROVERB_KEYWORD_STOPWORDS:
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
    normalized = text
    for source, target in MYANMAR_NORMALIZATION_REPLACEMENTS:
        normalized = normalized.replace(source, target)
    return normalized


def _search_text_variants(text: str) -> list[str]:
    variants = {text}
    variants.add(_strip_optional_myanmar_marks(text))
    return [variant for variant in variants if variant]


def _strip_optional_myanmar_marks(text: str) -> str:
    # Keep medial marks because they can change word identity completely.
    return re.sub(r"[\u1037\u1038\u1039\u103a]", "", text)
    return re.sub(r"[့း္်ျြွှ]", "", text)


def _synonym_similarity(query: str, searchable: str) -> float:
    query_groups = _matched_synonym_group_indexes(query)
    if not query_groups:
        return 0.0

    searchable_groups = _matched_synonym_group_indexes(searchable)
    matched = query_groups & searchable_groups
    if not matched:
        return 0.0

    if len(query_groups) == 1:
        return 0.35

    if len(matched) < 2:
        return 0.0

    return min(0.75, len(matched) / len(query_groups))


def _matched_synonym_group_indexes(text: str) -> set[int]:
    matched_groups: set[int] = set()

    for index, group in enumerate(MYANMAR_SYNONYM_GROUPS):
        if any(_contains_synonym_term(text, term) for term in group):
            matched_groups.add(index)

    return matched_groups


def _contains_synonym_term(text: str, term: str) -> bool:
    normalized_text = _normalize_search_text(text)
    normalized_term = _normalize_search_text(term)
    if not normalized_text or not normalized_term:
        return False

    tokens = normalized_text.split()
    if normalized_term in tokens:
        return True

    compact_term = _compact_synonym_text(normalized_term)
    if len(compact_term) <= 3:
        return any(_compact_synonym_text(token).startswith(compact_term) for token in tokens)

    return compact_term in _compact_synonym_text(normalized_text)


def _compact_synonym_text(text: str) -> str:
    compact = _apply_myanmar_normalization_replacements(text)
    compact = re.sub(r"[့း]+", "", compact)
    return re.sub(r"\s+", "", compact)


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


def _asks_for_proverb_only(question: str) -> bool:
    normalized_question = _normalize_search_text(question)
    compact_question = _compact_search_text(normalized_question)

    for pattern in PROVERB_ONLY_PATTERNS:
        normalized_pattern = _normalize_search_text(pattern)
        if normalized_pattern in normalized_question:
            return True
        if _compact_search_text(normalized_pattern) in compact_question:
            return True

    return False


def _asks_about_role(question: str) -> bool:
    normalized_question = _normalize_search_text(question)
    compact_question = _compact_search_text(normalized_question)

    for pattern in ROLE_QUESTION_PATTERNS:
        normalized_pattern = _normalize_search_text(pattern)
        if normalized_pattern in normalized_question:
            return True
        if _compact_search_text(normalized_pattern) in compact_question:
            return True

    return False


def _build_answer_prompt(context_json: str, user_question: str, language: str) -> str:
    if language == "en":
        return f"""
You are a Myanmar Proverbs AI Tutor.

Use ONLY the context below.
If there is no exact proverb match, choose the closest meaning.
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

Use ONLY the context below.
If there is no exact proverb match, choose the closest meaning.
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
    response_language = "my" if _asks_for_translation_to_myanmar(user_question) else _language_from_question(user_question)

    # Guardrail 1: Validate the question
    is_valid, _error_msg = validate_question(user_question)
    if not is_valid:
        return _no_result_answer(response_language)

    if _asks_for_translation_to_myanmar(user_question) and previous_answer:
        return _translate_previous_answer(previous_answer, "my")

    if _asks_about_role(user_question):
        return _role_answer(response_language)

    # Guardrail 2: Retrieve context
    sources = retrieve_context(user_question, top_k=settings.rag_top_k)

    if not sources:
        return _no_result_answer(response_language)

    if _asks_for_proverb_only(user_question):
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
    elif response_language == "my" and not _looks_teacher_styled(answer_meaning):
        answer["meaning_simple_mm"] = _teacher_style_meaning(best, response_language)

    if "sources" not in answer or not answer["sources"]:
        answer["sources"] = sources

    return create_guardrailed_answer(
        proverb=answer.get("proverb"),
        meaning_simple_mm=answer.get("meaning_simple_mm"),
        example_mm=answer.get("example_mm"),
        sources=answer.get("sources", []),
    )
