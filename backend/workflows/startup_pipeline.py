from backend.ai.startup_analyzer import analyze_startup

from backend.services.supabase_service import (
    upsert_startup
)


def process_startup(startup):

    print("Analyzing startup...")

    analysis = analyze_startup(startup)

    combined = {
        "startup_name": startup.get("startup_name"),
        "website": startup.get("website"),
        "sector": startup.get("sector"),
        "stage": startup.get("stage"),
        "hq_city": startup.get("hq_city"),
        "hq_country": startup.get("hq_country"),
        "founders": startup.get("founders"),
        "description": startup.get("description"),
        "source": startup.get("source"),
        "source_url": startup.get("source_url"),

        # AI structured analysis
        "analysis": analysis
    }

    print("Saving to Supabase...")

    response = upsert_startup(combined)

    print("Done")
    print(response)

    return response