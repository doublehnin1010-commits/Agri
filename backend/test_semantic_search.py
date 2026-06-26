"""
Test script to verify semantic search improvements for Burmese proverbs.

Usage: python test_semantic_search.py
"""

from app.services.rag import retrieve_context
from app.db.mongodb import get_db
from app.db.chroma import connect_chroma


def test_semantic_retrieval():
    """Test semantic retrieval with the user's specific query"""
    print("\n" + "="*60)
    print("Testing Semantic Search for Burmese Proverbs")
    print("="*60)
    
    # Initialize connections
    connect_chroma()
    
    # Test query: The user's question about criticism/blame
    test_query = "ဦးမောင်မောင်ကို လူတွေကနေ သူကို ကဲ့ရဲ့အပြစ်တင်နေသည်"
    print(f"\n📌 Test Query: {test_query}")
    print("   (Translation: U Maung Maung is being criticized/blamed by people)")
    
    print("\n🔍 Retrieving context...")
    results = retrieve_context(test_query, top_k=5)
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n✅ Found {len(results)} matching proverbs:\n")
    
    for idx, result in enumerate(results, 1):
        print(f"--- Result {idx} ---")
        print(f"Keyword: {result.get('keyword', 'N/A')}")
        print(f"Proverb: {result.get('proverb', 'N/A')}")
        print(f"Meaning: {result.get('meaning', 'N/A')}")
        print(f"Example: {result.get('example', 'N/A')}")
        
        # Show score info
        similarity = result.get("similarity")
        distance = result.get("score")
        if similarity is not None:
            print(f"Semantic Similarity: {similarity:.2%}")
        elif distance is not None:
            print(f"Lexical Distance: {distance:.4f}")
        print()
    
    # Check if expected proverb is found
    expected_proverb = "ကဲ့ရဲ့ ခုနစ်ရက်"
    found = False
    for result in results:
        if expected_proverb in result.get("proverb", ""):
            found = True
            break
    
    if found:
        print(f"✅ SUCCESS: Expected proverb containing '{expected_proverb}' was found!")
    else:
        print(f"⚠️  NOTE: Expected proverb containing '{expected_proverb}' not found")
        print("   This may mean:")
        print("   1. The proverb is not in the database yet")
        print("   2. It needs to be added with better keywords")
        print("   3. The semantic similarity threshold is too high")


def test_sample_queries():
    """Test with multiple sample queries"""
    print("\n" + "="*60)
    print("Testing Multiple Queries")
    print("="*60)
    
    connect_chroma()
    
    sample_queries = [
        ("ကဲ့ရဲ့အပြစ်တင်နေသည်", "being criticized"),
        ("အဘ နှင့် သမီးတို့ မြတ်နိုးမှု", "father and daughter respect"),
        ("ကြိုးစားရမည်", "should try hard"),
    ]
    
    for query, translation in sample_queries:
        print(f"\n📌 Query: {query} ({translation})")
        results = retrieve_context(query, top_k=3)
        
        if results:
            print(f"   ✅ Found {len(results)} results")
            for result in results:
                similarity = result.get("similarity")
                if similarity is not None:
                    print(f"      • {result.get('proverb')} (similarity: {similarity:.1%})")
                else:
                    print(f"      • {result.get('proverb')}")
        else:
            print("   ❌ No results found")


if __name__ == "__main__":
    try:
        test_semantic_retrieval()
        test_sample_queries()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
