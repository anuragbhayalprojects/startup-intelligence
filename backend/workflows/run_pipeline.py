from backend.scrapers.entrackr.scraper import scrape_entrackr
from backend.scrapers.inc42.scraper import scrape_inc42

from backend.workflows.startup_pipeline import process_startup


def run_pipeline():

    all_startups = []

    print("\nFetching Entrackr startups...\n")

    try:

        entrackr_data = scrape_entrackr()

        print(
            f"Fetched {len(entrackr_data)} startups from Entrackr"
        )

        all_startups.extend(entrackr_data)

    except Exception as e:

        print("Entrackr scraper failed")
        print(e)

    print("\nFetching Inc42 startups...\n")

    try:

        inc42_data = scrape_inc42()

        print(
            f"Fetched {len(inc42_data)} startups from Inc42"
        )

        all_startups.extend(inc42_data)

    except Exception as e:

        print("Inc42 scraper failed")
        print(e)

    print(
        f"\nTotal startups fetched: "
        f"{len(all_startups)}\n"
    )

    for startup in all_startups:

        try:

            process_startup(startup)

        except Exception as e:

            print(
                f"Pipeline failed for "
                f"{startup.get('startup_name')}"
            )

            print(e)

    print("\nPipeline completed.\n")


if __name__ == "__main__":

    run_pipeline()