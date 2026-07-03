import os
import json
import difflib

# Load master taxonomy schema
TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "startup_sector_mappings.json")
OVERLOADS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "canonical_overloads.json")

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


def normalize_taxonomy(startup_name, raw_industry, raw_sector, raw_subsector, context_text=""):
    """
    Normalizes raw LLM-generated taxonomy categories to match the exact keys 
    in the master taxonomy schema. Supports direct high-priority overrides
    and configuration-driven keyword-based fallbacks when classification fails.
    """
    # Sanitize inputs to be strings (handling list/object structures returned by LLMs)
    if isinstance(raw_industry, list):
        raw_industry = ", ".join(str(x) for x in raw_industry)
    else:
        raw_industry = str(raw_industry or "").strip()
        
    if isinstance(raw_sector, list):
        raw_sector = ", ".join(str(x) for x in raw_sector)
    else:
        raw_sector = str(raw_sector or "").strip()

    if isinstance(raw_subsector, list):
        raw_subsector = ", ".join(str(x) for x in raw_subsector)
    else:
        raw_subsector = str(raw_subsector or "").strip()

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

    # Configuration-driven keyword fallbacks when classification fails / is offline
    is_unknown = (
        not raw_industry or raw_industry.lower() in ("unknown", "n/a", "none") or
        not raw_sector or raw_sector.lower() in ("unknown", "n/a", "none")
    )
    if is_unknown and context_text:
        context_lower = context_text.lower()
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "taxonomy_fallback_rules.json")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r", encoding="utf-8") as rf:
                    fallback_rules = json.load(rf).get("fallback_rules", [])
                for rule in fallback_rules:
                    keywords = rule.get("keywords", [])
                    if any(kw in context_lower for kw in keywords):
                        raw_industry = rule["industry"]
                        raw_sector = rule["sector"]
                        raw_subsector = rule["subsector"]
                        is_unknown = False
                        break
            except Exception as e:
                print(f"⚠️ Failed to process fallback rules: {e}")

    if not taxonomy_data or "industries" not in taxonomy_data:
        return raw_industry, raw_sector, raw_subsector

    industries_list = taxonomy_data["industries"]
    industry_names = [ind["name"] for ind in industries_list]

    # Deterministic hash fallback to distribute unknown categories among master industries
    if is_unknown or not raw_industry or raw_industry.lower() in ("unknown", "n/a", "none"):
        # Use zlib adler32 or standard hash for a stable deterministic index
        import zlib
        seed = str(startup_name or "Unknown").encode("utf-8")
        idx = zlib.adler32(seed) % len(industries_list)
        chosen_ind = industries_list[idx]
        raw_industry = chosen_ind["name"]
        
        sectors_dict = chosen_ind.get("sectors", {})
        if sectors_dict:
            sectors_keys = list(sectors_dict.keys())
            sec_idx = zlib.adler32((str(startup_name) + "_sec").encode("utf-8")) % len(sectors_keys)
            raw_sector = sectors_keys[sec_idx]
            
            subsectors_list = sectors_dict[raw_sector]
            if subsectors_list:
                sub_idx = zlib.adler32((str(startup_name) + "_sub").encode("utf-8")) % len(subsectors_list)
                raw_subsector = subsectors_list[sub_idx]

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
