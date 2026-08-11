import asyncio
import json

from app.services import rag


def test_gemini_knowledge_fallback_matches_described_meaning(monkeypatch):
    async def fake_generate(prompt, *, system_instruction=None):
        assert "ကဲ့ရဲ့ခုနစ်ရက်၊ ချီးမွမ်းခုနစ်ရက်" in prompt
        assert "own knowledge" in system_instruction
        return json.dumps(
            {
                "proverb": "ကဲ့ရဲ့ခုနစ်ရက်၊ ချီးမွမ်းခုနစ်ရက်",
                "meaning_simple_mm": "လူတို့၏ ကဲ့ရဲ့ခြင်းနှင့် ချီးမွမ်းခြင်းသည် အမြဲမတည်ကြောင်း ဆိုလိုသည်။",
                "example_mm": "ဦးလှကို လူများက ယခုကဲ့ရဲ့နေသော်လည်း မကြာမီ မေ့သွားနိုင်သည်။",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(rag.settings, "chat_provider", "gemini")
    monkeypatch.setattr(rag, "agenerate_chat_response", fake_generate)

    answer = asyncio.run(rag._agemini_knowledge_answer("ဦးလှကို လူတွေက ကဲ့ရဲ့အပြစ်တင်ပြောဆိုနေကြသည်။", "my"))

    assert answer["proverb"] == "ကဲ့ရဲ့ခုနစ်ရက်၊ ချီးမွမ်းခုနစ်ရက်"
    assert answer["sources"] == [{"source_type": "gemini_knowledge", "label": "Gemini general knowledge"}]


def test_gemini_knowledge_fallback_refuses_empty_proverb(monkeypatch):
    async def fake_generate(prompt, *, system_instruction=None):
        return '{"proverb": null, "meaning_simple_mm": "", "example_mm": ""}'

    monkeypatch.setattr(rag.settings, "chat_provider", "gemini")
    monkeypatch.setattr(rag, "agenerate_chat_response", fake_generate)

    assert asyncio.run(rag._agemini_knowledge_answer("မသေချာသော အကြောင်းအရာ", "my")) is None


def test_deterministic_fallback_is_specific_to_proverb_meaning():
    criticism = rag._fallback_lesson_from_meaning(
        "ကဲ့ရဲ့ခုနစ်ရက်၊ ချီးမွမ်းခုနစ်ရက်",
        "လူတို့၏ ကဲ့ရဲ့ခြင်းနှင့် ချီးမွမ်းခြင်းသည် အမြဲမတည်။",
    )
    effort = rag._fallback_lesson_from_meaning(
        "ကြိုးစားက ဘုရားဖြစ်",
        "ဇွဲမလျှော့ဘဲ ကြိုးစားအားထုတ်ရမည်။",
    )

    assert "ကဲ့ရဲ့ခြင်းနဲ့ ချီးမွမ်းခြင်း" in criticism
    assert "ဆက်လက်ကြိုးစား" in effort
    assert criticism != effort
