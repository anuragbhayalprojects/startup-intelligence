import os
import json
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class FundingIntelligenceAgent(BaseAgent):
    """
    Extracts optional funding stages, total raised, and top investors list.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[FundingIntelligenceAgent] Extracting optional funding history details...")
        
        search_snippets = ""
        snippets = state.article_data.get("discovered_snippets", {})
        for cat, records in snippets.items():
            for rec in records:
                if cat in ["news", "funding_sources"]:
                    search_snippets += f"- {rec.get('title')}: {rec.get('snippet')}\n"

        prompt_template = """You are an investment analyst. Look at the news article details and the web search snippets, and extract the latest funding round and history if present.

News Article:
Headline: {{ headline }}
Description: {{ description }}

Search Context:
{{ search_snippets }}

Identify total funding raised, latest round stage (Seed, Series A, etc), date, and key investors.
Return ONLY a valid JSON object matching the following structure:
{
  "total_funding": "$10M",
  "latest_round": "Seed",
  "latest_round_date": "2026-06",
  "investors": ["Investor A", "Investor B"],
  "funding_history": [
    {
      "round": "Seed",
      "amount": "$10M",
      "date": "2026-06",
      "investors": ["Investor A"]
    }
  ]
}
If no details are present, return empty strings or lists.
"""
        try:
            # Safe truncation to prevent context overflow/timeout
            search_snippets = search_snippets[:2000]
            prompt = Template(prompt_template).render(
                headline=state.article_data.get("headline") or state.article_data.get("startup_name") or "",
                description=state.article_data.get("description", ""),
                search_snippets=search_snippets
            )
            extracted = call_ollama(prompt, json_format=True)
            
            state.market_intelligence["funding"] = {
                "value": {
                    "total_funding": extracted.get("total_funding", ""),
                    "latest_round": extracted.get("latest_round", ""),
                    "latest_round_date": extracted.get("latest_round_date", ""),
                    "investors": extracted.get("investors", []),
                    "funding_history": extracted.get("funding_history", [])
                },
                "confidence": 95 if extracted.get("total_funding") else 30
            }
            
            latest_round = extracted.get("latest_round")
            if latest_round and latest_round.lower() not in ["", "unknown"]:
                state.startup_features.startup_stage = latest_round
                
            self.log_audit(state, f"Resolved total funding: {extracted.get('total_funding', 'Unknown')}, latest round: {state.startup_features.startup_stage}")
        except Exception as e:
            self.log_audit(state, f"Funding intelligence failed: {e}")
            
        return state
