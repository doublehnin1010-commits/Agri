# Myanmar Proverbs Tutor - Guardrails Documentation

## Overview
This document explains the guardrails implemented in the Myanmar Proverbs Tutor system to ensure safe, accurate, and on-topic responses.

## Core Rules

### 1. **Answer ONLY from Retrieved Dataset**
- Never use external knowledge or training data
- Never guess or create information
- All answers must come from the proverb database

### 2. **Scope Limitation**
- **DO**: Answer questions about Myanmar proverbs
- **DON'T**: Provide information about:
  - General knowledge
  - Programming
  - Science
  - History
  - Politics
  - Other unrelated topics

### 3. **Child-Appropriate Content**
- Always explain in simple Burmese
- Use vocabulary suitable for children
- Keep explanations short and easy to understand

### 4. **Error Handling**
When no relevant proverb is found, respond with:
```
ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။
```
(Translation: "Sorry. I cannot find it in my proverbs database.")

---

## Implementation Details

### Files Modified

#### 1. `app/services/guardrails.py` (NEW)
Contains all guardrail logic:

**Functions:**
- `is_context_relevant()`: Checks if retrieved context has relevant proverbs
- `validate_question()`: Validates user input
- `create_guardrailed_answer()`: Formats answers with guardrails
- `create_no_result_answer()`: Returns error response in Burmese
- `is_answer_valid()`: Validates generated answer quality

**Key Constant:**
```python
NO_PROVERB_MESSAGE = "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။"
```

#### 2. `app/services/rag.py` (MODIFIED)
Enhanced `rag_answer()` function with 6 guardrails:

1. **Question Validation**: Checks if question is non-empty
2. **Context Retrieval**: Gets relevant proverbs from Chroma
3. **Relevance Check**: Validates retrieved context meets relevance threshold
4. **Prompt Guardrails**: Enhanced local LLM prompt with strict rules
5. **Answer Validation**: Ensures generated answer contains meaningful content
6. **Source Inclusion**: Guarantees sources are included in response

#### 3. `app/core/config.py` (MODIFIED)
Added configuration:
```python
rag_min_relevance_score: float = 0.3  # Relevance threshold
```

---

## Guardrail Flow

```
User Question
    ↓
[1] Question Validation (non-empty check)
    ↓
[2] Retrieve Context from Chroma (top-k results)
    ↓
[3] Relevance Check (score ≤ threshold)
    ├─ FAIL → Return NO_PROVERB_MESSAGE
    └─ PASS ↓
[4] Generate Answer via Ollama/Qwen3 (with guardrail prompt)
    ├─ ERROR → Return NO_PROVERB_MESSAGE
    └─ SUCCESS ↓
[5] Validate Answer Quality (proverb + meaning not empty)
    ├─ INVALID → Return NO_PROVERB_MESSAGE
    └─ VALID ↓
[6] Return Answer with Sources
```

---

## Configuration

### Adjusting Relevance Threshold

Edit `.env` file:
```ini
RAG_MIN_RELEVANCE_SCORE=0.3
```

- **Lower value** (e.g., 0.1): More strict, fewer results
- **Higher value** (e.g., 0.5): More lenient, more results
- **Chroma scoring**: Lower distances = more relevant

### Adjusting Retrieved Results

```ini
RAG_TOP_K=5
```

Number of proverbs to retrieve for each query. Default is 5.

---

## Testing the Guardrails

### Test Case 1: Valid Proverb Question
```
Query: "အဘ နှင့် သမီးတို့ မြတ်နိုးမှု အကြောင်း ရှိသလား"
Expected: Returns relevant proverb with meaning and example
```

### Test Case 2: Out-of-Scope Question
```
Query: "Python programming ကို ဘယ်လို လေ့လာရမလဲ"
Expected: Returns NO_PROVERB_MESSAGE
```

### Test Case 3: Empty Question
```
Query: ""
Expected: Returns NO_PROVERB_MESSAGE
```

### Test Case 4: Irrelevant Question
```
Query: "အရေးမဲ့သောအရာ"
Expected: Returns NO_PROVERB_MESSAGE (if no relevant proverbs found)
```

---

## Error Responses

All error cases return the following JSON structure:
```json
{
  "proverb": null,
  "meaning_simple_mm": "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။",
  "example_mm": null,
  "sources": []
}
```

---

## Success Response

All successful responses return:
```json
{
  "proverb": "မြန်မာစကားပုံ",
  "meaning_simple_mm": "ကလေးများ နားလည်ရှင်းရှင်း အဆိုအခွင့်",
  "example_mm": "ဥပမာ: ကျွန်ုပ် မိဘများ ကို နားထောင်ပါသည်",
  "sources": [
    {
      "keyword": "မိဘ",
      "proverb": "မြန်မာစကားပုံ",
      "meaning": "အဓိပ္ပါယ်",
      "example": "ဥပမာ",
      "score": 0.15
    }
  ]
}
```

---

## Security Considerations

1. **No External Generation**: Qwen3 is instructed to only use provided context
2. **Schema Validation**: All responses must match JSON schema
3. **Content Filtering**: Only Burmese explanations for children
4. **Source Transparency**: Every response includes sources for verification
5. **Score-Based Filtering**: Relevance score prevents off-topic results

---

## Future Enhancements

1. Add user-defined topic blacklist
2. Implement question intent classification
3. Add response sentiment analysis
4. Track rejected queries for model improvement
5. Add multi-language guardrail detection
