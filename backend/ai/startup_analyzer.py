import json
import requests

from backend.utils.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL
)


def analyze_startup(startup):

    prompt = f"""
You are a startup investment analyst.

Analyze the following startup and return ONLY valid JSON.

Startup Name:
{startup.get("startup_name")}

Description:
{startup.get("description")}

Sector:
{startup.get("sector")}

Return JSON in this exact format:

{{
    "summary": "...",
    "business_model": "...",
    "market_size": "...",
    "funding_signal": "...",
    "investment_score": 0,
    "risk_score": 0,
    "tags": ["tag1", "tag2"],
    "key_strengths": [
        "...",
        "..."
    ],
    "key_risks": [
        "...",
        "..."
    ]
}}

IMPORTANT:
- Return ONLY valid JSON
- No markdown
- No explanation
- No extra text
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

    raw_text = result.get("response", "").strip()

    try:
        parsed_json = json.loads(raw_text)
        return parsed_json

    except Exception as e:

        print("JSON Parsing Failed")
        print(e)

        return {
            "summary": raw_text,
            "business_model": None,
            "market_size": None,
            "funding_signal": None,
            "investment_score": 0,
            "risk_score": 0,
            "tags": [],
            "key_strengths": [],
            "key_risks": []
        }