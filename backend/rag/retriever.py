import os
import json
import re
import math
import requests
from typing import List, Dict, Any

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

FORBIDDEN_RAG_PATHS = {"antigravity_context.md", "antigravity_builder_ethos.md"}

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "nomic-embed-text"
INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge", "vector_index", "rag_embeddings.json"
)

class HybridRetriever:
    def __init__(self):
        self.chunks = []
        self.bm25 = None
        self.load_index()

    def load_index(self):
        if not os.path.exists(INDEX_PATH):
            print(f"⚠️ RAG index not found at {INDEX_PATH}. Please run build_knowledge_base.py first.")
            return

        try:
            with open(INDEX_PATH, "r") as f:
                self.chunks = json.load(f)
            
            if BM25Okapi and self.chunks:
                corpus = [chunk["content"] for chunk in self.chunks]
                tokenized_corpus = [self._tokenize(doc) for doc in corpus]
                self.bm25 = BM25Okapi(tokenized_corpus)
                print(f"✅ Loaded RAG index with {len(self.chunks)} chunks and initialized BM25.")
        except Exception as e:
            print(f"⚠️ Failed to load RAG index: {e}")

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude_1 = math.sqrt(sum(a * a for a in vec1))
        magnitude_2 = math.sqrt(sum(b * b for b in vec2))
        if magnitude_1 * magnitude_2 == 0:
            return 0.0
        return dot_product / (magnitude_1 * magnitude_2)

    def _get_embedding(self, text: str) -> List[float]:
        try:
            from backend.utils.ollama_helper import ensure_ollama_running
            ensure_ollama_running()
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": text
                },
                timeout=8.0
            )
            resp.raise_for_status()
            return resp.json().get("embedding") or []
        except Exception as e:
            print(f"⚠️ RAG embedding lookup failed: {e}")
            return []

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        # 1. Cosine similarity score
        query_embedding = self._get_embedding(query)
        embedding_scores = []
        if query_embedding:
            for chunk in self.chunks:
                sim = self._cosine_similarity(query_embedding, chunk["embedding"])
                embedding_scores.append(sim)
        else:
            embedding_scores = [0.0] * len(self.chunks)

        # 2. BM25 score
        bm25_scores = [0.0] * len(self.chunks)
        if self.bm25:
            tokenized_query = self._tokenize(query)
            bm25_scores = list(self.bm25.get_scores(tokenized_query))
            # Normalize BM25 scores to [0, 1] range to combine with Cosine
            max_bm25 = max(bm25_scores) if bm25_scores else 0
            if max_bm25 > 0:
                bm25_scores = [score / max_bm25 for score in bm25_scores]

        # 3. Hybrid score
        results = []
        for idx, chunk in enumerate(self.chunks):
            # Security exclusion check
            filepath = chunk.get("filepath", "")
            filename = os.path.basename(filepath)
            if filename in FORBIDDEN_RAG_PATHS or any(f in filepath for f in FORBIDDEN_RAG_PATHS):
                continue

            # Hybrid retrieval score = Cosine Similarity + BM25 keyword matching
            hybrid_score = embedding_scores[idx] + bm25_scores[idx]
            results.append({
                "category": chunk["category"],
                "filepath": chunk["filepath"],
                "header": chunk["header"],
                "content": chunk["content"],
                "score": hybrid_score,
                "similarity": embedding_scores[idx],
                "keyword_score": bm25_scores[idx]
            })

        # Sort and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Singleton instance
retriever_instance = None

def get_retriever():
    global retriever_instance
    if retriever_instance is None:
        retriever_instance = HybridRetriever()
    return retriever_instance
