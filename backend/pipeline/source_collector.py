"""
backend/pipeline/source_collector.py
----------------------------------------
Source-centric web content collector for Startup Intelligence OS — v2.

Implements the v2 source payload architecture:
  - raw_source_payload.crawled_pages: dynamic dict keyed by actual page role
  - raw_source_payload.search_snippets: field-bucketed with per-record metadata
  - raw_source_payload.crawl_metadata: pages crawled, playwright flag, timestamp

Link discovery keywords are read from search_queries.json via WebSearchOrchestrator
(no longer hardcoded in scraper_config.json).

Backward-compat: format_source_payload_for_prompt() still works with both
the old flat-field format and the new crawled_pages dict format.
"""

from __future__ import annotations

import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("startup_intelligence.source_collector")

_SCRAPER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config", "scraper_config.json"
)

# ---------------------------------------------------------------------------
# Scraper config loader with fallbacks
# ---------------------------------------------------------------------------

def _load_scraper_config() -> dict:
    """Loads scraper_config.json with sensible defaults."""
    defaults = {
        "client": {"timeout_seconds": 10, "min_body_characters": 600},
        "bm25_settings": {"chunk_size_chars": 1000, "chunk_overlap_chars": 150,
                          "character_budget_per_pass": 6000, "max_chunks_selected": 6},
    }
    try:
        if os.path.exists(_SCRAPER_CONFIG_PATH):
            with open(_SCRAPER_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Deep merge with defaults
                for k, v in defaults.items():
                    if k not in data:
                        data[k] = v
                return data
    except Exception as e:
        logger.warning(f"[SourceCollector] Failed to load scraper_config.json: {e} — using defaults")
    return defaults


_SCRAPER_CFG = _load_scraper_config()

# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------

def _fetch_html(url: str) -> str:
    """Fetches HTML using curl_cffi (browser impersonation) with requests fallback."""
    timeout = _SCRAPER_CFG.get("client", {}).get("timeout_seconds", 10)
    try:
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(
                url,
                impersonate="chrome120",
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; StartupIntelligenceBot/4.0)"},
            )
            if resp.status_code < 400:
                return resp.text
        except (ImportError, TypeError):
            import requests
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; StartupIntelligenceBot/4.0)"},
            )
            if resp.status_code < 400:
                return resp.text
    except Exception as e:
        logger.debug(f"[SourceCollector] Failed to fetch {url}: {e}")
    return ""


def _fetch_with_playwright(url: str) -> str:
    """Playwright headless browser fallback for JS-rendered sites."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=5000)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        logger.debug(f"[SourceCollector] Playwright failed for {url}: {e}")
    return ""


def _html_to_text(html: str, max_chars: int = 3000) -> str:
    """Converts HTML to clean plain text, removing nav/scripts/styles."""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "iframe", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.debug(f"[SourceCollector] HTML-to-text failed: {e}")
        return html[:max_chars]


def _extract_footer_text(html: str) -> str:
    """Extracts footer element text — often contains legal name and address."""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        footer = soup.find("footer")
        if footer:
            return footer.get_text(separator=" ", strip=True)[:600]
        # Fallback: look for copyright text patterns
        page_text = soup.get_text(separator=" ", strip=True)
        copyright_match = re.search(r'(©|copyright|pvt\.?\s*ltd|private limited|pte\s+limited).{0,200}', page_text, re.IGNORECASE)
        if copyright_match:
            return copyright_match.group(0)[:400]
    except Exception:
        pass
    return ""


def _extract_social_links(html: str) -> dict:
    """Extracts social media links from page HTML."""
    links: dict = {}
    if not html:
        return links
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        social_patterns = {
            "linkedin": r"linkedin\.com/company/[^/\"'\s]+",
            "twitter": r"(?:twitter|x)\.com/[^/\"'\s]+",
            "facebook": r"facebook\.com/[^/\"'\s]+",
            "instagram": r"instagram\.com/[^/\"'\s]+",
            "youtube": r"youtube\.com/[^/\"'\s]+",
            "github": r"github\.com/[^/\"'\s]+",
        }
        page_html = str(soup)
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, page_html, re.IGNORECASE)
            if match:
                url = "https://" + match.group(0) if not match.group(0).startswith("http") else match.group(0)
                links[platform] = url.split('"')[0].split("'")[0]
    except Exception:
        pass
    return links


def _extract_seo_metadata(html: str) -> dict:
    """Extracts title, meta description, and OG tags."""
    metadata: dict = {}
    if not html:
        return metadata
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            metadata["meta_description"] = desc_tag.get("content", "")
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            metadata["og_description"] = og_desc.get("content", "")
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title:
            metadata["og_title"] = og_title.get("content", "")
    except Exception:
        pass
    return metadata


# ---------------------------------------------------------------------------
# Link discovery — reads keywords from WebSearchOrchestrator
# ---------------------------------------------------------------------------

def _discover_sub_page_links(html: str, base_url: str, orchestrator=None) -> dict[str, str]:
    """
    Discovers crawlable sub-page links from homepage HTML.
    Keywords loaded from search_queries.json via WebSearchOrchestrator.
    Returns: { role_label: absolute_url }
    """
    links: dict[str, str] = {}
    if not html:
        return links

    # Load keyword buckets from orchestrator or defaults
    if orchestrator is None:
        from backend.utils.search import WebSearchOrchestrator
        orchestrator = WebSearchOrchestrator()

    id_cfg = orchestrator.get_link_discovery_keywords("identity_bucket")
    off_cfg = orchestrator.get_link_discovery_keywords("offerings_bucket")
    corp_cfg = orchestrator.get_link_discovery_keywords("corporate_bucket")

    # Build priority-ordered keyword map: bucket_name -> (keywords, max_urls)
    bucket_map = {
        "identity": (id_cfg["keywords"], id_cfg.get("max_urls", 2)),
        "offerings": (off_cfg["keywords"], off_cfg.get("max_urls", 7)),
        "corporate": (corp_cfg["keywords"], corp_cfg.get("max_urls", 1)),
    }

    bucket_counts: dict[str, int] = {k: 0 for k in bucket_map}

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            text = anchor.get_text(strip=True).lower()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            abs_url = urljoin(base_url, href)
            if urlparse(abs_url).netloc != urlparse(base_url).netloc:
                continue  # Skip external links
            for bucket, (keywords, max_u) in bucket_map.items():
                if bucket_counts[bucket] >= max_u:
                    continue
                if any(kw in href.lower() or kw in text for kw in keywords):
                    # Use the href path segment as the role key (dynamic naming)
                    path_segment = urlparse(abs_url).path.strip("/").split("/")[0] or "page"
                    role_key = re.sub(r"[^a-z0-9_-]", "", path_segment.lower()) or bucket
                    if role_key not in links:
                        links[role_key] = abs_url
                        bucket_counts[bucket] += 1
                    break
    except Exception as e:
        logger.debug(f"[SourceCollector] Link discovery failed: {e}")

    return links


# ---------------------------------------------------------------------------
# Single page crawler — returns structured page record
# ---------------------------------------------------------------------------

def _crawl_page(url: str, role: str, use_playwright: bool = True) -> dict:
    """
    Crawls a single page and returns a structured page record.
    Keys: url, page_title, text_content, footer_text, social_links, seo_metadata
    """
    min_chars = _SCRAPER_CFG.get("client", {}).get("min_body_characters", 600)
    max_chars = 6000  # loaded from pipeline_config in collect_source_payload

    html = _fetch_html(url)
    if not html and use_playwright:
        logger.info(f"[SourceCollector] Playwright fallback for {url}")
        html = _fetch_with_playwright(url)

    if not html or len(html) < min_chars:
        logger.debug(f"[SourceCollector] Skipping {url} — insufficient content")
        return {}

    return {
        "url": url,
        "page_title": _extract_seo_metadata(html).get("title", ""),
        "text_content": _html_to_text(html, max_chars=max_chars),
        "footer_text": _extract_footer_text(html),
        "social_links": _extract_social_links(html),
        "seo_metadata": _extract_seo_metadata(html),
    }


# ---------------------------------------------------------------------------
# Main collection API
# ---------------------------------------------------------------------------

def collect_source_payload(
    startup_name: str,
    website_url: Optional[str] = None,
    search_snippets: Optional[dict] = None,
    use_playwright_fallback: bool = True,
    orchestrator=None,
) -> dict:
    """
    Collects and structures raw source content from startup web properties.

    Returns raw_source_payload dict (v2 format):
    {
      "crawled_pages": {
        "<page_role>": {
          "url", "page_title", "text_content", "footer_text", "social_links", "seo_metadata"
        }, ...
      },
      "search_snippets": {
        "<field_bucket>": [
          { "title", "url", "snippet", "phase", "query", "source_domain" }, ...
        ], ...
      },
      "crawl_metadata": {
        "pages_crawled", "playwright_used", "crawl_timestamp", "website_url"
      }
    }
    """
    if orchestrator is None:
        from backend.utils.search import WebSearchOrchestrator
        orchestrator = WebSearchOrchestrator()

    crawled_pages: dict = {}
    playwright_used = False

    if not website_url:
        logger.info(f"[SourceCollector] No website URL for '{startup_name}' — skipping crawl.")
    else:
        # 1. Fetch homepage
        logger.info(f"[SourceCollector] Fetching homepage: {website_url}")
        homepage_html = _fetch_html(website_url)

        if not homepage_html and use_playwright_fallback:
            logger.info(f"[SourceCollector] Empty response — Playwright fallback for {website_url}")
            homepage_html = _fetch_with_playwright(website_url)
            playwright_used = bool(homepage_html)

        if homepage_html:
            homepage_record = {
                "url": website_url,
                "page_title": _extract_seo_metadata(homepage_html).get("title", ""),
                "text_content": _html_to_text(homepage_html, max_chars=6000),
                "footer_text": _extract_footer_text(homepage_html),
                "social_links": _extract_social_links(homepage_html),
                "seo_metadata": _extract_seo_metadata(homepage_html),
            }
            crawled_pages["homepage"] = homepage_record

            # 2. Discover sub-page links using keyword buckets from search_queries.json
            sub_links = _discover_sub_page_links(homepage_html, website_url, orchestrator)

            # 3. Crawl discovered sub-pages (dynamic keys = actual page role from URL path)
            for role, sub_url in sub_links.items():
                logger.info(f"[SourceCollector] Crawling sub-page role='{role}': {sub_url}")
                page_record = _crawl_page(sub_url, role, use_playwright=use_playwright_fallback)
                if page_record:
                    crawled_pages[role] = page_record

    pages_crawled = list(crawled_pages.keys())
    logger.info(
        f"[SourceCollector] Collected for '{startup_name}': pages={pages_crawled}, "
        f"playwright={playwright_used}"
    )

    return {
        "crawled_pages": crawled_pages,
        "search_snippets": search_snippets or {},
        "crawl_metadata": {
            "pages_crawled": pages_crawled,
            "playwright_used": playwright_used,
            "crawl_timestamp": datetime.now(timezone.utc).isoformat(),
            "website_url": website_url or "",
        },
    }


# ---------------------------------------------------------------------------
# Context formatting helpers for enrichers
# ---------------------------------------------------------------------------

def format_crawled_pages_for_enricher(
    crawled_pages: dict,
    enricher_key: str,
    pipeline_config: Optional[dict] = None,
    max_chars: int = 6000,
) -> str:
    """
    Formats crawled page content into a single prompt-ready text block
    for a specific enricher. Selects only the pages relevant to that enricher
    based on pipeline_config.v2_pipeline.enricher_crawled_page_map.

    Parameters
    ----------
    crawled_pages   : dict of page_role -> page_record (from collect_source_payload)
    enricher_key    : one of: corporate | identity | products | competitors | funding
    pipeline_config : optional dict from pipeline_config.json (for page map lookup)
    max_chars       : maximum total characters in output
    """
    # Load page-to-enricher mapping from config or use defaults
    if pipeline_config is None:
        try:
            import json as _json
            _pcp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pipeline_config.json")
            if os.path.exists(_pcp):
                with open(_pcp, "r", encoding="utf-8") as f:
                    pipeline_config = _json.load(f)
        except Exception:
            pipeline_config = {}

    page_map = (
        pipeline_config
        .get("v2_pipeline", {})
        .get("enricher_crawled_page_map", {})
    )
    default_page_map = {
        "corporate": ["homepage", "about", "contact", "privacy", "terms"],
        "identity": ["team", "about", "founders", "leadership", "homepage"],
        "products": ["products", "solutions", "platform", "services", "homepage"],
        "competitors": ["homepage", "about"],
        "funding": ["homepage", "about"],
    }
    relevant_role_prefixes = page_map.get(enricher_key, default_page_map.get(enricher_key, list(crawled_pages.keys())))

    parts = []
    for page_role, page_record in crawled_pages.items():
        if not isinstance(page_record, dict):
            continue
        # Match if any relevant prefix is in the page_role
        if not any(prefix in page_role for prefix in relevant_role_prefixes):
            continue

        page_title = page_record.get("page_title", page_role.upper())
        url = page_record.get("url", "")
        text = page_record.get("text_content", "")
        footer = page_record.get("footer_text", "")
        socials = page_record.get("social_links", {})

        section = f"=== {page_title} ({page_role}) ===\nURL: {url}\n{text}"
        if footer:
            section += f"\n[FOOTER]: {footer}"
        if socials:
            section += f"\n[SOCIAL LINKS]: {json.dumps(socials)}"
        parts.append(section)

    combined = "\n\n".join(parts)
    return combined[:max_chars]


def format_search_snippets_for_enricher(
    search_snippets: dict,
    enricher_key: str,
    pipeline_config: Optional[dict] = None,
    max_chars: int = 2000,
) -> str:
    """
    Formats field-bucketed search snippets into a prompt-ready text block
    for a specific enricher.

    Parameters
    ----------
    search_snippets : field-bucketed dict from raw_source_payload.search_snippets
    enricher_key    : one of: corporate | identity | products | competitors | funding
    pipeline_config : optional dict from pipeline_config.json (for field map lookup)
    max_chars       : maximum total characters in output
    """
    if pipeline_config is None:
        try:
            import json as _json
            _pcp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pipeline_config.json")
            if os.path.exists(_pcp):
                with open(_pcp, "r", encoding="utf-8") as f:
                    pipeline_config = _json.load(f)
        except Exception:
            pipeline_config = {}

    field_map = (
        pipeline_config
        .get("v2_pipeline", {})
        .get("enricher_snippet_field_map", {})
    )
    default_field_map = {
        "corporate": ["official_website", "official_linkedin", "headquarter", "founded_year"],
        "identity": ["founders_and_leadership"],
        "products": ["products_and_solutions"],
        "competitors": ["competitors"],
        "funding": ["funding_details"],
    }
    relevant_fields = field_map.get(enricher_key, default_field_map.get(enricher_key, []))

    parts = []
    for field_key in relevant_fields:
        records = search_snippets.get(field_key, [])
        if not records:
            continue
        parts.append(f"--- {field_key.upper().replace('_', ' ')} SNIPPETS ---")
        for rec in records[:5]:  # max 5 per field bucket
            title = rec.get("title", "")
            url = rec.get("url", "")
            snippet = rec.get("snippet", "")
            phase = rec.get("phase", "")
            parts.append(f"[{phase.upper()}] {title}\nURL: {url}\n{snippet}")

    combined = "\n\n".join(parts)
    return combined[:max_chars]


def format_source_payload_for_prompt(payload: dict, max_chars: int = 4000) -> str:
    """
    Backward-compatible formatter. Works with both v1 (flat fields) and
    v2 (crawled_pages dict) raw_source_payload formats.
    """
    # v2 format
    if "crawled_pages" in payload:
        return format_crawled_pages_for_enricher(
            payload["crawled_pages"], enricher_key="corporate", max_chars=max_chars
        )

    # v1 format fallback
    sections = []
    if payload.get("seo_metadata"):
        meta = payload["seo_metadata"]
        sections.append(
            f"=== SEO METADATA ===\nTitle: {meta.get('title', '')}\n"
            f"Description: {meta.get('meta_description', '') or meta.get('og_description', '')}"
        )
    for key, label in [
        ("homepage_text", "HOMEPAGE"),
        ("about_page_text", "ABOUT PAGE"),
        ("products_page_text", "PRODUCTS PAGE"),
        ("team_page_text", "TEAM PAGE"),
        ("linkedin_snippets", "LINKEDIN SNIPPETS"),
    ]:
        val = payload.get(key, "")
        if val:
            sections.append(f"=== {label} ===\n{val[:800]}")
    return "\n\n".join(sections)[:max_chars]
