from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import unicodedata
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings
from app.db.chroma import get_vectorstore
from app.services.guardrails import (
    create_guardrailed_answer,
    is_answer_valid,
    is_context_relevant,
    validate_question,
)
from app.services.conversation_memory import ConversationMemoryService
from app.services.llm_service import agenerate_chat_response, safe_json_from_llm
from app.services.rag_service import arun_rag_chain, parse_rag_answer
from app.services.retriever_service import (
    _compact_search_text,
    _normalize_search_text,
    aretrieve_context,
    invalidate_metadata_cache,
)

logger = logging.getLogger(__name__)

BOT_NAME = "Burmese Proverbs Hub"
NOT_FOUND_MESSAGE = (
    "ဝမ်းနည်းပါတယ်။ သင်မေးမြန်းထားသော စကားပုံ သို့မဟုတ် "
    "အကြောင်းအရာကို ကျွန်ုပ်၏ မြန်မာ့ရိုးရာစကားပုံဒေတာအတွင်း "
    "မတွေ့ရှိပါ။ အခြား မြန်မာ့ရိုးရာစကားပုံများ၊ "
    "အဓိပ္ပါယ်များနှင့် ပတ်သက်၍ ဆက်လက်မေးမြန်းနိုင်ပါတယ်။"
)
TOPIC_NOT_FOUND_MESSAGE = (
    "ဝမ်းနည်းပါတယ်။ သင်မေးထားသော အကြောင်းအရာနှင့် သက်ဆိုင်သော စကားပုံများကို "
    "ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။\n\n"
    "မြန်မာ့ရိုးရာစကားပုံများ၊ အဓိပ္ပါယ်များနှင့် ပတ်သက်ပြီး အခြားမေးခွန်းများကို "
    "ဆက်လက်မေးမြန်းနိုင်ပါတယ်။"
)
PROVERB_LIST_PAGE_SIZE = 5
PROVERB_LIST_RETRIEVAL_LIMIT = 20
OUT_OF_DOMAIN_TEMPLATE = (
    "ဒီ Burmese Proverbs Hub ကတော့ မြန်မာ့ရိုးရာစကားပုံများနှင့် သက်ဆိုင်သော အဓိပ္ပါယ်များကို "
    "ဖော်ပြပေးရန်အတွက် ဖန်တီးထားခြင်း ဖြစ်ပါတယ်။\n\n"
    "သင်မေးလိုက်သော '{question}' ဆိုတဲ့ မေးခွန်းဟာ မြန်မာ့ရိုးရာစကားပုံများနှင့် မသက်ဆိုင်ပါဘူး။\n\n"
    "ရိုးရာစကားပုံများ၊ စကားပုံအဓိပ္ပါယ်များနှင့် ပတ်သက်ပြီး မေးစရာများရှိပါက အခုပဲ မေးမြန်းနိုင်ပါတယ်။"
)


def _row_id(keyword: str | None, proverb: str) -> str:
    raw = f"{keyword or ''}||{proverb}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _source_with_id(source: dict[str, Any]) -> dict[str, Any]:
    proverb = str(source.get("proverb") or "").strip()
    if not proverb:
        return source
    return {**source, "id": source.get("id") or _row_id(source.get("keyword"), proverb)}


def _sources_with_ids(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_source_with_id(source) for source in sources]


def _normalize_row(row: dict[str, Any]) -> dict[str, str | None]:
    keyword = (row.get("keyword") or "").strip() or None
    proverb = (row.get("proverb") or "").strip()
    meaning = (row.get("meaning") or "").strip() or None
    english_meaning = (row.get("english_meaning") or row.get("englishMeaning") or "").strip() or None
    example = (row.get("example") or "").strip() or None
    if not proverb:
        raise ValueError("proverb is required")
    return {
        "keyword": keyword,
        "proverb": proverb,
        "meaning": meaning,
        "english_meaning": english_meaning,
        "example": example,
    }


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
        "intent": "proverb_query",
        "language": _language_from_question(question),
    }
    if not question or not question.strip():
        return fallback

    builtin_intent = _infer_builtin_intent(question)
    if builtin_intent:
        if isinstance(builtin_intent, str):
            return {"intent": builtin_intent, "language": fallback["language"]}
        return {**fallback, **builtin_intent}

    return fallback


async def _aclassify_user_intent(question: str) -> dict[str, Any]:
    fallback = {
        "intent": "proverb_query",
        "language": _language_from_question(question),
    }
    if not question or not question.strip():
        return fallback

    builtin_intent = _infer_builtin_intent(question)
    if builtin_intent:
        if isinstance(builtin_intent, str):
            return {"intent": builtin_intent, "language": fallback["language"]}
        return {**fallback, **builtin_intent}

    gemini_domain_intent = await _aclassify_domain_with_gemini(question)
    if gemini_domain_intent:
        return {**fallback, **gemini_domain_intent}

    return fallback


async def classify_user_intent(question: str) -> dict[str, Any]:
    """Public deterministic classifier used by chat routing and memory."""
    return await _aclassify_user_intent(question)


async def _aclassify_domain_with_gemini(question: str) -> dict[str, Any] | None:
    if settings.chat_provider.strip().lower() != "gemini":
        return None

    system_instruction = """
You classify whether a user query belongs to a Myanmar traditional proverb chatbot.
Return JSON only.

A query is proverb_related if the user asks for:
- a Myanmar proverb, meaning, lesson, example, or explanation
- proverbs related to a topic, person, object, idea, value, or situation
- a list of proverb-like items based on a theme
- follow-up about previously discussed proverbs

The user does not need to explicitly say "proverb" or "စကားပုံ".

A query is out_of_domain only when it clearly asks for general knowledge outside Myanmar proverbs, such as programming, sports, health, science, weather, politics, math, travel, business, or ordinary factual explanation.

Return one of:
{"domain":"out_of_domain"}
{"domain":"proverb_related","intent":"proverb_query"}
{"domain":"proverb_related","intent":"proverb_list","topic":"...","requested_count":5}
""".strip()
    prompt = f"""
User query:
{question}

Classify this query for the Myanmar proverb chatbot.
""".strip()
    try:
        raw = await agenerate_chat_response(prompt, system_instruction=system_instruction)
        result = safe_json_from_llm(raw)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Gemini domain classification failed: %s", exc)
        return None

    domain = str(result.get("domain") or "").strip().lower()
    if domain == "out_of_domain":
        return {"intent": "unrelated"}
    if domain != "proverb_related":
        return None

    intent = str(result.get("intent") or "proverb_query").strip()
    if intent == "proverb_list":
        topic = str(result.get("topic") or question).strip()
        requested_count = result.get("requested_count")
        if isinstance(requested_count, str):
            requested_count = _clamp_requested_count(requested_count)
        elif isinstance(requested_count, int):
            requested_count = max(1, min(requested_count, PROVERB_LIST_RETRIEVAL_LIMIT))
        else:
            requested_count = _extract_requested_proverb_count(_normalize_search_text(question))
        return {"intent": "proverb_list", "topic": topic, "requested_count": requested_count}

    return {"intent": "proverb_query"}


def _infer_builtin_intent(question: str) -> dict[str, Any] | str | None:
    normalized = _normalize_search_text(question)
    compact = _compact_search_text(normalized)
    plain_compact = re.sub(r"\s+", "", unicodedata.normalize("NFC", normalized))

    if _is_out_of_domain_question(normalized, plain_compact):
        return "unrelated"

    if re.fullmatch(r"(?:show|tell|give|list)?\s*(?:me)?\s*(?:more|next|next five|more proverbs|another five)[.!?]*", normalized):
        return {"intent": "follow_up", "action": "show_more_list"}

    if any(marker in plain_compact for marker in ["ထပ်ပြပါ", "နောက်ထပ်ပြပါ", "ထပ်ပြောပါ", "နောက်ထပ်စကားပုံ"]):
        return {"intent": "follow_up", "action": "show_more_list"}

    if re.search(r"နောက်ထပ်\s*[၁၂၃၄၅၆၇၈၉၀0-9]*\s*(?:ခု)?", normalized):
        return {"intent": "follow_up", "action": "show_more_list"}

    if re.fullmatch(r"(?:explain more|tell me more|more detail)[.!?]*", normalized):
        return {"intent": "follow_up", "action": "explain_more"}

    if re.fullmatch(r"(?:give|show)(?: me)? (?:an )?example[.!?]*", normalized):
        return {"intent": "follow_up", "action": "example"}

    if any(marker in plain_compact for marker in ["အသေးစိတ်ရှင်းပြပါ", "ဥပမာပေးပါ", "ဥပမာပြပါ"]):
        action = "example" if "ဥပမာ" in plain_compact else "explain_more"
        return {"intent": "follow_up", "action": action}

    if re.search(r"\b(?:english meaning|meaning in english)\b", normalized):
        return {"intent": "follow_up", "action": "english_meaning"}

    if re.fullmatch(r"(?:what does (?:this|it) mean|what is the meaning)[?!.]*", normalized):
        return {"intent": "follow_up", "action": "meaning"}

    if re.search(r"\b(?:another|one more) proverb like (?:this|it)\b", normalized):
        return {"intent": "follow_up", "action": "another_similar"}

    if re.fullmatch(r"(?:tell|give|show)(?: me)? another (?:one|proverb)[.!?]*", normalized):
        return {"intent": "follow_up", "action": "another_similar"}

    detail_selection = _extract_detail_selection(normalized)
    if detail_selection:
        return {"intent": "follow_up", "action": "detail", "selection": detail_selection}

    list_topic = _extract_proverb_list_topic(normalized)
    if list_topic:
        return {
            "intent": "proverb_list",
            "topic": list_topic,
            "requested_count": _extract_requested_proverb_count(normalized),
        }

    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", normalized):
        return "small_talk"

    if any(text in plain_compact for text in ["မင်္ဂလာပါ", "ဟယ်လို", "ဟိုင်း"]):
        return "small_talk"

    if re.search(r"\b(who|what)\s+(are|r)\s+(you|u)\b", normalized):
        return "role"

    if re.search(r"\b(your|ur)\s+(role|job|purpose|name|capabilit(?:y|ies))\b", normalized):
        return "role"

    if re.search(r"\b(role|job|purpose|name|capabilit(?:y|ies))\b", normalized) and any(
        marker in plain_compact
        for marker in ["မင်း", "နင်", "သင်", "ဒီsystem", "ဒီapp", "ဒီapplication", "thissystem", "thisapp"]
    ):
        return "role"

    if re.search(r"\bwhat\s+(is|does)\s+(this\s+)?(system|app|application)\b", normalized):
        return "role"

    if re.search(r"\bhow\s+can\s+(you|u)\s+help\b", normalized):
        return "role"

    if any(
        text in plain_compact
        for text in [
            "မင်းဘယ်သူလဲ",
            "မင်းကဘာလဲ",
            "မင်းဘာလဲ",
            "မင်းရဲ့role",
            "မင်းrole",
            "roleကဘာလဲ",
            "ဘယ်သူလဲ",
            "ဘာအလုပ်",
            "ဘာလုပ်နိုင်လဲ",
            "ဘာတွေလုပ်နိုင်",
            "ဘာတွေလုပ်ပေးနိုင်",
            "ဘာကူညီနိုင်",
            "ဒီစနစ်ကဘာလဲ",
            "ဒီappကဘာလဲ",
            "ဒီapplicationကဘာလဲ",
        ]
    ):
        return "role"

    if re.search(r"\btranslate\b.*\b(burmese|myanmar)\b", normalized):
        return {"intent": "follow_up", "action": "translate_myanmar"}

    if any(text in plain_compact for text in ["မြန်မာလို", "မြန်မာလိုပြန်", "ဗမာလို", "ဗမာလိုပြန်"]):
        return {"intent": "follow_up", "action": "translate_myanmar"}

    if re.search(r"\b(?:previous|last|above|these|those|all)\s+proverbs?\b.*\benglish\b", normalized):
        return {"intent": "follow_up", "action": "english_list"}

    if re.search(r"\btranslate\b.*\benglish\b", normalized):
        return {"intent": "follow_up", "action": "english_meaning"}

    if any(text in normalized for text in ["english", "in english", "explain in english"]):
        return {"intent": "follow_up", "action": "english_meaning"}

    if re.search(r"\bwhich proverb fits\b", normalized):
        return "proverb_query"

    if re.search(r"\b(thanks|thank you|thx|ty)\b", normalized):
        return "gratitude"

    if plain_compact in {"ကျေးဇူး", "ကျေးဇူးပါ", "ကျေးဇူးတင်ပါတယ်"} or (
        "ကျေးဇူးတင်" in plain_compact and len(plain_compact) <= len("ကျေးဇူးတင်ပါတယ်ခင်ဗျာ")
    ):
        return "gratitude"

    # Keep conversational acknowledgements out of semantic proverb search.
    # Otherwise a message such as "ok" may return an unrelated nearest match.
    if re.fullmatch(
        r"(?:ok(?:ay)?|yes|yeah|yep|alright|all right|got it|understood|sure)[.!]*",
        normalized,
    ):
        return "confirmation"

    if plain_compact in {"အိုကေ", "ဟုတ်", "ဟုတ်ကဲ့", "👍", "👌", "😀"}:
        return "confirmation"

    if re.search(r"\b(bye|goodbye|see you|see ya)\b", normalized):
        return "farewell"

    if any(text in plain_compact for text in ["နောက်မှတွေ့မယ်", "သွားပြီ", "တာ့တာ", "ဘိုင်"]):
        return "farewell"

    if re.search(r"\b(?:meaning|mean)\b", normalized):
        return "meaning_query"

    if re.search(r"\b(?:teacher|teach|lesson)\b", normalized):
        return "teacher_query"

    if re.search(r"\bcategory\b", normalized):
        return "category_query"

    return None


def _is_out_of_domain_question(normalized: str, plain_compact: str) -> bool:
    if "စကားပုံ" in normalized or "proverb" in normalized:
        return False

    english_patterns = [
        r"\bpython\b",
        r"\bprogram(?:ming)?\b",
        r"\bcode\b",
        r"\bjavascript\b",
        r"\bhtml\b",
        r"\bcss\b",
        r"\bhealth\b",
        r"\bmedicine\b",
        r"\bdisease\b",
        r"\bscience\b",
        r"\bmath\b",
        r"\bweather\b",
        r"\bnews\b",
        r"\bcapital\b",
        r"\bfootball\b",
        r"\bsoccer\b",
        r"\bsport(?:s)?\b",
        r"\bbasketball\b",
        r"\bvolleyball\b",
        r"\btennis\b",
        r"\bai works\b",
        r"\bwhat is ai\b",
        r"\bcloud computing\b",
    ]
    if any(re.search(pattern, normalized) for pattern in english_patterns):
        return True

    myanmar_markers = [
        "ကျန်းမာရေး",
        "ဆေး",
        "ရောဂါ",
        "ပရိုဂရမ်",
        "ကုဒ်",
        "သိပ္ပံ",
        "သင်္ချာ",
        "ရာသီဥတု",
        "သတင်း",
        "နိုင်ငံရေး",
    ]
    return any(marker in plain_compact for marker in myanmar_markers)


def _extract_proverb_list_topic(normalized: str) -> str | None:
    has_english_list_request = bool(
        re.search(r"\b(proverbs|all proverbs)\b", normalized)
        and re.search(r"\b(show|tell|give|list|find|what|which)\b", normalized)
    )
    has_english_topic_request = bool(
        re.search(r"\b(show|tell|give|list|find|search|related|about|for)\b", normalized)
        and re.search(r"\b(related to|about|theme|topic|idea|value|situation|success|effort|education|teacher|parent|honesty|work)\b", normalized)
    )
    has_myanmar_list_request = "စကားပုံ" in normalized and any(
        marker in normalized
        for marker in ["တွေ", "များ", "ပြော", "ပြပါ", "ရှာ", "ဖော်ပြ", "ပေး"]
    )
    has_myanmar_topic_request = any(
        marker in normalized
        for marker in [
            "နဲ့ဆိုင်တာ",
            "နှင့်ဆိုင်တာ",
            "နဲ့သက်ဆိုင်တာ",
            "နှင့်သက်ဆိုင်တာ",
            "နဲ့ပတ်သက်တာ",
            "နှင့်ပတ်သက်တာ",
            "အကြောင်း",
            "ဖော်ပြတဲ့",
        ]
    ) and any(marker in normalized for marker in ["ပြပါ", "ပြ", "ရှာ", "ရှာပေး", "ဖော်ပြ", "ပေး", "တွေ", "များ", "ခု"])
    if not has_english_list_request and not has_english_topic_request and not has_myanmar_list_request and not has_myanmar_topic_request:
        return None

    if has_myanmar_list_request or has_myanmar_topic_request:
        topic = normalized
        if "စကားပုံ" in topic:
            topic = topic.split("စကားပုံ", 1)[0]
        topic = re.sub(
            r"(မြန်မာ|နှင့်|နဲ့|နဲ့ဆိုင်တာ|နှင့်ဆိုင်တာ|နဲ့သက်ဆိုင်တာ|နှင့်သက်ဆိုင်တာ|နဲ့ပတ်သက်တာ|နှင့်ပတ်သက်တာ|နဲ့ပတ်သက်တဲ့|နှင့်ပတ်သက်သော|ပတ်သက်တဲ့|ပတ်သက်သော|အကြောင်း|အတွက်|ဖော်ပြတဲ့|တွေ|များ|ပြပါ|ပြ|ရှာပေးပါ|ရှာပေး|ရှာ|ဖော်ပြ|ပေး|ခု)",
            " ",
            topic,
        )
        topic = re.sub(r"(ဆိုင်တာ|သက်ဆိုင်တာ|ပတ်သက်တာ|[၀-၉0-9]+)", " ", topic)
        topic = " ".join(topic.split()).strip(" ?။၊.")
        return topic or normalized

    topic_match = re.search(r"\b(?:about|related to|talk about|for|on)\s+(.+)$", normalized)
    topic = topic_match.group(1) if topic_match else normalized
    topic = re.sub(r"\b(please|proverbs?|all|me|the|some|related|to)\b", " ", topic)
    topic = " ".join(topic.split()).strip(" ?.")
    return topic or normalized


def _extract_requested_proverb_count(normalized: str) -> int | None:
    myanmar_match = re.search(r"([၁၂၃၄၅၆၇၈၉][၀-၉]?)\s*(?:ခု|ပုဒ်|ကြောင်း)?", normalized)
    if myanmar_match:
        return _clamp_requested_count(myanmar_match.group(1).translate(str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")))

    english_match = re.search(r"\b([1-9][0-9]?)\s*(?:proverbs?|items?)?\b", normalized)
    if english_match:
        return _clamp_requested_count(english_match.group(1))

    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    for word, value in word_numbers.items():
        if re.search(rf"\b{word}\b", normalized):
            return value
    return None


def _clamp_requested_count(raw: str) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    return max(1, min(value, PROVERB_LIST_RETRIEVAL_LIMIT))


def _extract_detail_selection(normalized: str) -> str | None:
    has_english_detail = bool(re.search(r"\b(explain|tell|detail|meaning|about|want)\b", normalized))
    has_myanmar_detail = any(marker in normalized for marker in ["နံပါတ်", "ရှင်းပြ", "အဓိပ္ပါယ်", "ပြောပြ"])
    if not has_english_detail and not has_myanmar_detail:
        return None

    number_match = re.search(r"\b(?:number|no\.?|#)?\s*([1-9][0-9]?)\b", normalized)
    if number_match:
        return number_match.group(1)

    myanmar_number_match = re.search(r"(?:နံပါတ်)?\s*([၁၂၃၄၅၆၇၈၉][၀-၉]?)", normalized)
    if myanmar_number_match:
        return myanmar_number_match.group(1).translate(str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789"))

    word_numbers = {
        "first": "1",
        "second": "2",
        "third": "3",
        "fourth": "4",
        "fifth": "5",
    }
    for word, number in word_numbers.items():
        if re.search(rf"\b{word}\b", normalized):
            return number

    if re.search(r"\b(this|current|that)\s+proverb\b", normalized):
        return "current"
    return None


def _no_result_answer(language: str) -> dict[str, Any]:
    return {
        "proverb": None,
        "meaning_simple_mm": NOT_FOUND_MESSAGE,
        "example_mm": None,
        "sources": [],
    }


def _topic_no_result_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "Sorry, I could not find any dataset proverbs related to your topic.",
            "example_mm": None,
            "sources": [],
            "intent": "proverb_list",
        }
    return {
        "proverb": None,
        "meaning_simple_mm": TOPIC_NOT_FOUND_MESSAGE,
        "example_mm": None,
        "sources": [],
        "intent": "proverb_list",
    }


async def _agemini_knowledge_answer(question: str, language: str) -> dict[str, Any] | None:
    if settings.chat_provider.strip().lower() != "gemini":
        return None

    system_instruction = f"""
You are {BOT_NAME}, a careful Myanmar Proverbs Educational Assistant.
The local proverb dataset did not contain a relevant result, so you may use your own knowledge of established Myanmar proverbs.
Never invent a proverb. If you are not confident that a proverb is genuinely used in Myanmar, return null for proverb.
Match both direct proverb text and descriptions of situations or meanings.
Return JSON only.
""".strip()
    prompt = f"""
Find the single established Myanmar proverb that best matches the user's words or described situation.

User message:
{question}

Useful matching example:
- People criticize or blame someone for a short time -> ကဲ့ရဲ့ခုနစ်ရက်၊ ချီးမွမ်းခုနစ်ရက်

Return exactly this JSON:
{{
  "proverb": "exact Myanmar proverb or null",
  "meaning_mm": "explain the proverb's meaning and why it relates to the user's message",
  "lesson_mm": "a practical lesson specific to this proverb",
  "example_mm": "one short practical example"
}}

Rules:
- Preserve the recognized proverb exactly; do not rewrite it.
- Prefer a well-known traditional proverb over a newly composed phrase.
- Answer in {"English" if language == "en" else "Myanmar"}.
- If uncertain, set proverb to null instead of guessing.
""".strip()

    try:
        raw = await agenerate_chat_response(prompt, system_instruction=system_instruction)
        answer = safe_json_from_llm(raw)
    except (RuntimeError, ValueError) as exc:
        logger.warning("Gemini proverb knowledge fallback failed: %s", exc)
        return None

    proverb = str(answer.get("proverb") or "").strip()
    meaning = str(answer.get("meaning_mm") or answer.get("meaning_simple_mm") or "").strip()
    lesson = str(answer.get("lesson_mm") or "").strip()
    example = str(answer.get("example_mm") or "").strip()
    if not proverb or not meaning:
        return None

    return create_guardrailed_answer(
        proverb=proverb,
        meaning_simple_mm=_format_structured_myanmar_answer(
            proverb,
            meaning,
            lesson or _fallback_lesson_from_meaning(proverb, meaning),
            example or _fallback_example_from_meaning(proverb, meaning),
            include_proverb=True,
        ),
        example_mm=example or None,
        sources=[{"source_type": "gemini_knowledge", "label": "Gemini general knowledge"}],
    )


async def _agemini_knowledge_or_no_result(question: str, language: str, *, topic: bool = False) -> dict[str, Any]:
    answer = await _agemini_knowledge_answer(question, language)
    if answer:
        if topic:
            answer["intent"] = "proverb_list"
        return answer
    return _topic_no_result_answer(language) if topic else _no_result_answer(language)


def _out_of_domain_answer(question: str) -> dict[str, Any]:
    return {
        "proverb": None,
        "meaning_simple_mm": OUT_OF_DOMAIN_TEMPLATE.format(question=question.strip()),
        "example_mm": None,
        "sources": [],
        "intent": "unrelated",
    }


def _myanwise_explanation(source: dict[str, Any], language: str = "my") -> str | None:
    proverb = (source.get("proverb") or "").strip()
    if language == "en":
        meaning = (source.get("english_meaning") or source.get("meaning") or source.get("meaning_simple_mm") or "").strip()
        return meaning or None

    meaning = (source.get("meaning") or source.get("meaning_simple_mm") or "").strip()
    if not meaning:
        return None

    example = (source.get("example") or source.get("example_mm") or "").strip()

    lesson = _fallback_lesson_from_meaning(proverb, meaning)
    example_text = example or _fallback_example_from_meaning(proverb, meaning)
    return _format_structured_myanmar_answer(proverb, meaning, lesson, example_text, include_proverb=False)


def _format_structured_myanmar_answer(
    proverb: str,
    meaning: str,
    lesson: str,
    example: str,
    *,
    include_proverb: bool,
) -> str:
    sections = []
    if include_proverb:
        sections.append(f"စကားပုံ:\n{proverb}")
    sections.extend(
        [
            f"အဓိပ္ပါယ်:\n{meaning}",
            f"သင်ခန်းစာ:\n{lesson}",
            f"ဥပမာ:\n{example}",
        ]
    )
    return "\n\n".join(sections)


def _fallback_lesson_from_meaning(proverb: str, meaning: str) -> str:
    normalized = " ".join((meaning or proverb).split())
    if not normalized:
        return "စကားပုံ၏ အဓိပ္ပါယ်ကို သိရှိပြီး သက်ဆိုင်ရာအခြေအနေတွင် မှန်ကန်စွာ အသုံးချရန် သင်ပေးပါတယ်။"

    if any(word in normalized for word in ["ကဲ့ရဲ့", "ချီးမွမ်း", "အပြစ်တင်"]):
        return "လူတွေရဲ့ ကဲ့ရဲ့ခြင်းနဲ့ ချီးမွမ်းခြင်းဟာ အမြဲမတည်ဘဲ အချိန်တိုအတွင်း ပြောင်းလဲနိုင်တာကြောင့် သူတစ်ပါးစကားကြောင့် အလွန်အမင်း စိတ်ပျက်ဝမ်းနည်းခြင်း၊ ဘဝင်မြင့်ခြင်း မဖြစ်ဘဲ ကိုယ်မှန်ကန်သလို တည်ငြိမ်စွာ နေထိုင်ဖို့ သင်ပေးပါတယ်။"

    if any(word in normalized for word in ["နေကောင်း", "ရေချိုး", "ရက်", "ကျန်းမာ"]):
        return "ကျန်းမာရေးကောင်းလာခါစအချိန်မှာ အရာရာကို အလျင်မလိုဘဲ သတိထားလုပ်ဆောင်ရမယ်ဆိုတာ သင်ပေးပါတယ်။ ကိုယ့်ခန္ဓာကိုယ်အခြေအနေကို နားထောင်ပြီး သင့်တော်တဲ့အချိန်မှ လုပ်သင့်တာကို လုပ်တာက ပိုကောင်းပါတယ်။"
    if any(word in normalized for word in ["ဆရာ", "တပည့်", "ပညာ", "သင်"]):
        return "ပညာကို လေးစားပြီး ကြိုးစားသင်ယူရင် တတ်မြောက်မှု တိုးတက်လာနိုင်ကြောင်း သင်ပေးပါတယ်။ ဆရာသင်ပေးတာကို လက်တွေ့ကျင့်သုံးမှ အကျိုးရှိပါတယ်။"
    if any(word in normalized for word in ["မိဘ", "သားသမီး", "ကလေး"]):
        return "မိဘနှင့် သားသမီးအကြား မေတ္တာ၊ စောင့်ရှောက်မှုနှင့် တာဝန်ယူမှုကို တန်ဖိုးထားရမယ်ဆိုတာ သင်ပေးပါတယ်။ မိသားစုအတွင်း အပြန်အလှန်နားလည်မှုရှိဖို့ အရေးကြီးပါတယ်။"
    if any(word in normalized for word in ["ကြိုးစား", "အားထုတ်", "လုံ့လ"]):
        return "အောင်မြင်ချင်ရင် စိတ်မလျှော့ဘဲ ဆက်လက်ကြိုးစားရမယ်ဆိုတာ သင်ပေးပါတယ်။ ခက်ခဲတဲ့အချိန်မှာလည်း ဇွဲရှိရှိ ဆောင်ရွက်ရင် ရလဒ်ကောင်းရနိုင်ပါတယ်။"
    if any(word in normalized for word in ["သတိ", "ဆင်ခြင်", "စဉ်းစား"]):
        return "အလုပ်တစ်ခုမလုပ်ခင် အကျိုးအပြစ်ကို သေချာစဉ်းစားပြီး သတိရှိရှိ ဆောင်ရွက်ရမယ်ဆိုတာ သင်ပေးပါတယ်။ ဆင်ခြင်တုံတရားရှိရင် အမှားနည်းနိုင်ပါတယ်။"
    return f"“{normalized}” ဆိုတဲ့ အဓိပ္ပါယ်ကို နေ့စဉ်ဘဝမှာ နားလည်ပြီး လက်တွေ့ကျင့်သုံးဖို့ ဒီစကားပုံက သင်ပေးပါတယ်။"


def _fallback_example_from_meaning(proverb: str, meaning: str) -> str:
    normalized = " ".join((meaning or proverb).split())
    if any(word in normalized for word in ["ကဲ့ရဲ့", "ချီးမွမ်း", "အပြစ်တင်"]):
        return "ဦးလှကို လူတွေက ယခုအချိန်မှာ ကဲ့ရဲ့အပြစ်တင်နေကြပေမယ့် အချိန်ကြာလာတဲ့အခါ အဲဒီစကားတွေ လျော့နည်းပျောက်ကွယ်သွားတာမျိုး ဖြစ်ပါတယ်။"
    if any(word in normalized for word in ["နေကောင်း", "ရေချိုး", "ရက်", "ကျန်းမာ"]):
        return "ဖျားပြီး နေကောင်းလာခါစ ကျောင်းသားတစ်ယောက်က ချက်ချင်းအေးတဲ့ရေနဲ့ မချိုးဘဲ ခန္ဓာကိုယ်အခြေအနေကောင်းမှ ရေချိုးတာမျိုး ဖြစ်ပါတယ်။"
    if any(word in normalized for word in ["ဆရာ", "တပည့်", "ပညာ", "သင်"]):
        return "ကျောင်းသားတစ်ယောက်က ဆရာသင်ပေးတဲ့နည်းကို နေ့တိုင်းလေ့ကျင့်လို့ စာမေးပွဲမှာ ပိုမိုကောင်းမွန်တဲ့ရလဒ်ရတာမျိုး ဖြစ်ပါတယ်။"
    return f"“{proverb}” ဆိုတဲ့ စကားပုံကို {normalized} ဆိုတဲ့ သဘောနဲ့ ကိုက်ညီတဲ့အခြေအနေမျိုးမှာ အသုံးပြုနိုင်ပါတယ်။"


def _teacher_style_meaning(source: dict[str, Any], language: str = "my") -> str | None:
    meaning = (
        (source.get("english_meaning") or source.get("meaning") or "").strip()
        if language == "en"
        else (source.get("meaning") or "").strip()
    )
    if not meaning:
        return None

    proverb = (source.get("proverb") or "").strip()

    if language == "en":
        if "teacher" in proverb.lower() and "student" in proverb.lower():
            return "A student can become more skilled or successful than the teacher."
        return meaning

    formatted = _myanwise_explanation(source, language)
    if formatted:
        return formatted

    if "ဆရာ့ထက်" in proverb and "တပည့်" in proverb:
        return "ကလေးတို့ရေ၊ တပည့်က ကြိုးစားလို့ ဆရာထက် ပိုတော်လာတဲ့အခါ ဒီစကားပုံကို သုံးတာပါ။"

    return f" {meaning} "


def _looks_teacher_styled(meaning: str | None, language: str) -> bool:
    normalized_meaning = (meaning or "").strip()
    if not normalized_meaning:
        return False
    if language == "en":
        return normalized_meaning.startswith(("In simple words", "This proverb means"))
    return bool(re.match(r"^(အဓိပ္ပါယ်:|ကလေးတို့ရေ|ဆိုလိုတာက|လွယ်လွယ်ပြောရရင်)", normalized_meaning))


def _role_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": (
                f"I am {BOT_NAME}, a Myanmar Proverbs Educational Assistant. "
                "I use only the retrieved proverb dataset to explain Myanmar proverbs in a simple, student-friendly way."
            ),
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": (
           f"ကျွန်ုပ်သည် {BOT_NAME} ဖြစ်ပါသည်။ "
"မြန်မာစကားပုံများကို ဒေတာအတွင်းမှ ရှာဖွေပြီး အသုံးပြုသူများ နားလည်လွယ်ကူစေရန် "
"အဓိပ္ပါယ်၊ သင်ခန်းစာနှင့် လက်တွေ့အသုံးချနိုင်သော ဥပမာများဖြင့် ရှင်းပြပေးသော "
"ပညာရေးအထောက်အကူပြု AI ဖြစ်ပါသည်။"
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


def _acknowledgement_answer(language: str) -> dict[str, Any]:
    if language == "en":
        return {
            "proverb": None,
            "meaning_simple_mm": "Okay! Ask me anytime if you want another Myanmar proverb or more explanation.",
            "example_mm": None,
            "sources": [],
        }

    return {
        "proverb": None,
        "meaning_simple_mm": "ဟုတ်ကဲ့ပါ။ နောက်ထပ် စကားပုံတစ်ခု ဒါမှမဟုတ် အသေးစိတ်ရှင်းပြချက် လိုချင်ရင် မေးနိုင်ပါတယ်။",
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
    english_meaning = row.get("english_meaning")
    example = row["example"]
    doc = (
        f"keyword: {keyword or ''}\n"
        f"proverb: {proverb}\n"
        f"meaning: {meaning or ''}\n"
        f"english_meaning: {english_meaning or ''}\n"
        f"example: {example or ''}"
    )
    metadata = {
        "keyword": keyword,
        "proverb": proverb,
        "meaning": meaning,
        "english_meaning": english_meaning,
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
                "category": metadata.get("category"),
                "proverb": metadata.get("proverb") or "",
                "meaning": metadata.get("meaning"),
                "english_meaning": metadata.get("english_meaning"),
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
        "english_meaning": updates.get("english_meaning", current.get("english_meaning")),
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
    sources = _sources_with_ids(sources)
    best = sources[0]
    proverb = best.get("proverb")
    answer = create_guardrailed_answer(
        proverb=proverb,
        meaning_simple_mm=_teacher_style_meaning(best, language),
        example_mm=None if language == "en" else best.get("example"),
        sources=sources,
    )
    answer["language"] = language
    if proverb:
        answer["proverb_id"] = _row_id(best.get("keyword"), str(proverb))
    return answer


def _gemini_unavailable_answer(source: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    proverb = (source.get("proverb") or "").strip()
    meaning = (source.get("meaning") or "").strip()
    example = (source.get("example") or "").strip()
    lesson = _fallback_lesson_from_meaning(proverb, meaning)
    example_text = example or _fallback_example_from_meaning(proverb, meaning)
    return create_guardrailed_answer(
        proverb=proverb or None,
        meaning_simple_mm=_format_structured_myanmar_answer(
            proverb,
            meaning,
            lesson,
            example_text,
            include_proverb=True,
        ),
        example_mm=example_text,
        sources=sources,
    )


async def _aanswer_from_best_source(sources: list[dict[str, Any]], language: str = "my") -> dict[str, Any]:
    sources = _sources_with_ids(sources)
    if language == "en":
        return _answer_from_best_source(sources, language)

    if settings.chat_provider.strip().lower() != "gemini":
        return _answer_from_best_source(sources, language)

    best = sources[0]
    proverb = (best.get("proverb") or "").strip()
    meaning = (best.get("meaning") or "").strip()
    english_meaning = (best.get("english_meaning") or "").strip()
    example = (best.get("example") or "").strip()
    if not proverb or not meaning:
        return _answer_from_best_source(sources, language)

    system_instruction = f"""
You are {BOT_NAME}, a Myanmar Proverbs Educational Assistant.
The provided dataset record is the authority for the proverb and its meaning.
Use Gemini's Myanmar language, reasoning, and teaching ability to explain the lesson naturally.
Do not invent a different proverb. Do not replace or contradict the dataset meaning.
Return JSON only.
""".strip()
    record_json = json.dumps(
        {
            "proverb": proverb,
            "meaning": meaning,
            "english_meaning": english_meaning or None,
            "example": example or None,
        },
        ensure_ascii=False,
    )
    prompt = f"""
Generate ONLY the lesson and example for this Myanmar proverb dataset record.
Do not generate, rewrite, or paraphrase the proverb.
Do not generate, rewrite, summarize, or paraphrase the meaning.
The backend will copy the exact proverb and exact meaning from the dataset.

Dataset record JSON:
{record_json}

Return exactly this JSON:
{{
  "lesson_mm": "...",
  "example_mm": "..."
}}

Rules:
- lesson_mm is the သင်ခန်းစာ section only.
- lesson_mm must transform the dataset meaning into a practical life lesson.
- lesson_mm must explain how people can apply this proverb in real situations.
- lesson_mm must be easy for students to understand.
- lesson_mm must not copy the dataset meaning word-for-word.
- example_mm is the ဥပမာ section only.
- example_mm must be a simple real-life example based on the proverb and lesson.
- If the dataset has an example, you may use it as inspiration, but write a natural student-friendly example.
- Use simple Myanmar language.
""".strip()

    try:
        raw = await agenerate_chat_response(prompt, system_instruction=system_instruction)
        answer = safe_json_from_llm(raw)
    except (RuntimeError, ValueError) as exc:
        logger.warning("Gemini lesson/example generation failed: %s", exc)
        return _gemini_unavailable_answer(best, sources)

    lesson = (answer.get("lesson_mm") or "").strip()
    generated_example = (answer.get("example_mm") or "").strip()
    if not lesson:
        logger.warning("Gemini lesson/example generation returned no lesson.")
        return _gemini_unavailable_answer(best, sources)

    final_example = generated_example or example or "နေ့စဉ်ဘဝမှာ အလားတူအခြေအနေကြုံရင် ဒီစကားပုံကို သုံးပြီး ရှင်းပြနိုင်ပါတယ်။"
    meaning_simple_mm = _format_structured_myanmar_answer(
        proverb,
        meaning,
        lesson,
        final_example,
        include_proverb=True,
    )
    return create_guardrailed_answer(
        proverb=proverb,
        meaning_simple_mm=meaning_simple_mm,
        example_mm=final_example,
        sources=sources,
    ) | {"proverb_id": _row_id(best.get("keyword"), proverb), "language": language}


async def _aproverb_list_answer(
    sources: list[dict[str, Any]],
    topic: str,
    language: str,
    *,
    offset: int = 0,
    requested_count: int | None = None,
) -> dict[str, Any]:
    all_items = [source for source in sources if source.get("proverb")]
    all_items = _sources_with_ids(all_items)
    page_start = max(0, offset)
    page_size = requested_count or PROVERB_LIST_PAGE_SIZE
    page_items = all_items[page_start : page_start + page_size]
    if not page_items:
        return _topic_no_result_answer(language)

    lines: list[str] = []
    if requested_count and len(page_items) < requested_count:
        if language == "en":
            lines.append(f"I found only {len(page_items)} dataset proverbs related to {topic}.")
        else:
            lines.append(f"သင်မေးထားသော အကြောင်းအရာနှင့် သက်ဆိုင်သော စကားပုံများကို ဒေတာအတွင်း {len(page_items)} ခုသာ တွေ့ရှိပါသည်။")

    for index, item in enumerate(page_items, start=page_start + 1):
        formatted = await _answer_sections_for_source(item, language, include_proverb=False)
        if language == "en":
            lines.append(f"Proverb ({index}):\n{item.get('proverb')}\n\n{formatted}")
        else:
            lines.append(f"စကားပုံ ({index}):\n{item.get('proverb')}\n\n{formatted}")

    has_more = requested_count is None and page_start + page_size < len(all_items)
    guidance = None
    if has_more:
        guidance = (
            "You can ask 'show more' for more dataset proverbs."
            if language == "en"
            else "နောက်ထပ်ကြည့်ချင်ရင် 'ထပ်ပြပါ' လို့ မေးနိုင်ပါတယ်။"
        )
    return {
        "proverb": None,
        "meaning_simple_mm": "\n\n".join(lines),
        "example_mm": guidance,
        "sources": all_items,
        "intent": "proverb_list",
        "list_offset": page_start + page_size if has_more else page_start,
        "requested_count": requested_count,
    }


async def _answer_sections_for_source(source: dict[str, Any], language: str, *, include_proverb: bool) -> str:
    proverb = (source.get("proverb") or "").strip()
    meaning = (source.get("meaning") or "").strip()
    if language == "en":
        return meaning
    if settings.chat_provider.strip().lower() == "gemini":
        answer = await _aanswer_from_best_source([source], language)
        text = (answer.get("meaning_simple_mm") or "").strip()
        if text:
            if include_proverb:
                return text
            return re.sub(r"^စကားပုံ:\n.*?\n\n", "", text, count=1, flags=re.DOTALL)
    return _myanwise_explanation(source, language) or f"အဓိပ္ပါယ်:\n{meaning}"


def _english_example_from_source(source: dict[str, Any]) -> str:
    meaning = (source.get("english_meaning") or source.get("meaning") or "").strip().lower()
    if any(word in meaning for word in ["teacher", "student", "learn", "education", "knowledge"]):
        return "For example, a student practices what a teacher explains and slowly becomes more confident and skilled."
    if any(word in meaning for word in ["health", "sick", "recover", "water", "bath"]):
        return "For example, after recovering from illness, a person waits until their body feels strong before doing something that may affect their health."
    if any(word in meaning for word in ["speak", "conversation", "word", "tact", "expression"]):
        return "For example, when someone gives advice, they choose gentle words instead of speaking too directly and hurting another person."
    return "For example, when someone faces a situation, they think carefully about the result before choosing the most suitable action."


def _selected_source_from_previous(previous_answer: dict[str, Any] | None, selection: str) -> dict[str, Any] | None:
    if not previous_answer:
        return None

    sources = previous_answer.get("sources") or []
    if selection == "current":
        if previous_answer.get("proverb"):
            return {
                **(sources[0] if sources and isinstance(sources[0], dict) else {}),
                "proverb": previous_answer.get("proverb"),
                "meaning": previous_answer.get("meaning_simple_mm") or previous_answer.get("meaning"),
                "example": previous_answer.get("example_mm") or previous_answer.get("example"),
            }
        return sources[0] if sources else None

    try:
        index = int(selection) - 1
    except ValueError:
        return None
    if index < 0 or index >= len(sources):
        return None
    return sources[index]


async def _follow_up_answer(
    intent_data: dict[str, Any],
    previous_answer: dict[str, Any] | None,
    language: str,
) -> dict[str, Any]:
    action = str(intent_data.get("action") or "detail")
    if action == "english_list":
        sources = previous_answer.get("sources", []) if previous_answer else []
        items = [source for source in sources if source.get("proverb")]
        if not items:
            return _no_result_answer("en")

        lines = []
        for index, item in enumerate(items, start=1):
            proverb = (item.get("proverb") or "").strip()
            english_meaning = (item.get("english_meaning") or "").strip()
            meaning = (item.get("meaning") or item.get("meaning_simple_mm") or "").strip()
            example = (item.get("example") or item.get("example_mm") or "").strip()
            explanation = english_meaning or meaning
            english_example = example or _english_example_from_source(item)
            lines.append(
                f"Proverb ({index}):\n{proverb}\n\n"
                f"Meaning:\n{explanation}\n\n"
                f"Example:\n{english_example}"
            )

        return {
            "proverb": None,
            "meaning_simple_mm": "\n\n".join(lines),
            "example_mm": None,
            "sources": items,
            "intent": "proverb_list",
        }

    if action == "show_more_list":
        sources = previous_answer.get("sources", []) if previous_answer else []
        topic = str(intent_data.get("topic") or "").strip()
        offset = int((previous_answer or {}).get("list_offset") or PROVERB_LIST_PAGE_SIZE)
        if not sources:
            return _topic_no_result_answer(language)
        if offset >= len(sources):
            return {
                **await _aproverb_list_answer(sources, topic or "အရင်မေးထားတဲ့ အကြောင်းအရာ", language, offset=max(0, len(sources) - PROVERB_LIST_PAGE_SIZE)),
                "example_mm": "No more proverbs found in the retrieved dataset list." if language == "en" else "ယခုရှာတွေ့ထားတဲ့ စာရင်းထဲမှာ နောက်ထပ် စကားပုံ မရှိတော့ပါ။",
            }
        return await _aproverb_list_answer(sources, topic or "အရင်မေးထားတဲ့ အကြောင်းအရာ", language, offset=offset)

    source = _selected_source_from_previous(
        previous_answer,
        str(intent_data.get("selection") or "current"),
    )
    if not source:
        return _no_result_answer(language)

    proverb = (source.get("proverb") or "").strip()
    meaning = (source.get("meaning") or source.get("meaning_simple_mm") or "").strip()
    example = (source.get("example") or source.get("example_mm") or "").strip()
    sources = previous_answer.get("sources", []) if previous_answer else []

    if action == "english_meaning":
        english_meaning = (source.get("english_meaning") or "").strip()
        answer = create_guardrailed_answer(proverb, english_meaning or meaning, None, sources)
        answer["language"] = "en"
        return answer

    if action == "example":
        message = example or ("No example is stored for this proverb yet." if language == "en" else "ဤစကားပုံအတွက် ဥပမာ မရှိသေးပါ။")
        return create_guardrailed_answer(proverb, message, example or None, sources)

    detail_sources = [source]
    return await _aanswer_from_best_source(detail_sources, language)


def rag_answer(
    user_question: str,
    previous_answer: dict[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asyncio.run(arag_answer(user_question, previous_answer=previous_answer, memory=memory))


async def arag_answer(
    user_question: str,
    previous_answer: dict[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_intent = await _aclassify_user_intent(user_question)
    intent = user_intent["intent"]
    action = user_intent.get("action")
    response_language = "my" if action == "translate_myanmar" else "en" if action == "english_meaning" else user_intent["language"]
    previous_answer = previous_answer or ConversationMemoryService.previous_answer(memory)

    # Conversational intents are resolved before validation and retrieval. This
    # also permits single-codepoint emoji acknowledgements.
    if intent == "small_talk":
        return _greeting_answer(response_language)
    if intent == "gratitude":
        return _thanks_answer(response_language)
    if intent == "confirmation":
        return _acknowledgement_answer(response_language)
    if intent == "farewell":
        return _goodbye_answer(response_language)
    if intent == "role":
        return _role_answer(response_language)
    if intent == "unrelated":
        return _out_of_domain_answer(user_question)

    is_valid, _error_msg = validate_question(user_question)
    if not is_valid:
        return _no_result_answer(response_language)

    if intent == "follow_up" and action == "another_similar":
        topic = str((memory or {}).get("last_topic") or "").strip()
        if not topic:
            return _no_result_answer(response_language)
        sources = await aretrieve_context(topic, top_k=max(5, settings.rag_top_k))
        last_proverb = (previous_answer or {}).get("proverb")
        alternatives = [item for item in sources if item.get("proverb") != last_proverb]
        if not alternatives or not is_context_relevant(alternatives):
            return _no_result_answer(response_language)
        return await _aanswer_from_best_source(alternatives, response_language)

    if intent == "follow_up":
        return await _follow_up_answer(user_intent, previous_answer, response_language)

    if intent == "generate_image" and previous_answer:
        return await _follow_up_answer(user_intent, previous_answer, response_language)

    if intent == "proverb_list":
        topic = str(user_intent.get("topic") or user_question).strip()
        requested_count = user_intent.get("requested_count")
        result_count = int(requested_count or PROVERB_LIST_RETRIEVAL_LIMIT)
        sources = await aretrieve_context(topic, top_k=max(result_count, settings.rag_top_k))
        if not sources or not is_context_relevant(sources):
            return await _agemini_knowledge_or_no_result(topic, response_language, topic=True)
        return await _aproverb_list_answer(sources, topic, response_language, requested_count=requested_count)

    try:
        chain_result = await arun_rag_chain(user_question, language=response_language)
    except (ValueError, RuntimeError):
        sources = await aretrieve_context(user_question, top_k=settings.rag_top_k)
        if not sources:
            return await _agemini_knowledge_or_no_result(user_question, response_language)
        return await _aanswer_from_best_source(sources, response_language)

    sources = _sources_with_ids(chain_result.get("sources") or [])
    if not sources:
        return await _agemini_knowledge_or_no_result(user_question, response_language)

    if not is_context_relevant(sources):
        return await _agemini_knowledge_or_no_result(user_question, response_language)

    try:
        answer = parse_rag_answer(chain_result.get("text") or "")
    except (ValueError, RuntimeError):
        return await _aanswer_from_best_source(sources, response_language)

    if not is_answer_valid(answer):
        if not answer.get("proverb"):
            return await _agemini_knowledge_or_no_result(user_question, response_language)
        return await _aanswer_from_best_source(sources, response_language)

    best = sources[0]
    source_meaning = (best.get("meaning") or "").strip()
    answer_meaning = (answer.get("meaning_simple_mm") or "").strip()
    if answer_meaning == source_meaning:
        return await _aanswer_from_best_source(sources, response_language)
    elif response_language == "en" and not answer_meaning.startswith("In simple words"):
        answer["meaning_simple_mm"] = _teacher_style_meaning(best, response_language)
    elif response_language == "my" and not _looks_teacher_styled(answer_meaning, response_language):
        return await _aanswer_from_best_source(sources, response_language)

    if "sources" not in answer or not answer["sources"]:
        answer["sources"] = sources

    final_answer = create_guardrailed_answer(
        proverb=answer.get("proverb"),
        meaning_simple_mm=answer.get("meaning_simple_mm"),
        example_mm=None if response_language == "en" else answer.get("example_mm"),
        sources=answer.get("sources", []),
    )
    final_answer["language"] = response_language
    if best.get("proverb"):
        final_answer["proverb_id"] = _row_id(best.get("keyword"), str(best.get("proverb")))
    return final_answer

