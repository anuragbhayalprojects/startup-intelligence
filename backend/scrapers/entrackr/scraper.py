import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

def scrape_entrackr(num_startups: int = 10):
    """
    Scrapes startup information from Entrackr.

    Args:
        num_startups (int): The number of startups to scrape.

    Returns:
        list: A list of dictionaries, where each dictionary represents a startup.
    """
    startups = []
    url = "https://entrackr.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Entrackr data: {e}")
        return startups

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Entrackr homepage has news titles inside <h2> tags which are child of an <a> tag with class "clickable".
    seen_urls = set()
    
    for h2 in soup.find_all("h2"):
        parent = h2.parent
        classes = parent.get("class", []) if parent else []
        
        # Filter only clickable news articles and skip categories/nav links
        if "clickable" not in classes:
            continue
            
        href = parent.get("href")
        if not href:
            continue
            
        # Construct absolute URL
        if href.startswith("/"):
            article_url = "https://entrackr.com" + href
        else:
            article_url = href
            
        # Avoid duplicate entries
        if article_url in seen_urls:
            continue
            
        title = h2.get_text(strip=True)
        
        # Skip titles that are too short or not meaningful
        if len(title) <= 10:
            continue
            
        seen_urls.add(article_url)
        
        # Fetch individual article page to extract detailed description/excerpts
        description = "N/A"
        try:
            art_response = requests.get(article_url, headers=headers, timeout=5)
            if art_response.status_code == 200:
                art_soup = BeautifulSoup(art_response.text, "html.parser")
                paragraphs = []
                for p in art_soup.find_all("p"):
                    text = p.get_text(strip=True)
                    # Filter out short helper texts and standard boilerplates
                    if len(text) < 45:
                        continue
                    if any(phrase in text for phrase in ["Terms of Use", "Privacy Policy", "consent to the processing", "By clicking the button"]):
                        continue
                    paragraphs.append(text)
                
                if paragraphs:
                    # Combine first two significant paragraphs to form a rich description
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

    return startups

if __name__ == "__main__":
    data = scrape_entrackr(5)
    for startup in data:
        print(startup)
