"""
backend/pipeline/news_processor.py
--------------------------------
Main news processor that connects the Aggregator, Deduplicator,
and existing Startup Ingestion pipelines.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any
from backend.pipeline.news_aggregator import NewsAggregator
from backend.pipeline.deduplicator import Deduplicator
from backend.services.news_service import save_canonical_article
from backend.workflows.startup_pipeline import discover_startup_names, process_startup

import requests
import re
from bs4 import BeautifulSoup

logger = logging.getLogger("startup_intelligence.pipeline.news_processor")

def fetch_full_article_content(url: str) -> str:
    """Fetches the target URL, parses its HTML, and extracts clean, formatted paragraph text using shared context validator."""
    if not url:
        return ""
    try:
        from backend.scrapers.common.context_validator import extract_clean_paragraphs
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
            
        paragraphs = extract_clean_paragraphs(response.text)
        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"Failed to scrape full content for {url}: {e}")
        
    return ""






_INGESTION_ABORTED = False

def set_ingestion_aborted(val: bool):
    global _INGESTION_ABORTED
    _INGESTION_ABORTED = val

def is_ingestion_aborted() -> bool:
    global _INGESTION_ABORTED
    return _INGESTION_ABORTED


class NewsProcessor:
    def __init__(self, silent: bool = False, log_fn=None, status_fn=None):
        """Initialize the news processor.
        
        Args:
            silent: Suppress all logging/status updates (used by scheduler).
            log_fn: Optional callable(msg: str) for writing log lines.
            status_fn: Optional callable(**kwargs) for updating sync status.
        """
        self.aggregator = NewsAggregator()
        self.deduplicator = Deduplicator()
        self.silent = silent
        self._log_fn = log_fn
        self._status_fn = status_fn

    def add_log(self, msg: str):
        """Logs message to console and invokes the injected log callback if set."""
        logger.info(msg)
        if self.silent or self._log_fn is None:
            return
        try:
            self._log_fn(msg)
        except Exception:
            pass

    def update_status(self, current_step: str = None, discovered_increment: int = 0, processed_name: str = None, active: bool = None, last_news_sync: dict = None):
        """Invokes the injected status callback if set."""
        if self.silent or self._status_fn is None:
            return
        try:
            self._status_fn(current_step=current_step, discovered_increment=discovered_increment, active=active, last_news_sync=last_news_sync)
        except Exception:
            pass

    def run_ingestion_pipeline(self, limit_per_source: int = 5, sources_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Runs the full ingestion, deduplication, and startup mapping flow.
        Reuses the existing Startup Intelligence pipeline where appropriate.
        """
        set_ingestion_aborted(False)
        self.add_log("Starting Startup News Ingestion Pipeline...")
        self.update_status(current_step="Fetching RSS sources...", active=True)
        
        # 1. Fetch raw articles from configs
        raw_articles = self.aggregator.fetch_all_raw_articles(limit_per_source, sources_filter)
        if not raw_articles:
            self.add_log("No new articles fetched. Pipeline completed.")
            self.update_status(current_step="Idle", active=False)
            return {"status": "success", "processed_count": 0, "saved_count": 0}

        self.add_log(f"Aggregated {len(raw_articles)} raw stories across all feeds.")
        self.update_status(current_step="Deduplicating news feeds...")

        # 2. Filter exact and semantic duplicates (Before AI summary)
        canonical_articles = self.deduplicator.cluster_and_deduplicate(raw_articles)
        self.add_log(f"Deduplicated to {len(canonical_articles)} canonical clusters.")

        saved_count = 0
        processed_count = len(raw_articles)
        saved_headlines = []

        # 3. Process each canonical story
        for idx, art in enumerate(canonical_articles):
            if is_ingestion_aborted():
                self.add_log("🛑 Ingestion pipeline interrupted by user. Stopping execution...")
                self.update_status(current_step="Idle (Interrupted)", active=False)
                set_ingestion_aborted(False)
                return {"status": "interrupted", "processed_count": idx, "saved_count": saved_count}
                
            try:
                headline = art["headline"]
                description = art["description"]
                content = art["content"]
                
                # Check if this incoming canonical story is a semantic duplicate of a database article
                db_dup = self.deduplicator.check_semantic_database_duplicate(art)
                if db_dup:
                    self.add_log(f"🔗 Match found in DB for duplicate coverage: '{headline}'. Appending new source logo.")
                    # Format incoming article and its similar sources to append
                    incoming_sources = [{
                        "source": art["source"],
                        "headline": art["headline"],
                        "url": art["source_url"],
                        "published_at": art["published_at"],
                        "description": art.get("description", ""),
                        "content": art.get("content", "")
                    }]
                    for sim in art.get("similar_sources", []):
                        incoming_sources.append({
                            "source": sim["source"],
                            "headline": sim["headline"],
                            "url": sim["url"],
                            "published_at": sim["published_at"],
                            "description": sim.get("description", ""),
                            "content": sim.get("content", "")
                        })
                    
                    # Merge with existing similar sources in database
                    existing_sources = db_dup.get("similar_sources") or []
                    if not isinstance(existing_sources, list):
                        existing_sources = []
                    
                    # Add incoming sources if they are not already in existing_sources (deduplicated by URL)
                    existing_urls = {x.get("url") for x in existing_sources}
                    for inc_src in incoming_sources:
                        if inc_src.get("url") and inc_src.get("url") not in existing_urls:
                            existing_sources.append(inc_src)
                            
                    # Update database row in news_articles
                    from backend.services.supabase_service import supabase
                    supabase.table("news_articles").update({
                        "similar_sources": existing_sources
                    }).eq("id", db_dup["id"]).execute()
                    
                    saved_count += 1
                    self.update_status(discovered_increment=1)
                    continue

                self.update_status(current_step=f"Processing {idx + 1}/{len(canonical_articles)}: {headline[:40]}...")
                self.add_log(f"Fetching full article content from: {art['source_url']}")
                
                full_content = fetch_full_article_content(art["source_url"])
                if full_content:
                    self.add_log(f"Successfully scraped full article content ({len(full_content)} chars).")
                    content = full_content
                else:
                    self.add_log("Could not parse full article body, falling back to RSS summary.")
                    content = content or description
                    
                # Update the article content attribute in place
                art["content"] = content
                
                self.add_log(f"Extracting startup mentions from: '{headline}'")
                paragraphs = [content] if content else [description]
                
                p1_res = discover_startup_names(headline, paragraphs)
                discovered_items = p1_res.get("startups") or []
                ai_summary = p1_res.get("ai_summary") or ""
                
                # Check for startup names in all clustered duplicate articles in the same cluster to retain all startups!
                similar_sources = art.get("similar_sources") or []
                for sim in similar_sources:
                    sim_headline = sim.get("headline") or ""
                    sim_desc = sim.get("description") or ""
                    sim_content = sim.get("content") or ""
                    sim_paragraphs = [sim_content] if sim_content else ([sim_desc] if sim_desc else [])
                    sim_res = discover_startup_names(sim_headline, sim_paragraphs)
                    sim_items = sim_res.get("startups") or []
                    for item in sim_items:
                        item_name = item.get("name") if isinstance(item, dict) else item
                        # Add if not already in discovered_items
                        existing_names = {x.get("name") if isinstance(x, dict) else x for x in discovered_items}
                        if item_name and item_name not in existing_names:
                            discovered_items.append(item)

                startups_mentioned = []

                if discovered_items:
                    self.add_log(f"Discovered potential startups: {discovered_items}")
                    # For each startup, check database first to see if it already exists
                    for item in discovered_items:
                        name = item.get("name") if isinstance(item, dict) else item
                        if not name:
                            continue
                            
                        from backend.services.supabase_service import check_existing_startup
                        existing = check_existing_startup(name)
                        
                        if existing:
                            s_id = existing["id"]
                            s_name = existing.get("startup_name", name)
                            s_web = existing.get("website", "")
                            
                            startups_mentioned.append({
                                "id": s_id,
                                "name": s_name,
                                "website": s_web
                            })
                            self.update_status(processed_name=s_name)
                            # Link the canonical news event to the startup history in background
                            try:
                                from backend.services.news_repo import save_startup_news
                                save_startup_news(
                                    startup_id=s_id,
                                    headline=headline,
                                    summary=ai_summary or description,
                                    source=art["source"],
                                    source_url=art["source_url"],
                                    published_at=art["published_at"]
                                )
                            except Exception:
                                pass
                        else:
                            # Startup is NOT in repository: Add as placeholder mention (id=None, website="")
                            startups_mentioned.append({
                                "id": None,
                                "name": name,
                                "website": ""
                            })
                            self.update_status(processed_name=name)
                else:
                    logger.debug(f"No startups discovered in canonical story: '{headline}'")

                # Reuse the pre-extracted/generated AI summary, fallback to raw description if none was generated
                if not ai_summary:
                    ai_summary = description or headline
                
                # 4. Save canonical article to DB (which triggers legacy startup_news sync)
                saved = save_canonical_article(
                    headline=headline,
                    summary=ai_summary,
                    content=content or description,
                    source=art["source"],
                    source_url=art["source_url"],
                    published_at=art["published_at"],
                    category=art["category"],
                    similar_sources=art.get("similar_sources", []),
                    startups_mentioned=startups_mentioned
                )
                if saved:
                    saved_count += 1
                    self.update_status(discovered_increment=1)
                    saved_headlines.append(headline)
                    
            except Exception as e:
                self.add_log(f"❌ Failed to process article '{art.get('headline')}': {e}")
                logger.error(f"Failed to process article: {e}", exc_info=True)

        self.add_log(f"Startup News Ingestion Pipeline completed. Processed {processed_count} raw articles, saved {saved_count} canonical stories.")
        
        # Mark sync as completed and push status telemetry
        from datetime import datetime
        self.update_status(
            current_step="Idle", 
            active=False,
            last_news_sync={
                "completed_at": datetime.now().isoformat(),
                "processed_count": processed_count,
                "saved_count": saved_count,
                "articles": saved_headlines
            }
        )
        
        return {
            "status": "success",
            "processed_count": processed_count,
            "saved_count": saved_count
        }
