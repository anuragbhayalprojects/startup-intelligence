import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

def scrape_inc42(num_startups: int = 10):
    """
    Scrapes startup information from Inc42.

    Args:
        num_startups (int): The number of startups to scrape.

    Returns:
        list: A list of dictionaries, where each dictionary represents a startup.
    """
    startups = []
    url = "https://inc42.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Inc42 data: {e}")
        return startups

    soup = BeautifulSoup(response.text, "html.parser")
    
    seen_urls = set()
    
    # Inc42 homepage lists news articles inside h2 tags with class "entry-title"
    for h2 in soup.find_all("h2"):
        classes = h2.get("class", [])
        if "entry-title" not in classes:
            continue
            
        link_element = h2.find("a") or h2.find_parent("a")
        if not link_element:
            continue
            
        article_url = link_element.get("href")
        if not article_url:
            continue
            
        # Avoid duplicate articles
        if article_url in seen_urls:
            continue
            
        title = h2.get_text(strip=True)
        
        # Skip tags or section headers that are too short
        if len(title) <= 12:
            continue
            
        seen_urls.add(article_url)
        
        # Fetch detailed description/excerpt by querying the article page
        description = "N/A"
        try:
            art_response = requests.get(article_url, headers=headers, timeout=5)
            if art_response.status_code == 200:
                art_soup = BeautifulSoup(art_response.text, "html.parser")
                paragraphs = []
                for p in art_soup.find_all("p"):
                    if p.get("class"):
                        continue
                    text = p.get_text(strip=True)
                    # Filter short paragraphs and standard navigation/promo footers
                    if len(text) < 65:
                        continue
                    if any(phrase in text for phrase in ["Unlock", "newsletter", "Tired Of", "Terms of Use", "Privacy Policy"]):
                        continue
                    paragraphs.append(text)
                
                if paragraphs:
                    # Combine first two significant paragraphs to form a detailed description
                    description = " ".join(paragraphs[:2])
        except Exception as e:
            logging.warning(f"Failed to fetch description for {article_url}: {e}")
            
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

    return startups

if __name__ == "__main__":
    data = scrape_inc42(5)
    for startup in data:
        print(startup)
