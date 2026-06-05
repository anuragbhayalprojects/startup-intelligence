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

def load_priority_sources():
    """Loads priority search sources configuration from docs."""
    config_path = "/Users/anurag/Projects/startup-intelligence/docs/search_sources_config.json"
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
    Extracts titles, URLs, and snippet descriptions.
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # Add randomized jitter delay to prevent rate limits
    delay = random.uniform(2.0, 5.0)
    print(f"⏳ [Search Evasion] Delaying Google request by {delay:.2f} seconds...")
    time.sleep(delay)
    
    print(f"🔍 [Google Web Search] Querying Google: '{query}'...")
    try:
        kwargs = {"headers": headers, "timeout": 10}
        try:
            response = requests.get(url, impersonate="chrome120", **kwargs)
        except TypeError:
            response = requests.get(url, **kwargs)
            
        if response.status_code == 429:
            print("⚠️ [Google Web Search] Google rate limited (429).")
            return ""
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Google search results are contained inside class "g" divs
        result_divs = soup.find_all("div", class_="g")
        for idx, div in enumerate(result_divs[:4]):
            title_el = div.find("h3")
            link_el = div.find("a")
            # Google organic snippet class selectors
            snippet_el = div.find("div", class_=lambda c: c and ("VwiC3b" in c or "yD3Yfe" in c or "muw5gc" in c))
            if not snippet_el:
                snippet_el = div.find("div", class_="VwiC3b") or div.find("span", class_="aCO3fc") or div.find("div", class_="kb0PBd")
                
            if title_el and link_el:
                title = title_el.get_text(strip=True)
                href = link_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else "No snippet description available."
                results.append(f"[{idx+1}] Title: {title}\nURL: {href}\nSnippet: {snippet}\n")
                
        # General parser fallback
        if not results:
            for idx, h3 in enumerate(soup.find_all("h3")[:4]):
                parent = h3.find_parent("a")
                if parent:
                    href = parent.get("href", "")
                    title = h3.get_text(strip=True)
                    sibling = parent.find_next("div")
                    snippet = sibling.get_text(strip=True) if sibling else "No details."
                    results.append(f"[{idx+1}] Title: {title}\nURL: {href}\nSnippet: {snippet}\n")
                    
        context = "\n".join(results)
        if context.strip():
            print(f"✅ [Google Web Search] Scraped {len(results)} snippets.")
            return context
        else:
            print("⚠️ [Google Web Search] No search results parsed on Google page.")
            return ""
    except Exception as e:
        print(f"❌ [Google Web Search] Google search failed: {e}")
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
    
    # Add randomized jitter delay to prevent rate limits
    delay = random.uniform(2.0, 5.0)
    print(f"⏳ [Search Evasion] Delaying DDG request by {delay:.2f} seconds...")
    time.sleep(delay)
    
    print(f"🔍 [DDG Web Search] Querying DuckDuckGo: '{query}'...")
    try:
        kwargs = {"headers": headers, "timeout": 10}
        try:
            response = requests.get(url, impersonate="chrome120", **kwargs)
        except TypeError:
            response = requests.get(url, **kwargs)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        result_divs = soup.find_all("div", class_="result")
        for idx, div in enumerate(result_divs[:4]):
            title_link = div.find("a", class_="result__a")
            snippet_link = div.find("a", class_="result__snippet")
            
            if title_link and snippet_link:
                title = title_link.get_text(strip=True)
                snippet = snippet_link.get_text(strip=True)
                href = title_link.get("href", "")
                
                # Extract real URL from DDG redirect if present
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                real_url = qs.get("uddg", [None])[0] or href
                
                results.append(f"[{idx+1}] Title: {title}\nURL: {real_url}\nSnippet: {snippet}\n")
                
        if not results:
            snippets = soup.find_all("a", class_="result__snippet")
            for idx, snip in enumerate(snippets[:4]):
                snippet = snip.get_text(strip=True)
                results.append(f"[{idx+1}] Snippet: {snippet}\n")
                
        context = "\n".join(results)
        if context.strip():
            print(f"✅ [DDG Web Search] Scraped {len(results)} snippets.")
            return context
        else:
            print("⚠️ [DDG Web Search] No search results found on DDG page.")
            return "No web search snippets found."
            
    except Exception as e:
        print(f"❌ [DDG Web Search] DuckDuckGo search failed: {e}")
        return f"Could not perform web search due to error: {str(e)}"

def search_duckduckgo(query: str) -> str:
    """
    Main entry point for web searches. Tries Google Search first,
    falling back to DuckDuckGo search if Google returns no snippets or gets blocked.
    """
    # 1. Attempt Google Search
    google_res = search_google(query)
    if google_res and google_res.strip() and "Title:" in google_res:
        return google_res
        
    # 2. Fallback to DuckDuckGo
    print("🔄 [Web Search] Falling back to DuckDuckGo...")
    return search_ddg_raw(query)

if __name__ == "__main__":
    test_query = "Perfios founders funding revenue investors"
    print(search_duckduckgo(test_query))
