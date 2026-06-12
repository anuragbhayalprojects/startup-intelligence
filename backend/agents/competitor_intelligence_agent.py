import os
import json
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class CompetitorIntelligenceAgent(BaseAgent):
    """
    Identifies and validates competitors using search snippets and company product context.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[CompetitorIntelligenceAgent] Pinpointing direct competitors...")
        
        desc = state.article_data.get("description", "")
        products_text = ""
        products_data = state.market_intelligence.get("products", {})
        if isinstance(products_data, dict) and products_data.get("value"):
            products_text = json.dumps(products_data["value"])

        # Fetch search snippets query for competitors
        search_snippets = ""
        snippets = state.article_data.get("discovered_snippets", {})
        for cat, records in snippets.items():
            for rec in records:
                search_snippets += f"- {rec.get('title')}: {rec.get('snippet')}\n"

        prompt_template = """You are a senior analyst on the Startup Engagement and Investment Team. Analyze the business details and product offerings of the startup, and identify direct competitors to evaluate market position and differentiators.

Startup Details:
Startup Name: {{ startup_name }}
News Article Headline: {{ headline }}

Startup Description:
{{ description }}

Products:
{{ products_text }}

Search snippets context:
{{ search_snippets }}

Identify the top 3 direct competitors.
Return ONLY a valid JSON object matching the following structure:
{
  "competitors": [
    {
      "name": "Competitor Brand Name",
      "website": "https://competitor.com",
      "reason": "Explain similarity and overlap",
      "confidence": 85,
      "evidence_url": "Source link or homepage"
    }
  ]
}
"""
        try:
            prompt = Template(prompt_template).render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                description=desc,
                products_text=products_text,
                search_snippets=search_snippets
            )
            extracted = call_ollama(prompt, json_format=True)
            
            state.market_intelligence["competitors"] = {
                "value": extracted.get("competitors", []),
                "confidence": 80
            }
            self.log_audit(state, f"Identified {len(extracted.get('competitors', []))} direct competitors.")
        except Exception as e:
            self.log_audit(state, f"Competitor intelligence failed: {e}")
            
        return state
