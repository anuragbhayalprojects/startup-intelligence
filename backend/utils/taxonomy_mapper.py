import os
import json
import difflib

# Load master taxonomy schema
TAXONOMY_PATH = "/Users/anurag/Projects/startup-intelligence/docs/startup_sector_mappings.json"

try:
    with open(TAXONOMY_PATH, "r") as f:
        taxonomy_data = json.load(f)
except Exception as e:
    print(f"⚠️ Failed to load master taxonomy in mapper utility: {e}")
    taxonomy_data = {}

# Canonical Overloads for all database startups to ensure 100% correct mappings, founders, and profiles
CANONICAL_OVERLOADS = {
    "npci": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "UPI Infrastructure",
        "business_models": ["Transaction-Based", "B2B"],
        "industry_relevance": ["BFSI", "Consumer", "Enterprise"],
        "tags": ["upi", "digital-payments", "infrastructure"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Dilip Asbe",
                "role": "MD & CEO",
                "brief_details": "MD & CEO of National Payments Corporation of India (NPCI).",
                "linkedin_url": "https://www.linkedin.com/in/dilipasbe"
            }
        ]
    },
    "coinbase": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "Payments",
        "business_models": ["Transaction-Based", "SaaS"],
        "industry_relevance": ["BFSI", "Consumer"],
        "tags": ["crypto", "exchange", "digital-assets"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Brian Armstrong",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Coinbase, leading cryptocurrency platform.",
                "linkedin_url": "https://www.linkedin.com/in/brianarmstrong"
            },
            {
                "name": "Fred Ehrsam",
                "role": "Co-Founder",
                "brief_details": "Co-founder of Coinbase and Paradigm.",
                "linkedin_url": "https://www.linkedin.com/in/fredehrsam"
            }
        ]
    },
    "easemytrip": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "B2C"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["travel", "booking", "ota", "flights"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Nishant Pitti",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of EaseMyTrip, a major online travel portal.",
                "linkedin_url": "https://www.linkedin.com/in/nishantpitti"
            },
            {
                "name": "Rikant Pittie",
                "role": "Co-Founder",
                "brief_details": "Co-founder of EaseMyTrip, overseeing technology and operations.",
                "linkedin_url": "https://www.linkedin.com/in/rikantpitti"
            },
            {
                "name": "Prashant Pitti",
                "role": "Co-Founder",
                "brief_details": "Co-founder of EaseMyTrip, leading growth and marketing.",
                "linkedin_url": "https://www.linkedin.com/in/prashantpitti"
            }
        ]
    },
    "tbo tek": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["b2b-travel", "booking", "hospitality"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Ankush Nijhawan",
                "role": "Co-Founder",
                "brief_details": "Co-founder of TBO Tek, B2B travel distribution portal.",
                "linkedin_url": "https://www.linkedin.com/in/ankushnijhawan"
            },
            {
                "name": "Gaurav Bhatnagar",
                "role": "Co-Founder",
                "brief_details": "Co-founder of TBO Tek, directing travel software systems.",
                "linkedin_url": "https://www.linkedin.com/in/gauravbhatnagar"
            }
        ]
    },
    "tbo": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["b2b-travel", "booking", "hospitality"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Ankush Nijhawan",
                "role": "Co-Founder",
                "brief_details": "Co-founder of TBO Tek, B2B travel distribution portal.",
                "linkedin_url": "https://www.linkedin.com/in/ankushnijhawan"
            },
            {
                "name": "Gaurav Bhatnagar",
                "role": "Co-Founder",
                "brief_details": "Co-founder of TBO Tek, directing travel software systems.",
                "linkedin_url": "https://www.linkedin.com/in/gauravbhatnagar"
            }
        ]
    },
    "kyro digital": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "RegTech",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise"],
        "tags": ["revenue-operations", "billing", "fintech"],
        "funding_stage": "Seed",
        "founders": [
            {
                "name": "Samir Arora",
                "role": "Co-Founder & CEO",
                "brief_details": "Founder of Kyro Digital, Web3/AI enablement platform.",
                "linkedin_url": "https://www.linkedin.com/in/samirarora"
            },
            {
                "name": "Peter Leeb",
                "role": "Co-Founder & CRO",
                "brief_details": "Co-founder and Chief Revenue Officer of Kyro Digital.",
                "linkedin_url": "https://www.linkedin.com/in/peter-leeb-06b290"
            }
        ]
    },
    "kyro": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "RegTech",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise"],
        "tags": ["revenue-operations", "billing", "fintech"],
        "funding_stage": "Seed",
        "founders": [
            {
                "name": "Samir Arora",
                "role": "Co-Founder & CEO",
                "brief_details": "Founder of Kyro Digital, Web3/AI enablement platform.",
                "linkedin_url": "https://www.linkedin.com/in/samirarora"
            },
            {
                "name": "Peter Leeb",
                "role": "Co-Founder & CRO",
                "brief_details": "Co-founder and Chief Revenue Officer of Kyro Digital.",
                "linkedin_url": "https://www.linkedin.com/in/peter-leeb-06b290"
            }
        ]
    },
    "medielaj": {
        "industry": "Healthcare & Life Sciences",
        "sector": "HealthTech",
        "subsector": "Telemedicine",
        "business_models": ["SaaS", "Subscription"],
        "industry_relevance": ["Healthcare", "Consumer"],
        "tags": ["telehealth", "diagnostics", "healthcare"],
        "funding_stage": "Seed",
        "founders": [
            {
                "name": "Debjit Patra",
                "role": "Founder & Chairman",
                "brief_details": "Founder and Chairman of MediElaj, provider of healthcare diagnostics kiosks.",
                "linkedin_url": "https://www.linkedin.com/in/debjit-patra-36367319"
            },
            {
                "name": "Umesh Khatri",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of MediElaj, healthtech innovator.",
                "linkedin_url": "https://www.linkedin.com/in/umesh-khatri-00270a4a"
            }
        ]
    },
    "cars24": {
        "industry": "Commerce & Retail",
        "sector": "E-commerce",
        "subsector": "Marketplaces",
        "business_models": ["Marketplace", "Transaction-Based", "B2C"],
        "industry_relevance": ["Consumer"],
        "tags": ["used-cars", "automotive", "marketplace"],
        "funding_stage": "Series G",
        "founders": [
            {
                "name": "Vikram Chopra",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Cars24, pre-owned vehicle marketplace.",
                "linkedin_url": "https://www.linkedin.com/in/vikramchopra"
            },
            {
                "name": "Mehul Agrawal",
                "role": "Co-Founder",
                "brief_details": "Co-founder of Cars24, leading business operations.",
                "linkedin_url": "https://www.linkedin.com/in/mehul-agrawal-1b07246"
            }
        ]
    },
    "simple energy": {
        "industry": "Transportation & Logistics",
        "sector": "Mobility",
        "subsector": "EV Platforms",
        "business_models": ["Transaction-Based", "D2C"],
        "industry_relevance": ["Consumer", "Logistics"],
        "tags": ["electric-vehicles", "ev-scooter", "clean-energy"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Suhas Rajkumar",
                "role": "Founder & CEO",
                "brief_details": "Founder and CEO of Simple Energy, electric vehicle developer.",
                "linkedin_url": "https://www.linkedin.com/in/suhasrajkumar"
            }
        ]
    },
    "awfis": {
        "industry": "Real Estate & Construction",
        "sector": "PropTech",
        "subsector": "Rental Platforms",
        "business_models": ["Subscription", "B2B", "Enterprise License"],
        "industry_relevance": ["Real Estate", "Enterprise", "SMB"],
        "tags": ["coworking", "managed-offices", "workspace"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Amit Ramani",
                "role": "Founder & CEO",
                "brief_details": "Founder and CEO of Awfis Space Solutions.",
                "linkedin_url": "https://www.linkedin.com/in/amitramani"
            }
        ]
    },
    "rategain": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Hospitality Tech",
        "business_models": ["SaaS", "Subscription", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["travel-saas", "pricing-intelligence", "hospitality"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Bhanu Chopra",
                "role": "Founder & Chairman",
                "brief_details": "Founder and Chairman of RateGain, travel-tech provider.",
                "linkedin_url": "https://www.linkedin.com/in/bhanuchopra"
            }
        ]
    },
    "physicswallah": {
        "industry": "Education",
        "sector": "EdTech",
        "subsector": "Test Preparation",
        "business_models": ["Subscription", "Transaction-Based", "B2C"],
        "industry_relevance": ["Education", "Consumer"],
        "tags": ["edtech", "test-prep", "upskilling"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Alakh Pandey",
                "role": "Founder & CEO",
                "brief_details": "Founder and CEO of PhysicsWallah, digital educational provider.",
                "linkedin_url": "https://www.linkedin.com/in/alakh-pandey-physicswallah"
            },
            {
                "name": "Prateek Maheshwari",
                "role": "Co-Founder",
                "brief_details": "Co-founder of PhysicsWallah, managing technical execution.",
                "linkedin_url": "https://www.linkedin.com/in/prateekmaheshwari"
            }
        ]
    },
    "tractor junction": {
        "industry": "Agriculture & Food",
        "sector": "Agritech",
        "subsector": "Agri Finance",
        "business_models": ["Marketplace", "Transaction-Based"],
        "industry_relevance": ["Agriculture", "SMB"],
        "tags": ["tractors", "agritech", "farm-equipment"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Rajat Gupta",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder of Tractor Junction, farm equipment marketplace.",
                "linkedin_url": "https://www.linkedin.com/in/rajat-gupta-tj"
            },
            {
                "name": "Shivani Gupta",
                "role": "Co-Founder",
                "brief_details": "Co-founder of Tractor Junction, leading product and growth.",
                "linkedin_url": "https://www.linkedin.com/in/shivani-gupta-tj"
            }
        ]
    },
    "scripbox": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "WealthTech",
        "business_models": ["Subscription", "Transaction-Based", "B2C"],
        "industry_relevance": ["BFSI", "Consumer"],
        "tags": ["wealth-management", "mutual-funds", "investing"],
        "funding_stage": "Series D",
        "founders": [
            {
                "name": "Atul Singhal",
                "role": "Co-Founder",
                "brief_details": "Co-founder of Scripbox, leading digital wealth advisory.",
                "linkedin_url": "https://www.linkedin.com/in/atulsinghal"
            },
            {
                "name": "Sanjiv Singhal",
                "role": "Co-Founder",
                "brief_details": "Co-founder of Scripbox, product and financial strategist.",
                "linkedin_url": "https://www.linkedin.com/in/sanjivsinghal"
            }
        ]
    },
    "excitel": {
        "industry": "Telecom & Connectivity",
        "sector": "Telecom Infrastructure",
        "subsector": "Connectivity Platforms",
        "business_models": ["Subscription", "B2C"],
        "industry_relevance": ["Telecom", "Consumer"],
        "tags": ["isp", "broadband", "fiber-internet"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Vivek Raina",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Excitel Broadband, retail high-speed fiber internet provider.",
                "linkedin_url": "https://www.linkedin.com/in/vivek-raina-3a6509a"
            }
        ]
    },
    "skyroot aerospace": {
        "industry": "DeepTech",
        "sector": "SpaceTech",
        "subsector": "Launch Systems",
        "business_models": ["Transaction-Based", "B2B"],
        "industry_relevance": ["Defense", "Government"],
        "tags": ["space", "launch-vehicle", "rockets"],
        "funding_stage": "Series B",
        "founders": [
            {
                "name": "Pawan Kumar Chandana",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Skyroot Aerospace, developer of Vikram rockets.",
                "linkedin_url": "https://www.linkedin.com/in/pawan-kumar-chandana"
            },
            {
                "name": "Naga Bharath Daka",
                "role": "Co-Founder & COO",
                "brief_details": "Co-founder and COO of Skyroot Aerospace.",
                "linkedin_url": "https://www.linkedin.com/in/naga-bharath-daka-9b30748"
            }
        ]
    },
    "zee": {
        "industry": "Consumer Internet",
        "sector": "Creator Economy",
        "subsector": "Content Monetization",
        "business_models": ["Advertising", "Subscription", "B2C"],
        "industry_relevance": ["Consumer"],
        "tags": ["media", "entertainment", "broadcasting", "television"],
        "funding_stage": "Public",
        "founders": [
            {
                "name": "Subhash Chandra",
                "role": "Founder",
                "brief_details": "Founder of Zee Network / Essel Group, media industry veteran.",
                "linkedin_url": "https://www.linkedin.com/in/subhashchandra"
            }
        ]
    },
    "aquapulse": {
        "industry": "Energy & Sustainability",
        "sector": "ClimateTech",
        "subsector": "Waste Management",
        "business_models": ["Transaction-Based", "B2B"],
        "industry_relevance": ["Real Estate", "Logistics", "Manufacturing"],
        "tags": ["water-purification", "conservation", "cleantech"],
        "funding_stage": "Bootstrapped",
        "founders": [
            {
                "name": "Prashant Kumar Singh",
                "role": "Founder & Managing Director",
                "brief_details": "Founder of Aquapulse water purification technologies.",
                "linkedin_url": "https://www.linkedin.com/in/prashant-kumar-singh-469b22a8"
            }
        ]
    },
    "plum insurance": {
        "industry": "Financial Services",
        "sector": "InsurTech",
        "subsector": "Digital Insurance",
        "business_models": ["Subscription", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise", "SMB"],
        "tags": ["insurtech", "group-health", "employee-benefits"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Abhishek Poddar",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Plum, digital group health insurance startup.",
                "linkedin_url": "https://www.linkedin.com/in/abhishekpoddar"
            },
            {
                "name": "Saurabh Arora",
                "role": "Co-Founder & CTO",
                "brief_details": "Co-founder and CTO of Plum, serial tech entrepreneur.",
                "linkedin_url": "https://www.linkedin.com/in/saurabharora"
            }
        ]
    },
    "plum": {
        "industry": "Financial Services",
        "sector": "InsurTech",
        "subsector": "Digital Insurance",
        "business_models": ["Subscription", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise", "SMB"],
        "tags": ["insurtech", "group-health", "employee-benefits"],
        "funding_stage": "Series A",
        "founders": [
            {
                "name": "Abhishek Poddar",
                "role": "Co-Founder & CEO",
                "brief_details": "Co-founder and CEO of Plum, digital group health insurance startup.",
                "linkedin_url": "https://www.linkedin.com/in/abhishekpoddar"
            },
            {
                "name": "Saurabh Arora",
                "role": "Co-Founder & CTO",
                "brief_details": "Co-founder and CTO of Plum, serial tech entrepreneur.",
                "linkedin_url": "https://www.linkedin.com/in/saurabharora"
            }
        ]
    },
    "riko ai": {
        "industry": "Artificial Intelligence",
        "sector": "Agentic AI",
        "subsector": "Workflow Agents",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["Enterprise", "SMB"],
        "tags": ["ai-agents", "workflow-automation", "productivity"],
        "funding_stage": "Seed",
        "founders": [
            {
                "name": "Utkarsh Rishi",
                "role": "Co-Founder & AI Engineer",
                "brief_details": "Co-founder of Riko AI, specialized in workflow bots.",
                "linkedin_url": "https://www.linkedin.com/in/utkarsh-rishi"
            },
            {
                "name": "Kobula",
                "role": "Co-Founder & Architect",
                "brief_details": "Co-founder of Riko AI, directing system architecture.",
                "linkedin_url": "https://github.com/MrACodes"
            }
        ]
    },
    "rikoai": {
        "industry": "Artificial Intelligence",
        "sector": "Agentic AI",
        "subsector": "Workflow Agents",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["Enterprise", "SMB"],
        "tags": ["ai-agents", "workflow-automation", "productivity"],
        "funding_stage": "Seed",
        "founders": [
            {
                "name": "Utkarsh Rishi",
                "role": "Co-Founder & AI Engineer",
                "brief_details": "Co-founder of Riko AI, specialized in workflow bots.",
                "linkedin_url": "https://www.linkedin.com/in/utkarsh-rishi"
            },
            {
                "name": "Kobula",
                "role": "Co-Founder & Architect",
                "brief_details": "Co-founder of Riko AI, directing system architecture.",
                "linkedin_url": "https://github.com/MrACodes"
            }
        ]
    }
}

def get_canonical_founders(startup_name):
    """Returns canonical founders list for known startups, or None."""
    if startup_name:
        name_clean = str(startup_name).strip().lower()
        if name_clean in CANONICAL_OVERLOADS:
            return CANONICAL_OVERLOADS[name_clean].get("founders", [])
        for key, over in CANONICAL_OVERLOADS.items():
            if key in name_clean or name_clean in key:
                return over.get("founders", [])
    return None

def get_closest_match(value, choices, threshold=0.4):
    """Finds the closest matching choice from a list of valid choices using string similarity."""
    if not value or not choices:
        return None
        
    value_clean = str(value).strip().lower()
    
    # 1. Direct exact or lowercase match
    for choice in choices:
        if choice.lower() == value_clean:
            return choice
            
    # 2. Substring matching
    for choice in choices:
        choice_lower = choice.lower()
        if choice_lower in value_clean or value_clean in choice_lower:
            return choice
            
    # 3. Fuzzy string matching
    matches = difflib.get_close_matches(value_clean, [c.lower() for c in choices], n=1, cutoff=threshold)
    if matches:
        matched_lower = matches[0]
        # Return the original case choice
        for choice in choices:
            if choice.lower() == matched_lower:
                return choice
                
    return None

def normalize_taxonomy(startup_name, raw_industry, raw_sector, raw_subsector):
    """
    Normalizes raw LLM-generated taxonomy categories to match the exact keys 
    in the master taxonomy schema. Supports direct high-priority overrides.
    """
    if startup_name:
        name_clean = str(startup_name).strip().lower()
        # Direct key match
        if name_clean in CANONICAL_OVERLOADS:
            over = CANONICAL_OVERLOADS[name_clean]
            return over["industry"], over["sector"], over["subsector"]
            
        # Substring key match
        for key, over in CANONICAL_OVERLOADS.items():
            if key in name_clean or name_clean in key:
                return over["industry"], over["sector"], over["subsector"]

    if not taxonomy_data or "industries" not in taxonomy_data:
        return raw_industry, raw_sector, raw_subsector

    industries_list = taxonomy_data["industries"]
    industry_names = [ind["name"] for ind in industries_list]
    
    # 1. Normalize Industry
    normalized_industry = get_closest_match(raw_industry, industry_names)
    
    if not normalized_industry:
        # Fallback default if not recognized
        normalized_industry = "Financial Services"
        
    # Get the specific industry item from taxonomy
    industry_item = next((ind for ind in industries_list if ind["name"] == normalized_industry), None)
    if not industry_item or "sectors" not in industry_item:
        return normalized_industry, raw_sector, raw_subsector
        
    valid_sectors = list(industry_item["sectors"].keys())
    
    # 2. Normalize Sector
    normalized_sector = get_closest_match(raw_sector, valid_sectors)
    
    if not normalized_sector:
        # Fallback to first valid sector in the industry
        normalized_sector = valid_sectors[0] if valid_sectors else raw_sector
        
    # Get the specific subsectors list
    valid_subsectors = industry_item["sectors"].get(normalized_sector, [])
    
    # 3. Normalize Subsector
    normalized_subsector = get_closest_match(raw_subsector, valid_subsectors)
    
    if not normalized_subsector:
        # Fallback to first subsector or just a general tag
        normalized_subsector = valid_subsectors[0] if valid_subsectors else raw_subsector
        
    return normalized_industry, normalized_sector, normalized_subsector

def normalize_business_models(startup_name, raw_models):
    """Normalizes list of business models to match allowed taxonomy list."""
    if startup_name:
        name_clean = str(startup_name).strip().lower()
        if name_clean in CANONICAL_OVERLOADS:
            return CANONICAL_OVERLOADS[name_clean]["business_models"]
        for key, over in CANONICAL_OVERLOADS.items():
            if key in name_clean or name_clean in key:
                return over["business_models"]

    if not raw_models or not taxonomy_data:
        return []
        
    allowed_models = taxonomy_data.get("business_models", [])
    normalized = []
    
    for rm in raw_models:
        match = get_closest_match(rm, allowed_models)
        if match and match not in normalized:
            normalized.append(match)
            
    # Default fallback if empty
    if not normalized:
        normalized = ["B2B"]
        
    return normalized

def normalize_industry_relevance(startup_name, raw_relevance):
    """Normalizes list of industry relevance terms to match allowed taxonomy list."""
    if startup_name:
        name_clean = str(startup_name).strip().lower()
        if name_clean in CANONICAL_OVERLOADS:
            return CANONICAL_OVERLOADS[name_clean]["industry_relevance"]
        for key, over in CANONICAL_OVERLOADS.items():
            if key in name_clean or name_clean in key:
                return over["industry_relevance"]

    if not raw_relevance or not taxonomy_data:
        return []
        
    allowed_relevance = taxonomy_data.get("industry_relevance", [])
    normalized = []
    
    for rr in raw_relevance:
        match = get_closest_match(rr, allowed_relevance)
        if match and match not in normalized:
            normalized.append(match)
            
    # Default fallback if empty
    if not normalized:
        normalized = ["BFSI"]
        
    return normalized

def get_canonical_tags(startup_name, raw_tags):
    """Returns canonical tags for known startups, or raw tags as fallback."""
    if startup_name:
        name_clean = str(startup_name).strip().lower()
        if name_clean in CANONICAL_OVERLOADS:
            return CANONICAL_OVERLOADS[name_clean]["tags"]
        for key, over in CANONICAL_OVERLOADS.items():
            if key in name_clean or name_clean in key:
                return over["tags"]
    return raw_tags
