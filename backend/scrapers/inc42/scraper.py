import requests
from bs4 import BeautifulSoup


def scrape_inc42():
    startups = []

    url = "https://inc42.com"

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
                "source": "Inc42",
                "city": "India",
                "country": "India"
            })

    return startups


if __name__ == "__main__":
    data = scrape_inc42()

    for startup in data:
        print(startup)