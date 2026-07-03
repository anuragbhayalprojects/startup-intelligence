from backend.workflows.startup_pipeline import process_startup


def test_process_startup_run():
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


def test_clean_string_suffixes():
    from backend.workflows.startup_pipeline import clean_string, get_clean_startup_name
    assert clean_string("PayU India") == "PayU"
    assert clean_string("PhonePe India") == "PhonePe"
    assert clean_string("Turtlemint Technologies") == "Turtlemint"
    assert get_clean_startup_name("PayU India Turns Profitable", "PayU India") == "PayU"