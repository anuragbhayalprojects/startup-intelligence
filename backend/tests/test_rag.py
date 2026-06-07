import os
from backend.rag.retriever import get_retriever

def test_hybrid_retriever_initialization():
    retriever = get_retriever()
    assert retriever is not None
    assert isinstance(retriever.chunks, list)

def test_hybrid_retriever_search():
    retriever = get_retriever()
    if not retriever.chunks:
        # Skip if index not created/empty in test environment
        return
        
    query = "claims fraud automation"
    results = retriever.retrieve(query, top_k=3)
    
    assert len(results) > 0
    assert "score" in results[0]
    assert "content" in results[0]
    # Verify sorted by descending score
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i+1]["score"]
