import requests
from bs4 import BeautifulSoup
import urllib.parse

def search_duckduckgo(query: str) -> str:
    """
    Performs a zero-key lightweight web search on DuckDuckGo HTML search 
    and returns titles and snippets to enrich startup analysis.
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    print(f"🔍 [Web Search] Querying DuckDuckGo: '{query}'...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Select result container divs
        result_divs = soup.find_all("div", class_="result")
        for idx, div in enumerate(result_divs[:4]):
            title_link = div.find("a", class_="result__a")
            snippet_link = div.find("a", class_="result__snippet")
            
            if title_link and snippet_link:
                title = title_link.get_text(strip=True)
                snippet = snippet_link.get_text(strip=True)
                results.append(f"[{idx+1}] Title: {title}\nSnippet: {snippet}\n")
                
        # Alternate fallback selectors if classes differ
        if not results:
            snippets = soup.find_all("a", class_="result__snippet")
            for idx, snip in enumerate(snippets[:4]):
                snippet = snip.get_text(strip=True)
                results.append(f"[{idx+1}] Snippet: {snippet}\n")
                
        context = "\n".join(results)
        if context.strip():
            print(f"✅ [Web Search] Found {len(results)} snippets.")
            return context
        else:
            print("⚠️ [Web Search] No search results found on page.")
            return "No web search snippets found."
            
    except Exception as e:
        print(f"❌ [Web Search] DuckDuckGo search failed: {e}")
        return f"Could not perform web search due to error: {str(e)}"
        
if __name__ == "__main__":
    test_query = "Perfios founders funding revenue investors"
    print(search_duckduckgo(test_query))
