import os
import json
import difflib

# Load master taxonomy schema
TAXONOMY_PATH = "/Users/anurag/Projects/startup-intelligence/docs/startup_sector_mappings.json"
OVERLOADS_PATH = "/Users/anurag/Projects/startup-intelligence/backend/config/canonical_overloads.json"

try:
    with open(TAXONOMY_PATH, "r") as f:
        taxonomy_data = json.load(f)
except Exception as e:
    print(f"⚠️ Failed to load master taxonomy in mapper utility: {e}")
    taxonomy_data = {}

try:
    if os.path.exists(OVERLOADS_PATH):
        with open(OVERLOADS_PATH, "r") as f:
            CANONICAL_OVERLOADS = json.load(f)
    else:
        CANONICAL_OVERLOADS = {}
except Exception as e:
    print(f"⚠️ Failed to load canonical overloads in mapper utility: {e}")
    CANONICAL_OVERLOADS = {}


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


def get_closest_match(value, choices, threshold=0.6):
    """Finds the closest matching choice from a list of valid choices using string similarity."""
    if not value or not choices:
        return None
        
    import re
    def normalize(s):
        s = str(s).lower().strip()
        s = re.sub(r'[-_]', ' ', s)
        s = re.sub(r'\s+', ' ', s)
        return s

    val_norm = normalize(value)
    
    # 1. Exact match on normalized strings
    for choice in choices:
        if normalize(choice) == val_norm:
            return choice
            
    # 2. Word-boundary matching on normalized strings
    if len(val_norm) >= 2:
        for choice in choices:
            choice_norm = normalize(choice)
            pattern_val = r'\b' + re.escape(val_norm) + r'\b'
            pattern_choice = r'\b' + re.escape(choice_norm) + r'\b'
            if re.search(pattern_val, choice_norm) or re.search(pattern_choice, val_norm):
                return choice
                
    # 3. Fuzzy string matching on normalized strings
    choice_norms = [normalize(c) for c in choices]
    matches = difflib.get_close_matches(val_norm, choice_norms, n=1, cutoff=threshold)
    if matches:
        matched_norm = matches[0]
        # Return the original case choice
        for choice in choices:
            if normalize(choice) == matched_norm:
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
