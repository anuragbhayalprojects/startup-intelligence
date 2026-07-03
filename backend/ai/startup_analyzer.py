import os
import requests
import json
from jinja2 import Template
from backend.utils.search import load_priority_sources, search_duckduckgo
from backend.services.tracxn_service import fetch_tracxn_startup_data

# --- Constants ---
try:
    from backend.utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL
except ImportError:
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../prompts/detailed_analysis_prompt.txt")
FUNDING_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../prompts/funding_extraction_prompt.txt")
FUNDING_SOURCES_PATH = os.path.join(os.path.dirname(__file__), "../config/funding_sources.json")

# --- Utility Functions ---

def load_prompt_template():
    """Loads the analysis prompt from the specified file."""
    try:
        with open(PROMPT_PATH, "r") as f:
            return Template(f.read())
    except FileNotFoundError:
        raise RuntimeError(f"Prompt file not found at {PROMPT_PATH}")

def clean_llm_response(response_text):
    """Cleans the LLM's response to extract the core JSON object."""
    if not response_text:
        return ""
        
    # 1. Try finding ```json block first
    json_start = response_text.find('```json')
    json_end = response_text.rfind('```')

    if json_start != -1:
        json_start += 7
        if json_end > json_start:
            return response_text[json_start:json_end].strip()

    # 2. Try finding raw ``` block
    raw_start = response_text.find('```')
    raw_end = response_text.rfind('```')
    if raw_start != -1 and raw_end > raw_start:
        content = response_text[raw_start+3:raw_end].strip()
        if content.startswith('{') and content.endswith('}'):
            return content

    # 3. Fallback: find the outermost curly braces
    first_brace = response_text.find('{')
    last_brace = response_text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return response_text[first_brace:last_brace+1].strip()

    return response_text.strip()

# --- Pass 1: Name Discovery ---

def discover_startup_names(headline: str, paragraphs) -> list[dict]:
    """
    Pass 1: Analyzes news text/headline using local LLM to extract all startup names and descriptions.
    Returns a list of dicts, each with keys 'name' and 'description', or None if analysis failed.
    """
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    elif not isinstance(paragraphs, list):
        paragraphs = []

    if not OLLAMA_BASE_URL:
        print("⚠️ [Startup Analyzer] Ollama base URL not set. Skipping Pass 1 name discovery.")
        return None
        
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/name_discovery_prompt.txt")
    try:
        with open(prompt_path, "r") as f:
            prompt_template = Template(f.read())
        p1 = paragraphs[0] if len(paragraphs) > 0 else ""
        p2 = paragraphs[1] if len(paragraphs) > 1 else ""
        # Join all remaining paragraphs beyond the second one into paragraph_3
        p3 = "\n\n".join(paragraphs[2:]) if len(paragraphs) > 2 else ""
        prompt = prompt_template.render(headline=headline, paragraph_1=p1, paragraph_2=p2, paragraph_3=p3)
    except Exception as e:
        print(f"⚠️ [Startup Analyzer] Failed to load name discovery template: {e}")
        return None
        
    try:
        from backend.ai.router import call_ai
        data = call_ai(prompt, task="extraction", json_format=True)
        
        startups = []
        if isinstance(data, dict):
            startups = data.get("startups") or data.get("extracted_startup_names") or []
        elif isinstance(data, list):
            startups = data
            
        clean_list = []
        for item in startups:
            if isinstance(item, dict):
                name = item.get("name") or item.get("startup_name")
                desc = item.get("description") or item.get("summary") or ""
            elif isinstance(item, str):
                name = item
                desc = ""
            else:
                continue
                
            if isinstance(name, str) and name.strip() and name.lower() != "none":
                clean_list.append({
                    "name": name.strip(),
                    "description": desc.strip()
                })
                
        print(f"✨ [Pass 1] Extracted {len(clean_list)} startups: {[item['name'] for item in clean_list]}")
        return clean_list
    except Exception as e:
        print(f"⚠️ [Pass 1] Name discovery failed: {e}")
        
    return None

# --- News Summary: Startup-Specific News Snippet Generation ---

def generate_news_summary(startup_name: str, headline: str, description: str) -> str:
    """
    Generates a 2-3 sentence news summary specifically about the named startup
    from the given article headline and description.
    Used before Pass 2 to give each startup an isolated, grounded description.
    Returns a plain-text summary string, or an empty string on failure.
    """
    if not OLLAMA_BASE_URL:
        return description  # Fallback: use raw description if Ollama is unavailable

    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/news_summary_prompt.txt")
    try:
        with open(prompt_path, "r") as f:
            prompt_template = Template(f.read())
        prompt = prompt_template.render(
            startup_name=startup_name,
            headline=headline,
            description=description
        )
    except Exception as e:
        print(f"⚠️ [News Summary] Failed to load news summary template: {e}")
        return description

    try:
        from backend.ai.router import call_ai
        summary = call_ai(prompt, task="news_summary", json_format=False)
        if summary and len(summary) > 20:
            print(f"📰 [News Summary] Generated for '{startup_name}': {summary[:100]}...")
            return summary
    except Exception as e:
        print(f"⚠️ [News Summary] Generation failed for '{startup_name}': {e}")

    # Fallback: Truncate to first 3 sentences of raw description for a brief summary
    import re
    if description:
        sentences = re.split(r'(?<=[.!?])\s+', description.strip())
        fallback_summary = " ".join(sentences[:3])
        return fallback_summary
    return description or ""


# --- Pass 3: Dedicated Funding Enrichment ---

def _load_funding_sources() -> dict:
    """Loads the funding_sources.json config. Returns empty dict on failure."""
    try:
        with open(FUNDING_SOURCES_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [Pass 3] Failed to load funding_sources.json: {e}")
        return {}


def build_funding_queries(startup_name: str, website: str = "") -> list:
    """
    Builds multiple tiered DDG search queries for funding data,
    ordered by source priority from funding_sources.json.
    Returns a list of query strings.
    """
    config = _load_funding_sources()
    sources = sorted(config.get("sources", []), key=lambda s: s.get("priority", 99))
    keywords = config.get("fallback_query_keywords", ["funding", "investors", "raised"])

    queries = []
    # Tier 1: India-first sources in pairs
    for i in range(0, len(sources), 2):
        pair = sources[i:i+2]
        site_filter = " OR ".join(f"site:{s['domain']}" for s in pair)
        queries.append(f'"{startup_name}" funding raised investors ({site_filter})')

    # Tier 2: Generic fallback
    kw_str = " ".join(keywords[:4])
    queries.append(f'"{startup_name}" {kw_str}')

    return queries


def collect_funding_snippets(startup_name: str, website: str = "") -> str:
    """
    Runs tiered DDG queries and aggregates funding search snippets.
    Stops early when sufficient context is collected (max_snippets_chars from config).
    Returns combined plain-text snippets.
    """
    config = _load_funding_sources()
    max_chars = config.get("max_snippets_chars", 2000)
    timeout = config.get("query_timeout_seconds", 12)

    queries = build_funding_queries(startup_name, website)
    all_snippets = []
    total_chars = 0

    for query in queries:
        if total_chars >= max_chars:
            break
        try:
            print(f"💰 [Pass 3] Funding search: '{query[:80]}...'")
            snippets = search_duckduckgo(query)
            if snippets:
                all_snippets.append(snippets)
                total_chars += len(snippets)
        except Exception as e:
            print(f"⚠️ [Pass 3] Funding query failed: {e}")
            continue

    combined = "\n\n".join(all_snippets)
    print(f"💰 [Pass 3] Collected {len(combined)} chars of funding context for '{startup_name}'")
    return combined


def extract_funding_rounds(startup_name: str, funding_snippets: str) -> dict:
    """
    Pass 3: Runs a dedicated lightweight LLM call to extract structured
    funding round data from the collected search snippets.
    Returns a dict: {rounds: [...], total_funding: str, latest_stage: str, latest_date: str}
    """
    if not OLLAMA_BASE_URL:
        return {}
    if not funding_snippets or len(funding_snippets.strip()) < 50:
        print(f"⚠️ [Pass 3] Insufficient funding snippets for '{startup_name}'. Skipping LLM call.")
        return {}

    try:
        with open(FUNDING_PROMPT_PATH, "r") as f:
            prompt_template = Template(f.read())
        prompt = prompt_template.render(
            startup_name=startup_name,
            funding_search_context=funding_snippets
        )
    except Exception as e:
        print(f"⚠️ [Pass 3] Failed to load funding extraction template: {e}")
        return {}

    try:
        from backend.ai.router import call_ai
        data = call_ai(prompt, task="enrichment_funding", json_format=True)
        rounds = data.get("rounds", []) if isinstance(data, dict) else []
        print(f"💰 [Pass 3] Extracted {len(rounds)} funding round(s) for '{startup_name}'")
        return data
    except Exception as e:
        print(f"⚠️ [Pass 3] Funding extraction failed for '{startup_name}': {e}")
        return {}



def build_filtered_query(startup_name: str, topic: str, website: str = "") -> str:
    """Builds a search query filtered by priority sources and website domain."""
    sources = load_priority_sources()
    site_filters = []
    for s in sources:
        domain = s.get("domain")
        if domain:
            site_filters.append(f"site:{domain}")
            
    if website:
        # Extract clean domain and insert it as the first site restrict filter
        clean_domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if clean_domain:
            site_filters.insert(0, f"site:{clean_domain}")
            
    filter_str = " OR ".join(site_filters)
    query = f'"{startup_name}" {topic}'
    if filter_str:
        query += f" ({filter_str})"
    return query

def analyze_startup(startup):
    """
    Pass 2: Analyzes a startup using local LLM with targeted multi-phase web search
    snippets context and returns structured JSON data.
    """
    if not OLLAMA_BASE_URL:
        return {"error": "Ollama server is not configured. Please set OLLAMA_BASE_URL."}

    startup_name = startup.get("startup_name", "")
    clean_name = startup_name.split(" raises ")[0].split(" acquires ")[0].split(" launches ")[0].strip()
    
    # 1. Fetch Tracxn verified profile first
    tracxn_profile = fetch_tracxn_startup_data(clean_name)
    website = tracxn_profile.get("website", "")
    
    # 2. Phase 1: Search for official website if not found in Tracxn
    from backend.utils.search import load_search_queries
    config = load_search_queries()
    analyzer_cfg = config.get("startup_analyzer", {})
    if not website:
        website_query_tmpl = analyzer_cfg.get("website_query", "{clean_name} official website")
        website_query = website_query_tmpl.format(clean_name=clean_name)
        print(f"🔍 [Phase 1] Searching for official website for: '{clean_name}'")
        try:
            website_snippets = search_duckduckgo(website_query)
        except Exception as e:
            print(f"⚠️ Website search failed: {e}")
            website_snippets = ""
    else:
        website_snippets = f"Verified official website retrieved: {website}"

    # 3. Phase 2: Search for founders (anchored with website URL and premium source filter)
    founders_base = analyzer_cfg.get("founders_query_base", "founders co-founders LinkedIn")
    founders_query = build_filtered_query(clean_name, founders_base, website)
    print(f"🔍 [Phase 2] Searching for founders: '{founders_query}'")
    try:
        founders_snippets = search_duckduckgo(founders_query)
        if not founders_snippets or "No search results" in founders_snippets or "Could not perform web search" in founders_snippets:
            print(f"🔄 [Phase 2] Broad search fallback for founders of: '{clean_name}'")
            fallback_tmpl = analyzer_cfg.get("founders_fallback", '"{clean_name}" founders OR co-founders')
            founders_snippets = search_duckduckgo(fallback_tmpl.format(clean_name=clean_name))
    except Exception as e:
        print(f"⚠️ Founders search failed: {e}")
        founders_snippets = ""

    # 4. Phase 3: Search for funding and financials (anchored with website URL and premium source filter)
    funding_base = analyzer_cfg.get("funding_query_base", "funding round valuation investors revenue")
    funding_query = build_filtered_query(clean_name, funding_base, website)
    print(f"🔍 [Phase 3] Searching for funding: '{funding_query}'")
    try:
        funding_snippets = search_duckduckgo(funding_query)
        if not funding_snippets or "No search results" in funding_snippets or "Could not perform web search" in funding_snippets:
            print(f"🔄 [Phase 3] Broad search fallback for funding of: '{clean_name}'")
            fallback_tmpl = analyzer_cfg.get("funding_fallback", '"{clean_name}" funding round valuation investors')
            funding_snippets = search_duckduckgo(fallback_tmpl.format(clean_name=clean_name))
    except Exception as e:
        print(f"⚠️ Funding search failed: {e}")
        funding_snippets = ""

    # Combine snippets into single formatted search context
    search_context = (
        f"=== WEBSITE SEARCH CONTEXT ===\n{website_snippets}\n\n"
        f"=== FOUNDERS & LEADERSHIP SEARCH CONTEXT ===\n{founders_snippets}\n\n"
        f"=== FUNDING & METRICS SEARCH CONTEXT ===\n{funding_snippets}\n\n"
    )

    # 5. Load Master Taxonomy Schema JSON
    try:
        taxonomy_path = os.path.join(os.path.dirname(__file__), "../config/startup_sector_mappings.json")
        with open(taxonomy_path, "r") as tf:
            taxonomy_data = json.load(tf)
        taxonomy_str = json.dumps(taxonomy_data, indent=2)
    except Exception as te:
        print(f"⚠️ [Startup Analyzer] Failed to load taxonomy JSON: {te}")
        taxonomy_str = "{}"

    # 6. Render prompts and run Ollama inference
    try:
        prompt_template = load_prompt_template()
        prompt = prompt_template.render(
            startup=startup, 
            search_context=search_context,
            taxonomy_context=taxonomy_str
        )
    except Exception as e:
        return {"error": f"Failed to render prompt template: {str(e)}"}

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 8192
                }
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

    try:
        result_text = response.json().get("response", "")
        cleaned_json_text = clean_llm_response(result_text)
        analysis_result = json.loads(cleaned_json_text)
        
        # Inject verified details from Tracxn directly if found
        if tracxn_profile:
            if "extracted_startup_name" not in analysis_result or analysis_result["extracted_startup_name"] == "None":
                analysis_result["extracted_startup_name"] = tracxn_profile["startup_name"]
            analysis_result["startup_website"] = tracxn_profile["website"]
            analysis_result["founded_year"] = tracxn_profile["founded_year"]
            if tracxn_profile["founders"]:
                analysis_result["founders"] = tracxn_profile["founders"]

        # --- Pass 3: Dedicated Funding Enrichment ---
        print(f"\n💰 [Pass 3] Starting dedicated funding enrichment for '{clean_name}'...")
        funding_snippets = collect_funding_snippets(clean_name, website)
        funding_data = extract_funding_rounds(clean_name, funding_snippets)

        if funding_data and funding_data.get("rounds"):
            # Merge rich funding data into the analysis result
            analysis_result["funding_rounds"] = funding_data.get("rounds", [])
            analysis_result["total_funding"] = funding_data.get("total_funding", "")
            analysis_result["latest_stage"] = funding_data.get("latest_stage", "")
            analysis_result["latest_funding_date"] = funding_data.get("latest_date", "")
            # Keep backward-compat funding_stages using Pass 3 data
            rounds = funding_data["rounds"]
            latest = rounds[0] if rounds else {}
            all_investors = []
            for r in rounds:
                if r.get("lead_investor"):
                    all_investors.append(r["lead_investor"])
                all_investors.extend(r.get("co_investors", []))
            analysis_result["funding_stages"] = {
                "series": latest.get("stage", ""),
                "amount": funding_data.get("total_funding", ""),
                "investors": list(dict.fromkeys(all_investors))  # deduplicated
            }
            print(f"💰 [Pass 3] Merged {len(rounds)} round(s) into analysis for '{clean_name}'")
        elif tracxn_profile:
            # Fallback: use Tracxn flat data if Pass 3 found nothing
            analysis_result.setdefault("funding_stages", {})
            analysis_result["funding_stages"]["series"] = tracxn_profile.get("funding_stage", "")
            analysis_result["funding_stages"]["amount"] = tracxn_profile.get("funding_amount", "")
            analysis_result["funding_rounds"] = []
            print(f"💰 [Pass 3] No rounds found — using Tracxn flat data as fallback.")
        else:
            analysis_result["funding_rounds"] = []

        return analysis_result

    except json.JSONDecodeError as e:
        return {
            "error": "Failed to decode LLM response into JSON.",
            "original_response": result_text,
            "reason": str(e)
        }
    except Exception as e:
        return {"error": f"An unexpected error occurred during response processing: {str(e)}"}

if __name__ == '__main__':
    mock_startup = {
        'startup_name': 'Fintech Innovations Inc.',
        'description': 'A company developing AI-driven solutions for fraud detection in digital payments.',
        'source': 'TechCrunch',
        'source_url': 'https://techcrunch.com/startup/fintech-innovations'
    }
    
    analysis = analyze_startup(mock_startup)
    print("--- Startup Analysis Complete ---")
    print(json.dumps(analysis, indent=2))
