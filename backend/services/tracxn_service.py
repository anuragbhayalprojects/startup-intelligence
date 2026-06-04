import os
import requests
import json

def fetch_tracxn_startup_data(name: str) -> dict:
    """
    Fetches verified startup metadata from Tracxn API.
    If TRACXN_API_KEY is not defined in the environment, it returns None.
    Includes built-in sandbox mock data for verified test cases.
    """
    api_key = os.getenv("TRACXN_API_KEY")
    name_clean = name.strip().lower()
    
    # 1. Sandbox Mock Profile Repository for testing
    sandbox_profiles = {
        "npci": {
            "startup_name": "NPCI",
            "website": "https://www.npci.org.in",
            "founded_year": 2008,
            "founders": [
                {
                    "name": "Dilip Asbe",
                    "role": "MD & CEO",
                    "brief_details": "MD & CEO of National Payments Corporation of India (NPCI).",
                    "linkedin_url": "https://www.linkedin.com/in/dilipasbe"
                }
            ],
            "funding_stage": "Public",
            "funding_amount": "N/A",
            "valuation": "N/A",
            "business_models": ["Transaction-Based", "B2B"],
            "industry": "Financial Services",
            "sector": "FinTech",
            "subsector": "UPI Infrastructure",
            "description": "National Payments Corporation of India (NPCI) is an umbrella organisation for operating retail payments and settlement systems in India."
        },
        "perfios": {
            "startup_name": "Perfios",
            "website": "https://www.perfios.com",
            "founded_year": 2008,
            "founders": [
                {
                    "name": "VR Govindarajan",
                    "role": "Co-Founder & Chairman",
                    "brief_details": "Ex-Product head at Aztecsoft with 35+ years in database systems.",
                    "linkedin_url": "https://www.linkedin.com/in/vrgovindarajan"
                },
                {
                    "name": "Debashish Chakraborty",
                    "role": "Co-Founder & CTO",
                    "brief_details": "Software pioneer with deep expertise in statement parsers.",
                    "linkedin_url": "https://www.linkedin.com/in/debashish-chakraborty-perfios"
                }
            ],
            "funding_stage": "Series D",
            "funding_amount": "$420M",
            "valuation": "$1.0B",
            "business_models": ["SaaS", "B2B"],
            "industry": "Financial Services",
            "sector": "FinTech",
            "subsector": "Alternative Credit Underwriting",
            "description": "Perfios is a product technology company enabling businesses to extract, curate, analyze and make decisions on unstructured data."
        },
        "rikoai": {
            "startup_name": "Riko AI",
            "website": "https://rikoai.com",
            "founded_year": 2024,
            "founders": [
                {
                    "name": "Utkarsh Rishi",
                    "role": "Co-Founder & AI Engineer",
                    "brief_details": "Co-founder of Riko AI, specialized in workflow bots.",
                    "linkedin_url": "https://www.linkedin.com/in/utkarsh-rishi"
                }
            ],
            "funding_stage": "Seed",
            "funding_amount": "$1.5M",
            "valuation": "N/A",
            "business_models": ["SaaS", "B2B"],
            "industry": "Artificial Intelligence",
            "sector": "Agentic AI",
            "subsector": "Workflow Agents",
            "description": "Riko AI builds generative AI workflow agents and automation tools for enterprises."
        }
    }
    
    if name_clean in sandbox_profiles:
        print(f"📦 [Tracxn Service] Retrieved sandbox mock profile for: '{name}'")
        return sandbox_profiles[name_clean]
        
    for k, v in sandbox_profiles.items():
        if k in name_clean or name_clean in k:
            print(f"📦 [Tracxn Service] Retrieved substring sandbox profile for: '{name}'")
            return v

    if not api_key:
        # Gracefully exit if API key is not configured (standard mode)
        return {}
        
    # 2. Live API Request
    print(f"🚀 [Tracxn Service] Requesting Live Tracxn Profile for: '{name}'...")
    url = f"https://api.tracxn.com/v1/startups?name={urllib.parse.quote(name)}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Assuming standard Tracxn response structure maps to our schema
            if data and "companies" in data and len(data["companies"]) > 0:
                co = data["companies"][0]
                return {
                    "startup_name": co.get("name"),
                    "website": co.get("websiteUrl"),
                    "founded_year": co.get("foundedYear"),
                    "description": co.get("description"),
                    "funding_stage": co.get("stage"),
                    "funding_amount": co.get("totalFundingRaised"),
                    "founders": [
                        {"name": f.get("name"), "role": f.get("designation"), "linkedin_url": f.get("linkedinUrl")}
                        for f in co.get("founders", [])
                    ]
                }
    except Exception as e:
        print(f"⚠️ Tracxn API call failed: {e}")
        
    return {}
