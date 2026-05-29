import requests
from bs4 import BeautifulSoup


def scrape_entrackr():
    startups = []

    url = "https://entrackr.com"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    articles = soup.find_all("h2")

    for article in articles[:10]:
        title = article.get_text(strip=True)

        if title:
            startups.append({
                "startup_name": title,
                "industry": "Unknown",
                "source": "Entrackr",
                "city": "India",
                "country": "India"
            })

    return startups


if __name__ == "__main__":
    data = scrape_entrackr()

    for startup in data:
        print(startup)