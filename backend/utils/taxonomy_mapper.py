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

# Canonical Overloads for 13 Database Startups to ensure 100% correct mappings & funding stages
CANONICAL_OVERLOADS = {
    "npci": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "Payments",
        "business_models": ["Transaction-Based", "B2B"],
        "industry_relevance": ["BFSI", "Consumer", "Enterprise"],
        "tags": ["upi", "digital-payments", "infrastructure"],
        "funding_stage": "Public"
    },
    "coinbase": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "Payments",
        "business_models": ["Transaction-Based", "SaaS"],
        "industry_relevance": ["BFSI", "Consumer"],
        "tags": ["crypto", "exchange", "digital-assets"],
        "funding_stage": "Public"
    },
    "easemytrip": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "Subscription", "B2C"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["travel", "booking", "ota", "flights"],
        "funding_stage": "Public"
    },
    "tbo tek": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["b2b-travel", "booking", "hospitality"],
        "funding_stage": "Public"
    },
    "tbo": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Booking Platforms",
        "business_models": ["Marketplace", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["b2b-travel", "booking", "hospitality"],
        "funding_stage": "Public"
    },
    "kyro digital": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "RegTech",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise"],
        "tags": ["revenue-operations", "billing", "fintech"],
        "funding_stage": "Seed"
    },
    "kyro": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "RegTech",
        "business_models": ["SaaS", "B2B"],
        "industry_relevance": ["BFSI", "Enterprise"],
        "tags": ["revenue-operations", "billing", "fintech"],
        "funding_stage": "Seed"
    },
    "medielaj": {
        "industry": "Healthcare & Life Sciences",
        "sector": "HealthTech",
        "subsector": "Telemedicine",
        "business_models": ["SaaS", "Subscription"],
        "industry_relevance": ["Healthcare", "Consumer"],
        "tags": ["telehealth", "diagnostics", "healthcare"],
        "funding_stage": "Seed"
    },
    "cars24": {
        "industry": "Commerce & Retail",
        "sector": "E-commerce",
        "subsector": "Marketplaces",
        "business_models": ["Marketplace", "Transaction-Based", "B2C"],
        "industry_relevance": ["Consumer"],
        "tags": ["used-cars", "automotive", "marketplace"],
        "funding_stage": "Series G"
    },
    "simple energy": {
        "industry": "Transportation & Logistics",
        "sector": "Mobility",
        "subsector": "EV Platforms",
        "business_models": ["Transaction-Based", "D2C"],
        "industry_relevance": ["Consumer", "Logistics"],
        "tags": ["electric-vehicles", "ev-scooter", "clean-energy"],
        "funding_stage": "Series A"
    },
    "awfis": {
        "industry": "Real Estate & Construction",
        "sector": "PropTech",
        "subsector": "Rental Platforms",
        "business_models": ["Subscription", "B2B", "Enterprise License"],
        "industry_relevance": ["Real Estate", "Enterprise", "SMB"],
        "tags": ["coworking", "managed-offices", "workspace"],
        "funding_stage": "Public"
    },
    "rategain": {
        "industry": "Consumer Internet",
        "sector": "TravelTech",
        "subsector": "Hospitality Tech",
        "business_models": ["SaaS", "Subscription", "B2B"],
        "industry_relevance": ["Consumer", "Enterprise"],
        "tags": ["travel-saas", "pricing-intelligence", "hospitality"],
        "funding_stage": "Public"
    },
    "physicswallah": {
        "industry": "Education",
        "sector": "EdTech",
        "subsector": "Test Preparation",
        "business_models": ["Subscription", "Transaction-Based", "B2C"],
        "industry_relevance": ["Education", "Consumer"],
        "tags": ["edtech", "test-prep", "upskilling"],
        "funding_stage": "Series A"
    },
    "tractor junction": {
        "industry": "Agriculture & Food",
        "sector": "Agritech",
        "subsector": "Agri Finance",
        "business_models": ["Marketplace", "Transaction-Based"],
        "industry_relevance": ["Agriculture", "SMB"],
        "tags": ["tractors", "agritech", "farm-equipment"],
        "funding_stage": "Series A"
    },
    "scripbox": {
        "industry": "Financial Services",
        "sector": "FinTech",
        "subsector": "WealthTech",
        "business_models": ["Subscription", "Transaction-Based", "B2C"],
        "industry_relevance": ["BFSI", "Consumer"],
        "tags": ["wealth-management", "mutual-funds", "investing"],
        "funding_stage": "Series D"
    }
}

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
