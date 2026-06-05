try:
    from curl_cffi import requests
except ImportError:
    import requests
import feedparser
from bs4 import BeautifulSoup
import logging
import time
import random

logging.basicConfig(level=logging.INFO)

def scrape_entrackr(num_startups: int = 10):
    """
    Scrapes startup information from Entrackr.
    Attempts RSS feed parsing first, and falls back to HTML scraping if that fails.

    Args:
        num_startups (int): The number of startups to scrape.

    Returns:
        list: A list of dictionaries, where each dictionary represents a startup.
    """
    startups = []
    rss_url = "https://entrackr.com/rss"
    homepage_url = "https://entrackr.com"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    # 1. Attempt RSS Feed parsing
    print(f"📡 [Entrackr Scraper] Attempting RSS Feed: {rss_url}...")
    rss_success = False
    try:
        kwargs = {"headers": headers, "timeout": 15}
        try:
            response = requests.get(rss_url, impersonate="chrome120", **kwargs)
        except TypeError:
            response = requests.get(rss_url, **kwargs)
            
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            if feed.entries:
                rss_success = True
                print(f"✅ [Entrackr Scraper] Successfully parsed {len(feed.entries)} entries from RSS feed.")
                
                for entry in feed.entries:
                    title = entry.get("title", "")
                    article_url = entry.get("link", "")
                    
                    if not title or not article_url or len(title) <= 10:
                        continue
                        
                    # Fetch description
                    description = "N/A"
                    # Try to fetch article page for first 2 paragraphs
                    delay = random.uniform(1.0, 3.0)
                    print(f"⏳ [Entrackr Scraper] Jitter delay: {delay:.2f} seconds before article fetch...")
                    time.sleep(delay)
                    
                    try:
                        art_kwargs = {"headers": headers, "timeout": 5}
                        try:
                            art_response = requests.get(article_url, impersonate="chrome120", **art_kwargs)
                        except TypeError:
                            art_response = requests.get(article_url, **art_kwargs)
                            
                        if art_response.status_code == 200:
                            art_soup = BeautifulSoup(art_response.text, "html.parser")
                            paragraphs = []
                            for p in art_soup.find_all("p"):
                                text = p.get_text(strip=True)
                                if len(text) < 45:
                                    continue
                                if any(phrase in text for phrase in ["Terms of Use", "Privacy Policy", "consent to the processing", "By clicking the button"]):
                                    continue
                                paragraphs.append(text)
                            if paragraphs:
                                description = " ".join(paragraphs[:2])
                    except Exception as e:
                        logging.warning(f"Failed to fetch details for {article_url}, falling back to RSS summary: {e}")
                        # Fallback to RSS summary/description
                        description = entry.get("summary") or entry.get("description") or "N/A"
                        # Strip HTML if summary has it
                        if description != "N/A":
                            description = BeautifulSoup(description, "html.parser").get_text(strip=True)
                            
                    startups.append({
                        "startup_name": title,
                        "source_url": article_url,
                        "description": description,
                        "source": "Entrackr",
                        "city": "India",
                        "country": "India",
                        "hq_city": "India",
                        "hq_country": "India"
                    })
                    
                    if len(startups) >= num_startups:
                        break
    except Exception as e:
        logging.error(f"RSS parser failed for Entrackr: {e}")

    # 2. Fallback: HTML scraping if RSS failed or returned nothing
    if not rss_success or not startups:
        print("🔄 [Entrackr Scraper] Falling back to HTML Scraping...")
        try:
            kwargs = {"headers": headers, "timeout": 15}
            try:
                response = requests.get(homepage_url, impersonate="chrome120", **kwargs)
            except TypeError:
                response = requests.get(homepage_url, **kwargs)
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            seen_urls = set()
            
            for h2 in soup.find_all("h2"):
                parent = h2.parent
                classes = parent.get("class", []) if parent else []
                if "clickable" not in classes:
                    continue
                href = parent.get("href")
                if not href:
                    continue
                article_url = homepage_url + href if href.startswith("/") else href
                
                if article_url in seen_urls:
                    continue
                title = h2.get_text(strip=True)
                if len(title) <= 10:
                    continue
                seen_urls.add(article_url)
                
                description = "N/A"
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)
                
                try:
                    art_kwargs = {"headers": headers, "timeout": 5}
                    try:
                        art_response = requests.get(article_url, impersonate="chrome120", **art_kwargs)
                    except TypeError:
                        art_response = requests.get(article_url, **art_kwargs)
                        
                    if art_response.status_code == 200:
                        art_soup = BeautifulSoup(art_response.text, "html.parser")
                        paragraphs = []
                        for p in art_soup.find_all("p"):
                            text = p.get_text(strip=True)
                            if len(text) < 45:
                                continue
                            if any(phrase in text for phrase in ["Terms of Use", "Privacy Policy", "consent to the processing", "By clicking the button"]):
                                continue
                            paragraphs.append(text)
                        if paragraphs:
                            description = " ".join(paragraphs[:2])
                except Exception as e:
                    logging.warning(f"Failed to fetch description for {article_url}: {e}")
                    
                startups.append({
                    "startup_name": title,
                    "source_url": article_url,
                    "description": description,
                    "source": "Entrackr",
                    "city": "India",
                    "country": "India",
                    "hq_city": "India",
                    "hq_country": "India"
                })
                
                if len(startups) >= num_startups:
                    break
        except Exception as e:
            logging.error(f"HTML fallback scraper failed for Entrackr: {e}")

    return startups

if __name__ == "__main__":
    data = scrape_entrackr(2)
    for startup in data:
        print(startup)
