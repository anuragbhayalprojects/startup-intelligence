"""
backend/services/news_service.py
--------------------------------
Service layer for canonical news_articles and custom sources.
Handles backward-compatible sync to startup_news when startups are resolved.
"""

from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from backend.services.supabase_service import supabase
from backend.services.news_repo import save_startup_news

logger = logging.getLogger("startup_intelligence.services.news_service")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SOURCES_CONFIG_PATH = os.path.join(PROJECT_ROOT, "backend", "config", "sources.json")


def load_sources_from_config() -> List[Dict[str, Any]]:
    """Loads all configured sources from sources.json."""
    if not os.path.exists(SOURCES_CONFIG_PATH):
        logger.warning(f"sources.json not found at {SOURCES_CONFIG_PATH}")
        return []
    try:
        with open(SOURCES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load sources config: {e}")
        return []


def save_sources_to_config(sources: List[Dict[str, Any]]) -> bool:
    """Saves the sources list to sources.json."""
    try:
        # Create directories if they do not exist
        os.makedirs(os.path.dirname(SOURCES_CONFIG_PATH), exist_ok=True)
        with open(SOURCES_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(sources, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save sources config: {e}")
        return False


def get_all_sources() -> List[Dict[str, Any]]:
    """Returns list of all active sources."""
    return load_sources_from_config()


def add_custom_source(name: str, url: str, category: str) -> Dict[str, Any]:
    """Validates and appends a new custom RSS feed configuration to sources.json."""
    sources = load_sources_from_config()
    
    # Generate clean ID
    source_id = name.lower().replace(" ", "_").replace("-", "_")
    
    # Check for duplicates
    for s in sources:
        if s.get("id") == source_id or s.get("rss_url") == url:
            return {"status": "exists", "source": s}

    new_source = {
        "id": source_id,
        "name": name,
        "category": category,
        "enabled": true,
        "priority": 3,
        "parser_type": "rss",
        "feed_type": "standard",
        "rss_url": url,
        "poll_interval_minutes": 120,
        "timeout_seconds": 15,
        "retry_count": 2,
        "deduplication_enabled": true,
        "language": "en",
        "country": "IN",
        "tags": ["custom", "user-added"]
    }
    
    sources.append(new_source)
    if save_sources_to_config(sources):
        return {"status": "created", "source": new_source}
    return {"status": "error", "message": "Failed to write to configuration file"}


def save_canonical_article(
    headline: str,
    summary: str,
    content: str,
    source: str,
    source_url: str,
    published_at: Optional[str] = None,
    category: str = "aggregator",
    similar_sources: Optional[List[Dict[str, Any]]] = None,
    startups_mentioned: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Saves or updates a canonical news article in news_articles.
    Syncs corresponding records to startup_news for any resolved startups.
    """
    try:
        # Check for duplicate by source_url or exact headline in news_articles
        existing = supabase.table("news_articles").select("*").eq("source_url", source_url).execute()
        if not existing.data:
            existing = supabase.table("news_articles").select("*").eq("headline", headline).execute()
        
        record = {
            "headline": headline,
            "summary": summary,
            "content": content,
            "source": source,
            "source_url": source_url,
            "published_at": published_at or datetime.now(timezone.utc).isoformat(),
            "category": category,
            "similar_sources": similar_sources or [],
            "startups_mentioned": startups_mentioned or []
        }
        
        if existing.data:
            # Update existing article record
            article_id = existing.data[0]["id"]
            
            # Retain the primary canonical article credentials to prevent overwrite
            record["source"] = existing.data[0]["source"]
            record["source_url"] = existing.data[0]["source_url"]
            record["published_at"] = existing.data[0]["published_at"]
            
            # Merge startups_mentioned if needed
            exist_startups = existing.data[0].get("startups_mentioned") or []
            exist_startup_names = {s.get("name") for s in exist_startups if isinstance(s, dict)}
            for new_s in (startups_mentioned or []):
                if new_s.get("name") not in exist_startup_names:
                    exist_startups.append(new_s)
            record["startups_mentioned"] = exist_startups
            
            # Merge similar_sources
            exist_sim = existing.data[0].get("similar_sources") or []
            exist_urls = {s.get("url") for s in exist_sim if isinstance(s, dict)}
            
            # If the incoming source is different from the primary source, append it
            if source_url != record["source_url"]:
                if source_url not in exist_urls:
                    exist_sim.append({
                        "source": source,
                        "headline": headline,
                        "url": source_url,
                        "published_at": published_at or datetime.now(timezone.utc).isoformat(),
                        "description": content or summary
                    })
            
            # Merge any other similar_sources that came with the payload
            for new_sim in (similar_sources or []):
                new_sim_url = new_sim.get("url")
                if new_sim_url and new_sim_url != record["source_url"] and new_sim_url not in exist_urls:
                    exist_sim.append(new_sim)
                    
            record["similar_sources"] = exist_sim
            
            res = supabase.table("news_articles").update(record).eq("id", article_id).execute()
            saved_article = res.data[0] if res.data else None
        else:
            # Insert new article record
            res = supabase.table("news_articles").insert(record).execute()
            saved_article = res.data[0] if res.data else None

        if not saved_article:
            return None

        # Retroactive synchronization to startup_news for backward compatibility
        sync_to_legacy_startup_news(saved_article)
        
        return saved_article
    except Exception as e:
        logger.error(f"Failed to save canonical article: {e}")
        return None


def sync_to_legacy_startup_news(article: Dict[str, Any]) -> None:
    """Syncs resolved startups in an article back to legacy startup_news table."""
    startups = article.get("startups_mentioned") or []
    if not startups:
        return
        
    for startup_ref in startups:
        try:
            startup_id = startup_ref.get("id")
            if not startup_id:
                # Find startup ID dynamically by name prefix match in case ID wasn't stored
                name = startup_ref.get("name")
                if name:
                    found = supabase.table("startups").select("id").eq("startup_name", name).execute()
                    if found.data:
                        startup_id = found.data[0]["id"]
            
            if startup_id:
                # Save startup-specific news entry
                save_startup_news(
                    startup_id=int(startup_id),
                    headline=article.get("headline", ""),
                    summary=article.get("summary", ""),
                    source=article.get("source", ""),
                    source_url=article.get("source_url", ""),
                    published_at=article.get("published_at"),
                    startup_mentions=article.get("startups_mentioned", []),
                    raw_source_payload={"content": article.get("content", "")},
                    cleaned_source_payload={"headline": article.get("headline"), "summary": article.get("summary")},
                    pipeline_status={"stage": "SYNCED_FROM_CANONICAL"}
                )
                logger.debug(f"Synced article ID {article['id']} to legacy startup_news for startup_id={startup_id}")
        except Exception as e:
            logger.error(f"Failed to sync legacy news for startup_ref={startup_ref}: {e}")


def resolve_source_search_terms(source_name: str) -> List[str]:
    """Resolves a high-level source select name into its database aliases and variants."""
    source_lower = source_name.lower()
    terms = [source_name]
    if "economic times" in source_lower:
        terms.extend(["Economic Times", "The Economic Times", "Economic Times Startup"])
    elif "yourstory" in source_lower:
        terms.extend(["YourStory", "YourStory.com"])
    elif "moneycontrol" in source_lower:
        terms.extend(["Moneycontrol", "Moneycontrol.com"])
    elif "mint" in source_lower:
        terms.extend(["Mint", "livemint.com"])
    return list(set(terms))


def get_filtered_articles(
    search: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    industry: Optional[str] = None,
    startup: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Retrieves list of canonical news articles matching filters, ordered by published_at desc."""
    try:
        query = supabase.table("news_articles").select("*", count="exact")
        
        # Apply filters
        if category:
            query = query.eq("category", category)
        if source:
            terms = resolve_source_search_terms(source)
            or_conditions = []
            for t in terms:
                escaped_t = t.replace("\"", "\\\"")
                or_conditions.append(f"source.eq.{t}")
                or_conditions.append(f"similar_sources.cs.[{{\"source\":\"{escaped_t}\"}}]")
            query = query.or_(",".join(or_conditions))
            
        # Standard filter logic
        if from_date:
            query = query.gte("published_at", from_date)
        if to_date:
            query = query.lte("published_at", to_date)
            
        # Order and pagination
        query = query.order("published_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        res = query.execute()
        articles = res.data or []
        total_count = res.count or len(articles)
        
        # Post-filter in python for fields stored inside JSONB column (startups_mentioned)
        # or requiring search match against multiple text fields (search/industry filters)
        filtered_articles = []
        for art in articles:
            # Source promotion logic if source filter was requested
            if source:
                terms = resolve_source_search_terms(source)
                terms_lower = [t.lower() for t in terms]
                art_src_lower = (art.get("source") or "").lower()
                if art_src_lower not in terms_lower:
                    # Match must be in similar_sources. Promote it!
                    similar = art.get("similar_sources") or []
                    for idx_sim, sim in enumerate(similar):
                        sim_src_lower = (sim.get("source") or "").lower()
                        if sim_src_lower in terms_lower:
                            # Swap matching entry with primary entry
                            similar_copy = list(similar)
                            similar_copy.pop(idx_sim)
                            original_primary = {
                                "source": art["source"],
                                "headline": art["headline"],
                                "url": art["source_url"],
                                "published_at": art["published_at"],
                                "description": art.get("content") or art.get("summary") or ""
                            }
                            similar_copy.append(original_primary)
                            
                            # Promote matching source details
                            art = dict(art) # copy to avoid mutating original
                            art["source"] = sim["source"]
                            art["source_url"] = sim["url"]
                            art["headline"] = sim["headline"]
                            art["published_at"] = sim.get("published_at") or art["published_at"]
                            art["similar_sources"] = similar_copy
                            break

            # 1. Startup filter (check if name matches any startup in startups_mentioned JSONB)
            if startup:
                mentions = art.get("startups_mentioned") or []
                match = False
                for m in mentions:
                    if isinstance(m, dict) and startup.lower() in (m.get("name") or "").lower():
                        match = True
                        break
                if not match:
                    continue
            
            # 2. Industry filter (requires fetching the startup profile's industry)
            if industry:
                mentions = art.get("startups_mentioned") or []
                match = False
                for m in mentions:
                    if isinstance(m, dict) and m.get("id"):
                        # Get startup details
                        st_res = supabase.table("startups").select("industry").eq("id", m["id"]).execute()
                        if st_res.data:
                            ind = st_res.data[0].get("industry") or ""
                            if industry.lower() in ind.lower():
                                match = True
                                break
                if not match:
                    continue
                    
            # 3. Text search query (matches headline, summary, content, source)
            if search:
                search_lower = search.lower()
                text_pool = f"{art.get('headline','') } {art.get('summary','') } {art.get('content','') } {art.get('source','') }".lower()
                if search_lower not in text_pool:
                    continue
                    
            filtered_articles.append(art)
            
        return {
            "total": total_count,
            "articles": filtered_articles
        }
    except Exception as e:
        logger.error(f"Failed to fetch filtered news articles: {e}")
        return {"total": 0, "articles": []}
