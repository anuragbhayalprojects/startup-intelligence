import re
import os
import json
from pathlib import Path
from datetime import datetime, timezone
import dateutil.parser
from backend.ai.startup_analyzer import (
    analyze_startup,
    discover_startup_names,
    generate_news_summary,
    collect_funding_snippets,
    extract_funding_rounds
)
from backend.services.supabase_service import (
    upsert_startup,
    save_startup_analysis,
    save_funding_rounds,
    check_existing_startup,
    save_startup_news,
    get_startup_news,
    supabase
)

# ---------------------------------------------------------------------------
# Pipeline module delegations (Phase 3 refactor)
# These imports replace inline implementations. The functions below are
# thin wrappers that delegate to the canonical pipeline/ package modules.
# ---------------------------------------------------------------------------
try:
    from backend.pipeline.search_engine import (
        verify_website as _verify_website,
        search_website_duckduckgo as _search_website_duckduckgo,
        get_clean_website as _get_clean_website_impl,
    )
    _PIPELINE_SEARCH_ENGINE_AVAILABLE = True
except ImportError:
    _PIPELINE_SEARCH_ENGINE_AVAILABLE = False

try:
    from backend.pipeline.article_cleaner import (
        get_clean_startup_name as _article_cleaner_get_name,
        is_news_duplicate as _article_cleaner_is_duplicate,
    )
    _PIPELINE_ARTICLE_CLEANER_AVAILABLE = True
except ImportError:
    _PIPELINE_ARTICLE_CLEANER_AVAILABLE = False

# ---------------------------------------------------------------------------
# Backward-compatibility re-export: get_clean_website()
# The canonical implementation now lives in backend.pipeline.search_engine.
# This re-export preserves the existing import surface for:
#   - backend/scripts/enrich_existing_taxonomy.py
#   - backend/cleanup_db.py
#   - backend/agents/enrichment_agent.py
# ---------------------------------------------------------------------------
try:
    from backend.utils.website_resolver import get_clean_website  # noqa: F401
except ImportError:
    # Fallback: use new pipeline module if utils version not available
    if _PIPELINE_SEARCH_ENGINE_AVAILABLE:
        from backend.pipeline.search_engine import get_clean_website  # noqa: F401
    else:
        def get_clean_website(clean_name, extracted_website):  # type: ignore[misc]
            """Fallback stub — install backend/pipeline/search_engine.py."""
            return extracted_website or None



# ---------------------------------------------------------------------------
# External Rules Configuration Loader
# ---------------------------------------------------------------------------
_NAME_RULES_CACHE: dict | None = None
_HEADLINE_PATTERNS_CACHE: dict | None = None

def load_name_resolution_rules() -> dict:
    """
    Loads name resolution rules from backend/config/name_resolution_rules.json.
    Results are cached in-process to avoid repeated file I/O.
    """
    global _NAME_RULES_CACHE
    if _NAME_RULES_CACHE is not None:
        return _NAME_RULES_CACHE
    config_path = Path(__file__).resolve().parent.parent / "config" / "name_resolution_rules.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _NAME_RULES_CACHE = json.load(f)
    except Exception as e:
        # Graceful fallback to empty config — hardcoded defaults inside functions still apply
        print(f"⚠️ [Pipeline] Could not load name_resolution_rules.json: {e}")
        _NAME_RULES_CACHE = {}
    return _NAME_RULES_CACHE


def load_headline_patterns() -> dict:
    """
    Loads regex patterns from backend/config/headline_patterns.json.
    Results are cached in-process to avoid repeated file I/O.
    """
    global _HEADLINE_PATTERNS_CACHE
    if _HEADLINE_PATTERNS_CACHE is not None:
        return _HEADLINE_PATTERNS_CACHE
    config_path = Path(__file__).resolve().parent.parent / "config" / "headline_patterns.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _HEADLINE_PATTERNS_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [Pipeline] Could not load headline_patterns.json: {e}")
        _HEADLINE_PATTERNS_CACHE = {}
    return _HEADLINE_PATTERNS_CACHE


def are_headlines_describing_same_event(headline1: str, headline2: str) -> bool:
    """
    Asks the local Ollama model if two headlines describe the exact same corporate event.
    """
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    
    if not base_url:
        return False
        
    prompt = f"""You are a precise semantic news deduplication assistant.
    Your job is to determine if two headlines from different sources are reporting on the exact same corporate event (such as a funding round, launch, acquisition, or leadership change for a startup).
    
    Note:
    1. Different sources may describe the same event with different word order or focus (e.g. source A emphasizes the lead investor: "Panthera Growth leads...", while source B emphasizes the startup: "Innefu Labs raises...").
    2. The monetary amount (e.g., "$30 Mn", "$30 million") and the company names matching is a very strong indicator of the same funding event.
    
    Headline 1: "{headline1}"
    Headline 2: "{headline2}"
    
    Based on the rules, are these two headlines describing the same corporate event?
    Respond with only a single word: YES or NO. Do not explain."""
    try:
        from backend.utils.ollama_helper import ensure_ollama_running
        ensure_ollama_running()
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 512, "temperature": 0.0}
            },
            headers={"Content-Type": "application/json"},
            timeout=5.0
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip().lower()
        return "yes" in result
    except requests.exceptions.ConnectionError:
        print("⚠️ [Pipeline] Ollama AI service is offline. Assuming different events.")
        return False
    except Exception:
        return False

def are_news_events_describing_same_story(headline1: str, desc1: str, headline2: str, desc2: str) -> bool:
    """
    Asks the local Ollama model if two news events (headlines and descriptions) describe the exact same event or story.
    """
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    
    if not base_url:
        return False
        
    prompt = f"""You are a precise semantic news deduplication assistant.
Your job is to determine if two news events (each having a headline and a description/summary) from different sources are reporting on the exact same corporate event or story (such as a funding round, launch, acquisition, policy update, or leadership change for a startup).

Note:
1. Different sources may describe the same event with different word order or focus (e.g. source A emphasizes the lead investor: "Panthera Growth leads...", while source B emphasizes the startup: "Innefu Labs raises...").
2. The description/summary provides context. If both headlines and descriptions are talking about the exact same underlying event (e.g., the same $30M funding round, or the same product launch), they are duplicates.
3. If they describe completely different events (e.g. one is a funding round from 2024, and the other is a news article about a GST fine or partnership in 2026), they are NOT duplicates.

News Event 1:
Headline: "{headline1}"
Context/Description: "{desc1}"

News Event 2:
Headline: "{headline2}"
Context/Description: "{desc2}"

Based on the rules, do these two news events describe the same corporate event or story?
Respond with only a single word: YES or NO. Do not explain."""
    try:
        from backend.utils.ollama_helper import ensure_ollama_running
        ensure_ollama_running()
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 1024, "temperature": 0.0}
            },
            headers={"Content-Type": "application/json"},
            timeout=8.0
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip().lower()
        return "yes" in result
    except requests.exceptions.ConnectionError:
        print("⚠️ [Pipeline] Ollama AI service is offline. Assuming different stories.")
        return False
    except Exception:
        return False

def is_news_duplicate(new_headline: str, new_description: str, existing_news: list, source_url: str = "") -> bool:
    """
    Determines if a new headline is a duplicate of any existing news.
    Only returns True for exact identical headlines or source URL matches to allow repeating news summaries.
    """
    if not existing_news:
        return False
        
    clean_new_headline = new_headline.strip().lower()
    clean_new_url = source_url.strip().lower() if source_url else ""
    
    for news in existing_news:
        exist_headline = (news.get("headline") or "").strip().lower()
        exist_url = (news.get("source_url") or "").strip().lower()
        
        if clean_new_headline == exist_headline:
            return True
        if clean_new_url and clean_new_url == exist_url:
            return True
            
    return False

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
    
    rules = load_name_resolution_rules()
    verbs = rules.get("verbs", [])
    prefixes = rules.get("prefixes", [])
    
    # Pre-process compound hyphenated company suffixes (e.g. PhonePe-owned -> PhonePe owned)
    text = re.sub(r'\b(\w+)-(owned|backed|funded|incubated|acquired|led|run)\b', r'\1 \2', text, flags=re.IGNORECASE)
    
    # 1. Split at common action verbs, financial descriptors, or noise in headlines (loaded from config)
    if verbs:
        verbs_sorted = sorted(verbs, key=len, reverse=True)
        verbs_pattern = r'\b(' + '|'.join(re.escape(v) for v in verbs_sorted) + r')\b'
        match = re.split(verbs_pattern, text, maxsplit=1, flags=re.IGNORECASE)
        part = match[0] if match else text
    else:
        part = text
    
    # 2. Split at possessive indicators (e.g. Behind Awfis' -> Behind Awfis)
    part = re.split(r"[’']s?\b", part)[0]
    
    # 3. Strip starting auxiliary words or descriptive prefixes (loaded from config)
    if prefixes:
        prefixes_sorted = sorted(prefixes, key=len, reverse=True)
        prefixes_pattern = r'^(' + '|'.join(re.escape(p).replace(r'\ ', r'\s+') for p in prefixes_sorted) + r')\s+'
        cleaned = re.sub(prefixes_pattern, '', part.strip(), flags=re.IGNORECASE)
    else:
        cleaned = part.strip()
    
    # 4. Strip standard quote, rupee symbol, and other unwanted special characters
    cleaned = re.sub(r"[’'\"`₹$%\+\-\[\]\(\)]", "", cleaned).strip()
    
    # Remove extra whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 5. Strip standard suffixes (e.g. Pvt Ltd, India, Global, etc.) from the end
    suffixes = rules.get("suffixes", [])
    if suffixes:
        suffixes_sorted = sorted(suffixes, key=len, reverse=True)
        suffixes_pattern = r'\s+\b(' + '|'.join(re.escape(s) for s in suffixes_sorted) + r')\b$'
        cleaned = re.sub(suffixes_pattern, '', cleaned, flags=re.IGNORECASE).strip()
        
    return cleaned

def get_clean_startup_name(headline, extracted_name, source=None, source_url=None):
    """
    Cleans the news headline to extract only the actual startup brand name.
    Uses AI extracted name as primary, with a robust mapped lookup fallback.

    Filtering rules are loaded dynamically from:
        backend/config/name_resolution_rules.json
    """
    # Load rules from external config (cached after first call)
    rules = load_name_resolution_rules()

    generic_placeholders = rules.get("generic_placeholders", [])
    replacements = rules.get("replacements", {})
    investor_names = set(rules.get("investor_names", []))
    bad_terms = set(rules.get("bad_terms", []))
    locations = set(rules.get("locations", []))
    generic_words = set(rules.get("generic_words", []))
    product_split_terms = rules.get("product_split_terms", [])

    def _truncate_at_product_term(name: str) -> str:
        words = name.split()
        if len(words) < 3:
            return name
        for i, word in enumerate(words[1:], start=1):  # Start scanning from 2nd word
            if word.lower() in product_split_terms:
                truncated = " ".join(words[:i])
                if truncated:
                    return truncated
        return name

    def is_invalid_startup_name(name):
        if not name:
            return True
        name_lower = name.lower().strip()

        # Ignore if name matches news source or source domain
        if source:
            src_lower = source.lower().strip()
            if name_lower == src_lower or src_lower in name_lower or name_lower in src_lower:
                return True
        if source_url:
            domain = source_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].split(".")[0].lower()
            if domain and (name_lower == domain or domain in name_lower or name_lower in domain):
                return True

        # Filter out very short names
        if len(name_lower) < 3:
            return True

        # Filter out names starting with ex, former, or containing ex-executive prefix structures
        if (
            name_lower.startswith("ex ") or 
            name_lower.startswith("former ") or 
            name_lower.startswith("ex-") or 
            name_lower.startswith("exmirae") or
            name_lower.startswith("exceo") or
            name_lower.startswith("exfounder") or
            name_lower.startswith("exvp") or
            name_lower.startswith("exdirector")
        ):
            return True
            
        # If it starts with ex followed by any investor name or bad term (e.g. exmirae, exsoftbank)
        if name_lower.startswith("ex") and len(name_lower) > 2:
            rest = name_lower[2:].strip()
            if rest in investor_names or any(inv in rest for inv in investor_names) or rest in bad_terms:
                return True

        # Split into individual lowercase tokens
        tokens = re.findall(r'\b\w+\b', name_lower)

        # Check for investor / tech giant names
        if any(inv in tokens for inv in investor_names):
            return True

        # 1. Combined names or roundups containing "and", "or", "&", or ","
        if "and" in tokens or "or" in tokens or "&" in name_lower or "," in name_lower:
            return True

        # 2. Forbidden organisational terms (word-boundary matched to prevent false-positive substring matches like "mint" in "turtlemint")
        if any(t in tokens for t in bad_terms) or any(re.search(r'\b' + re.escape(t) + r'\b', name_lower) for t in bad_terms):
            return True

        # 3. Geographic / location names
        if any(loc in tokens for loc in locations):
            return True

        # 4. Generic industry terms / placeholders (token-level)
        if any(w in tokens for w in generic_words):
            return True

        # 5. Whole-name check against generic placeholders list
        if name_lower in [p.lower() for p in generic_placeholders]:
            return True

        return False

    # -----------------------------------------------------------------------
    # 1. Try AI-extracted name first
    # -----------------------------------------------------------------------
    if extracted_name:
        # Apply product-term truncation BEFORE validity check
        extracted_name = _truncate_at_product_term(extracted_name.strip())

        cleaned_ai = clean_string(extracted_name)
        if cleaned_ai and not is_invalid_startup_name(cleaned_ai.lower().strip()):
            if len(cleaned_ai.split()) <= 4 and len(cleaned_ai) <= 30:
                if cleaned_ai.lower() not in ["and", "to", "for", "with", "the"]:
                    ai_key = cleaned_ai.lower().strip()
                    if ai_key in replacements:
                        return replacements[ai_key]
                    return cleaned_ai

    # -----------------------------------------------------------------------
    # 2. Layered fallback: Headline pattern matching
    # -----------------------------------------------------------------------
    patterns_config = load_headline_patterns()
    for pattern_entry in patterns_config.get("patterns", []):
        rx = pattern_entry.get("regex")
        groups = pattern_entry.get("groups", [1])
        match = re.match(rx, headline, re.IGNORECASE)
        if match:
            for g in groups:
                try:
                    candidate = match.group(g)
                    candidate_clean = clean_string(candidate)
                    if candidate_clean and not is_invalid_startup_name(candidate_clean):
                        final_key = candidate_clean.lower().strip()
                        if final_key in replacements:
                            return replacements[final_key]
                        return candidate_clean
                except IndexError:
                    continue

    # -----------------------------------------------------------------------
    # 3. Last resort fallback: clean string from headline (first 2 words)
    # -----------------------------------------------------------------------
    cleaned_fallback = clean_string(headline)
    words = cleaned_fallback.split()
    if len(words) > 0:
        candidate = " ".join(words[:2])
        if not is_invalid_startup_name(candidate):
            final_key = candidate.lower().strip()
            if final_key in replacements:
                return replacements[final_key]
            return candidate

    return None

def verify_website(url):
    """
    Checks if a URL is active by making a lightweight HTTP request.
    Delegates to backend.pipeline.search_engine.verify_website.
    """
    if _PIPELINE_SEARCH_ENGINE_AVAILABLE:
        return _verify_website(url)
    # Inline fallback if search_engine module not available
    if not url:
        return False
    if "example.com" in url or "localhost" in url:
        return False
    import requests
    if not url.startswith("http"):
        url = "https://" + url
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code != 404:
            return True
        response = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
        return response.status_code != 404
    except Exception:
        return False

def search_website_duckduckgo(clean_name):
    """
    Searches DuckDuckGo HTML for the official website of the company name.
    Delegates to backend.pipeline.search_engine.search_website_duckduckgo.
    """
    if _PIPELINE_SEARCH_ENGINE_AVAILABLE:
        return _search_website_duckduckgo(clean_name)
    pipeline_log(f"⚠️ [Pipeline] search_engine module not available, skipping DuckDuckGo search for '{clean_name}'")
    return None


def get_clean_website(clean_name, extracted_website):
    """
    Returns the clean, official startup website URL.
    Delegates to backend.pipeline.search_engine.get_clean_website.
    """
    if _PIPELINE_SEARCH_ENGINE_AVAILABLE:
        return _get_clean_website_impl(clean_name, extracted_website or "")
    # Minimal inline fallback
    if extracted_website and extracted_website.startswith("http"):
        return extracted_website
    return ""


def process_startup(startup, industry_filter: str = "", sector_filter: str = "", subsector_filter: str = "", resolution_only: bool = False):
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
    # If startup_name is already explicitly passed, bypass LLM Name Discovery call
    if startup.get("startup_name"):
        discovered_items = [{"name": startup["startup_name"], "description": startup.get("news_summary") or startup.get("description", "")}]
        pipeline_log(f"⚡ [process_startup] Bypassing name discovery. Using pre-provided startup: '{startup['startup_name']}'")
    else:
        paragraphs = startup.get("paragraphs") or [original_description]
        discovered_items = discover_startup_names(original_headline, paragraphs)
    
    # Trigger Python heuristics fallback ONLY if discovery failed (None).
    # If the LLM successfully ran but determined there are no operating startups ([]),
    # we respect that decision and do not trigger heuristics.
    if discovered_items is None:
        fallback_name = get_clean_startup_name(original_headline, None, source=startup.get("source"), source_url=startup.get("source_url"))
        if fallback_name:
            discovered_items = [{"name": fallback_name, "description": ""}]
            
    if not discovered_items:
        pipeline_log(f"Skipping generic/industry news article (no startup name extracted): '{original_headline}'")
        return None
        
    processed_results = []
    
    for item in discovered_items:
        name = item.get("name") if isinstance(item, dict) else item
        extracted_desc = item.get("description") if isinstance(item, dict) else ""
        
        clean_name = get_clean_startup_name(original_headline, name, source=startup.get("source"), source_url=startup.get("source_url"))
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
            "headline": original_headline,
            "description": original_description,
            "text_content": "\n\n".join(paragraphs) if paragraphs else original_description,
            "source": startup.get("source", "Unknown"),
            "source_url": startup.get("source_url", "")
        }
        
        # Cache Check: Check if startup already exists and has a fresh analysis
        existing_startup = check_existing_startup(clean_name)
        if existing_startup and os.getenv("FORCE_STARTUP_PIPELINE_RUN") != "true":
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
                        # Check global filters on cache hit first
                        match_ind = existing_startup.get("industry", "")
                        match_sec = existing_startup.get("sector", "")
                        match_sub = existing_startup.get("subsector", "")
                        
                        if industry_filter and (not match_ind or industry_filter.strip().lower() not in match_ind.strip().lower()):
                            pipeline_log(f"⚠️ Skipping cache hit '{clean_name}': industry '{match_ind}' does not match filter '{industry_filter}'")
                            continue
                        if sector_filter and (not match_sec or sector_filter.strip().lower() not in match_sec.strip().lower()):
                            pipeline_log(f"⚠️ Skipping cache hit '{clean_name}': sector '{match_sec}' does not match filter '{sector_filter}'")
                            continue
                        if subsector_filter and (not match_sub or subsector_filter.strip().lower() not in match_sub.strip().lower()):
                            pipeline_log(f"⚠️ Skipping cache hit '{clean_name}': subsector '{match_sub}' does not match filter '{subsector_filter}'")
                            continue
                            
                        existing_news = get_startup_news(startup_id) or []
                        news_summary = None
                        if is_news_duplicate(original_headline, original_description, existing_news, source_url=startup.get("source_url", "")):
                            pipeline_log(f"⏭️ Skipping duplicate news event for '{clean_name}': '{original_headline}'")
                        else:
                            pipeline_log(f"✅ Cache hit: '{clean_name}' already exists with a fresh analysis (created {age.days} days ago). Saving new news event.")
                            news_summary = extracted_desc or generate_news_summary(clean_name, original_headline, original_description)

                            # Save news snapshot even for cache hits — so news history accumulates
                            try:
                                save_startup_news(
                                    startup_id=startup_id,
                                    headline=original_headline,
                                    summary=news_summary,
                                    source=startup.get("source", ""),
                                    source_url=startup.get("source_url", ""),
                                    published_at=startup.get("published_at"),
                                    startup_mentions=[{"startup_name": item.get("name") if isinstance(item, dict) else item, "article_context": original_description[:500]} for item in discovered_items],
                                    raw_source_payload=startup,
                                    cleaned_source_payload={"headline": original_headline, "description": original_description, "summary": news_summary},
                                    pipeline_status={"stage": "CACHE_HIT", "completed_stages": ["DISCOVERY"]}
                                )
                                pipeline_log(f"📰 Saved news event for cache hit '{clean_name}'.")
                            except Exception as e:
                                pipeline_log(f"⚠️ Failed to save news event for cache hit '{clean_name}': {e}")

                        # Update description with the startup-specific summary
                        if news_summary:
                            try:
                                supabase.table("startups").update({"description": news_summary}).eq("id", startup_id).execute()
                                existing_startup["description"] = news_summary
                            except Exception as e:
                                pipeline_log(f"⚠️ Failed to update description for cache hit '{clean_name}': {e}")

                        # Check if funding data is stale (>60 days) — run Pass 3 if needed
                        funding_analysis_rec = analysis_resp.data[0] if analysis_resp.data else {}
                        last_funding_at_str = funding_analysis_rec.get("last_funding_enriched_at")
                        funding_stale = True
                        if last_funding_at_str:
                            try:
                                last_funding_at = dateutil.parser.isoparse(last_funding_at_str)
                                if last_funding_at.tzinfo is None:
                                    last_funding_at = last_funding_at.replace(tzinfo=timezone.utc)
                                funding_age_days = (datetime.now(timezone.utc) - last_funding_at).days
                                funding_stale = funding_age_days > 60
                            except Exception:
                                funding_stale = True
                        # Also stale if funding_rounds column is null or empty
                        existing_rounds = funding_analysis_rec.get("funding_rounds")
                        if not existing_rounds:
                            funding_stale = True

                        if funding_stale:
                            pipeline_log(f"💰 Funding data stale for '{clean_name}'. Running Pass 3 targeted enrichment...")
                            try:
                                funding_snippets = collect_funding_snippets(clean_name)
                                funding_data = extract_funding_rounds(clean_name, funding_snippets)
                                if funding_data:
                                    analysis_id = funding_analysis_rec.get("id")
                                    save_funding_rounds(startup_id, funding_data, analysis_id)
                                    pipeline_log(f"💰 Funding rounds updated for '{clean_name}'.")
                            except Exception as fe:
                                pipeline_log(f"⚠️ Pass 3 funding update failed for '{clean_name}': {fe}")

                        processed_results.append({
                            "startup": existing_startup,
                            "analysis": record.get("analysis_json") or {},
                            "summary": news_summary
                        })
                        continue
        
        # Step 2a: Generate a startup-specific news summary (fixes shared-description bug)
        if extracted_desc:
            news_summary = extracted_desc
            pipeline_log(f"Step 2a: Using pre-extracted news summary for '{clean_name}'...")
        else:
            pipeline_log(f"Step 2a: Generating startup-specific news summary for '{clean_name}'...")
            news_summary = generate_news_summary(clean_name, original_headline, original_description)
            
        startup_item["news_summary"] = news_summary
        pipeline_log(f"📰 News summary: {news_summary[:120]}...")

        # Step 2b: Run Sequential Multi-Agent Orchestration Pipeline
        pipeline_log("Step 2b: Running Sequential Multi-Agent Orchestrator...")
        try:
            from backend.workflows.agent_orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator()
            state = orchestrator.run_pipeline(startup_item, resolution_only=resolution_only)
            startup_id = state.startup_id
        except Exception as e:
            pipeline_log(f"❌ Multi-Agent Orchestrator failed for '{clean_name}'. Error: {e}")
            continue

        if not startup_id:
            pipeline_log(f"❌ Failed to persist startup '{clean_name}'.")
            continue

        # Post-enrichment filter check (read from state)
        industry = state.startup_features.industry
        sector = state.startup_features.sector
        subsector = state.startup_features.subsector

        if industry_filter and (not industry or industry_filter.strip().lower() not in industry.strip().lower()):
            pipeline_log(f"⚠️ Skipping '{clean_name}': industry '{industry}' does not match filter '{industry_filter}'")
            continue
        if sector_filter and (not sector or sector_filter.strip().lower() not in sector.strip().lower()):
            pipeline_log(f"⚠️ Skipping '{clean_name}': sector '{sector}' does not match filter '{sector_filter}'")
            continue
        if subsector_filter and (not subsector or subsector_filter.strip().lower() not in subsector.strip().lower()):
            pipeline_log(f"⚠️ Skipping '{clean_name}': subsector '{subsector}' does not match filter '{subsector_filter}'")
            continue

        # Step 3: Save news event to startup_news history table
        pipeline_log("Step 3: Saving news event to startup_news history...")
        try:
            existing_news = get_startup_news(startup_id) or []
            if is_news_duplicate(original_headline, original_description, existing_news, source_url=startup.get("source_url", "")):
                pipeline_log(f"⏭️ Skipping duplicate news event for new startup '{clean_name}': '{original_headline}'")
            else:
                raw_payload = {
                    "homepage_text": state.article_data.get("crawled_content", {}).get("homepage", {}).get("text_content", "") if isinstance(state.article_data.get("crawled_content"), dict) else "",
                    "about_page_text": state.article_data.get("crawled_content", {}).get("about", {}).get("text_content", "") if isinstance(state.article_data.get("crawled_content"), dict) else "",
                    "search_snippets": {
                        "identity_discovery": state.article_data.get("discovered_snippets", {}),
                        "funding_search": state.article_data.get("funding_search_context", ""),
                    }
                }
                cleaned_payload = {
                    "headline": original_headline,
                    "description": original_description,
                    "summary": news_summary,
                    "company_intelligence": state.article_data.get("company_intelligence", {}),
                }
                res_metadata = {
                    "canonical_startup_name": state.identity.get("brand_name", clean_name),
                    "website_url": state.identity.get("website", ""),
                    "linkedin_url": state.identity.get("linkedin_company_url", ""),
                    "confidence_scores": {
                        "identity_confidence": state.identity.get("identity_confidence", 0.0),
                    },
                    "resolution_method": state.identity.get("identity_source", ""),
                }
                p_status = {
                    "stage": "COMPLETED",
                    "completed_stages": ["DISCOVERY", "RESOLUTION", "ENRICHMENT"],
                    "errors": state.errors,
                }
                save_startup_news(
                    startup_id=startup_id,
                    headline=original_headline,
                    summary=news_summary,
                    source=startup.get("source", ""),
                    source_url=startup.get("source_url", ""),
                    published_at=startup.get("published_at"),
                    startup_mentions=[{"startup_name": item.get("name") if isinstance(item, dict) else item, "article_context": original_description[:500]} for item in discovered_items],
                    raw_source_payload=raw_payload,
                    cleaned_source_payload=cleaned_payload,
                    resolution_metadata=res_metadata,
                    pipeline_status=p_status
                )
                pipeline_log(f"📰 News event saved for '{clean_name}'.")
        except Exception as e:
            pipeline_log(f"⚠️ Failed to save news event for '{clean_name}': {e}")

        # Auto-assign FPRs
        try:
            from backend.api.routes.startups import assign_fprs_for_startup
            assign_fprs_for_startup(startup_id)
        except Exception as ae:
            pipeline_log(f"⚠️ Failed to auto-assign FPRs for '{clean_name}': {ae}")

        pipeline_log(f"✅ Successfully processed startup: {clean_name}")
        
        # Retrieve final saved rows to match returning type signature
        s_res = supabase.table("startups").select("*").eq("id", startup_id).execute()
        a_res = supabase.table("startup_analysis").select("*").eq("startup_id", startup_id).execute()
        processed_results.append({
            "startup": s_res.data[0] if s_res.data else {},
            "analysis": a_res.data[0].get("analysis_json") if a_res.data else {},
            "summary": news_summary
        })

    return processed_results if processed_results else None