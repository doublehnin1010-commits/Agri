"""
Guardrails for Myanmar Proverbs Tutor.
Ensures responses stay within scope and follow system rules.
"""

from typing import Any

from app.core.config import settings


# Burmese error message when context is empty or irrelevant
NO_PROVERB_MESSAGE = "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။"


def is_context_relevant(
    context: list[dict[str, Any]], min_relevance_score: float | None = None
) -> bool:
    """
    Check if retrieved context is relevant to the query.
    
    Args:
        context: List of retrieved proverbs with scores
        min_relevance_score: Minimum relevance threshold for semantic similarity (higher = more relevant)
                           If None, uses the configured RAG retrieval thresholds.
    
    Returns:
        True if context contains at least one relevant proverb, False otherwise
    """
    if not context:
        return False

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

    # Check if any proverb has a score accepted by the retrieval layer.
    # For semantic search: similarity score (higher is better, range 0-1)
    # For lexical search: distance score (lower is better, range 0-1)
    for item in context:
        # Try semantic similarity first (new approach)
        similarity = item.get("similarity")
        if similarity is not None:
            if similarity >= semantic_threshold:
                return True
        
        # Fall back to distance score (old approach)
        score = item.get("score")
        if score is not None and score <= (1.0 - lexical_threshold):
            return True

    return False


def validate_question(question: str) -> tuple[bool, str | None]:
    """
    Validate if a question is about Myanmar proverbs.
    
    Args:
        question: User's question
    
    Returns:
        Tuple of (is_valid, error_message)
        If valid, returns (True, None)
        If invalid, returns (False, error_message_in_burmese)
    """
    if not question or not question.strip():
        return False, NO_PROVERB_MESSAGE

    # Question should not be too short (to avoid single word queries)
    # This is a soft check; empty context will handle it anyway
    return True, None


def create_guardrailed_answer(
    proverb: str | None,
    meaning_simple_mm: str | None,
    example_mm: str | None,
    sources: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """
    Create a properly formatted answer with all guardrail checks.
    
    Args:
        proverb: The proverb text
        meaning_simple_mm: Simple Burmese meaning
        example_mm: Simple Burmese example
        sources: Retrieved context sources
    
    Returns:
        Formatted answer dict
    """
    return {
        "proverb": proverb,
        "meaning_simple_mm": meaning_simple_mm,
        "example_mm": example_mm,
        "sources": sources or [],
    }


def create_no_result_answer() -> dict[str, Any]:
    """
    Create an error response when no relevant proverb is found.
    
    Returns:
        Answer dict with error message
    """
    return {
        "proverb": None,
        "meaning_simple_mm": NO_PROVERB_MESSAGE,
        "example_mm": None,
        "sources": [],
    }


def is_answer_valid(answer: dict[str, Any]) -> bool:
    """
    Check if generated answer contains valid proverb information.
    
    Args:
        answer: Generated answer dict from the local LLM
    
    Returns:
        True if answer contains meaningful content, False otherwise
    """
    proverb = (answer.get("proverb") or "").strip()
    meaning = (answer.get("meaning_simple_mm") or "").strip()

    # Answer must contain both proverb and meaningful explanation
    if not proverb or not meaning:
        return False

    return True
