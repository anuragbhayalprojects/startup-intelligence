from backend.workflows.startup_pipeline import process_startup


sample = {
    "startup_name": "TestAI",
    "website": "https://testai.com",
    "sector": "AI",
    "stage": "Seed",
    "hq_city": "Bangalore",
    "hq_country": "India",
    "founders": "John Doe",
    "description": "AI startup for workflow automation and analytics",
    "source": "manual",
    "source_url": "https://example.com"
}


process_startup(sample)