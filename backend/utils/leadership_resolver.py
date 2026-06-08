"""
leadership_resolver.py
----------------------
Resolves founder and leadership team profiles for startups.

Priority waterfall (per leadership_priority.json):
  1. Identity registry (startup_identity table)
  2. CANONICAL_OVERLOADS founders override
  3. Website scraping (about/team/leadership pages)
  4. LinkedIn company page scraping (title + name extraction)
  5. Search-based discovery (Google → DuckDuckGo)

Fallback hierarchy for "top leader" when founders are unknown:
  MD > Co-Founder > CEO > Executive Director > President > Business Head > GM
  (configurable in backend/config/leadership_priority.json)
"""

import os
import json
import re
from typing import Optional

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
_LEADERSHIP_CFG_PATH = os.path.join(_CONFIG_DIR, "leadership_priority.json")


def _load_leadership_config() -> dict:
    try:
        if os.path.exists(_LEADERSHIP_CFG_PATH):
            with open(_LEADERSHIP_CFG_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "fallback_hierarchy": [
            {"role": "Founder", "priority": 1},
            {"role": "Co-Founder", "priority": 2},
            {"role": "CEO", "priority": 3},
        ],
        "max_founders_to_return": 5,
        "max_leadership_to_return": 3,
        "minimum_confidence_to_store": 0.40,
        "prefer_founders_over_executives": True,
    }


_LEADERSHIP_CFG = _load_leadership_config()

# --------------------------------------------------------------------------- #
# Known founder overrides (high-confidence, canonical)
# --------------------------------------------------------------------------- #

_KNOWN_FOUNDERS_CACHE = None
def _load_known_founders() -> dict:
    global _KNOWN_FOUNDERS_CACHE
    if _KNOWN_FOUNDERS_CACHE is not None:
        return _KNOWN_FOUNDERS_CACHE
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "founder_overrides.json")
    try:
        with open(config_path, "r") as f:
            _KNOWN_FOUNDERS_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [LeadershipResolver] Failed to load founder_overrides.json: {e}")
        _KNOWN_FOUNDERS_CACHE = {}
    return _KNOWN_FOUNDERS_CACHE

KNOWN_FOUNDERS = _load_known_founders()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _get_max_founders() -> int:
    return _LEADERSHIP_CFG.get("max_founders_to_return", 5)


def _get_max_leadership() -> int:
    return _LEADERSHIP_CFG.get("max_leadership_to_return", 3)


def _role_priority(role: str) -> int:
    """Returns a lower number for higher-priority roles (founders first)."""
    role_lower = role.lower()
    for item in _LEADERSHIP_CFG.get("fallback_hierarchy", []):
        for label in item.get("labels", [item.get("role", "")]):
            if label.lower() in role_lower:
                return item.get("priority", 99)
    return 99


def _sort_by_role_priority(leaders: list[dict]) -> list[dict]:
    return sorted(leaders, key=lambda x: _role_priority(x.get("role", "")))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

_FOUNDER_QUERIES_CACHE = None
def _load_founder_queries() -> dict:
    global _FOUNDER_QUERIES_CACHE
    if _FOUNDER_QUERIES_CACHE is not None:
        return _FOUNDER_QUERIES_CACHE
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "founder_search_queries.json")
    try:
        with open(config_path) as f:
            _FOUNDER_QUERIES_CACHE = json.load(f)
    except Exception:
        _FOUNDER_QUERIES_CACHE = {}
    return _FOUNDER_QUERIES_CACHE

def scrape_linkedin_about(linkedin_url: str) -> list[dict]:
    if not linkedin_url or "linkedin.com/company" not in linkedin_url:
        return []
    
    try:
        from curl_cffi import requests as crequests
        from bs4 import BeautifulSoup
        
        # Ensure we request the about sub-page
        url = linkedin_url.rstrip("/")
        if not url.endswith("/about"):
            url += "/about"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        res = crequests.get(url, headers=headers, impersonate="chrome", timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            text = soup.get_text()
            match = re.search(r'(?:Founded\s+by|Founders)\b[:\s\-]+([A-Z][a-zA-Z\s,]+)', text)
            if match:
                names_str = match.group(1).split("\n")[0].strip()
                names = re.split(r',|\band\b', names_str)
                founders = []
                for name in names:
                    name_clean = name.strip()
                    if name_clean and len(name_clean.split()) >= 2 and len(name_clean.split()) <= 4:
                        founders.append({
                            "name": name_clean,
                            "role": "Founder",
                            "linkedin_url": "",
                            "brief_details": "Extracted from LinkedIn company about page"
                        })
                return founders
    except Exception:
        pass
    return []

def scrape_website_team_page(website: str) -> list[dict]:
    if not website or "example.com" in website:
        return []
        
    import requests
    from bs4 import BeautifulSoup
    
    if not website.startswith("http"):
        website = "https://" + website
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    team_urls = [website]
    try:
        res = requests.get(website, headers=headers, timeout=3, allow_redirects=True)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if any(kw in href for kw in ["about", "team", "leadership", "people", "management"]):
                    full_url = href if href.startswith("http") else website.rstrip("/") + "/" + href.lstrip("/")
                    if full_url not in team_urls:
                        team_urls.append(full_url)
    except Exception:
        pass
        
    role_pattern = re.compile(r'\b(Co-Founder|Founder|CEO|Managing\s+Director|Chief\s+Executive)\b', re.IGNORECASE)
    name_pattern = re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')
    
    founders = []
    seen_names = set()
    
    for url in team_urls[:3]:
        try:
            res = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for element in soup(["script", "style"]):
                    element.decompose()
                    
                for tag in soup.find_all(["h2", "h3", "h4", "h5", "strong", "p", "span", "div"]):
                    text = tag.get_text().strip()
                    if role_pattern.search(text):
                        context = tag.parent.get_text()
                        for name in name_pattern.findall(context):
                            name_clean = name.strip()
                            if name_clean.lower() not in ["founder", "co-founder", "ceo", "cfo", "cto", "about", "contact", "home", "privacy", "policy"]:
                                if name_clean not in seen_names and len(name_clean.split()) >= 2:
                                    seen_names.add(name_clean)
                                    founders.append({
                                        "name": name_clean,
                                        "role": role_pattern.search(text).group(1).title(),
                                        "linkedin_url": "",
                                        "brief_details": f"Extracted from website: {url}"
                                    })
        except Exception:
            continue
            
    return founders

def resolve_founders(
    brand_name: str,
    analysis_json: Optional[dict] = None,
    startup_id: Optional[int] = None,
    skip_registry: bool = False,
) -> list[dict]:
    """
    Resolves the founder/leadership team for a startup using a 5-level waterfall strategy.
    """
    clean_lower = brand_name.strip().lower()
    max_founders = _get_max_founders()

    # Level 1 — Identity registry
    if startup_id and not skip_registry:
        try:
            from backend.services.supabase_service import supabase
            res = supabase.table("startup_identity").select("leadership, primary_founder_name, primary_founder_linkedin, primary_founder_title").eq("startup_id", startup_id).execute()
            if res.data:
                row = res.data[0]
                registry_leadership = row.get("leadership") or []
                if registry_leadership:
                    return _sort_by_role_priority(registry_leadership)[:max_founders]
                if row.get("primary_founder_name"):
                    return [{
                        "name": row["primary_founder_name"],
                        "role": row.get("primary_founder_title") or "Founder",
                        "linkedin_url": row.get("primary_founder_linkedin") or "",
                        "brief_details": "",
                    }]
        except Exception as e:
            print(f"⚠️ [LeadershipResolver] Registry lookup failed: {e}")

    # Level 1.5 — CANONICAL_OVERLOADS / KNOWN_FOUNDERS
    try:
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS, get_canonical_founders
        canonical = get_canonical_founders(brand_name)
        if canonical:
            return _sort_by_role_priority(canonical)[:max_founders]
    except Exception:
        pass

    for key, leaders in KNOWN_FOUNDERS.items():
        if key == clean_lower or key in clean_lower:
            return leaders[:max_founders]

    # AI analysis JSON founders
    if analysis_json and isinstance(analysis_json, dict):
        founders = analysis_json.get("founders", [])
        if founders and isinstance(founders, list):
            return _sort_by_role_priority(founders)[:max_founders]

    # Level 2 — LinkedIn company page about scraping
    try:
        from backend.utils.linkedin_resolver import resolve_linkedin_company_url
        linkedin_url = resolve_linkedin_company_url(brand_name, startup_id, skip_registry)
        if linkedin_url:
            linkedin_founders = scrape_linkedin_about(linkedin_url)
            if linkedin_founders:
                return _sort_by_role_priority(linkedin_founders)[:max_founders]
    except Exception as e:
        print(f"⚠️ [LeadershipResolver] Level 2 LinkedIn about scraping failed: {e}")

    # Level 3 — Website About/Team scraping
    try:
        from backend.utils.website_resolver import resolve_website
        website = resolve_website(brand_name, None, startup_id, skip_registry)
        if website:
            web_founders = scrape_website_team_page(website)
            if web_founders:
                return _sort_by_role_priority(web_founders)[:max_founders]
    except Exception as e:
        print(f"⚠️ [LeadershipResolver] Level 3 Website scraping failed: {e}")

    # Level 4 — Funding articles search (inc42/yourstory)
    try:
        from backend.utils.search import search_duckduckgo
        query = f'"{brand_name}" founder OR CEO site:inc42.com OR site:yourstory.com'
        snippets = search_duckduckgo(query)
        extracted = _extract_founders_from_snippets(brand_name, snippets)
        if extracted:
            return _sort_by_role_priority(extracted)[:max_founders]
    except Exception as e:
        print(f"⚠️ [LeadershipResolver] Level 4 Funding articles search failed: {e}")

    # Level 5 — Search engine results using config founder_search_queries.json
    try:
        from backend.utils.search import search_duckduckgo
        queries_cfg = _load_founder_queries()
        strategies = queries_cfg.get("founder_search", {})
        
        for tier in ["v1", "v2", "v3"]:
            q_list = strategies.get(tier, [])
            for q_tmpl in q_list:
                query = q_tmpl.format(brand_name=brand_name)
                snippets = search_duckduckgo(query)
                extracted = _extract_founders_from_snippets(brand_name, snippets)
                if extracted:
                    return _sort_by_role_priority(extracted)[:max_founders]
    except Exception as e:
        print(f"⚠️ [LeadershipResolver] Level 5 Config search failed: {e}")

    return []

def _extract_founders_from_snippets(brand_name: str, snippets: str) -> list[dict]:
    """
    Best-effort extraction of founder names from search snippets.
    Uses simple NER-style pattern matching.
    """
    if not snippets:
        return []
    founders = []
    patterns = [
        re.compile(r"(?:founder|co-founder|ceo|cto|md|managing director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)", re.IGNORECASE),
        re.compile(r"([A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:founder|co-founder|ceo|cto)", re.IGNORECASE),
    ]
    seen_names = set()
    for pattern in patterns:
        for m in pattern.finditer(snippets):
            name = m.group(1).strip()
            if name and name not in seen_names and len(name.split()) >= 2:
                # Exclude matching the startup name or roles as the name
                if name.lower() not in [brand_name.lower(), "co-founder", "founder", "managing director", "chief executive"]:
                    seen_names.add(name)
                    founders.append({
                        "name": name,
                        "role": "Co-Founder",
                        "linkedin_url": "",
                        "brief_details": "Extracted from search snippets",
                    })
    return founders
