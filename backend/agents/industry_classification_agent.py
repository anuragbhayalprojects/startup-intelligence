# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.product_enricher.ProductEnricher
# as part of the modular enrichment refactor (feature/modular-company-intelligence-refactor).
#
# STATUS: Removed from AgentOrchestrator execution path. Retained for:
#   - Regression comparison during migration safety period
#   - Import compatibility with any external scripts still using this class
#
# DO NOT extend or add new logic here. Use the replacement module above.
# This file will be removed after migration safety period ends.
# =============================================================================
import os
import json
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class IndustryClassificationAgent(BaseAgent):
    """
    Classifies the startup strictly into the taxonomy framework (Industry, Sector, Subsector)
    provided in the taxonomy mapping JSON.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[IndustryClassificationAgent] Mapping startup to master taxonomy...")
        
        # Load startup taxonomy config context
        tax_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "startup_taxonomy.json")
        try:
            with open(tax_path, "r") as f:
                taxonomy = json.load(f)
                taxonomy_context = json.dumps(taxonomy, indent=2)
        except Exception:
            taxonomy_context = "{}"
            
        desc = state.article_data.get("description", "")
        products_text = ""
        products_data = state.market_intelligence.get("products", {})
        if isinstance(products_data, dict) and products_data.get("value"):
            products_text = json.dumps(products_data["value"])

        prompt_template = """You are a taxonomy mapping analyst on the Startup Engagement and Investment Team. Your goal is to map the company to the allowed master taxonomy to keep our deal flow pipeline categorized.

Startup Details:
Startup Name: {{ startup_name }}
News Article Headline: {{ headline }}

Master Taxonomy Options:
{{ taxonomy_context }}

Company Description:
{{ description }}

Company Products/Services:
{{ products_text }}

Your response must strictly match the taxonomy options. Do not make up industries, sectors, or subsectors.
Return ONLY a valid JSON object matching this structure:
{
  "industry": "Clean industry matching taxonomy",
  "sector": "Clean sector matching taxonomy",
  "subsector": "Clean subsector matching taxonomy",
  "confidence": 95
}
"""
        try:
            prompt = Template(prompt_template).render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                taxonomy_context=taxonomy_context,
                description=desc,
                products_text=products_text
            )
            classification = call_ollama(prompt, json_format=True) or {}
            
            from backend.utils.taxonomy_mapper import normalize_taxonomy
            
            raw_ind = classification.get("industry", "Unknown")
            raw_sec = classification.get("sector", "Unknown")
            raw_sub = classification.get("subsector", "Unknown")
            
            normalized_ind, normalized_sec, normalized_sub = normalize_taxonomy(
                state.startup_name, raw_ind, raw_sec, raw_sub, context_text=desc
            )
            
            state.startup_features.industry = normalized_ind
            state.startup_features.sector = normalized_sec
            state.startup_features.subsector = normalized_sub
            
            state.market_intelligence["industry_classification"] = {
                "value": {
                    "industry": normalized_ind,
                    "sector": normalized_sec,
                    "subsector": normalized_sub
                },
                "confidence": classification.get("confidence", 80)
            }
            self.log_audit(state, f"Mapped industry classification to {normalized_sec} > {normalized_sub}")
        except Exception as e:
            self.log_audit(state, f"Failed industry classification: {e}")
            
        return state
