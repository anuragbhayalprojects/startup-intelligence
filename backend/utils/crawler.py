try:
    from curl_cffi import requests
except ImportError:
    import requests
from bs4 import BeautifulSoup
import re

def scrape_page(url: str, timeout: float = 3.5) -> dict:
    """Scrapes a URL page content and returns meta metadata and text blocks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    result = {
        "url": url,
        "title": "",
        "meta_description": "",
        "text_content": "",
        "legal_company_name": "",
        "headquarters": ""
    }
    if not url.startswith("http"):
        url = "https://" + url

    try:
        kwargs = {"headers": headers, "timeout": timeout, "allow_redirects": True}
        try:
            resp = requests.get(url, impersonate="chrome120", **kwargs)
        except TypeError:
            resp = requests.get(url, **kwargs)
            
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract basic title
            if soup.title:
                result["title"] = soup.title.get_text(strip=True)
                
            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc:
                result["meta_description"] = meta_desc.get("content", "").strip()
                
            # Decompose scripts and styling elements
            for el in soup(["script", "style", "noscript", "iframe", "header", "footer"]):
                el.decompose()
                
            text = soup.get_text(separator=" ", strip=True)
            # Remove redundant blank lines and spaces
            text = re.sub(r"\s+", " ", text)
            result["text_content"] = text[:3000] # Cap text snippet content size
            
            # Check for legal suffixes Pvt. Ltd / Private Limited / Inc / LLC
            legal_pattern = re.compile(r"\b([A-Z][a-zA-Z\s,]{2,40}?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Inc\.?|LLC))\b")
            match = legal_pattern.search(text)
            if match:
                result["legal_company_name"] = match.group(1).strip()
    except Exception:
        pass
    return result

def crawl_startup_targets(homepage_url: str) -> dict:
    """Visits homepage and matching identity target pages to gather corporate details."""
    crawler_res = {
        "homepage": {},
        "about": {},
        "privacy": {},
        "terms": {}
    }
    
    if not homepage_url:
        return crawler_res
        
    root_url = homepage_url.rstrip("/")
    crawler_res["homepage"] = scrape_page(root_url)
    
    # Optional targeted crawl paths
    targets = [
        ("about", "/about"),
        ("about", "/about-us"),
        ("privacy", "/privacy-policy"),
        ("terms", "/terms-and-conditions"),
        ("terms", "/terms-of-use")
    ]
    
    for key, path in targets:
        # Stop crawling once we find values for specific targets
        if crawler_res[key]:
            continue
        scraped = scrape_page(root_url + path, timeout=2.5)
        if scraped.get("text_content"):
            crawler_res[key] = scraped
            
    return crawler_res

def crawl_product_pages(homepage_url: str) -> str:
    """Crawls specific product target pages to extract features and use-cases text content."""
    if not homepage_url:
        return ""
        
    root_url = homepage_url.rstrip("/")
    product_paths = ["/products", "/product", "/platform", "/solutions", "/services", "/offerings", "/use-cases"]
    
    collected_texts = []
    
    # Fast try on homepage first
    hp_scrape = scrape_page(root_url)
    if hp_scrape.get("text_content"):
        collected_texts.append(f"--- Homepage ---\n{hp_scrape['text_content']}")
        
    # Walk and crawl subpages
    for path in product_paths:
        url = root_url + path
        scraped = scrape_page(url, timeout=2.5)
        if scraped.get("text_content") and len(scraped["text_content"]) > 100:
            collected_texts.append(f"--- Solutions/Product Page: {path} ---\n{scraped['text_content']}")
            if len(collected_texts) >= 3: # Cap subpage crawls to prevent timeouts
                break
                
    return "\n\n".join(collected_texts)
