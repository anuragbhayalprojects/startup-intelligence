"""
backend/pipeline/search_engine.py
------------------------------------
Dynamic search engine for Startup Intelligence OS.

Extracted from backend/workflows/startup_pipeline.py as part of the
pipeline modularization refactor (feature/modular-company-intelligence-refactor).

Provides:
  - verify_website()               — HTTP liveness check for a URL
  - search_website_duckduckgo()    — DuckDuckGo website discovery search
  - get_clean_website()            — Multi-strategy website resolution (primary entry point)
  - build_search_queries()         — Builds targeted DuckDuckGo query set for a startup

Backward compat: startup_pipeline.py re-imports these functions from here.
All callers of startup_pipeline.search_website_duckduckgo / verify_website
can import directly from this module going forward.
"""

from __future__ import annotations

import re
import os
import json
import logging
import urllib.parse
from typing import Optional

import requests

logger = logging.getLogger("startup_intelligence.pipeline.search_engine")

# ---------------------------------------------------------------------------
# Constants — loaded from config with fallbacks
# ---------------------------------------------------------------------------

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

def _load_known_domains() -> dict:
    """Loads known_domains.json if available, else returns inline fallback map."""
    path = os.path.join(_CONFIG_DIR, "known_domains.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.debug(f"[SearchEngine] known_domains.json load failed: {e}")
    # Inline fallback for the most common cases
    return {
        "coinbase": "https://www.coinbase.com",
        "cars24": "https://www.cars24.com",
        "awfis": "https://www.awfis.com",
        "scripbox": "https://www.scripbox.com",
        "physicswallah": "https://www.pw.live",
        "physics wallah": "https://www.pw.live",
        "easemytrip": "https://www.easemytrip.com",
        "tbo tek": "https://www.tbo.com",
        "tbo": "https://www.tbo.com",
        "rapido": "https://www.rapido.autos",
        "innovaccer": "https://www.innovaccer.com",
        "zepto": "https://www.zepto.com",
        "skyroot aerospace": "https://www.skyroot.in",
        "skyroot": "https://www.skyroot.in",
        "ola electric": "https://www.olaelectric.com",
        "rategain": "https://www.rategain.com",
        "plum": "https://www.plumhq.com",
        "plum insurance": "https://www.plumhq.com",
    }

_NEWS_DOMAINS_EXCLUDE = [
    "duckduckgo.com", "wikipedia.org", "linkedin.com", "twitter.com",
    "facebook.com", "youtube.com", "instagram.com", "inc42.com",
    "entrackr.com", "techcrunch.com", "yourstory.com", "vccircle.com",
    "moneycontrol.com", "crunchbase.com", "tracxn.com",
]

_NEWS_PATH_SIGNALS = [
    "/news/", "/article/", "/press/", "/raises-", "-raises-", "-funding",
    "/funding/", "/blog/", "/feed/", "/portfolio/", "/deals/",
    "/funding-round", "/category/",
]

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def verify_website(url: str) -> bool:
    """
    Checks if a URL is active by making a lightweight HTTP HEAD/GET request.
    Returns True if the URL resolves and returns a non-404 status.
    """
    if not url:
        return False
    if "example.com" in url or "localhost" in url:
        return False

    if not url.startswith("http"):
        url = "https://" + url

    try:
        response = requests.head(url, headers=_REQUEST_HEADERS, timeout=3, allow_redirects=True)
        if response.status_code != 404:
            return True
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=3, allow_redirects=True)
        return response.status_code != 404
    except requests.exceptions.RequestException:
        try:
            response = requests.get(url, headers=_REQUEST_HEADERS, timeout=3, allow_redirects=True)
            return response.status_code != 404
        except Exception:
            return False
    except Exception:
        return False


def search_website_duckduckgo(clean_name: str) -> Optional[str]:
    """
    Searches DuckDuckGo HTML for the official website of a startup by name.

    Applies URL quality filters to exclude news article results, deep paths,
    and known media domains. Returns the first valid official-looking URL.
    """
    from bs4 import BeautifulSoup

    query = f"{clean_name} official website"
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    logger.info(f"[SearchEngine] DuckDuckGo search for: '{clean_name}' website")

    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=5)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        result_divs = soup.find_all("div", class_="result")

        for div in result_divs[:5]:
            title_link = div.find("a", class_="result__a")
            if not title_link:
                continue
            href = title_link.get("href", "")
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            real_url = qs.get("uddg", [None])[0] or href

            if not real_url or not real_url.startswith("http"):
                continue

            real_url_lower = real_url.lower()
            path_parts = [
                p for p in real_url.replace("https://", "").replace("http://", "").split("/") if p
            ]
            is_deep = len(path_parts) > 1
            has_news_path = any(k in real_url_lower for k in _NEWS_PATH_SIGNALS)
            has_date_in_path = any(p.isdigit() and len(p) == 4 for p in path_parts)

            if any(domain in real_url_lower for domain in _NEWS_DOMAINS_EXCLUDE):
                continue
            if is_deep and (has_news_path or has_date_in_path or len(real_url) > 50):
                continue
            if verify_website(real_url):
                logger.info(f"[SearchEngine] Found official website via DuckDuckGo: {real_url}")
                return real_url

    except Exception as e:
        logger.warning(f"[SearchEngine] DuckDuckGo search failed for '{clean_name}': {e}")

    return None


def get_clean_website(clean_name: str, extracted_website: str = "") -> str:
    """
    Multi-strategy website resolution for a startup. Canonical entry point.

    Strategy order:
      1. Validate AI-extracted website (if provided)
      2. Known exact domain mappings (config/known_domains.json + inline fallback)
      3. DuckDuckGo search
      4. Inferred domain (word1word2.com / .in)

    Parameters
    ----------
    clean_name         : Cleaned startup brand name
    extracted_website  : Website URL extracted by an AI agent (may be empty or incorrect)

    Returns
    -------
    str: Resolved website URL, or empty string if all strategies fail
    """
    _bad_source_domains = [
        "google.com", "inc42.com", "entrackr.com", "techcrunch.com",
        "yourstory.com", "vccircle.com", "moneycontrol.com", "indiatimes.com",
        "livemint.com", "linkedin.com", "twitter.com", "facebook.com",
        "youtube.com", "wikipedia.org", "medium.com",
    ]
    _bad_chars = ["₹", "$", "%", "&", "?", "'", "'", "`", " ", "'"]

    # Strategy 1: Validate AI-extracted website
    if extracted_website and "error" not in extracted_website and len(extracted_website) <= 100:
        ext_lower = extracted_website.lower()
        if not any(bd in ext_lower for bd in _bad_source_domains):
            if not any(c in extracted_website for c in _bad_chars):
                extracted_website = extracted_website.strip()
                path_parts = [
                    p for p in extracted_website.replace("https://", "").replace("http://", "").split("/") if p
                ]
                is_deep = len(path_parts) > 1
                has_news_path = any(k in ext_lower for k in _NEWS_PATH_SIGNALS)
                has_date = any(p.isdigit() and len(p) == 4 for p in path_parts)
                if not (is_deep and (has_news_path or has_date or len(extracted_website) > 50)):
                    if verify_website(extracted_website):
                        return extracted_website

    # Strategy 2: Known exact domain mapping
    known_domains = _load_known_domains()
    name_key = clean_name.lower().strip()
    if name_key in known_domains:
        return known_domains[name_key]

    # Strategy 3: DuckDuckGo search
    searched_url = search_website_duckduckgo(clean_name)
    if searched_url:
        return searched_url

    # Strategy 4: Inferred domain fallback
    words = clean_name.split()[:2]
    clean_word = "".join(words).lower()
    clean_word = re.sub(r"[^a-z0-9]", "", clean_word)
    if clean_word:
        for tld in (".com", ".in"):
            inferred = f"https://www.{clean_word}{tld}"
            if verify_website(inferred):
                return inferred

    return ""


def build_search_queries(startup_name: str, website: str = "", sector: str = "") -> list[str]:
    """
    Builds a targeted set of DuckDuckGo search queries for a startup.
    Used by source_collector.py to gather web content for enrichment.

    Returns a list of query strings ordered by specificity.
    """
    queries = []
    name = startup_name.strip()

    # Core identity queries
    queries.append(f"{name} startup India about")
    queries.append(f"{name} company products services")
    if website:
        queries.append(f"site:{website} about")

    # Sector-specific query
    if sector and sector.lower() not in ("unknown", ""):
        queries.append(f"{name} {sector} startup")

    # Funding queries
    queries.append(f"{name} funding raised investors")

    # Founder queries
    queries.append(f"{name} founder CEO LinkedIn")

    return queries
