import re
import os
import json
from datetime import datetime, timezone
import dateutil.parser
from backend.ai.startup_analyzer import analyze_startup, discover_startup_names
from backend.services.supabase_service import (
    upsert_startup,
    save_startup_analysis,
    check_existing_startup,
    supabase
)

def pipeline_log(message):
    print(message)
    try:
        from backend.api.routes.startups import add_scrape_log
        add_scrape_log(message)
    except Exception:
        pass

def clean_string(text):
    """
    Core string cleaning utility that strips action verbs, possessives, 
    and descriptive prefixes to isolate the actual startup brand name.
    """
    if not text:
        return ""
    
    # Pre-process compound hyphenated company suffixes (e.g. PhonePe-owned -> PhonePe owned)
    text = re.sub(r'\b(\w+)-(owned|backed|funded|incubated|acquired|led|run)\b', r'\1 \2', text, flags=re.IGNORECASE)
    
    # 1. Split at common action verbs, financial descriptors, or noise in headlines (Expanded)
    verbs_pattern = r'\b(acquires|acquiring|acquisition|raises|raising|launches|launching|posts|secures|securing|crosses|signs|partners|to\s+invest|to|is|re-enters|enters|announces|backing|backs|rolls|gets|got|funding|deploys|commits|unveils|debuts|be|are|was|were|has|have|had|premiumisation|buyback|revenue|profit|shares|capital|investment|opportunities|valuation|valued\s+at|value|pre-money|round|esop|registrations|report|weekly|monthly|annually|results|performance|earnings|stocks|stock|share|options|option|units|unit|equity|debt|rallies|seeks|plans|hit|hits|gst|soup|scores|score|goes|go|wins|win|grabs|grab|leads|lead|led\s+by|eyes|eye|targets|target|bids|bid|prepares|prepare|aims|aim|buys|buy|sells|sell|makes|make|mark|marks|down|up|closes|closed|invests\s+in|invests|funded|funds|partners\s+with|owned|backed|incubated|run)\b'
    
    # Split text at the first occurrence of any action verbs
    match = re.split(verbs_pattern, text, maxsplit=1, flags=re.IGNORECASE)
    part = match[0] if match else text
    
    # 2. Split at possessive indicators (e.g. Behind Awfis' -> Behind Awfis)
    part = re.split(r"[’']s?\b", part)[0]
    
    # 3. Strip starting auxiliary words or descriptive prefixes (Expanded)
    prefixes_pattern = r'^(healthcare\s+startup|fintech\s+startup|spacetech\s+startup|saas\s+startup|edtech\s+startup|d2c\s+brand|ipo-bound\s+used\s+car\s+marketplace|used\s+car\s+marketplace|online\s+travel\s+aggregator\s*\(?ota\)?\s+platform|business-focused\s+travel\s+distribution\s+platform|online\s+travel\s+aggregator|quick\s+commerce\s+firm|crypto\s+major|car\s+marketplace|spacetech\s+firm|spacetech\s+player|travel\s+platform|startup|can|behind|inside|why|how|after|about|with|from|ai-focused|ai-powered|b2b\s+platform|lending\s+firm|remittance\s+provider|insurtech\s+firm|insurtech\s+startup|edtech\s+venture|agritech\s+firm|proptech\s+startup|wealthtech\s+firm)\s+'
    
    cleaned = re.sub(prefixes_pattern, '', part.strip(), flags=re.IGNORECASE)
    
    # 4. Strip standard quote, rupee symbol, and other unwanted special characters
    cleaned = re.sub(r"[’'\"`₹$%\+\-\[\]\(\)]", "", cleaned).strip()
    
    # Remove extra whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def get_clean_startup_name(headline, extracted_name):
    """
    Cleans the news headline to extract only the actual startup name.
    Uses AI extracted name as primary, with a robust case-insensitive fallback.
    """
    generic_placeholders = [
        "n/a", "none", "various", "various startups", "indian startups", "industry", 
        "generic", "not applicable", "various companies", "multiple startups", "unknown",
        "real money", "gaming", "after months", "months of", "indian startup",
        "haryana", "delhi", "karnataka", "maharashtra", "bengaluru", "mumbai", "india",
        "punjab", "gujarat", "tamil nadu", "kerala", "coalition", "consortium",
        "association", "alliance", "d2c", "direct-to-consumer", "b2b", "sme",
        "startup", "startups", "government", "various names", "digital commerce coalition"
    ]
    
    replacements = {
        "upi": "NPCI",
        "scriipbox": "Scripbox"
    }

    def is_invalid_startup_name(name):
        if not name:
            return True
        name_lower = name.lower().strip()
        
        # Split into individual lowercase tokens
        tokens = re.findall(r'\b\w+\b', name_lower)
        
        # Check for investor/tech giant names
        investor_names = {
            "vanguard", "prosus", "softbank", "tiger global", "peak xv", "sequoia", 
            "westbridge", "temasek", "accel", "lightspeed", "elevation", "matrix partners", 
            "kalaari", "nexus", "chiratae", "google", "apple", "microsoft", "amazon", "meta"
        }
        if any(inv in tokens for inv in investor_names):
            return True
        
        # 1. Check for combined names or roundups containing "and", "or", "&", or ","
        if "and" in tokens or "or" in tokens or "&" in name_lower or "," in name_lower:
            return True
            
        # 2. Check if the name matches or contains any of the forbidden terms
        bad_terms = {"coalition", "consortium", "association", "alliance", "government", "ministry", "commission", "state"}
        if any(t in tokens for t in bad_terms) or any(t in name_lower for t in bad_terms):
            return True
            
        # 3. Check for geographic/location names
        locations = {"haryana", "delhi", "karnataka", "maharashtra", "bengaluru", "mumbai", "india", "punjab", "gujarat", "tamil nadu", "kerala"}
        if any(loc in tokens for loc in locations):
            return True
            
        # 4. Check for generic industry terms / placeholders
        generic_words = {
            "n/a", "none", "various", "generic", "unknown", "industry", "platform", "platforms", 
            "startup", "startups", "company", "companies", "firm", "firms", "player", "players",
            "d2c", "b2b", "sme", "smes", "msme", "msmes", "funding", "round", "various names"
        }
        if any(w in tokens for w in generic_words):
            return True
            
        # 5. Check the whole name against generic placeholders
        if name_lower in generic_placeholders:
            return True
            
        return False

    # 1. Try AI-extracted name first
    if extracted_name:
        clean_name_stripped = extracted_name.lower().strip()
        if not is_invalid_startup_name(clean_name_stripped):
            cleaned_ai = clean_string(extracted_name)
            if cleaned_ai and not is_invalid_startup_name(cleaned_ai):
                if len(cleaned_ai.split()) <= 3 and len(cleaned_ai) <= 30:
                    if cleaned_ai.lower() not in ["and", "to", "for", "with", "the"]:
                        ai_key = cleaned_ai.lower().strip()
                        if ai_key in replacements:
                            return replacements[ai_key]
                        return cleaned_ai

    # 2. Case-Insensitive Heuristics fallback
    cleaned_fallback = clean_string(headline)
    
    words = cleaned_fallback.split()
    if len(words) > 2:
        cleaned_fallback = " ".join(words[:2])
        
    if is_invalid_startup_name(cleaned_fallback):
        return None
        
    final_name = cleaned_fallback.strip()
    
    final_key = final_name.lower().strip()
    if final_key in replacements:
        return replacements[final_key]
        
    return final_name

def verify_website(url):
    """
    Checks if a URL is active by making a lightweight HTTP request.
    """
    if not url:
        return False
    if "example.com" in url or "localhost" in url:
        return False
    
    import requests
    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code != 404:
            return True
        
        response = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
        return response.status_code != 404
    except requests.exceptions.RequestException:
        try:
            response = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
            return response.status_code != 404
        except Exception:
            return False
    except Exception:
        return False

def search_website_duckduckgo(clean_name):
    """
    Searches DuckDuckGo HTML for the official website of the company name.
    """
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse
    
    query = f"{clean_name} official website"
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    pipeline_log(f"🔍 [Pipeline Website Search] Querying DuckDuckGo for: '{clean_name}' website...")
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            result_divs = soup.find_all("div", class_="result")
            for div in result_divs[:3]:
                title_link = div.find("a", class_="result__a")
                if title_link:
                    href = title_link.get("href")
                    parsed = urllib.parse.urlparse(href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    real_url = qs.get("uddg", [None])[0] or href
                    
                    if real_url and real_url.startswith("http"):
                        real_url_lower = real_url.lower()
                        exclude_domains = [
                            "duckduckgo.com", "wikipedia.org", "linkedin.com", "twitter.com", 
                            "facebook.com", "youtube.com", "instagram.com", "news", "blog", 
                            "inc42.com", "entrackr.com", "techcrunch.com"
                        ]
                        if not any(domain in real_url_lower for domain in exclude_domains):
                            if verify_website(real_url):
                                pipeline_log(f"✅ Found active official website via search: {real_url}")
                                return real_url
    except Exception as e:
        pipeline_log(f"⚠️ Search for website failed: {e}")
    return None

def get_clean_website(clean_name, extracted_website):
    """
    Returns the clean, official startup website URL.
    Uses AI extracted website as primary, with a robust mapped lookup fallback.
    """
    # 1. Try AI-extracted website first
    if extracted_website and "error" not in extracted_website and "google.com" not in extracted_website and len(extracted_website) <= 40:
        if not any(char in extracted_website for char in ["₹", "$", "%", "&", "?", "'", "’", "`", " ", "’"]):
            extracted_website = extracted_website.strip()
            if verify_website(extracted_website):
                return extracted_website
        
    # 2. Known exact mappings for standard startups
    known_domains = {
        "coinbase": "https://www.coinbase.com",
        "cars24": "https://www.cars24.com",
        "awfis": "https://www.awfis.com",
        "scripbox": "https://www.scripbox.com",
        "scriipbox": "https://www.scripbox.com",
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
        "zee": "https://www.zee.com",
        "plum": "https://www.plumhq.com",
        "plum insurance": "https://www.plumhq.com",
        "aquapulse": "https://www.aquapulse.co.in"
    }
    
    name_key = clean_name.lower().strip()
    if name_key in known_domains:
        return known_domains[name_key]
        
    # 3. Search for a right website on Google/DuckDuckGo
    searched_url = search_website_duckduckgo(clean_name)
    if searched_url:
        return searched_url

    # 4. Inferred domain generator fallback
    words = clean_name.split()[:2]
    clean_word = "".join(words).lower()
    clean_word = re.sub(r'[^a-z0-9]', '', clean_word)
    
    if clean_word:
        inferred = f"https://www.{clean_word}.com"
        if verify_website(inferred):
            return inferred
        inferred_in = f"https://www.{clean_word}.in"
        if verify_website(inferred_in):
            return inferred_in
        
    return ""

def process_startup(startup):
    """
    Two-Pass AI Pipeline processor:
    Pass 1: Discover all startup names mentioned in the news headline & body.
    For each discovered name:
      - targeted web search anchored with domain.
      - Pass 2: strategic details enrichment.
      - Database write.
    """
    original_headline = startup.get("startup_name", "")
    original_description = startup.get("description", "")
    pipeline_log(f"\n--- Processing News Headline: '{original_headline}' ---")
    
    # Step 1: Run Pass 1 (Name Discovery) to extract all featured startup names
    discovered_names = discover_startup_names(original_headline, original_description)
    
    # Only fallback to headline cleaning if discovery actually failed (returned None)
    if discovered_names is None:
        fallback_name = get_clean_startup_name(original_headline, None)
        if fallback_name:
            discovered_names = [fallback_name]
    elif not discovered_names:
        # LLM successfully ran and determined there were no startup names
        pipeline_log(f"Skipping generic/industry news article (no startup name extracted by AI): '{original_headline}'")
        return None
            
    if not discovered_names:
        pipeline_log(f"Skipping generic/industry news article (no startup name extracted): '{original_headline}'")
        return None
        
    processed_results = []
    
    for name in discovered_names:
        clean_name = get_clean_startup_name(original_headline, name)
        if not clean_name:
            continue
            
        # Filter out generic terms
        macro_terms = [
            "indian startup", "funding", "acquisitions", "various", "gaming", 
            "report", "stories", "months of", "after months", "funding and",
            "e2w", "ew", "e2w registrations", "electric two wheelers", 
            "electric two-wheeler", "electric two wheeler"
        ]
        if any(term in clean_name.lower() for term in macro_terms) and len(clean_name.split()) > 1:
            pipeline_log(f"Skipping generic phrase match: '{clean_name}'")
            continue
            
        pipeline_log(f"\n✨ Processing Discovered Startup: '{clean_name}'")
        
        # Build individual startup item for Pass 2 enrichment
        startup_item = {
            "startup_name": clean_name,
            "description": original_description,
            "source": startup.get("source", "Unknown"),
            "source_url": startup.get("source_url", "")
        }
        
        # Cache Check: Check if startup already exists and has a fresh analysis
        existing_startup = check_existing_startup(clean_name)
        if existing_startup:
            startup_id = existing_startup["id"]
            analysis_resp = supabase.table("startup_analysis").select("*").eq("startup_id", startup_id).execute()
            if analysis_resp.data:
                record = analysis_resp.data[0]
                created_at_str = record.get("created_at")
                if created_at_str:
                    created_at = dateutil.parser.isoparse(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age = now - created_at
                    if age.days < 30:
                        pipeline_log(f"✅ Cache hit: '{clean_name}' already exists with a fresh analysis (created {age.days} days ago). Skipping re-analysis.")
                        processed_results.append({
                            "startup": existing_startup,
                            "analysis": record.get("analysis_json") or {}
                        })
                        continue
        
        # Step 2: Run Pass 2 (Rich Data Enrichment using targeted search)
        pipeline_log("Step 2: Running AI Pass 2 detailed enrichment...")
        analysis = analyze_startup(startup_item)
        
        if not analysis or "error" in analysis:
            pipeline_log(f"❌ AI Pass 2 analysis failed for '{clean_name}'. Error: {analysis.get('error') if analysis else 'No response'}")
            continue
            
        # Get verified website domain
        website = get_clean_website(clean_name, analysis.get("startup_website"))
        startup_item["website"] = website
        
        pipeline_log(f"Extracted website domain: '{website}'")
        
        # Step 3: Upsert basic startup details
        pipeline_log("Step 3: Saving startup metadata to Supabase...")
        response = upsert_startup(startup_item)
        
        if response and len(response) > 0:
            startup_id = response[0]["id"]
            
            # Step 4: Save strategic enrichment analysis parameters
            pipeline_log("Step 4: Saving startup AI analysis parameters to Supabase...")
            analysis_response = save_startup_analysis(startup_id, analysis)
            
            pipeline_log(f"✅ Successfully processed startup: {clean_name}")
            processed_results.append({
                "startup": response[0],
                "analysis": analysis_response
            })
            
    return processed_results if processed_results else None