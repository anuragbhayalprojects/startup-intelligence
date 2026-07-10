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
from backend.workflows.startup_pipeline import are_headlines_describing_same_event

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


def calculate_token_overlap(title1: str, title2: str) -> float:
    """Calculates the overlap percentage of key tokens between two titles."""
    tokens1 = clean_and_tokenize(title1)
    tokens2 = clean_and_tokenize(title2)
    
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1.intersection(tokens2)
    smaller_set_size = min(len(tokens1), len(tokens2))
    
    return len(intersection) / smaller_set_size


class Deduplicator:
    def __init__(self):
        pass

    def check_exact_database_duplicate(self, url: str, headline: str) -> bool:
        """Checks if the article URL or exact headline already exists in news_articles."""
        try:
            # Check URL
            res_url = supabase.table("news_articles").select("id").eq("source_url", url).execute()
            if res_url.data:
                return True
                
            # Check exact Headline
            res_headline = supabase.table("news_articles").select("id").eq("headline", headline).execute()
            if res_headline.data:
                return True
        except Exception as e:
            logger.error(f"Error checking exact DB duplicate: {e}")
        return False

    def cluster_and_deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates incoming articles by:
        1. Checking database exact matches.
        2. Grouping novel incoming items into clusters based on title similarity.
        3. Merging similar articles in the same run to produce a single canonical item.
        """
        novel_articles = []
        
        # Phase 1: Syntactic check (URL/exact title in DB)
        for art in articles:
            url = art.get("source_url", "")
            title = art.get("headline", "")
            if not self.check_exact_database_duplicate(url, title):
                novel_articles.append(art)
                
        logger.info(f"Filtered out exact DB duplicates. Novel articles to check: {len(novel_articles)}")
        
        # Phase 2: In-run Clustering using Token Overlap + Ollama fallback
        clustered_articles: List[Dict[str, Any]] = []
        
        for incoming in novel_articles:
            matched_canonical = None
            
            # Compare against already accumulated canonical articles
            for canonical in clustered_articles:
                # 1. Check token overlap similarity threshold
                overlap = calculate_token_overlap(incoming["headline"], canonical["headline"])
                if overlap >= 0.55:
                    logger.info(f"High token overlap ({overlap:.2f}) found between: '{incoming['headline']}' and '{canonical['headline']}'")
                    # 2. Confirm semantically with local Ollama
                    if are_headlines_describing_same_event(incoming["headline"], canonical["headline"]):
                        logger.info(f"✅ Ollama confirmed semantic duplicate: '{incoming['headline']}' matches '{canonical['headline']}'")
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
