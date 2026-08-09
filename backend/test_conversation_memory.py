import asyncio
import http.client
from unittest.mock import AsyncMock, patch

from app.services.conversation_memory import ConversationMemoryService
from app.services.rag import arag_answer, classify_user_intent


def test_non_knowledge_intents_skip_rag():
    messages = ["ok", "okay", "yes", "yeah", "thanks", "thank you", "hello", "bye", "👍", "👌", "😀"]

    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            for message in messages:
                answer = await arag_answer(message)
                assert answer["proverb"] is None
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_myanmar_role_question_skips_rag():
    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("မင်းက ဘာတွေလုပ်နိုင်သလဲ")

            assert answer["proverb"] is None
            assert "မြန်မာစကားပုံ" in answer["meaning_simple_mm"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_out_of_domain_football_question_skips_rag():
    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("explain about football")

            assert answer["proverb"] is None
            assert answer["intent"] == "unrelated"
            assert "မြန်မာ့ရိုးရာစကားပုံများနှင့် မသက်ဆိုင်ပါဘူး" in answer["meaning_simple_mm"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_gemini_domain_classifier_blocks_unknown_general_topic():
    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                return_value='{"domain":"out_of_domain"}',
            ),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("explain investment banking")

            assert answer["proverb"] is None
            assert answer["intent"] == "unrelated"
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_follow_up_uses_memory_without_rag():
    memory = {
        **ConversationMemoryService.empty(),
        "last_proverb": "ဆင်စွယ်မှန် ပိုးမစား",
        "last_meaning": "စစ်မှန်သောအရာသည် မပျက်စီးနိုင်ဟု ဆိုလိုသည်။",
        "last_example": "ရိုးသားမှုကို အခက်အခဲက မဖျက်ဆီးနိုင်ပါ။",
        "last_sources": [
            {
                "proverb": "ဆင်စွယ်မှန် ပိုးမစား",
                "meaning": "စစ်မှန်သောအရာသည် မပျက်စီးနိုင်ဟု ဆိုလိုသည်။",
                "english_meaning": "What is genuine endures.",
                "example": "ရိုးသားမှုကို အခက်အခဲက မဖျက်ဆီးနိုင်ပါ။",
            }
        ],
    }

    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            english = await arag_answer("English meaning", memory=memory)
            example = await arag_answer("Give example", memory=memory)
            assert english["meaning_simple_mm"] == "What is genuine endures."
            assert example["example_mm"] == memory["last_example"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_numbered_follow_up_uses_remembered_list_without_rag():
    memory = {
        **ConversationMemoryService.empty(),
        "last_sources": [
            {
                "proverb": "First proverb",
                "meaning": "First meaning",
                "english_meaning": "First English meaning",
                "example": "First example",
            },
            {
                "proverb": "Second proverb",
                "meaning": "Second meaning",
                "english_meaning": "Second English meaning",
                "example": "Second example",
            },
        ],
    }

    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("Explain number 2", memory=memory)

            assert answer["proverb"] == "Second proverb"
            assert "Second meaning" in answer["meaning_simple_mm"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_show_more_uses_next_remembered_list_page_without_rag():
    sources = [
        {
            "proverb": f"Proverb {index}",
            "meaning": f"Meaning {index}",
            "example": f"Example {index}",
        }
        for index in range(1, 8)
    ]
    memory = {
        **ConversationMemoryService.empty(),
        "last_sources": sources,
        "last_list_offset": 5,
    }

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("show more", memory=memory)

            assert answer["intent"] == "proverb_list"
            assert "Proverb (6):\nProverb 6" in answer["meaning_simple_mm"]
            assert "Proverb (7):\nProverb 7" in answer["meaning_simple_mm"]
            assert "Proverb (1):\nProverb 1" not in answer["meaning_simple_mm"]
            assert answer["sources"] == sources
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_english_follow_up_explains_previous_proverb_list_without_rag():
    memory = {
        **ConversationMemoryService.empty(),
        "last_sources": [
            {
                "proverb": "First proverb",
                "meaning": "First Myanmar meaning",
                "english_meaning": "First English meaning",
                "example": "First example",
            },
            {
                "proverb": "Second proverb",
                "meaning": "Second Myanmar meaning",
                "english_meaning": "Second English meaning",
                "example": "Second example",
            },
        ],
    }

    async def run():
        with (
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("explain previous proverbs with english", memory=memory)

            assert answer["intent"] == "proverb_list"
            assert "Proverb (1):\nFirst proverb" in answer["meaning_simple_mm"]
            assert "ဒီစကားပုံက First English meaning" in answer["meaning_simple_mm"]
            assert "First English meaning" in answer["meaning_simple_mm"]
            assert "Proverb (2):\nSecond proverb" in answer["meaning_simple_mm"]
            assert "ဒီစကားပုံက Second English meaning" in answer["meaning_simple_mm"]
            assert "Second English meaning" in answer["meaning_simple_mm"]
            assert "ဥပမာပြောရရင် First example" in answer["meaning_simple_mm"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_topic_list_respects_requested_count_and_keeps_dataset_meaning():
    sources = [
        {
            "proverb": f"Dataset proverb {index}",
            "meaning": f"Exact meaning {index}",
            "example": "",
        }
        for index in range(1, 4)
    ]

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock, return_value=sources) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("ပညာနဲ့ဆိုင်တဲ့ စကားပုံ ၂ ခု ပြပါ")

            assert answer["intent"] == "proverb_list"
            assert "စကားပုံ (1):\nDataset proverb 1" in answer["meaning_simple_mm"]
            assert "အဓိပ္ပါယ်:\nExact meaning 1" in answer["meaning_simple_mm"]
            assert "စကားပုံ (2):\nDataset proverb 2" in answer["meaning_simple_mm"]
            assert "Dataset proverb 3" not in answer["meaning_simple_mm"]
            retrieve.assert_awaited_once()
            assert retrieve.await_args.kwargs["top_k"] == 2
            chain.assert_not_awaited()

    asyncio.run(run())


def test_topic_request_for_one_proverb_returns_detail_sections():
    sources = [
        {
            "proverb": "Mistake proverb",
            "meaning": "A person should learn from a mistake and avoid repeating it.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "proverb_list",
                    "language": "my",
                    "topic": "mistakes",
                    "requested_count": 1,
                },
            ),
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock, return_value=sources) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("အမှားကနေသင်ခန်းစာယူတဲ့စကားပုံ တစ်ခု")

            assert answer["proverb"] == "Mistake proverb"
            assert answer.get("intent") != "proverb_list"
            assert "အဓိပ္ပါယ်:\nA person should learn from a mistake and avoid repeating it." in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\n" in answer["meaning_simple_mm"]
            assert "ဥပမာ:\n" in answer["meaning_simple_mm"]
            retrieve.assert_awaited_once()
            assert retrieve.await_args.args[0] == "mistakes"
            chain.assert_not_awaited()

    asyncio.run(run())


def test_topic_list_reports_when_fewer_than_requested_are_available():
    sources = [
        {
            "proverb": "Only proverb",
            "meaning": "Only exact meaning",
            "example": "",
        }
    ]

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock, return_value=sources),
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock),
        ):
            answer = await arag_answer("ဆရာနဲ့ပတ်သက်တဲ့ စကားပုံ ၃ ခု ပြပါ")

            assert "ဒေတာအတွင်း 1 ခုသာ တွေ့ရှိပါသည်" in answer["meaning_simple_mm"]
            assert "စကားပုံ (1):\nOnly proverb" in answer["meaning_simple_mm"]
            assert "အဓိပ္ပါယ်:\nOnly exact meaning" in answer["meaning_simple_mm"]

    asyncio.run(run())


def test_topic_request_without_proverb_word_is_in_domain():
    sources = [
        {
            "proverb": "Education proverb",
            "meaning": "Education exact meaning",
            "example": "",
        }
    ]

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock, return_value=sources) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("ပညာနဲ့ဆိုင်တာ ၅ ခု ပြပါ")

            assert answer["intent"] == "proverb_list"
            assert "ဒေတာအတွင်း 1 ခုသာ တွေ့ရှိပါသည်" in answer["meaning_simple_mm"]
            assert "စကားပုံ (1):\nEducation proverb" in answer["meaning_simple_mm"]
            retrieve.assert_awaited_once()
            assert retrieve.await_args.args[0] == "ပညာ"
            chain.assert_not_awaited()

    asyncio.run(run())


def test_gemini_domain_classifier_allows_ambiguous_proverb_theme():
    sources = [
        {
            "proverb": "Gratitude proverb",
            "meaning": "Gratitude exact meaning",
            "example": "",
        }
    ]

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                side_effect=[
                    '{"domain":"proverb_related","intent":"proverb_list","topic":"ကျေးဇူးသိတတ်မှု","requested_count":4}',
                    '{"lesson_mm":"Generated lesson","example_mm":"Generated example"}',
                ],
            ),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock, return_value=sources) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("ကျေးဇူးသိတတ်မှု ၄ ခု")

            assert answer["intent"] == "proverb_list"
            assert "ဒေတာအတွင်း 1 ခုသာ တွေ့ရှိပါသည်" in answer["meaning_simple_mm"]
            assert "စကားပုံ (1):\nGratitude proverb" in answer["meaning_simple_mm"]
            assert "အဓိပ္ပါယ်:\nGratitude exact meaning" in answer["meaning_simple_mm"]
            retrieve.assert_awaited_once()
            assert retrieve.await_args.args[0] == "ကျေးဇူးသိတတ်မှု"
            assert retrieve.await_args.kwargs["top_k"] == 4
            chain.assert_not_awaited()

    asyncio.run(run())


def test_next_five_without_proverb_word_is_follow_up():
    memory = {
        **ConversationMemoryService.empty(),
        "last_sources": [
            {"proverb": f"Proverb {index}", "meaning": f"Meaning {index}", "example": ""}
            for index in range(1, 8)
        ],
        "last_list_offset": 5,
    }

    async def run():
        with (
            patch("app.services.rag.settings.chat_provider", "ollama"),
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch("app.services.rag.arun_rag_chain", new_callable=AsyncMock) as chain,
        ):
            answer = await arag_answer("နောက်ထပ် ၅ ခု", memory=memory)

            assert answer["intent"] == "proverb_list"
            assert "စကားပုံ (6):\nProverb 6" in answer["meaning_simple_mm"]
            retrieve.assert_not_awaited()
            chain.assert_not_awaited()

    asyncio.run(run())


def test_gemini_detail_keeps_dataset_proverb_and_meaning_exact():
    sources = [
        {
            "proverb": "Exact dataset proverb",
            "meaning": "Exact dataset meaning must not be rewritten.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={"intent": "follow_up", "language": "my", "action": "detail", "selection": "current"},
            ),
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch("app.services.rag.settings.fast_response_mode", False),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                return_value='{"lesson_mm":"Generated lesson only.","example_mm":"Generated example only."}',
            ),
        ):
            answer = await arag_answer("ဒီစကားပုံကို ရှင်းပြပါ", previous_answer={"sources": sources})

            assert answer["proverb"] == "Exact dataset proverb"
            assert "စကားပုံ:\nExact dataset proverb" in answer["meaning_simple_mm"]
            assert "အဓိပ္ပါယ်:\nExact dataset meaning must not be rewritten." in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\nGenerated lesson only." in answer["meaning_simple_mm"]
            assert "ဥပမာ:\nGenerated example only." in answer["meaning_simple_mm"]

    asyncio.run(run())


def test_gemini_detail_uses_gemini_for_lesson_and_example():
    sources = [
        {
            "proverb": "Gemini proverb",
            "meaning": "Gemini exact meaning.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={"intent": "follow_up", "language": "my", "action": "detail", "selection": "current"},
            ),
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch("app.services.rag.settings.fast_response_mode", True),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                return_value='{"lesson_mm":"Gemini generated lesson.","example_mm":"Gemini generated example."}',
            ) as generate,
        ):
            answer = await arag_answer("ဒီစကားပုံကို ရှင်းပြပါ", previous_answer={"sources": sources})

            assert answer["proverb"] == "Gemini proverb"
            assert "အဓိပ္ပါယ်:\nGemini exact meaning." in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\nGemini generated lesson." in answer["meaning_simple_mm"]
            assert "ဥပမာ:\nGemini generated example." in answer["meaning_simple_mm"]
            generate.assert_awaited_once()

    asyncio.run(run())


def test_gemini_query_keeps_dataset_meaning_and_generates_lesson_example():
    sources = [
        {
            "proverb": "Gemini retrieved proverb",
            "meaning": "Exact dataset meaning.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={"intent": "proverb_query", "language": "my"},
            ),
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch("app.services.rag.settings.fast_response_mode", True),
            patch("app.services.rag.is_context_relevant", return_value=True),
            patch(
                "app.services.rag.arun_rag_chain",
                new_callable=AsyncMock,
                return_value={
                    "text": '{"proverb":"Gemini retrieved proverb","meaning_simple_mm":"Gemini rewritten meaning that must not be used.","example_mm":"Gemini chain example."}',
                    "sources": sources,
                },
            ) as chain,
            patch("app.services.rag.aretrieve_context", new_callable=AsyncMock) as retrieve,
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                return_value='{"lesson_mm":"Gemini generated lesson.","example_mm":"Gemini generated example."}',
            ) as generate,
        ):
            answer = await arag_answer("အမှားကနေသင်ခန်းစာယူတဲ့စကားပုံ")

            assert answer["proverb"] == "Gemini retrieved proverb"
            assert "အဓိပ္ပါယ်:\nExact dataset meaning." in answer["meaning_simple_mm"]
            assert "Gemini rewritten meaning that must not be used." not in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\nGemini generated lesson." in answer["meaning_simple_mm"]
            assert "ဥပမာ:\nGemini generated example." in answer["meaning_simple_mm"]
            chain.assert_awaited_once()
            retrieve.assert_not_awaited()
            generate.assert_awaited_once()

    asyncio.run(run())


def test_gemini_failure_still_returns_useful_lesson():
    sources = [
        {
            "proverb": "Exact dataset proverb",
            "meaning": "Exact dataset meaning must stay exact.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={"intent": "follow_up", "language": "my", "action": "detail", "selection": "current"},
            ),
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch("app.services.rag.settings.fast_response_mode", False),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Gemini failed"),
            ),
        ):
            answer = await arag_answer("ဒီစကားပုံကို ရှင်းပြပါ", previous_answer={"sources": sources})

            assert "အဓိပ္ပါယ်:\nExact dataset meaning must stay exact." in answer["meaning_simple_mm"]
            assert "အခြေခံပြီး လူတစ်ယောက်အနေနဲ့" not in answer["meaning_simple_mm"]
            assert "Gemini" not in answer["meaning_simple_mm"]
            assert "ခဏနောက်မှ" not in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\n" in answer["meaning_simple_mm"]
            assert "နေ့စဉ်ဘဝ" in answer["meaning_simple_mm"]

    asyncio.run(run())


def test_gemini_remote_disconnect_still_returns_useful_lesson():
    sources = [
        {
            "proverb": "Exact dataset proverb",
            "meaning": "Exact dataset meaning must stay exact.",
            "example": "",
        }
    ]

    async def run():
        with (
            patch(
                "app.services.rag._aclassify_user_intent",
                new_callable=AsyncMock,
                return_value={"intent": "follow_up", "language": "my", "action": "detail", "selection": "current"},
            ),
            patch("app.services.rag.settings.chat_provider", "gemini"),
            patch("app.services.rag.settings.fast_response_mode", False),
            patch(
                "app.services.rag.agenerate_chat_response",
                new_callable=AsyncMock,
                side_effect=http.client.RemoteDisconnected("Remote end closed connection without response"),
            ),
        ):
            answer = await arag_answer("ဒီစကားပုံကို ရှင်းပြပါ", previous_answer={"sources": sources})

            assert "အဓိပ္ပါယ်:\nExact dataset meaning must stay exact." in answer["meaning_simple_mm"]
            assert "သင်ခန်းစာ:\n" in answer["meaning_simple_mm"]
            assert "ဥပမာ:\n" in answer["meaning_simple_mm"]

    asyncio.run(run())


def test_intent_names_are_stable():
    async def run():
        assert (await classify_user_intent("hello"))["intent"] == "small_talk"
        assert (await classify_user_intent("thanks"))["intent"] == "gratitude"
        assert (await classify_user_intent("ok"))["intent"] == "confirmation"
        assert (await classify_user_intent("bye"))["intent"] == "farewell"
        assert (await classify_user_intent("Explain more"))["intent"] == "follow_up"

    asyncio.run(run())
