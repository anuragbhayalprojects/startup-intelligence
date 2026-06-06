import sys
import os
import logging
import time
import random
import feedparser
import dateutil.parser
from bs4 import BeautifulSoup

# Align sys.path for standalone script execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from backend.scrapers.common.http_client import get_session, safe_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrapers.inc42")

def parse_published_date(date_str: str) -> str:
    if not date_str:
        return None
    try:
        return dateutil.parser.parse(date_str).isoformat()
    except Exception:
        return None


def scrape_inc42(num_startups: int = 10):
    """
    Scrapes startup information from Inc42.
    Attempts RSS feed parsing first, and falls back to HTML scraping if that fails.

    Args:
        num_startups (int): The number of startups to scrape.

    Returns:
        list: A list of dictionaries, where each dictionary represents a startup.
    """
    startups = []
    rss_url = "https://inc42.com/feed/"
    homepage_url = "https://inc42.com"
    
    # Initialize connection pooling session
    session = get_session()
    
    # 1. Attempt RSS Feed parsing
    logger.info(f"📡 [Inc42 Scraper] Attempting RSS Feed: {rss_url}...")
    rss_success = False
    try:
        response = safe_request(session, rss_url, timeout=15)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            if feed.entries:
                rss_success = True
                logger.info(f"✅ [Inc42 Scraper] Successfully parsed {len(feed.entries)} entries from RSS feed.")
                
                for entry in feed.entries:
                    title = entry.get("title", "")
                    article_url = entry.get("link", "")
                    
                    if not title or not article_url or len(title) <= 12:
                        continue
                        
                    # Fetch description
                    description = "N/A"
                    # Try to fetch article page for first 2 paragraphs
                    delay = random.uniform(1.0, 2.5)
                    logger.info(f"⏳ [Inc42 Scraper] Jitter delay: {delay:.2f} seconds before article fetch...")
                    time.sleep(delay)
                    
                    try:
                        art_response = safe_request(session, article_url, timeout=5)
                        if art_response.status_code == 200:
                            art_soup = BeautifulSoup(art_response.text, "html.parser")
                            paragraphs = []
                            for p in art_soup.find_all("p"):
                                # Skip utility or widget paragraphs
                                if p.get("class") and any(c in p.get("class") for c in ["wp-block-post-excerpt__excerpt", "widget-title"]):
                                    continue
                                text = p.get_text(strip=True)
                                if len(text) < 65:
                                    continue
                                if any(phrase in text for phrase in ["Unlock", "newsletter", "Tired Of", "Terms of Use", "Privacy Policy", "Follow us on"]):
                                    continue
                                paragraphs.append(text)
                            if paragraphs:
                                description = " ".join(paragraphs[:2])
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for {article_url}, falling back to RSS summary: {e}")
                    
                    if description == "N/A":
                        # Fallback to RSS summary/description
                        description = entry.get("summary") or entry.get("description") or "N/A"
                        if description != "N/A":
                            description = BeautifulSoup(description, "html.parser").get_text(strip=True)
                            
                    startups.append({
                        "startup_name": title,
                        "source_url": article_url,
                        "description": description,
                        "source": "Inc42",
                        "published_at": parse_published_date(entry.get("published")),
                        "city": "India",
                        "country": "India",
                        "hq_city": "India",
                        "hq_country": "India"
                    })
                    
                    if len(startups) >= num_startups:
                        break
    except Exception as e:
        logger.error(f"RSS parser failed for Inc42: {e}")

    # 2. Fallback: HTML scraping if RSS failed or returned nothing
    if not rss_success or not startups:
        logger.warning("🔄 [Inc42 Scraper] RSS sweep returned no data. Falling back to HTML Scraping...")
        try:
            response = safe_request(session, homepage_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            seen_urls = set()
            
            # Diagnostic check: collect multiple title/link matching heuristics
            candidates = []
            
            # Heuristic 1: h2/h1/h3 tags containing entry-title or containing anchors
            for h in soup.find_all(["h1", "h2", "h3", "h4"]):
                title_text = h.get_text(strip=True)
                link_el = h.find("a") or h.find_parent("a")
                if link_el and link_el.get("href") and len(title_text) > 12:
                    candidates.append((title_text, link_el.get("href")))
                    
            # Heuristic 2: custom card element links
            for a in soup.find_all("a", href=True):
                url = a["href"]
                title_text = a.get_text(strip=True)
                # Check for standard Inc42 article path indicators
                if "/features/" in url or "/buzz/" in url or "/funding/" in url or "/news/" in url:
                    if len(title_text) > 15:
                        candidates.append((title_text, url))
                        
            # Filter and deduplicate candidates
            for title, url in candidates:
                article_url = url if url.startswith("http") else homepage_url + url
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)
                
                description = "N/A"
                delay = random.uniform(1.0, 2.5)
                logger.info(f"⏳ [Inc42 HTML Fallback] Jitter delay: {delay:.2f} seconds before article fetch...")
                time.sleep(delay)
                
                try:
                    art_response = safe_request(session, article_url, timeout=5)
                    if art_response.status_code == 200:
                        art_soup = BeautifulSoup(art_response.text, "html.parser")
                        paragraphs = []
                        for p in art_soup.find_all("p"):
                            text = p.get_text(strip=True)
                            if len(text) < 65:
                                continue
                            if any(phrase in text for phrase in ["Unlock", "newsletter", "Tired Of", "Terms of Use", "Privacy Policy", "Follow us on"]):
                                continue
                            paragraphs.append(text)
                        if paragraphs:
                            description = " ".join(paragraphs[:2])
                except Exception as e:
                    logger.warning(f"Failed to fetch description for {article_url}: {e}")
                    
                startups.append({
                    "startup_name": title,
                    "source_url": article_url,
                    "description": description,
                    "source": "Inc42",
                    "city": "India",
                    "country": "India",
                    "hq_city": "India",
                    "hq_country": "India"
                })
                
                if len(startups) >= num_startups:
                    break
        except Exception as e:
            logger.error(f"HTML fallback scraper failed for Inc42: {e}")

    # Close the session to release connection pool resources
    session.close()
    return startups

if __name__ == "__main__":
    data = scrape_inc42(2)
    for startup in data:
        print("\n--- Startup Found ---")
        print("Name/Headline:", startup["startup_name"])
        print("URL:", startup["source_url"])
        print("Snippet:", startup["description"][:120], "...")
