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

def load_priority_sources():
    """Loads priority search sources configuration from config."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "search_sources_config.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
                return data.get("priority_sources", [])
    except Exception as e:
        print(f"⚠️ Failed to load search sources configuration: {e}")
    return []

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
    
    # Fast bypass or jitter delay
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

_SEARCH_CACHE = {}

def search_duckduckgo(query: str) -> str:
    """
    Main entry point. DuckDuckGo is the default primary discovery engine.
    Google searches are secondary, optional and non-blocking.
    Uses in-memory query cache to avoid redundant web scrapes.
    """
    normalized_query = query.strip().lower()
    if normalized_query in _SEARCH_CACHE:
        print(f"⚡ [Search Cache Hit] Reusing results for: '{query}'")
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
    
    news_domains = ["inc42.com", "entrackr.com", "yourstory.com", "techcrunch.com", "livemint.com", "economictimes", "moneycontrol"]
    if any(nd in url_lower for nd in news_domains) or "/news/" in url_lower or "/article/" in url_lower:
        return "news"
        
    funding_keywords = ["crunchbase.com", "tracxn.com", "pitchbook.com", "dealroom"]
    if any(fk in url_lower for fk in funding_keywords):
        return "funding_sources"
        
    social_domains = ["twitter.com", "x.com", "facebook.com", "youtube.com", "instagram.com", "github.com"]
    if any(sd in url_lower for sd in social_domains):
        return "social_profiles"
        
    return "official_website"

def load_search_queries() -> dict:
    """Loads search query templates configuration."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "search_queries.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load search queries configuration: {e}")
    return {}

def discover_search_evidence(startup_name: str) -> dict:
    """
    Runs multi-query discovery for a startup to collect candidate URLs,
    page titles, and snippets.
    """
    config = load_search_queries()
    identity_discovery = config.get("identity_discovery", {})
    templates = identity_discovery.get("queries", [
        "{startup_name} official website",
        "{startup_name} company",
        "{startup_name} linkedin",
        "{startup_name} startup",
        "{startup_name} products"
    ])
    
    queries = [t.format(startup_name=startup_name) for t in templates]

    
    classification_map = {
        "official_website": [],
        "linkedin": [],
        "news": [],
        "funding_sources": [],
        "directories": [],
        "social_profiles": []
    }
    
    visited_urls = set()
    
    for q in queries:
        content = search_duckduckgo(q)
        # Parse titles, URLs and snippets
        matches = re.findall(r"\[\d+\] Title: (.*?)\nURL: (.*?)\nSnippet: (.*?)\n", content, re.DOTALL)
        for title, url, snippet in matches:
            url_clean = url.strip()
            if url_clean in visited_urls:
                continue
            visited_urls.add(url_clean)
            
            cat = classify_url(url_clean)
            record = {
                "title": title.strip(),
                "url": url_clean,
                "snippet": snippet.strip()
            }
            classification_map[cat].append(record)
            
    return classification_map
