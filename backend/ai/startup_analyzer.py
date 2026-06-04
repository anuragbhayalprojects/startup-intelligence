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

def discover_startup_names(headline: str, description: str) -> list:
    """
    Pass 1: Analyzes news text/headline using local LLM to extract all startup names.
    Returns a list of clean startup name strings, or None if the analysis failed.
    """
    if not OLLAMA_BASE_URL:
        print("⚠️ [Startup Analyzer] Ollama base URL not set. Skipping Pass 1 name discovery.")
        return None
        
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/name_discovery_prompt.txt")
    try:
        with open(prompt_path, "r") as f:
            prompt_template = Template(f.read())
        prompt = prompt_template.render(headline=headline, description=description)
    except Exception as e:
        print(f"⚠️ [Startup Analyzer] Failed to load name discovery template: {e}")
        return None
        
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 4096
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=25.0
        )
        response.raise_for_status()
        result_text = response.json().get("response", "")
        cleaned_json = clean_llm_response(result_text)
        data = json.loads(cleaned_json)
        if isinstance(data, list):
            names = data
        elif isinstance(data, dict):
            names = data.get("extracted_startup_names", [])
        else:
            names = []
            
        if isinstance(names, list):
            clean_list = []
            for name in names:
                if isinstance(name, dict):
                    name = name.get("name") or name.get("startup_name") or (list(name.values())[0] if name.values() else None)
                if isinstance(name, str) and name.strip() and name.lower() != "none":
                    clean_list.append(name.strip())
            print(f"✨ [Pass 1] Extracted {len(clean_list)} startup names: {clean_list}")
            return clean_list
    except Exception as e:
        print(f"⚠️ [Pass 1] Name discovery prompt failed: {e}")
        
    return None

# --- Pass 2: Data Enrichment & Core Analysis Function ---

def build_filtered_query(startup_name: str, topic: str, website: str = "") -> str:
    """Builds a search query filtered by priority sources and website domain."""
    sources = load_priority_sources()
    site_filters = []
    for s in sources:
        domain = s.get("domain")
        if domain:
            site_filters.append(f"site:{domain}")
            
    filter_str = " OR ".join(site_filters)
    query = f"{startup_name} {topic}"
    if filter_str:
        query += f" ({filter_str})"
    if website:
        # Extract clean domain
        clean_domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if clean_domain:
            query += f" {clean_domain}"
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
    if not website:
        website_query = f"{clean_name} official website"
        print(f"🔍 [Phase 1] Searching for official website for: '{clean_name}'")
        try:
            website_snippets = search_duckduckgo(website_query)
        except Exception as e:
            print(f"⚠️ Website search failed: {e}")
            website_snippets = ""
    else:
        website_snippets = f"Verified official website retrieved: {website}"

    # 3. Phase 2: Search for founders (anchored with website URL and premium source filter)
    founders_query = build_filtered_query(clean_name, "founders co-founders LinkedIn", website)
    print(f"🔍 [Phase 2] Searching for founders: '{founders_query}'")
    try:
        founders_snippets = search_duckduckgo(founders_query)
    except Exception as e:
        print(f"⚠️ Founders search failed: {e}")
        founders_snippets = ""

    # 4. Phase 3: Search for funding and financials (anchored with website URL and premium source filter)
    funding_query = build_filtered_query(clean_name, "funding round valuation investors revenue", website)
    print(f"🔍 [Phase 3] Searching for funding: '{funding_query}'")
    try:
        funding_snippets = search_duckduckgo(funding_query)
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
        taxonomy_path = os.path.join(os.path.dirname(__file__), "../../docs/startup_sector_mappings.json")
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
            if "funding_stages" not in analysis_result:
                analysis_result["funding_stages"] = {}
            analysis_result["funding_stages"]["series"] = tracxn_profile["funding_stage"]
            analysis_result["funding_stages"]["amount"] = tracxn_profile["funding_amount"]
            
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
