import os
import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

def analyze_startup(startup):

    # Fallback if Ollama not available
    if not OLLAMA_BASE_URL:

        return {
            "summary": f"{startup.get('startup_name')} is a startup in the {startup.get('sector')} sector.",
            "investment_score": 50,
            "risk_level": "Medium",
            "tags": ["startup"]
        }

    prompt = f"""
    Analyze this startup:

    Name: {startup.get('startup_name')}
    Sector: {startup.get('sector')}
    Description: {startup.get('description')}

    Return:
    - summary
    - investment_score
    - risk_level
    - tags
    """

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()

    return {
        "summary": result.get("response", ""),
        "investment_score": 70,
        "risk_level": "Medium",
        "tags": ["ai-generated"]
    }