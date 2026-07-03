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
        "headquarters": "",
        "footer_text": "",
        "social_links": {}
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
            # Check for redirect to root to avoid duplicate pages (e.g. if /about redirects to /)
            import urllib.parse
            req_parsed = urllib.parse.urlparse(url)
            resp_url = resp.url if isinstance(resp.url, str) else url
            resp_parsed = urllib.parse.urlparse(resp_url)
            if req_parsed.path.strip("/") and not resp_parsed.path.strip("/"):
                # Redirected to homepage/root! Skip to avoid duplicate context
                return result

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract basic title
            if soup.title:
                result["title"] = soup.title.get_text(strip=True)
                
            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc:
                result["meta_description"] = meta_desc.get("content", "").strip()

            # --- Extract Social Links & Legal Names before tag decomposition ---
            social_links = {}
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href:
                    continue
                href_lower = href.lower()
                
                # Check for LinkedIn company or school page
                if "linkedin.com/company/" in href_lower or "linkedin.com/school/" in href_lower:
                    social_links["linkedin"] = href
                # Also track individual profiles in case they represent founders
                elif "linkedin.com/in/" in href_lower:
                    if "linkedin_profiles" not in social_links:
                        social_links["linkedin_profiles"] = []
                    if href not in social_links["linkedin_profiles"]:
                        social_links["linkedin_profiles"].append(href)
                elif "twitter.com/" in href_lower or "x.com/" in href_lower:
                    social_links["twitter"] = href
                elif "facebook.com/" in href_lower:
                    social_links["facebook"] = href
                elif "instagram.com/" in href_lower:
                    social_links["instagram"] = href
                elif "github.com/" in href_lower:
                    social_links["github"] = href
                elif "crunchbase.com/" in href_lower:
                    social_links["crunchbase"] = href

            result["social_links"] = social_links

            # Regex pattern for legal company suffixes
            legal_pattern = re.compile(
                r"\b([A-Z][a-zA-Z\s,]{2,40}?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Inc\.?|LLC))\b"
            )

            # Look specifically in footer tags or elements matching class/id containing 'footer' or 'copyright'
            footer_elements = soup.find_all(["footer", "div", "p", "span"])
            target_texts = []
            footer_texts = []
            for el in footer_elements:
                is_footer = el.name == "footer"
                classes = el.get("class", [])
                classes_str = " ".join(classes) if isinstance(classes, list) else str(classes)
                el_id = str(el.get("id", ""))
                
                if (
                    is_footer 
                    or "footer" in classes_str.lower() 
                    or "footer" in el_id.lower() 
                    or "copyright" in classes_str.lower() 
                    or "copyright" in el_id.lower()
                ):
                    text = el.get_text(" ", strip=True)
                    if text:
                        cleaned = re.sub(r"\s+", " ", text).strip()
                        target_texts.append(cleaned)
                        if len(cleaned) < 500 and cleaned not in footer_texts:
                            footer_texts.append(cleaned)

            result["footer_text"] = " | ".join(footer_texts)

            legal_company_name = ""
            for text in target_texts:
                match = legal_pattern.search(text)
                if match:
                    legal_company_name = match.group(1).strip()
                    break

            # Check whole body if not found in footer targets
            if not legal_company_name:
                whole_page_text = soup.get_text(" ", strip=True)
                match = legal_pattern.search(whole_page_text)
                if match:
                    legal_company_name = match.group(1).strip()

            result["legal_company_name"] = legal_company_name
                
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
            text_content = extract_clean_text_from_html(resp.text)
            result["text_content"] = text_content[:max_page_cap] # Cap text snippet content size
            
            # If no legal name extracted yet, fallback to the cleaned text
            if not result["legal_company_name"]:
                match = legal_pattern.search(result["text_content"])
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
        "contact": {},
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
        ("contact", "/contact"),
        ("contact", "/contact-us"),
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
    
    collected_texts = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. Fetch homepage to parse links dynamically
    candidate_paths = set()
    try:
        try:
            resp = requests.get(homepage_url, impersonate="chrome120", headers=headers, timeout=4)
        except TypeError:
            resp = requests.get(homepage_url, headers=headers, timeout=4)
            
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extensive list of product-related keywords to capture all scenarios
            product_keywords = [
                "product", "solution", "platform", "service", "offering", "use-case",
                "loan", "card", "wealth", "business", "secure", "feature", "pricing",
                "how-it-works", "pay", "insurance", "credit", "invest", "emi", "personal",
                "instant", "software", "api", "dev", "tech", "merchant", "enterprise",
                "retail", "partner", "buy", "save", "plan", "industry",
                "collections", "collection", "shop", "category", "categories", "store",
                "menu", "catalog", "catalogue", "item", "items"
            ]
            # Boilerplate/administrative keywords to exclude
            exclude_keywords = [
                "blog", "contact", "about", "career", "job", "privacy", "terms", "policy",
                "faq", "press", "news", "event", "cookie", "legal", "support", "help",
                "login", "signin", "signup", "register", "logout", "unsubscribe",
                "sitemap", "disclaimer", "feedback", "media", "resource"
            ]
            
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith("#") or "javascript:" in href.lower() or "mailto:" in href.lower() or "tel:" in href.lower():
                    continue
                # Normalize link to path
                path = href
                if href.startswith("http"):
                    if href.startswith(root_url):
                        path = href[len(root_url):]
                    else:
                        continue
                if not path.startswith("/"):
                    path = "/" + path
                
                # Split path to check structure
                path_parts = [p.lower() for p in path.split("/") if p]
                if not path_parts:
                    continue
                
                # Exclude administrative pages anywhere in the path
                if any(any(ex in part for ex in exclude_keywords) for part in path_parts):
                    continue
                
                # Match if any part matches product keywords or it is a simple 1-level path
                has_product_kw = any(any(kw in part for kw in product_keywords) for part in path_parts)
                is_one_level = len(path_parts) == 1
                
                if has_product_kw or is_one_level:
                    candidate_paths.add(path)
    except Exception as e:
        print(f"[crawler] Failed fetching homepage dynamically: {e}")

    # Fallback to static paths if no candidates were found
    if not candidate_paths:
        candidate_paths = {"/products", "/product", "/platform", "/solutions", "/services", "/offerings", "/use-cases"}

    # 2. Scrape homepage text -> Skip this to avoid duplicating homepage text in the prompt
    # hp_scrape = scrape_page(root_url)
    # if hp_scrape.get("text_content"):
    #     collected_texts.append(f"--- Homepage ---\n{hp_scrape['text_content']}")

    # 3. Walk and crawl dynamically extracted subpages
    crawled_count = 0
    # Sort paths so we crawl in a deterministic, clean order
    for path in sorted(list(candidate_paths)):
        if path == "/":
            continue
        url = root_url + path
        scraped = scrape_page(url, timeout=2.5)
        if scraped.get("text_content") and len(scraped["text_content"]) > 100:
            collected_texts.append(f"--- Solutions/Product Page: {path} ---\n{scraped['text_content']}")
            crawled_count += 1
            if crawled_count >= 3: # Cap subpage crawls to prevent timeouts
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
