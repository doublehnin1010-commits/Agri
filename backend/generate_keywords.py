"""
Generate and add keywords to all proverbs in the database.
This improves semantic search by providing relevant keywords/synonyms.

Usage: python generate_keywords.py
"""

import json
import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings
from app.services.llm import generate_answer
from typing import Any

def get_collection():
    """Get Chroma collection"""
    chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return chroma_client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )


def generate_keywords_for_proverb(proverb: str, meaning: str | None = None, example: str | None = None) -> str:
    """
    Use LLM to generate relevant keywords for a proverb.
    Returns comma-separated keywords in Burmese.
    """
    prompt = f"""You are a Myanmar language expert. Analyze this proverb and generate relevant keywords/synonyms that would help someone search for it.

Proverb: {proverb}
Meaning: {meaning or 'Not provided'}
Example: {example or 'Not provided'}

Generate 5-8 relevant keywords in Burmese that capture the main concepts, themes, and meanings of this proverb. 
These keywords help people find this proverb when searching with similar words.

Return ONLY a comma-separated list of Burmese keywords. Example: "အခေါ်အဝေါ်, အုပ်စုကျ, စည်းမျဥ်း, ကျေးဇူး"

Keywords:"""

    try:
        result = generate_answer(prompt)
        # Clean up the response
        keywords = result.strip()
        if "Keywords:" in keywords:
            keywords = keywords.split("Keywords:")[-1].strip()
        return keywords
    except Exception as e:
        print(f"  WARNING: Error generating keywords from LLM: {e}")
        # fall back to heuristic extraction
        return generate_keywords_heuristic(proverb)


def generate_keywords_heuristic(text: str, max_keywords: int = 6) -> str:
    """
    Heuristic keyword generator for Burmese text.
    - Normalize punctuation
    - Split on whitespace
    - Remove common Burmese stopwords
    - Return top unique tokens up to `max_keywords` as comma-separated list
    """
    import re

    if not text:
        return ""

    s = text.strip()
    s = re.sub(r'[၊။!?.,;:"\'"`(){}\[\]<>]', " ", s)
    tokens = [t.strip() for t in s.split() if t.strip()]

    stopwords = {
        "ကို", "သည်", "၏", "နှင့်", "နှင့်", "တို့", "တစ်", "ထဲ", "မ", "က", "ဖြင့်", "အတွက်",
        "သည့်", "ခြင်း", "ဖြစ်",
    }

    filtered = []
    for t in tokens:
        if t in stopwords:
            continue
        if len(t) <= 1:
            continue
        if t in filtered:
            continue
        filtered.append(t)

    # If not enough tokens, include character n-grams
    if len(filtered) < max_keywords:
        chars = re.sub(r"\s+", "", s)
        ngrams = []
        for n in (3, 2):
            for i in range(max(0, len(chars) - n + 1)):
                ngrams.append(chars[i : i + n])
        for ng in ngrams:
            if ng in filtered or ng in stopwords:
                continue
            filtered.append(ng)
            if len(filtered) >= max_keywords:
                break

    return ", ".join(filtered[:max_keywords])


def process_all_proverbs():
    """Extract, enhance, and update all proverbs with keywords"""
    print("\n" + "="*70)
    print("GENERATING KEYWORDS FOR ALL PROVERBS")
    print("="*70)
    
    col = get_collection()
    
    # Get all proverbs (Chroma doesn't support "ids" in include, so we get it separately)
    result = col.get(limit=100000, include=["metadatas"])
    metadatas = result.get("metadatas") or []
    ids = result.get("ids") or []  # ids are returned automatically
    
    print(f"\n[INFO] Found {len(metadatas)} proverbs to process\n")
    
    # Prepare updates
    updated_ids = []
    updated_metadatas = []
    updated_docs = []
    
    skipped = 0
    processed = 0
    
    for idx, (proverb_id, md) in enumerate(zip(ids, metadatas), 1):
        if not md:
            skipped += 1
            continue
        
        proverb = md.get("proverb", "").strip()
        meaning = md.get("meaning", "").strip()
        example = md.get("example", "").strip()
        current_keyword = md.get("keyword", "").strip()
        
        # Skip if keywords already exist
        if current_keyword:
            print(f"[{idx}/{len(metadatas)}] SKIP - Already has keywords: {proverb[:40]}")
            skipped += 1
            continue
        
        print(f"[{idx}/{len(metadatas)}] Processing: {proverb[:50]}")
        
        # Generate keywords
        keywords = generate_keywords_for_proverb(proverb, meaning, example)
        
        if keywords:
            print(f"             Keywords: {keywords[:60]}")
            
            # Update metadata
            updated_md = {
                "keyword": keywords,
                "proverb": proverb,
                "meaning": meaning,
                "example": example,
            }
            
            # Build document string for embedding
            doc = f"keyword: {keywords}\nproverb: {proverb}\nmeaning: {meaning}\nexample: {example}"
            
            updated_ids.append(proverb_id)
            updated_metadatas.append(updated_md)
            updated_docs.append(doc)
            processed += 1
        else:
            print(f"             WARNING: Could not generate keywords")
            skipped += 1
        
        # Batch update every 10 proverbs
        if len(updated_ids) >= 10:
            col.upsert(
                ids=updated_ids,
                documents=updated_docs,
                metadatas=updated_metadatas
            )
            print(f"  SAVED batch of {len(updated_ids)} proverbs\n")
            updated_ids = []
            updated_metadatas = []
            updated_docs = []
    
    # Final batch
    if updated_ids:
        col.upsert(
            ids=updated_ids,
            documents=updated_docs,
            metadatas=updated_metadatas
        )
        print(f"  SAVED final batch of {len(updated_ids)} proverbs\n")
    
    print("="*70)
    print(f"COMPLETE: Processed {processed}, Skipped {skipped}")
    print("="*70)
    print("\nNext steps:")
    print("   1. Verify the keywords look good")
    print("   2. Run test_semantic_search.py to test retrieval")
    print("   3. Adjust RAG_SEMANTIC_THRESHOLD if needed")


def verify_keywords():
    """Show sample proverbs with their new keywords"""
    print("\n" + "="*70)
    print("SAMPLE OF PROVERBS WITH KEYWORDS")
    print("="*70 + "\n")
    
    col = get_collection()
    result = col.get(limit=100000, include=["metadatas"])
    metadatas = result.get("metadatas") or []
    
    samples_shown = 0
    for md in metadatas:
        if not md:
            continue
        
        if md.get("keyword"):
            samples_shown += 1
            print(f"Proverb: {md.get('proverb')}")
            print(f"   Keywords: {md.get('keyword')}")
            print()
            
            if samples_shown >= 5:
                break
    
    if samples_shown == 0:
        print("NOTE: No proverbs with keywords yet. Run generate_keywords_for_proverb() first.")


if __name__ == "__main__":
    try:
        process_all_proverbs()
        print("\n" + "="*70)
        print("VERIFYING RESULTS")
        print("="*70)
        verify_keywords()
        
        print("\nKeyword generation complete!")
        print("\nTo test improved search, run:")
        print("   python test_semantic_search.py")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
