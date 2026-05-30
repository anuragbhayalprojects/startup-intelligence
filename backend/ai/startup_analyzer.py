import os
import requests
import json
from jinja2 import Template

# --- Constants ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
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
    # Find the start and end of the JSON block
    json_start = response_text.find('```json')
    json_end = response_text.rfind('```')

    if json_start != -1:
        # Adjust start position to be after the ```json marker
        json_start += 7
        if json_end > json_start:
            response_text = response_text[json_start:json_end]

    # Basic cleaning
    return response_text.strip()

# --- Core Analysis Function ---

def analyze_startup(startup):
    """Analyzes a startup using a local LLM and returns structured JSON data."""
    if not OLLAMA_BASE_URL:
        return {"error": "Ollama server is not configured. Please set OLLAMA_BASE_URL."}

    try:
        prompt_template = load_prompt_template()
        prompt = prompt_template.render(startup=startup)
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
