"""
backend/pipeline/news_aggregator.py
---------------------------------
Aggregates news from configured RSS sources and query-based Google News RSS feeds.
"""

from __future__ import annotations
import os
import json
import logging
import urllib.parse
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Any
from backend.services.news_service import load_sources_from_config

logger = logging.getLogger("startup_intelligence.pipeline.news_aggregator")


def clean_html_text(html: str) -> str:
    """Helper to strip HTML tags and return clean text."""
    if not html:
        return ""
    try:
        return BeautifulSoup(html, "html.parser").get_text(strip=True)
    except Exception:
        return html


def parse_pub_date(pub_date_str: str) -> str:
    """Attempts to parse pub date string to standard ISO format."""
    if not pub_date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        import dateutil.parser
        dt = dateutil.parser.parse(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


class NewsAggregator:
    def __init__(self):
        self.sources = load_sources_from_config()

    def fetch_all_raw_articles(self, limit_per_source: int = 10, sources_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Iterates over enabled sources and fetches recent articles.
        Processes Google News query queries as sub-feeds.
        """
        all_articles: List[Dict[str, Any]] = []

        for source in self.sources:
            if not source.get("enabled", True):
                continue
            if sources_filter is not None and source.get("id") not in sources_filter:
                continue
                
            logger.info(f"Aggregating from source: {source['name']} ({source['category']})")
            
            if source.get("feed_type") == "google_news":
                # Fetch query list from google_news_queries.json
                google_articles = self.fetch_google_news_feed(source, limit_per_source)
                all_articles.extend(google_articles)
            else:
                # Standard RSS feed source
                rss_articles = self.fetch_rss_source(source, limit_per_source)
                all_articles.extend(rss_articles)

        logger.info(f"Total raw articles aggregated from all sources: {len(all_articles)}")
        return all_articles

    def fetch_rss_source(self, source: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Parses a standard RSS URL and returns a list of formatted articles."""
        articles = []
        url = source.get("rss_url")
        if not url:
            return []

        try:
            # Add random user-agent or standard client settings
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=source.get("timeout_seconds", 12))
            
            feed = feedparser.parse(response.text)
            entries = feed.entries[:limit]
            
            for entry in entries:
                headline = entry.get("title", "")
                link = entry.get("link", "")
                desc = clean_html_text(entry.get("summary") or entry.get("description") or "")
                
                if headline and link:
                    articles.append({
                        "headline": headline,
                        "description": desc,
                        "content": desc,  # V1 simplified: use description as body or fetch lightweight below
                        "source": source["name"],
                        "source_url": link,
                        "published_at": parse_pub_date(entry.get("published") or entry.get("pubDate")),
                        "category": source["category"],
                        "tags": source.get("tags") or []
                    })
        except Exception as e:
            logger.error(f"Error scraping standard RSS source '{source['name']}': {e}")

        return articles

    def fetch_google_news_feed(self, source: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Generates query-based RSS URLs for Google News and aggregates their feeds."""
        articles = []
        
        # Load queries from config
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        queries_path = os.path.join(project_root, "backend", "config", "google_news_queries.json")
        
        if not os.path.exists(queries_path):
            logger.warning("google_news_queries.json not found, using generic search query")
            queries = ["Indian startup"]
        else:
            try:
                with open(queries_path, "r", encoding="utf-8") as f:
                    queries = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load google_news_queries.json: {e}")
                queries = ["Indian startup"]

        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        
        for query in queries:
            encoded_query = urllib.parse.quote_plus(query)
            # Google news search RSS endpoint
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            try:
                response = requests.get(rss_url, headers=headers, timeout=source.get("timeout_seconds", 12))
                feed = feedparser.parse(response.text)
                entries = feed.entries[:limit]
                
                for entry in entries:
                    headline = entry.get("title", "")
                    link = entry.get("link", "")
                    desc = clean_html_text(entry.get("summary") or entry.get("description") or "")
                    
                    # Google News RSS formats titles as "Headline - Source"
                    # We can clean this up and split the source if needed
                    clean_headline = headline
                    source_name = source["name"] # fallback
                    
                    if " - " in headline:
                        parts = headline.rsplit(" - ", 1)
                        clean_headline = parts[0].strip()
                        source_name = parts[1].strip()

                    if clean_headline and link:
                        articles.append({
                            "headline": clean_headline,
                            "description": desc,
                            "content": desc,
                            "source": source_name,
                            "source_url": link,
                            "published_at": parse_pub_date(entry.get("published") or entry.get("pubDate")),
                            "category": source["category"],
                            "tags": source.get("tags") or []
                        })
            except Exception as e:
                logger.error(f"Error fetching Google News query '{query}': {e}")
                
        return articles
