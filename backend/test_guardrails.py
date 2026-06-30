"""
Test script for Myanmar Proverbs Tutor Guardrails
Run this to verify guardrails are working correctly.

Usage: python test_guardrails.py
"""

import sys
import json
from app.services.guardrails import (
    is_context_relevant,
    validate_question,
    create_no_result_answer,
    is_answer_valid,
)
from app.services.rag import rag_answer


def test_validate_question():
    """Test question validation guardrail"""
    print("\n=== Testing Question Validation ===")

    # Test 1: Valid question
    valid, msg = validate_question("အဘ နှင့် သမီးတို့ မြတ်နိုးမှု အကြောင်း ရှိသလား")
    assert valid is True and msg is None, "Valid question should pass"
    print("✓ Valid question: PASS")

    # Test 2: Empty question
    valid, msg = validate_question("")
    assert valid is False and msg is not None, "Empty question should fail"
    print("✓ Empty question: PASS")

    # Test 3: Whitespace only
    valid, msg = validate_question("   ")
    assert valid is False and msg is not None, "Whitespace-only question should fail"
    print("✓ Whitespace-only question: PASS")


def test_context_relevance():
    """Test context relevance guardrail"""
    print("\n=== Testing Context Relevance ===")

    # Test 1: No context
    assert is_context_relevant([]) is False, "Empty context should fail"
    print("✓ Empty context: PASS")

    # Test 2: Relevant context (low score = more relevant in Chroma)
    context = [
        {
            "proverb": "သုံးခါ စမ်းမြင့်တက္ကဆ",
            "meaning": "ကြိုးစားရမည်",
            "score": 0.15,
        }
    ]
    assert is_context_relevant(context, min_relevance_score=0.3) is True
    print("✓ Relevant context (score=0.15): PASS")

    # Test 3: Irrelevant context (high score = less relevant)
    context = [
        {
            "proverb": "စကားပုံ",
            "meaning": "အဓိပ္ပါယ်",
            "score": 0.8,
        }
    ]
    assert is_context_relevant(context, min_relevance_score=0.3) is False
    print("✓ Irrelevant context (score=0.8): PASS")

    # Test 4: Mixed context (should pass if any relevant)
    context = [
        {"proverb": "စကားပုံ1", "meaning": "အဓိပ္ပါယ်", "score": 0.8},
        {"proverb": "စကားပုံ2", "meaning": "အဓိပ္ပါယ်", "score": 0.15},
        {"proverb": "စကားပုံ3", "meaning": "အဓိပ္ပါယ်", "score": 0.5},
    ]
    assert is_context_relevant(context, min_relevance_score=0.3) is True
    print("✓ Mixed context (has relevant items): PASS")


def test_answer_validation():
    """Test answer validation guardrail"""
    print("\n=== Testing Answer Validation ===")

    # Test 1: Valid answer
    valid_answer = {
        "proverb": "သုံးခါ စမ်းမြင့်တက္ကဆ",
        "meaning_simple_mm": "ကြိုးစားရမည်",
        "example_mm": "ဥပမာ",
    }
    assert is_answer_valid(valid_answer) is True
    print("✓ Valid answer: PASS")

    # Test 2: Missing proverb
    invalid_answer = {
        "proverb": "",
        "meaning_simple_mm": "ကြိုးစားရမည်",
        "example_mm": "ဥပမာ",
    }
    assert is_answer_valid(invalid_answer) is False
    print("✓ Missing proverb: PASS")

    # Test 3: Missing meaning
    invalid_answer = {
        "proverb": "သုံးခါ စမ်းမြင့်တက္ကဆ",
        "meaning_simple_mm": "",
        "example_mm": "ဥပမာ",
    }
    assert is_answer_valid(invalid_answer) is False
    print("✓ Missing meaning: PASS")

    # Test 4: Null values
    invalid_answer = {
        "proverb": None,
        "meaning_simple_mm": None,
        "example_mm": None,
    }
    assert is_answer_valid(invalid_answer) is False
    print("✓ Null values: PASS")


def test_greeting_response():
    """Greeting should return a friendly reply instead of a no-data error."""
    print("\n=== Testing Greeting Response ===")

    answer = rag_answer("Hello")

    assert answer["proverb"] is None, "Greeting should not return a proverb"
    assert answer["meaning_simple_mm"] is not None, "Greeting should include a friendly message"
    assert "မင်္ဂလာပါ" in answer["meaning_simple_mm"] or "Hello" in answer["meaning_simple_mm"], "Greeting should be friendly"
    print("✓ Greeting reply: PASS")


def test_no_result_answer():
    """Test no-result answer response"""
    print("\n=== Testing No-Result Answer ===")

    answer = create_no_result_answer()

    assert answer["proverb"] is None, "Proverb should be None"
    assert (
        answer["meaning_simple_mm"]
        == "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။"
    ), "Should contain standard error message"
    assert answer["sources"] == [], "Sources should be empty"

    print("✓ No-result answer format: PASS")
    print(f"  Error message: {answer['meaning_simple_mm']}")


def run_all_tests():
    """Run all guardrail tests"""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Myanmar Proverbs Tutor - Guardrails Test Suite      ║")
    print("╚═══════════════════════════════════════════════════════╝")

    try:
        test_validate_question()
        test_context_relevance()
        test_answer_validation()
        test_greeting_response()
        test_no_result_answer()

        print("\n╔═══════════════════════════════════════════════════════╗")
        print("║  ✓ ALL TESTS PASSED                                  ║")
        print("╚═══════════════════════════════════════════════════════╝")
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
