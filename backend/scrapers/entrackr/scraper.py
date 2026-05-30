
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
    url = "https://entrackr.com/category/startup/"
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
    articles = soup.find_all("div", class_="news-post", limit=num_startups)

    for article in articles:
        title_element = article.find("h3", class_="post-title")
        link_element = title_element.find("a") if title_element else None
        excerpt_element = article.find("div", class_="post-excerpt")

        if title_element and link_element:
            title = title_element.get_text(strip=True)
            article_url = link_element['href']
            description = excerpt_element.get_text(strip=True) if excerpt_element else "N/A"
            
            # Placeholder for further details to be extracted from the article page
            startups.append({
                "startup_name": title,
                "source_url": article_url,
                "description": description,
                "source": "Entrackr",
                "city": "India", 
                "country": "India"
            })

    return startups

if __name__ == "__main__":
    data = scrape_entrackr(5)
    for startup in data:
        print(startup)
