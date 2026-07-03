"""
website_resolver.py
-------------------
Canonical website resolution logic for the Startup Intelligence OS.

This module is the single source of truth for resolving startup websites.
The get_clean_website() function from startup_pipeline.py is preserved here
as the authoritative implementation, with startup_pipeline.py re-exporting
it as a backward-compatibility shim.

Priority waterfall:
  1. Identity registry (DB lookup)
  2. CANONICAL_OVERLOADS / known_domains map
  3. AI-extracted website (from analysis_json)
  4. Domain inference (brand_name.com / .in)
  5. Search-based discovery (Google → DuckDuckGo)
"""

import os
import json
import time
import random
import re
from typing import Optional

# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
_PRIORITY_CFG_PATH = os.path.join(_CONFIG_DIR, "search_priority.json")
_PROVIDER_CFG_PATH = os.path.join(_CONFIG_DIR, "search_provider_config.json")


def _load_json(path: str, fallback: dict) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ [WebsiteResolver] Failed to load config {path}: {e}")
    return fallback


_priority_cfg = _load_json(_PRIORITY_CFG_PATH, {})
_provider_cfg = _load_json(_PROVIDER_CFG_PATH, {})

# --------------------------------------------------------------------------- #
# Config loaders for domains and filters
# --------------------------------------------------------------------------- #

_KNOWN_DOMAINS_CACHE = None
def load_known_domains() -> dict:
    global _KNOWN_DOMAINS_CACHE
    if _KNOWN_DOMAINS_CACHE is not None:
        return _KNOWN_DOMAINS_CACHE
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "known_domains.json")
    try:
        with open(config_path, "r") as f:
            _KNOWN_DOMAINS_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [WebsiteResolver] Failed to load known_domains.json: {e}")
        _KNOWN_DOMAINS_CACHE = {}
    return _KNOWN_DOMAINS_CACHE

_RESOLVER_CFG_CACHE = None
def load_resolver_config() -> dict:
    global _RESOLVER_CFG_CACHE
    if _RESOLVER_CFG_CACHE is not None:
        return _RESOLVER_CFG_CACHE
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "website_resolver_config.json")
    try:
        with open(config_path, "r") as f:
            _RESOLVER_CFG_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [WebsiteResolver] Failed to load website_resolver_config.json: {e}")
        _RESOLVER_CFG_CACHE = {}
    return _RESOLVER_CFG_CACHE

# Load caches at startup
KNOWN_DOMAINS = load_known_domains()
_resolver_cfg = load_resolver_config()

_BAD_DOMAINS = frozenset(_resolver_cfg.get("bad_domains", []))
_NEWS_PATH_PATTERNS = frozenset(_resolver_cfg.get("news_path_patterns", []))
_BAD_CHARS = frozenset(_resolver_cfg.get("bad_chars", []))


def _is_likely_official_url(url: str) -> bool:
    """Returns True if the URL looks like an official company homepage."""
    if not url or len(url) > 120:
        return False
    low = url.lower()
    # Check for bad domains
    if any(bd in low for bd in _BAD_DOMAINS):
        return False
    # Check for bad chars that indicate an article link
    if any(c in url for c in _BAD_CHARS):
        return False
    # Check for news-style deep path patterns
    if any(pat in low for pat in _NEWS_PATH_PATTERNS):
        return False
    # Check for deep paths (more than 1 path segment is suspicious)
    path_parts = [p for p in url.replace("https://", "").replace("http://", "").split("/") if p]
    if len(path_parts) > 1:
        # Allow /en, /in, /us, /home, /index.html, common landing suffixes
        allowed_suffixes = {"en", "in", "us", "home", "index.html", "index.htm", ""}
        if path_parts[-1].lower() not in allowed_suffixes:
            return False
        # Reject if any path segment looks like a year (2020, 2021, 2022...)
        if any(p.isdigit() and len(p) == 4 for p in path_parts):
            return False
    return True


def _infer_domain(brand_name: str) -> Optional[str]:
    """Guesses the official domain from a brand name (best-effort)."""
    # 1. If brand_name already contains a valid TLD suffix, test it directly first
    brand_clean = re.sub(r"\s+", "", brand_name.lower().strip())
    if re.search(r"\.[a-z]{2,6}(?:\.[a-z]{2,6})?$", brand_clean):
        for candidate in [f"https://www.{brand_clean}", f"https://{brand_clean}"]:
            if _verify_website(candidate):
                return candidate

    clean = re.sub(r"[^a-zA-Z0-9]", "", brand_name.lower().strip())
    if not clean:
        return None
    candidates = [
        f"https://www.{clean}.com",
        f"https://www.{clean}.in",
        f"https://www.{clean}.co",
        f"https://{clean}.com",
        f"https://{clean}.in",
        f"https://{clean}.io",
    ]
    for url in candidates:
        if _verify_website(url):
            return url
    return None


def _verify_website(url: str, timeout: int = 6) -> bool:
    """Lightweight HTTP HEAD check to confirm a URL is live."""
    try:
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.head(url, timeout=timeout, allow_redirects=True, impersonate="chrome120")
        except (ImportError, TypeError):
            import requests
            resp = requests.head(url, timeout=timeout, allow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0 (compatible; StartupBot/1.0)"})
        return resp.status_code < 400
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def resolve_website(
    brand_name: str,
    extracted_website: Optional[str] = None,
    startup_id: Optional[int] = None,
    skip_registry: bool = False,
) -> Optional[str]:
    """
    Resolves the canonical official website URL for a startup.

    Resolution waterfall:
      1. startup_identity table (if startup_id provided & skip_registry=False)
      2. KNOWN_DOMAINS map / CANONICAL_OVERLOADS
      3. extracted_website (AI-extracted, after sanitization check)
      4. Domain inference from brand name
      5. Search-based discovery (Google → DuckDuckGo) — only if all above fail

    Parameters
    ----------
    brand_name      : Clean short brand name (e.g. "Perfios", not "Perfios raises $30M")
    extracted_website : AI-extracted URL string from analysis_json, if available
    startup_id      : DB id from startups table for registry lookup
    skip_registry   : If True, bypasses identity registry lookup (useful for seeding)

    Returns
    -------
    str | None : The canonical website URL, or None if not resolved
    """
    clean_name_lower = brand_name.strip().lower()

    # Step 1 — Identity registry lookup
    if startup_id and not skip_registry:
        try:
            from backend.services.supabase_service import supabase
            res = supabase.table("startups").select("website").eq("id", startup_id).execute()
            if res.data and res.data[0].get("website"):
                url = res.data[0]["website"]
                if _is_likely_official_url(url):
                    return url
        except Exception as e:
            print(f"⚠️ [WebsiteResolver] Identity registry lookup failed: {e}")

    # Step 2 — CANONICAL_OVERLOADS / KNOWN_DOMAINS map
    try:
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
        for key, val in CANONICAL_OVERLOADS.items():
            if key in clean_name_lower or clean_name_lower in key:
                if "website" in val:
                    return val["website"]
    except Exception:
        pass

    for key, url in KNOWN_DOMAINS.items():
        if key in clean_name_lower or clean_name_lower == key:
            return url

    # Step 3 — AI-extracted website (after sanitization)
    if extracted_website and _is_likely_official_url(extracted_website):
        if _verify_website(extracted_website):
            return extracted_website

    # Step 4 — Domain inference from brand name
    inferred = _infer_domain(brand_name)
    if inferred:
        return inferred

    # Step 5 — Search-based discovery
    try:
        from backend.utils.search import search_duckduckgo, load_search_queries
        config = load_search_queries()
        query_template = config.get("website_resolver", {}).get("query", "{brand_name} official website")
        query = query_template.format(brand_name=brand_name)
        snippets = search_duckduckgo(query)
        # Extract first URL from snippets
        url_pattern = re.compile(r"https?://[^\s\"\'>]+\.[a-z]{2,6}(?:/[^\s\"\'<>]*)?")
        for m in url_pattern.finditer(snippets):
            candidate = m.group(0).rstrip(".,;)")
            if _is_likely_official_url(candidate) and _verify_website(candidate):
                return candidate
    except Exception as e:
        print(f"⚠️ [WebsiteResolver] Search-based discovery failed: {e}")

    return None


def get_clean_website(clean_name: str, extracted_website: Optional[str]) -> Optional[str]:
    """
    Backward-compatible wrapper around resolve_website().
    This exact signature is used across startup_pipeline.py, enrichment_agent.py,
    and cleanup_db.py — do NOT change the signature.
    """
    return resolve_website(
        brand_name=clean_name,
        extracted_website=extracted_website,
        startup_id=None,
        skip_registry=False,
    )
