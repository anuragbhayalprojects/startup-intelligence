
from .entrackr.scraper import scrape_entrackr
from .inc42.scraper import scrape_inc42
# Import other scrapers as they are created

def run_scraper(source: str, num_startups: int = 10):
    """
    Runs the specified scraper and returns the scraped data.

    Args:
        source (str): The name of the source to scrape (e.g., 'entrackr', 'inc42').
        num_startups (int): The number of startups to scrape.

    Returns:
        list: A list of dictionaries, where each dictionary represents a startup.
    """
    if source.lower() == 'entrackr':
        return scrape_entrackr(num_startups)
    elif source.lower() == 'inc42':
        return scrape_inc42(num_startups)
    # Add other sources here
    else:
        raise ValueError(f"Scraper for source '{source}' not found.")

if __name__ == '__main__':
    # Example usage
    try:
        entrackr_data = run_scraper('entrackr', 5)
        print("Scraped from Entrackr:")
        print(entrackr_data)

        inc42_data = run_scraper('inc42', 3)
        print("\nScraped from Inc42:")
        print(inc42_data)

    except ValueError as e:
        print(e)
