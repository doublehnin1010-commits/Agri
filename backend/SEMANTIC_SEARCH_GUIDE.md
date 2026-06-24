# Semantic Search Optimization Guide

## Problem Summary
Your original system only used **lexical search** (matching words and letter sequences), which fails when the user's question and the proverb use different words but have the same meaning.

### Example:
- **User Query**: "ဦးမောင်မောင်ကို လူတွေကနေ သူကို ကဲ့ရဲ့အပြစ်တင်နေသည်" (being criticized)
- **Expected Proverb**: "ကဲ့ရဲ့ခုနှစ်ရက် ချီးမွန်းခုနှစ်ရက်" (about criticism/blame)
- **Problem**: No direct word match, so it wasn't returned

## Solution: Hybrid Search

The improved system now uses:

1. **Primary: Semantic Search** - Finds meaning-based matches using embeddings
2. **Fallback: Lexical Search** - Finds exact word/letter matches

## How to Optimize Your Proverbs

### 1. **Keywords Field** - Most Important
The `keyword` field is crucial for both search types:

```json
{
  "keyword": "ကဲ့ရဲ့, အပြစ်တင်, အရှုံးခံ, မုန်းခြင်း, ဆန့်ကျင်, နှိုင်းယှဉ်",
  "proverb": "ကဲ့ရဲ့ခုနှစ်ရက် ချီးမွန်းခုနှစ်ရက်",
  "meaning": "တစ်ခုကို ကဲ့ရဲ့လျှင် အြခားတစ်ခုကို ချီးမွန်းရမည်။",
  "example": "အဆင့်မြင့်နှင့် အဆင့်နိမ့်ကို ယုံမျှဖြင့် ကဲ့ရဲ့ချီးမွန်းရပါသည်။"
}
```

### 2. **Good Keywords Include:**
- **Synonyms**: Alternative words with same meaning
- **Related Concepts**: Words that connect to the idea
- **Common Queries**: What users might actually search for

Example for a proverb about patience:
```
keyword: "ခံ, စိတ်ခိုင်လုံ, ကြီးမြတ်, ရှည်, စောင့်, မျက်မှောက်, ဆုံးအုံး"
```

### 3. **Meaning & Example Fields**
- **Meaning**: Should explain in simple, searchable Burmese
- **Example**: Real-world usage helps with semantic understanding

## Testing Your Changes

### Option 1: Run the Test Script
```bash
python test_semantic_search.py
```

### Option 2: Manual Test via API
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "ဦးမောင်မောင်ကို လူတွေကနေ သူကို ကဲ့ရဲ့အပြစ်တင်နေသည်"}'
```

## Configuration Settings

You can adjust search behavior in `.env`:

```env
# Semantic similarity threshold (0-1, higher = stricter)
# Lower values = more permissive semantic matching
RAG_SEMANTIC_THRESHOLD=0.5

# Minimum relevance score (0-1)
# For semantic: higher = more relevant
RAG_MIN_RELEVANCE_SCORE=0.75

# Lexical search similarity (0-1)
RAG_MIN_LEXICAL_SIMILARITY=0.5
```

## Recommended Threshold Values

| Use Case | rag_semantic_threshold | Reason |
|----------|------------------------|--------|
| **Strict** | 0.7 | Only very similar meanings |
| **Balanced** (default) | 0.5 | Good balance of coverage & accuracy |
| **Permissive** | 0.3 | More results, possibly less relevant |

## Troubleshooting

### Query Not Returning Expected Proverb?
1. **Check if proverb exists**: Verify it's in MongoDB/Chroma
2. **Check keywords**: Add more related keywords
3. **Lower threshold**: Reduce `rag_semantic_threshold` in config
4. **Run test script**: Use `test_semantic_search.py` to debug

### Getting Too Many Results?
- Increase `rag_semantic_threshold` (e.g., 0.6 → 0.75)
- Add more specific keywords
- Review relevance scoring in guardrails

### Chroma Index Not Updating?
- Proverbs are embedded when added/updated
- If you edited proverbs directly in DB, restart the app
- Check: `chroma_data/` directory exists and has data

## What Changed

### Files Modified:
1. **app/services/rag.py**
   - Added `_retrieve_semantic_context()` - Uses Chroma query with embeddings
   - Modified `retrieve_context()` - Tries semantic first, lexical fallback

2. **app/services/guardrails.py**
   - Updated `is_context_relevant()` - Supports semantic similarity scores

3. **app/core/config.py**
   - Added `rag_semantic_threshold` - Configurable semantic threshold

### What Stays The Same:
- Lexical search still works as fallback
- All existing API endpoints unchanged
- Database structure unchanged
- Guardrails still active

## Performance Impact

✅ **Benefits**:
- Finds semantically similar proverbs even with different words
- Better user experience for meaning-based queries
- Still has lexical fallback for exact matches

⚠️ **Considerations**:
- Semantic search slightly slower than lexical-only
- Requires Chroma with embeddings (already configured)
- Works best with good keywords in proverbs

## Next Steps

1. **Verify Test**: Run `test_semantic_search.py`
2. **Add Keywords**: Ensure proverbs have comprehensive keywords
3. **Adjust Thresholds**: Fine-tune based on your results
4. **Monitor**: Track user satisfaction with retrieved proverbs
