try:
    from curl_cffi import requests
except ImportError:
    import requests
from bs4 import BeautifulSoup
import re

def extract_clean_text_from_html(html_text: str) -> str:
    """
    Parses HTML, removes boilerplates, computes link density per block,
    and filters out low-density blocks or matches against boilerplate patterns.
    """
    import os
    import json
    
    # Load defaults
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "crawler_rules.json")
    link_density_threshold = 0.3
    min_block_length = 20
    boilerplate_patterns = []

    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                link_density_threshold = config.get("link_density_threshold", link_density_threshold)
                min_block_length = config.get("min_block_length", min_block_length)
                boilerplate_patterns = config.get("boilerplate_patterns", boilerplate_patterns)
        except Exception:
            pass

    soup = BeautifulSoup(html_text, "html.parser")
    # Decompose script, style, noscript, iframe, header, footer elements
    for el in soup(["script", "style", "noscript", "iframe", "header", "footer"]):
        el.decompose()

    # Identify blocks (paragraphs, divs, list items, headers, sections, articles)
    blocks = soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"])
    cleaned_blocks = []

    # Compile boilerplate patterns for faster execution
    compiled_patterns = [re.compile(pat, re.IGNORECASE) for pat in boilerplate_patterns]

    for block in blocks:
        # Only process block element if it does not contain nested block elements that we'll process separately.
        if block.name == "div" and block.find(["p", "div", "section", "article"]):
            continue

        text = block.get_text(" ", strip=True)
        if len(text) < min_block_length:
            continue

        # Calculate Link Density
        links = block.find_all("a")
        link_text_len = sum(len(a.get_text(strip=True)) for a in links)
        total_text_len = len(text)
        
        link_density = link_text_len / total_text_len if total_text_len > 0 else 0.0
        if link_density > link_density_threshold:
            continue

        # Check Boilerplate Keywords
        is_boilerplate = False
        for pat in compiled_patterns:
            if pat.search(text):
                is_boilerplate = True
                break
        
        if is_boilerplate:
            continue

        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()
        cleaned_blocks.append(text)

    # Fallback to get_text if block extraction yields nothing
    if not cleaned_blocks:
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        
        lines = []
        for line in text.split(". "):
            is_bp = False
            for pat in compiled_patterns:
                if pat.search(line):
                    is_bp = True
                    break
            if not is_bp and len(line) >= min_block_length:
                lines.append(line)
        return ". ".join(lines)

    # Deduplicate blocks while preserving order
    seen = set()
    unique_blocks = []
    for b in cleaned_blocks:
        if b not in seen:
            seen.add(b)
            unique_blocks.append(b)

    return " ".join(unique_blocks)


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
                
            import os
            import json
            max_page_cap = 3000
            rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "crawler_rules.json")
            if os.path.exists(rules_path):
                try:
                    with open(rules_path, "r", encoding="utf-8") as rf:
                        max_page_cap = json.load(rf).get("max_page_character_cap", max_page_cap)
                except Exception:
                    pass

            # Extract pure text content using the density calculator and boilerplate filter
            text = extract_clean_text_from_html(resp.text)
            result["text_content"] = text[:max_page_cap] # Cap text snippet content size
            
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
                
    import os
    import json
    max_total_cap = 10000
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "crawler_rules.json")
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as rf:
                max_total_cap = json.load(rf).get("max_total_product_crawl_cap", max_total_cap)
        except Exception:
            pass

    return "\n\n".join(collected_texts)[:max_total_cap]
