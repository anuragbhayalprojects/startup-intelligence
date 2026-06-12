"""
linkedin_resolver.py
--------------------
LinkedIn URL resolution for startups and founders.

Resolution waterfall:
  1. Identity registry (startup_identity table)
  2. CANONICAL_OVERLOADS (taxonomy_mapper)
  3. Known LinkedIn company slugs map
  4. Search-based discovery (Google → DuckDuckGo)

Note: LinkedIn actively blocks scraping. Resolution relies primarily on
the registry and search snippets — not direct crawling.
"""

import os
import json
import re
from typing import Optional

# --------------------------------------------------------------------------- #
# Known LinkedIn company page slugs loader
# --------------------------------------------------------------------------- #

_KNOWN_LINKEDIN_CACHE = None

def load_known_linkedin() -> dict[str, str]:
    global _KNOWN_LINKEDIN_CACHE
    if _KNOWN_LINKEDIN_CACHE is not None:
        return _KNOWN_LINKEDIN_CACHE
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "known_linkedin.json")
    try:
        with open(config_path, "r") as f:
            _KNOWN_LINKEDIN_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [LinkedInResolver] Failed to load known_linkedin.json: {e}")
        _KNOWN_LINKEDIN_CACHE = {}
    return _KNOWN_LINKEDIN_CACHE


KNOWN_LINKEDIN = load_known_linkedin()


_LINKEDIN_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9\-_\./]+"
)


def resolve_linkedin_company_url(
    brand_name: str,
    startup_id: Optional[int] = None,
    skip_registry: bool = False,
) -> Optional[str]:
    """
    Resolves the canonical LinkedIn company page URL.

    Parameters
    ----------
    brand_name   : Clean brand name
    startup_id   : Optional startup DB id for registry lookup
    skip_registry: If True, skip identity registry lookup

    Returns
    -------
    str | None : LinkedIn company URL or None
    """
    clean_lower = brand_name.strip().lower()

    # Step 1 — Identity registry
    if startup_id and not skip_registry:
        try:
            from backend.services.supabase_service import supabase
            res = supabase.table("startups").select("linkedin_company_url, linkedin_url").eq("id", startup_id).execute()
            if res.data:
                row = res.data[0]
                url = row.get("linkedin_company_url") or row.get("linkedin_url")
                if url:
                    return url
        except Exception as e:
            print(f"⚠️ [LinkedInResolver] Registry lookup failed: {e}")

    # Step 2 — CANONICAL_OVERLOADS
    try:
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
        for key, val in CANONICAL_OVERLOADS.items():
            if key in clean_lower or clean_lower in key:
                if "linkedin_url" in val:
                    return val["linkedin_url"]
    except Exception:
        pass

    # Step 3 — Known map
    for key, url in KNOWN_LINKEDIN.items():
        if key == clean_lower or key in clean_lower:
            return url

    # Step 4 — Search-based extraction
    try:
        from backend.utils.search import search_duckduckgo, load_search_queries
        config = load_search_queries()
        query_template = config.get("linkedin_resolver", {}).get("query", "{brand_name} LinkedIn company page")
        query = query_template.format(brand_name=brand_name)
        snippets = search_duckduckgo(query)
        for m in _LINKEDIN_URL_PATTERN.finditer(snippets):
            url = m.group(0).rstrip(".,;)")
            if "/company/" in url:
                return url
    except Exception as e:
        print(f"⚠️ [LinkedInResolver] Search-based extraction failed: {e}")

    return None
