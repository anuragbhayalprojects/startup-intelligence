"""
backend/pipeline/deduplicator.py
--------------------------------
Deduplicator checks exact URL/headline matches in PostgreSQL,
runs a fast token-overlap similarity check on titles,
and invokes local Ollama semantic helpers to group similar articles.
"""

from __future__ import annotations
import logging
import re
from typing import List, Dict, Any
from backend.services.supabase_service import supabase

logger = logging.getLogger("startup_intelligence.pipeline.deduplicator")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "by", 
    "for", "with", "about", "against", "between", "into", "through", "during", "before", 
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", 
    "over", "under", "again", "further", "then", "once", "here", "there", "all", "any", 
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", 
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", 
    "don", "should", "now", "raises", "funding", "startup", "startups", "raises", "funding",
    "raised", "round", "lead", "leads", "capital", "crore", "crores", "million", "millions",
    "investment", "invests", "backed", "owned"
}


def clean_and_tokenize(text: str) -> set[str]:
    """Strips special characters, converts to lowercase, and extracts non-stopword tokens."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    words = cleaned.split()
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def calculate_jaccard_similarity(title1: str, title2: str) -> float:
    """Calculates the Jaccard similarity coefficient (intersection over union) of key tokens between two titles."""
    tokens1 = clean_and_tokenize(title1)
    tokens2 = clean_and_tokenize(title2)
    
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union)


def are_contexts_describing_same_event(headline1: str, context1: str, headline2: str, context2: str) -> bool:
    """Asks the local Ollama model if two stories describe the exact same corporate event based on their headlines and descriptions."""
    import os
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    if not base_url:
        return False
        
    # Clean and truncate contexts to prevent context window bloat
    ctx1 = (context1 or "")[:1200].strip()
    ctx2 = (context2 or "")[:1200].strip()
    
    prompt = f"""You are a precise semantic news deduplication assistant.
    Your job is to determine if two news stories from different sources are reporting on the exact same corporate event (such as a funding round, launch, acquisition, or partnership for a startup), using their headlines and descriptions.
    
    Story 1:
    Headline: "{headline1}"
    Description: "{ctx1}"
    
    Story 2:
    Headline: "{headline2}"
    Description: "{ctx2}"
    
    Based on the headlines and descriptions, are these two stories describing the same corporate event?
    Respond with only a single word: YES or NO. Do not explain."""
    
    try:
        from backend.ai.router import call_ai
        # Route through call_ai for observability logging
        res = call_ai(prompt, task="extraction", json_format=False)
        if isinstance(res, str):
            clean_res = res.strip().upper()
            return "YES" in clean_res
    except Exception as e:
        logger.warning(f"Error calling Ollama context verification: {e}")
    return False


class Deduplicator:
    def __init__(self):
        pass

    def check_exact_database_duplicate(self, url: str) -> bool:
        """Checks if the article URL already exists in news_articles."""
        try:
            # Check URL
            res_url = supabase.table("news_articles").select("id").eq("source_url", url).execute()
            if res_url.data:
                return True
        except Exception as e:
            logger.warning(f"DB duplicate check failed: {e}")
        return False

    def check_semantic_database_duplicate(self, incoming: Dict[str, Any], days_limit: int = 7) -> Dict[str, Any] | None:
        """
        Compares the incoming article against recent articles in the database.
        Returns the matched database article row if a duplicate is found, so it can be merged.
        """
        try:
            from datetime import datetime, timedelta, timezone
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_limit)).isoformat()
            
            # Fetch recent articles from Supabase
            res = supabase.table("news_articles") \
                .select("id, headline, source, source_url, published_at, similar_sources, summary, content") \
                .gte("published_at", cutoff_date) \
                .execute()
                
            recent_articles = res.data or []
            
            for db_art in recent_articles:
                similarity = calculate_jaccard_similarity(incoming["headline"], db_art["headline"])
                
                # High Jaccard similarity: matched!
                if similarity >= 0.75:
                    logger.info(f"DB Match (Jaccard {similarity:.2f}): '{incoming['headline']}' matches DB '{db_art['headline']}'")
                    return db_art
                    
                # Moderate Jaccard similarity: verify context semantically via Ollama
                elif similarity >= 0.35:
                    ctx1 = incoming.get("description") or incoming.get("content") or ""
                    ctx2 = db_art.get("summary") or db_art.get("content") or ""
                    
                    if are_contexts_describing_same_event(incoming["headline"], ctx1, db_art["headline"], ctx2):
                        logger.info(f"✅ DB Match (Semantic LLM): '{incoming['headline']}' matches DB '{db_art['headline']}'")
                        return db_art
        except Exception as e:
            logger.warning(f"Error checking semantic DB duplicate: {e}")
            
        return None

    def cluster_and_deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates incoming articles by:
        1. Filtering out exact URLs that already exist in the database.
        2. Comparing headlines using token Jaccard similarity.
        3. Falling back to LLM context/description semantic checks for moderate similarity scores.
        """
        novel_articles = []
        
        # Phase 1: Syntactic check (URL in DB)
        for art in articles:
            url = art.get("source_url", "")
            if not self.check_exact_database_duplicate(url):
                novel_articles.append(art)
                
        logger.info(f"Filtered out exact DB duplicates. Novel articles to check: {len(novel_articles)}")
        
        # Phase 2: In-run Clustering
        clustered_articles: List[Dict[str, Any]] = []
        
        for incoming in novel_articles:
            matched_canonical = None
            
            # Compare against already accumulated canonical articles
            for canonical in clustered_articles:
                similarity = calculate_jaccard_similarity(incoming["headline"], canonical["headline"])
                
                # High similarity: Merge immediately without LLM call
                if similarity >= 0.75:
                    logger.info(f"High headline Jaccard similarity ({similarity:.2f}) found between: '{incoming['headline']}' and '{canonical['headline']}'. Merging immediately.")
                    matched_canonical = canonical
                    break
                
                # Moderate similarity: Check context similarity via Ollama
                elif similarity >= 0.35:
                    logger.info(f"Moderate headline Jaccard similarity ({similarity:.2f}) found between: '{incoming['headline']}' and '{canonical['headline']}'. Checking context similarity.")
                    
                    ctx1 = incoming.get("description", "") or incoming.get("content", "")
                    ctx2 = canonical.get("description", "") or canonical.get("content", "")
                    
                    if are_contexts_describing_same_event(incoming["headline"], ctx1, canonical["headline"], ctx2):
                        logger.info(f"✅ Ollama confirmed semantic duplicate based on context matching: '{incoming['headline']}' matches '{canonical['headline']}'")
                        matched_canonical = canonical
                        break
            
            if matched_canonical:
                # Merge incoming as a duplicate source under similar_sources
                similar_entry = {
                    "source": incoming["source"],
                    "headline": incoming["headline"],
                    "url": incoming["source_url"],
                    "published_at": incoming["published_at"],
                    "description": incoming.get("description", ""),
                    "content": incoming.get("content", "")
                }
                matched_canonical["similar_sources"].append(similar_entry)
            else:
                # Treat as a new canonical story cluster
                incoming["similar_sources"] = []
                clustered_articles.append(incoming)

        logger.info(f"Deduplication clustered {len(novel_articles)} novel articles into {len(clustered_articles)} unique stories.")
        return clustered_articles
