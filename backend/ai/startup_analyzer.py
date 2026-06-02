import os
import requests
import json
from jinja2 import Template

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
        # if it looks like json, return it
        if content.startswith('{') and content.endswith('}'):
            return content

    # 3. Fallback: find the outermost curly braces
    first_brace = response_text.find('{')
    last_brace = response_text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return response_text[first_brace:last_brace+1].strip()

    return response_text.strip()

# --- Core Analysis Function ---

def analyze_startup(startup):
    """Analyzes a startup using a local LLM and returns structured JSON data."""
    if not OLLAMA_BASE_URL:
        return {"error": "Ollama server is not configured. Please set OLLAMA_BASE_URL."}

    # Fetch web search context
    startup_name = startup.get("startup_name", "")
    # Remove common action words if they reside in name (from crawler headlines)
    clean_name = startup_name.split(" raises ")[0].split(" acquires ")[0].split(" launches ")[0].strip()
    search_query = f"{clean_name} founders founding year series funding amount investors revenue ebitda multiple"
    
    try:
        from backend.utils.search import search_duckduckgo
        search_context = search_duckduckgo(search_query)
    except Exception as e:
        print(f"⚠️ [Startup Analyzer] Failed to perform web search: {e}")
        search_context = "No web search context available."

    # Load Master Taxonomy Schema JSON
    try:
        taxonomy_path = os.path.join(os.path.dirname(__file__), "../../docs/startup_sector_mappings.json")
        with open(taxonomy_path, "r") as tf:
            taxonomy_data = json.load(tf)
        taxonomy_str = json.dumps(taxonomy_data, indent=2)
    except Exception as te:
        print(f"⚠️ [Startup Analyzer] Failed to load taxonomy JSON: {te}")
        taxonomy_str = "{}"

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
                "stream": False
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

    try:
        result_text = response.json().get("response", "")
        cleaned_json_text = clean_llm_response(result_text)
        
        # Now, parse the cleaned text
        analysis_result = json.loads(cleaned_json_text)
        return analysis_result

    except json.JSONDecodeError as e:
        return {
            "error": "Failed to decode LLM response into JSON.",
            "original_response": result_text,
            "reason": str(e)
        }
    except Exception as e:
        return {"error": f"An unexpected error occurred during response processing: {str(e)}"}

# --- Example Usage ---

if __name__ == '__main__':
    mock_startup = {
        'startup_name': 'Fintech Innovations Inc.',
        'description': 'A company developing AI-driven solutions for fraud detection in digital payments.',
        'source': 'TechCrunch',
        'source_url': 'https://techcrunch.com/startup/fintech-innovations'
    }
    
    analysis = analyze_startup(mock_startup)
    
    print("--- Startup Analysis Complete ---")
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        if 'original_response' in analysis:
            print(f"Original LLM Response:\n{analysis['original_response']}")
    else:
        print(json.dumps(analysis, indent=2))
