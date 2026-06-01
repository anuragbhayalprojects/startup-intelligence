import re
from backend.ai.startup_analyzer import analyze_startup

from backend.services.supabase_service import (
    upsert_startup,
    save_startup_analysis
)


def clean_string(text):
    """
    Core string cleaning utility that strips action verbs, possessives, 
    and descriptive prefixes to isolate the actual startup brand name.
    """
    if not text:
        return ""
    
    # 1. Split at common action verbs, financial descriptors, or noise in headlines
    verbs_pattern = r'\b(acquires|raises|launches|posts|secures|crosses|signs|partners|to\s+invest|to|is|re-enters|enters|announces|backs|rolls|gets|funding|deploys|commits|unveils|debuts|be|are|was|were|has|have|had|premiumisation|buyback|revenue|profit|shares|capital|investment|acquisition|opportunities|valuation|round|esop|registrations|report|weekly|monthly|annually|results|performance|earnings|stocks|stock|share|options|option|units|unit|equity|debt|rallies|seeks|plans|hit|hits|gst|soup)\b'
    
    # Split text at the first occurrence of any action verbs
    match = re.split(verbs_pattern, text, maxsplit=1, flags=re.IGNORECASE)
    part = match[0] if match else text
    
    # 2. Split at possessive indicators (e.g. Behind Awfis' -> Behind Awfis)
    part = re.split(r"[’']s?\b", part)[0]
    
    # 3. Strip starting auxiliary words or descriptive prefixes
    prefixes_pattern = r'^(healthcare\s+startup|fintech\s+startup|spacetech\s+startup|saas\s+startup|edtech\s+startup|d2c\s+brand|ipo-bound\s+used\s+car\s+marketplace|used\s+car\s+marketplace|online\s+travel\s+aggregator\s*\(?ota\)?\s+platform|business-focused\s+travel\s+distribution\s+platform|online\s+travel\s+aggregator|quick\s+commerce\s+firm|crypto\s+major|car\s+marketplace|spacetech\s+firm|spacetech\s+player|travel\s+platform|startup|can|behind|inside|why|how|after|about|with|from)\s+'
    
    cleaned = re.sub(prefixes_pattern, '', part.strip(), flags=re.IGNORECASE)
    
    # 4. Strip standard quote, rupee symbol, and other unwanted special characters
    cleaned = re.sub(r"[’'\"`₹$%\+\-\[\]\(\)]", "", cleaned).strip()
    
    # Remove extra whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def get_clean_startup_name(headline, analysis):
    """
    Cleans the news headline to extract only the actual startup name.
    Uses AI extracted name as primary, with a robust case-insensitive fallback.
    """
    generic_placeholders = [
        "n/a", "none", "various", "various startups", "indian startups", "industry", 
        "generic", "not applicable", "various companies", "multiple startups", "unknown",
        "real money", "gaming", "after months", "months of", "indian startup"
    ]
    
    replacements = {
        "upi": "NPCI",
    }

    # 1. Try AI-extracted name first
    clean_name = analysis.get("extracted_startup_name") if analysis else None
    if clean_name and "error" not in analysis:
        clean_name_stripped = clean_name.lower().strip()
        if clean_name_stripped not in generic_placeholders:
            cleaned_ai = clean_string(clean_name)
            if cleaned_ai and len(cleaned_ai.split()) <= 3 and len(cleaned_ai) <= 30:
                # Exclude generic short noise words
                if cleaned_ai.lower() not in ["and", "to", "for", "with", "the"]:
                    ai_key = cleaned_ai.lower().strip()
                    if ai_key in replacements:
                        return replacements[ai_key]
                    return cleaned_ai

    # 2. Case-Insensitive Heuristics fallback
    cleaned_fallback = clean_string(headline)
    
    # Take only the first two words as a safe fallback if it's still too long
    words = cleaned_fallback.split()
    if len(words) > 2:
        cleaned_fallback = " ".join(words[:2])
        
    if cleaned_fallback.lower().strip() in generic_placeholders:
        return None
        
    final_name = cleaned_fallback.strip()
    
    # Apply special brand mappings (e.g. UPI -> NPCI)
    final_key = final_name.lower().strip()
    if final_key in replacements:
        return replacements[final_key]
        
    return final_name


def get_clean_website(clean_name, analysis):
    """
    Returns the clean, official startup website URL.
    Uses AI extracted website as primary, with a robust mapped lookup fallback.
    """
    # 1. Try AI-extracted website first
    website = analysis.get("startup_website") if analysis else None
    if website and "error" not in analysis and "google.com" not in website and len(website) <= 40:
        # Validate that the URL doesn't contain weird characters
        if not any(char in website for char in ["₹", "$", "%", "&", "?", "'", "’", "`", " ", "’"]):
            return website.strip()
        
    # 2. Known exact mappings for standard Indian/global startups in the news
    known_domains = {
        "coinbase": "https://www.coinbase.com",
        "cars24": "https://www.cars24.com",
        "awfis": "https://www.awfis.com",
        "scripbox": "https://www.scripbox.com",
        "physicswallah": "https://www.pw.live",
        "physics wallah": "https://www.pw.live",
        "easemytrip": "https://www.easemytrip.com",
        "tbo tek": "https://www.tbo.com",
        "tbo": "https://www.tbo.com",
        "simple energy": "https://www.simpleenergy.in",
        "medielaj": "https://www.medielaj.in",
        "rapido": "https://www.rapido.autos",
        "innovaccer": "https://www.innovaccer.com",
        "zepto": "https://www.zepto.com",
        "skyroot aerospace": "https://www.skyroot.in",
        "skyroot": "https://www.skyroot.in",
        "tractor junction": "https://www.tractorjunction.com",
        "upi": "https://www.npci.org.in",
        "npci": "https://www.npci.org.in",
        "kyro capital": "https://www.kyro.co",
        "kyro": "https://www.kyro.co",
        "ola electric": "https://www.olaelectric.com",
        "ola": "https://www.olaelectric.com",
        "e2w": "https://www.olaelectric.com",
        "rategain": "https://www.rategain.com",
        "rategain technologies": "https://www.rategain.com",
        "zee": "https://www.zee.com"
    }
    
    name_key = clean_name.lower().strip()
    if name_key in known_domains:
        return known_domains[name_key]
        
    # 3. Inferred domain generator fallback
    # Take up to 2 words of the clean name, join them, strip non-alphanumeric
    words = clean_name.split()[:2]
    clean_word = "".join(words).lower()
    clean_word = re.sub(r'[^a-z0-9]', '', clean_word)
    
    if not clean_word:
        clean_word = "startup"
        
    return f"https://www.{clean_word}.com"


def process_startup(startup):

    print(f"\n--- Processing Headline: {startup.get('startup_name')} ---")

    print("Step 1: Running AI structured analysis...")

    analysis = analyze_startup(startup)

    # Clean the startup name from the headline
    original_headline = startup.get("startup_name")
    clean_name = get_clean_startup_name(original_headline, analysis)
    
    # Filter out general/macro industry reports that do not center on a single startup
    if not clean_name:
        print(f"Skipping generic/industry news article (no specific startup name extracted): '{original_headline}'")
        return None
        
    # Exclude macro reports and generic phrases explicitly
    macro_terms = [
        "indian startup", "funding", "acquisitions", "various", "gaming", 
        "report", "stories", "months of", "after months", "funding and",
        "e2w", "ew", "e2w registrations", "electric two wheelers", 
        "electric two-wheeler", "electric two wheeler"
    ]
    if any(term in clean_name.lower() for term in macro_terms) and len(clean_name.split()) > 1:
        print(f"Skipping macro/industry analysis headline: '{clean_name}'")
        return None

    # Get the official clean website URL
    website = get_clean_website(clean_name, analysis)
        
    print(f"Extracted actual startup name: '{clean_name}'")
    print(f"Extracted startup website: '{website}'")
    
    # Update the startup metadata
    startup["startup_name"] = clean_name
    startup["website"] = website

    print("Step 2: Saving basic startup info to Supabase...")

    # Exclude generic names that don't look like startups
    if len(clean_name) <= 2 or clean_name.lower() in ["and", "to", "for", "with", "the"]:
        print(f"Skipping extremely short or generic non-startup name: '{clean_name}'")
        return None

    response = upsert_startup(startup)

    if response and len(response) > 0:
        startup_id = response[0]["id"]

        print("Step 3: Saving startup AI analysis to Supabase...")

        analysis_response = save_startup_analysis(startup_id, analysis)

        print(f"Successfully processed: {clean_name}")
        
        return {
            "startup": response[0],
            "analysis": analysis_response
        }
    else:
        print(f"Failed to upsert startup info in DB for {clean_name}")
        return None