"""Guardrails for Myanmar Proverbs Tutor.

Ensures responses stay within scope, maintain high quality, and adhere to
system rules.
"""

import logging
from typing import Any, Final

from app.core.config import settings

# Setup structured logging for production observability
logger = logging.getLogger(__name__)

# User-facing UX fallback messages tailored for a friendly Myanmar AI Assistant
DEFAULT_FALLBACK_MESSAGE: Final[str] = (
    "မင်္ဂလာပါ။ ဝမ်းနည်းပါတယ်ခင်ဗျာ၊ သင်ရှာဖွေနေတဲ့ စကားပုံကို "
    "ကျွန်ုပ်၏ စကားပုံဒေတာဘေ့စ်ထဲမှာ ရှာမတွေ့ပါဘူး။ အခြားစကားပုံများဖြင့် ပြန်လည်မေးမြန်းနိုင်ပါတယ်။"
)
EMPTY_INPUT_MESSAGE: Final[str] = (
    "ကျေးဇူးပြု၍ စကားပုံ သို့မဟုတ် စကားပုံနှင့်ပတ်သက်သည့် မေးခွန်းတစ်ခုခုကို အနည်းငယ်အကျယ်တဝင့် ရိုက်ထည့်ပေးပါခင်ဗျာ။"
)


class ProverbGuardrail:
    """Handles validation, relevance filtering, and standard response formatting

    for the Myanmar Proverbs Tutor system.
    """

    @staticmethod
    def is_context_relevant(
        context: list[dict[str, Any]], min_relevance_score: float | None = None
    ) -> bool:
        """Evaluates whether the retrieved RAG context meets similarity

        thresholds.

        Args:
            context: List of retrieved proverbs with their respective match
              scores.
            min_relevance_score: Override threshold for semantic similarity. If
              None, configuration defaults are applied.

        Returns:
            True if at least one document passes the threshold criteria, False
            otherwise.
        """
        if not context:
            logger.warning("Relevance check invoked with empty context data.")
            return False

        # Resolve thresholds gracefully using configuration fallbacks
        semantic_threshold = (
            min_relevance_score
            if min_relevance_score is not None
            else settings.rag_semantic_threshold
        )
        lexical_threshold = (
            min_relevance_score
            if min_relevance_score is not None
            else settings.rag_min_lexical_similarity
        )

        # Lexical limit translated directly to mirror standard distance conditions
        max_allowed_distance = 1.0 - lexical_threshold

        for item in context:
            # 1. Primary Check: Semantic Similarity (Higher score is better, range 0.0 - 1.0)
            similarity = item.get("similarity")
            if similarity is not None and similarity >= semantic_threshold:
                return True

            # 2. Fallback Check: Lexical Distance (Lower score is better, range 0.0 - 1.0)
            score = item.get("score")
            if score is not None and score <= max_allowed_distance:
                return True

        return False

    @staticmethod
    def validate_question(question: str | None) -> tuple[bool, str | None]:
        """Validates incoming user queries for basic integrity and input length.

        Args:
            question: Raw input string provided by the user.

        Returns:
            A tuple of (is_valid, error_message).
            If valid, returns (True, None).
            If invalid, returns (False, dynamic_burmese_error_message).
        """
        if not question or not question.strip():
            return False, EMPTY_INPUT_MESSAGE

        cleaned_question = question.strip()

        # Guardrail against overly short or ambiguous single-character inputs
        if len(cleaned_question) < 2:
            return False, EMPTY_INPUT_MESSAGE

        return True, None

    @staticmethod
    def create_guardrailed_answer(
        proverb: str | None,
        meaning_simple_mm: str | None,
        example_mm: str | None,
        sources: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Constructs a production-ready, structured schema response.

        Args:
            proverb: The formal name/text of the Myanmar proverb.
            meaning_simple_mm: A simplified explanation in Myanmar text.
            example_mm: An illustrative real-life context example in Myanmar.
            sources: Metadata list containing RAG reference documents.

        Returns:
            A standardized dictionary schema for downstream consumption.
        """
        return {
            "proverb": proverb.strip() if proverb else None,
            "meaning_simple_mm": (
                meaning_simple_mm.strip() if meaning_simple_mm else None
            ),
            "example_mm": example_mm.strip() if example_mm else None,
            "sources": sources if sources is not None else [],
        }

    @classmethod
    def create_no_result_answer(
        cls, message: str = DEFAULT_FALLBACK_MESSAGE
    ) -> dict[str, Any]:
        """Constructs a structured fallback response when no metrics pass standard

        filters.

        Args:
            message: Custom fallback text matching the expected UX criteria.

        Returns:
            An empty answer dictionary populated with user-facing warnings.
        """
        return cls.create_guardrailed_answer(
            proverb=None,
            meaning_simple_mm=message,
            example_mm=None,
            sources=[],
        )

    @staticmethod
    def is_answer_valid(answer: dict[str, Any]) -> bool:
        """Validates LLM generations for structural completeness before serving

        users.

        Args:
            answer: Generated dictionary payload under evaluation.

        Returns:
            True if both the proverb text and semantic breakdown exist, False
            otherwise.
        """
        if not answer or not isinstance(answer, dict):
            return False

        proverb = (answer.get("proverb") or "").strip()
        meaning = (answer.get("meaning_simple_mm") or "").strip()

        # Enforce that an answer is invalid if it misses the core proverb structure or defaults to standard error text
        if not proverb or not meaning or meaning == DEFAULT_FALLBACK_MESSAGE:
            logger.warning("Generated output failed validation safety checks.")
            return False

        return True


# Keep the module-level API used by the RAG service and existing callers.
# The implementation lives on ProverbGuardrail, while these aliases preserve
# backward compatibility with the original function-based interface.
is_context_relevant = ProverbGuardrail.is_context_relevant
validate_question = ProverbGuardrail.validate_question
create_guardrailed_answer = ProverbGuardrail.create_guardrailed_answer
create_no_result_answer = ProverbGuardrail.create_no_result_answer
is_answer_valid = ProverbGuardrail.is_answer_valid
