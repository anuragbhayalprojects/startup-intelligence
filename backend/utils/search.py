"""
backend/utils/search.py
---------------------------
Web search utilities for Startup Intelligence OS.

Two layers:
  1. Low-level HTTP search functions (DuckDuckGo, Google) — unchanged
  2. WebSearchOrchestrator class — typed interface to search_queries.json v2.0

WebSearchOrchestrator is the single entry point for all search query operations:
  - Initial discovery (all 8 field buckets)
  - Fallback and AI-recheck queries
  - BM25 query string retrieval
  - Link discovery keyword retrieval
  - Resolver query retrieval
"""

from __future__ import annotations

try:
    from curl_cffi import requests
except ImportError:
    import requests

from bs4 import BeautifulSoup
import urllib.parse
import os
import json
import time
import random
import re
import logging
from typing import Optional

logger = logging.getLogger("startup_intelligence.search")

# ---------------------------------------------------------------------------
# Low-level HTTP search functions (unchanged from v1)
# ---------------------------------------------------------------------------

def search_google(query: str) -> str:
    """
    Performs a zero-key organic HTML scrape of Google Search results.
    Optional and non-blocking.
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    delay = random.uniform(1.0, 3.0)
    time.sleep(delay)

    try:
        kwargs = {"headers": headers, "timeout": 5}
        try:
            response = requests.get(url, impersonate="chrome120", **kwargs)
        except TypeError:
            response = requests.get(url, **kwargs)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            result_divs = soup.find_all("div", class_="g")
            for idx, div in enumerate(result_divs[:4]):
                title_el = div.find("h3")
                link_el = div.find("a")
                snippet_el = div.find("div", class_=lambda c: c and ("VwiC3b" in c or "yD3Yfe" in c or "muw5gc" in c))
                if not snippet_el:
                    snippet_el = div.find("div", class_="VwiC3b") or div.find("span", class_="aCO3fc")
                if title_el and link_el:
                    title = title_el.get_text(strip=True)
                    href = link_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else "No snippet description available."
                    results.append(f"[{idx+1}] Title: {title}\nURL: {href}\nSnippet: {snippet}\n")
            return "\n".join(results)
    except Exception:
        pass
    return ""


def search_ddg_raw(query: str) -> str:
    """
    Performs a zero-key HTML scrape of DuckDuckGo.
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    delay = random.uniform(8.0, 15.0)
    time.sleep(delay)

    try:
        kwargs = {"headers": headers, "timeout": 8}
        try:
            response = requests.get(url, impersonate="chrome120", **kwargs)
        except TypeError:
            response = requests.get(url, **kwargs)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        result_divs = soup.find_all("div", class_="result")
        for idx, div in enumerate(result_divs[:5]):
            title_link = div.find("a", class_="result__a")
            snippet_link = div.find("a", class_="result__snippet")

            if title_link and snippet_link:
                title = title_link.get_text(strip=True)
                snippet = snippet_link.get_text(strip=True)
                href = title_link.get("href", "")

                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                real_url = qs.get("uddg", [None])[0] or href

                results.append(f"[{idx+1}] Title: {title}\nURL: {real_url}\nSnippet: {snippet}\n")

        if not results:
            snippets = soup.find_all("a", class_="result__snippet")
            for idx, snip in enumerate(snippets[:5]):
                snippet = snip.get_text(strip=True)
                results.append(f"[{idx+1}] Snippet: {snippet}\n")

        context = "\n".join(results)
        return context if context.strip() else "No web search snippets found."
    except Exception as e:
        return f"Could not perform web search due to error: {str(e)}"


_SEARCH_CACHE: dict = {}


def search_duckduckgo(query: str) -> str:
    """
    Main entry point for raw search. DuckDuckGo primary, Google fallback.
    Uses in-memory query cache to avoid redundant web scrapes.
    """
    normalized_query = query.strip().lower()
    if normalized_query in _SEARCH_CACHE:
        logger.debug(f"[Search Cache Hit] Reusing results for: '{query}'")
        return _SEARCH_CACHE[normalized_query]

    ddg_res = search_ddg_raw(query)
    if ddg_res and "No web search snippets found" not in ddg_res and "error" not in ddg_res.lower():
        _SEARCH_CACHE[normalized_query] = ddg_res
        return ddg_res

    res = search_google(query) or ddg_res
    _SEARCH_CACHE[normalized_query] = res
    return res


def classify_url(url: str) -> str:
    """Classifies a URL into a standard target category."""
    url_lower = url.lower()
    if "linkedin.com/company/" in url_lower:
        return "linkedin"

    news_domains = ["inc42.com", "entrackr.com", "yourstory.com", "techcrunch.com",
                    "livemint.com", "economictimes", "moneycontrol", "vccircle.com", "businessstandard.com"]
    if any(nd in url_lower for nd in news_domains) or "/news/" in url_lower or "/article/" in url_lower:
        return "news"

    funding_keywords = ["crunchbase.com", "tracxn.com", "pitchbook.com", "dealroom"]
    if any(fk in url_lower for fk in funding_keywords):
        return "funding_sources"

    social_domains = ["twitter.com", "x.com", "facebook.com", "youtube.com", "instagram.com", "github.com"]
    if any(sd in url_lower for sd in social_domains):
        return "social_profiles"

    return "official_website"


# ---------------------------------------------------------------------------
# WebSearchOrchestrator — v2 typed interface to search_queries.json
# ---------------------------------------------------------------------------

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config", "search_queries.json"
)
_PIPELINE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config", "pipeline_config.json"
)

# Hard-coded fallback defaults — used if search_queries.json is missing or corrupt
_DEFAULT_DISCOVERY_QUERIES = {
    "official_website": ["{startup_name} official website", "{startup_name} company"],
    "official_linkedin": ["{startup_name} linkedin"],
    "founders_and_leadership": ["{startup_name} founders co-founders CEO"],
    "products_and_solutions": ["{startup_name} products"],
    "funding_details": ["{startup_name} funding rounds investors"],
    "competitors": ["{startup_name} competitors"],
    "headquarter": ["{startup_name} headquarters location"],
    "founded_year": ["{startup_name} founded year"],
}

_DEFAULT_FALLBACK_QUERIES = {
    "official_website": ["{clean_name} official website", "{clean_name} company"],
    "founders_and_leadership": ["{clean_name} founders co-founders"],
    "products_and_solutions": ["{clean_name} products services"],
    "funding_details": ["{clean_name} funding investors"],
    "competitors": ["{clean_name} competitors"],
    "headquarter": ["{clean_name} headquarters"],
    "founded_year": ["{clean_name} founded year"],
    "official_linkedin": ["{clean_name} linkedin"],
}


class WebSearchOrchestrator:
    """
    Central interface to search_queries.json v2.0.

    Loads the config once at construction and exposes typed accessor methods
    for all query types used across the pipeline:
      - Initial discovery (field-bucketed, {startup_name})
      - Fallback / AI-Recheck queries (field-bucketed, {clean_name})
      - BM25 query strings (per enricher key)
      - Link discovery keywords (per crawler bucket)
      - Resolver query templates ({brand_name})

    All run_*() methods parse results into structured records:
      { title, url, snippet, phase, query, source_domain }
    """

    def __init__(self):
        self._config: dict = self._load_config()
        self._pipeline_config: dict = self._load_pipeline_config()

    # ------------------------------------------------------------------
    # Config loading with fallbacks
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        """Loads search_queries.json with graceful fallback to defaults."""
        try:
            if os.path.exists(_CONFIG_PATH):
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("version", "1.0") >= "2.0":
                        logger.info("[WebSearchOrchestrator] Loaded search_queries.json v2.0")
                        return data
                    else:
                        logger.warning("[WebSearchOrchestrator] search_queries.json is pre-v2. Using defaults.")
        except Exception as e:
            logger.error(f"[WebSearchOrchestrator] Failed to load search_queries.json: {e}")
        return {}

    def _load_pipeline_config(self) -> dict:
        """Loads pipeline_config.json for v2 controls."""
        try:
            if os.path.exists(_PIPELINE_CONFIG_PATH):
                with open(_PIPELINE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[WebSearchOrchestrator] Failed to load pipeline_config.json: {e}")
        return {}

    # ------------------------------------------------------------------
    # Query accessors
    # ------------------------------------------------------------------

    def get_initial_discovery_queries(self, startup_name: str, field: str) -> list[str]:
        """
        Returns formatted initial discovery query list for a single field bucket.

        Parameters
        ----------
        startup_name : raw discovered startup name
        field        : one of the 8 field bucket keys (e.g. 'founders_and_leadership')
        """
        templates = (
            self._config
            .get("initial_discovery", {})
            .get(field, {})
            .get("queries", _DEFAULT_DISCOVERY_QUERIES.get(field, []))
        )
        return [t.replace("{startup_name}", startup_name) for t in templates]

    def get_all_initial_discovery_queries(self, startup_name: str) -> dict[str, list[str]]:
        """
        Returns all 8 field bucket query lists formatted with {startup_name}.
        Returns: { field_key: [query_string, ...], ... }
        """
        buckets = self._pipeline_config.get("v2_pipeline", {}).get(
            "discovery_field_buckets",
            list(_DEFAULT_DISCOVERY_QUERIES.keys())
        )
        return {
            field: self.get_initial_discovery_queries(startup_name, field)
            for field in buckets
        }

    def get_fallback_queries(self, enricher_key: str, clean_name: str, brand_name: str = "") -> list[str]:
        """
        Returns formatted fallback query list for a field bucket.

        Parameters
        ----------
        enricher_key : field bucket key matching fallback_and_ai_recheck (e.g. 'funding_details')
        clean_name   : resolved brand name (replaces {clean_name})
        brand_name   : optional confirmed brand name (replaces {brand_name}, defaults to clean_name)
        """
        _brand = brand_name or clean_name
        templates = (
            self._config
            .get("fallback_and_ai_recheck", {})
            .get(enricher_key, {})
            .get("queries", _DEFAULT_FALLBACK_QUERIES.get(enricher_key, []))
        )
        max_q = self._pipeline_config.get("v2_pipeline", {}).get("fallback_max_queries_per_field", 3)
        formatted = [
            t.replace("{clean_name}", clean_name).replace("{brand_name}", _brand)
            for t in templates[:max_q]
        ]
        return formatted

    def get_bm25_query(self, enricher_key: str) -> str:
        """
        Returns the BM25 keyword string for a given enricher key.
        enricher_key: corporate_query | identity_query | product_query | competitor_query | funding_query
        """
        defaults = {
            "corporate_query": "legal name registered office address linkedin url founding year established headquarters",
            "identity_query": "founders leadership team profiles background linkedin url histories executive officers",
            "product_query": "products services solutions technology platforms categories features targets deployment models",
            "competitor_query": "competitors alternatives comparable companies direct indirect market rivals substitutes",
            "funding_query": "funding round investment raised series seed investors valuation crore million lead co-investor",
        }
        return (
            self._config
            .get("internal_crawler_queries", {})
            .get("bm25_queries", {})
            .get(enricher_key, defaults.get(enricher_key, ""))
        )

    def get_link_discovery_keywords(self, bucket: str) -> dict:
        """
        Returns link discovery config for a crawler bucket.
        bucket: identity_bucket | offerings_bucket | corporate_bucket
        Returns: { keywords: [...], max_urls: int }
        """
        defaults = {
            "identity_bucket": {"keywords": ["team", "about", "founders", "leadership"], "max_urls": 2},
            "offerings_bucket": {"keywords": ["products", "solutions", "services", "platform"], "max_urls": 7},
            "corporate_bucket": {"keywords": ["contact", "privacy", "legal", "terms"], "max_urls": 1},
        }
        return (
            self._config
            .get("internal_crawler_queries", {})
            .get("link_discovery_keywords", {})
            .get(bucket, defaults.get(bucket, {"keywords": [], "max_urls": 1}))
        )

    def get_resolver_query(self, resolver_key: str, brand_name: str) -> str:
        """
        Returns a formatted resolver query string.
        resolver_key: website_resolver | linkedin_resolver
        """
        template = (
            self._config
            .get("resolvers", {})
            .get(resolver_key, {})
            .get("query", f"{brand_name} official website")
        )
        return template.replace("{brand_name}", brand_name)

    def get_api_recheck_query(self, field_key: str, clean_name: str) -> str:
        """Returns a single formatted api_rechecks query for UI-triggered re-enrichment."""
        template = self._config.get("api_rechecks", {}).get(field_key, f"{clean_name} {field_key}")
        return template.replace("{clean_name}", clean_name)

    # ------------------------------------------------------------------
    # Search execution with structured record output
    # ------------------------------------------------------------------

    def _parse_results(self, raw: str, query: str, phase: str) -> list[dict]:
        """
        Parses raw search engine text into structured snippet records.
        Each record: { title, url, snippet, phase, query, source_domain }
        """
        records = []
        visited_urls: set = set()
        matches = re.findall(r"\[\d+\] Title: (.*?)\nURL: (.*?)\nSnippet: (.*?)\n", raw, re.DOTALL)
        for title, url, snippet in matches:
            url_clean = url.strip()
            if url_clean in visited_urls:
                continue
            visited_urls.add(url_clean)
            try:
                source_domain = urllib.parse.urlparse(url_clean).netloc.replace("www.", "")
            except Exception:
                source_domain = ""
            records.append({
                "title": title.strip(),
                "url": url_clean,
                "snippet": snippet.strip(),
                "phase": phase,
                "query": query,
                "source_domain": source_domain,
            })
        return records

    def run_search(self, query: str, phase: str = "initial") -> list[dict]:
        """
        Runs a single search query and returns structured snippet records.
        Fallback: DDG primary, Google secondary.
        """
        logger.info(f"[WebSearchOrchestrator] Searching: '{query}' (phase={phase})")
        raw = search_duckduckgo(query)
        return self._parse_results(raw, query, phase)

    def run_field_searches(self, field: str, queries: list[str], phase: str = "initial") -> list[dict]:
        """
        Runs a list of queries for a field bucket and deduplicates by URL.
        Returns merged list of structured records.
        """
        all_records: list[dict] = []
        seen_urls: set = set()
        for q in queries:
            records = self.run_search(q, phase=phase)
            for rec in records:
                if rec["url"] not in seen_urls:
                    seen_urls.add(rec["url"])
                    all_records.append(rec)
        max_snips = self._pipeline_config.get("v2_pipeline", {}).get("fallback_max_snippets_per_field", 5)
        return all_records if phase == "initial" else all_records[:max_snips]

    def discover_all_evidence(self, startup_name: str) -> dict[str, list[dict]]:
        """
        Fires initial discovery queries for ALL 8 field buckets.
        Returns field-bucketed dict of snippet records tagged with phase='initial'.

        This is the main entry point for Phase 3 of the v2 pipeline.
        """
        all_queries = self.get_all_initial_discovery_queries(startup_name)
        result: dict[str, list[dict]] = {}
        for field, queries in all_queries.items():
            logger.info(f"[WebSearchOrchestrator] Discovering field='{field}' with {len(queries)} queries")
            result[field] = self.run_field_searches(field, queries, phase="initial")
        return result

    def run_fallback_for_field(
        self,
        enricher_key: str,
        clean_name: str,
        brand_name: str = "",
    ) -> list[dict]:
        """
        Fires fallback queries for a single field bucket.
        Returns snippet records tagged with phase='fallback'.
        """
        queries = self.get_fallback_queries(enricher_key, clean_name, brand_name)
        logger.info(
            f"[WebSearchOrchestrator] Running fallback for key='{enricher_key}' "
            f"clean_name='{clean_name}' ({len(queries)} queries)"
        )
        return self.run_field_searches(enricher_key, queries, phase="fallback")


# ---------------------------------------------------------------------------
# Backward-compatibility shims (v1 callers — deprecated, do not extend)
# ---------------------------------------------------------------------------

def load_search_queries() -> dict:
    """
    DEPRECATED: Use WebSearchOrchestrator instead.
    Retained for backward compatibility with v1 callers.
    """
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[load_search_queries] Failed: {e}")
    return {}


def load_priority_sources() -> list:
    """Loads priority search sources configuration."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "search_sources_config.json"
    )
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
                return data.get("priority_sources", [])
    except Exception as e:
        logger.warning(f"[load_priority_sources] Failed: {e}")
    return []


def discover_search_evidence(startup_name: str) -> dict:
    """
    DEPRECATED shim: delegates to WebSearchOrchestrator.discover_all_evidence().
    Returns classification_map keyed by URL category (legacy format) for v1 compatibility.
    """
    orchestrator = WebSearchOrchestrator()
    field_bucketed = orchestrator.discover_all_evidence(startup_name)

    # Convert field-bucketed dict to legacy URL-category-keyed format
    classification_map: dict = {
        "official_website": [],
        "linkedin": [],
        "news": [],
        "funding_sources": [],
        "directories": [],
        "social_profiles": [],
    }
    seen_urls: set = set()
    for field, records in field_bucketed.items():
        for rec in records:
            url = rec.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            cat = classify_url(url)
            classification_map.setdefault(cat, []).append({
                "title": rec.get("title", ""),
                "url": url,
                "snippet": rec.get("snippet", ""),
            })
    return classification_map
