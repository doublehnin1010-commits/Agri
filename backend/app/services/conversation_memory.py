"""Conversation state management for the existing MongoDB chat records.

The service is intentionally storage-agnostic: the chat router loads/saves the
returned dictionary in its existing ``chat_history`` document. This avoids a
second database and keeps memory scoped to one conversation.
"""

from __future__ import annotations

from typing import Any


class ConversationMemoryService:
    """Build, read, and update compact state used by conversational routing."""

    MAX_HISTORY_ITEMS = 20

    @classmethod
    def load(cls, conversation: dict[str, Any] | None) -> dict[str, Any]:
        if not conversation:
            return cls.empty()

        stored = conversation.get("memory")
        if isinstance(stored, dict):
            return {**cls.empty(), **stored}

        # Backfill state for conversations created before memory was added.
        messages = conversation.get("messages") or []
        for item in reversed(messages):
            answer = item.get("answer") if isinstance(item, dict) else None
            if isinstance(answer, dict) and (answer.get("proverb") or answer.get("sources")):
                return cls.update(cls.empty(), "proverb_query", answer)

        legacy_answer = conversation.get("assistant_message")
        if isinstance(legacy_answer, dict):
            return cls.update(cls.empty(), "proverb_query", legacy_answer)
        return cls.empty()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {
            "last_intent": None,
            "last_proverb": None,
            "last_topic": None,
            "last_meaning": None,
            "last_example": None,
            "last_sources": [],
            "history": [],
        }

    @classmethod
    def previous_answer(cls, memory: dict[str, Any] | None) -> dict[str, Any] | None:
        if not memory:
            return None

        sources = memory.get("last_sources") or []
        if not memory.get("last_proverb") and not sources:
            return None

        return {
            "proverb": memory.get("last_proverb"),
            "meaning_simple_mm": memory.get("last_meaning"),
            "example_mm": memory.get("last_example"),
            "sources": sources,
        }

    @classmethod
    def update(
        cls,
        memory: dict[str, Any] | None,
        intent: str,
        answer: dict[str, Any],
        *,
        topic: str | None = None,
        user_message: str | None = None,
    ) -> dict[str, Any]:
        state = {**cls.empty(), **(memory or {})}
        state["last_intent"] = intent

        sources = answer.get("sources") or []
        proverb = answer.get("proverb")
        if proverb:
            state["last_proverb"] = proverb
            state["last_meaning"] = answer.get("meaning_simple_mm") or answer.get("meaning")
            state["last_example"] = answer.get("example_mm") or answer.get("example")
            state["last_sources"] = sources
        elif intent == "proverb_list" and sources:
            state["last_sources"] = sources

        if topic:
            state["last_topic"] = topic
        elif proverb and sources:
            first = sources[0] if isinstance(sources[0], dict) else {}
            state["last_topic"] = first.get("category") or first.get("keyword") or state.get("last_topic")

        history = list(state.get("history") or [])
        history.append({"role": "user", "content": user_message or "", "intent": intent})
        history.append(
            {
                "role": "assistant",
                "proverb": answer.get("proverb"),
                "content": answer.get("meaning_simple_mm") or "",
            }
        )
        state["history"] = history[-cls.MAX_HISTORY_ITEMS :]
        return state
