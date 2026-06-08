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
# Known LinkedIn company page slugs
# --------------------------------------------------------------------------- #

KNOWN_LINKEDIN: dict[str, str] = {
    "razorpay": "https://www.linkedin.com/company/razorpay",
    "zerodha": "https://www.linkedin.com/company/zerodha",
    "cred": "https://www.linkedin.com/company/getcred",
    "groww": "https://www.linkedin.com/company/groww-in",
    "meesho": "https://www.linkedin.com/company/meesho",
    "nykaa": "https://www.linkedin.com/company/nykaa",
    "byjus": "https://www.linkedin.com/company/byjus",
    "byju's": "https://www.linkedin.com/company/byjus",
    "unacademy": "https://www.linkedin.com/company/unacademy",
    "swiggy": "https://www.linkedin.com/company/swiggy-in",
    "zomato": "https://www.linkedin.com/company/zomato",
    "paytm": "https://www.linkedin.com/company/paytm",
    "phonepe": "https://www.linkedin.com/company/phonepe-internet",
    "freshworks": "https://www.linkedin.com/company/freshworks",
    "perfios": "https://www.linkedin.com/company/perfios",
    "digit insurance": "https://www.linkedin.com/company/digit-insurance",
    "godigit": "https://www.linkedin.com/company/digit-insurance",
    "artivatic.ai": "https://www.linkedin.com/company/artivatic",
    "artivatic": "https://www.linkedin.com/company/artivatic",
    "juspay": "https://www.linkedin.com/company/juspay",
    "signzy": "https://www.linkedin.com/company/signzy",
    "yubi": "https://www.linkedin.com/company/yubi-formerly-credavenue",
    "m2p fintech": "https://www.linkedin.com/company/m2p-solutions",
    "m2p": "https://www.linkedin.com/company/m2p-solutions",
    "setu": "https://www.linkedin.com/company/setu-api",
    "decentro": "https://www.linkedin.com/company/decentro-tech",
    "smallcase": "https://www.linkedin.com/company/smallcase",
    "zepto": "https://www.linkedin.com/company/zepto",
    "innovaccer": "https://www.linkedin.com/company/innovaccer",
}


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
            res = supabase.table("startup_identity").select("linkedin_company_url").eq("startup_id", startup_id).execute()
            if res.data and res.data[0].get("linkedin_company_url"):
                return res.data[0]["linkedin_company_url"]
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
        from backend.utils.search import search_duckduckgo
        query = f"{brand_name} LinkedIn company page"
        snippets = search_duckduckgo(query)
        for m in _LINKEDIN_URL_PATTERN.finditer(snippets):
            url = m.group(0).rstrip(".,;)")
            if "/company/" in url:
                return url
    except Exception as e:
        print(f"⚠️ [LinkedInResolver] Search-based extraction failed: {e}")

    return None
