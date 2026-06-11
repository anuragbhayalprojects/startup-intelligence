import os
import json
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class OpportunityMappingAgent(BaseAgent):
    """
    Designates matching use-cases and potential sandbox integrations across 
    ICICI Bank, ICICI Lombard, ICICI Securities, ICICI Prudential, and ICICI AMC.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[OpportunityMappingAgent] Designing ICICI Group sandbox integration opportunities...")
        
        desc = state.article_data.get("description", "")
        products_text = ""
        products_data = state.market_intelligence.get("products", {})
        if isinstance(products_data, dict) and products_data.get("value"):
            products_text = json.dumps(products_data["value"])

        prompt_template = """You are a strategic partnership head for ICICI Group.
Analyze the startup's details and generate specific co-creation or pilot integration opportunities for ICICI Group companies:
- ICICI Bank (Retail, Corporate, SME banking)
- ICICI Lombard (General insurance)
- ICICI Securities (Wealth, trading, equity)
- ICICI Prudential AMC (Asset management)
- ICICI Prudential Life (Life insurance)
- ICICI HFC (Home finance)

Description:
{{ description }}

Products:
{{ products_text }}

Your response should contain concrete, feasible opportunities. Return ONLY a valid JSON object matching the following structure:
{
  "opportunity_mapping": [
    {
      "icici_entity": "Must be EXACTLY one of: ICICI Bank, ICICI Lombard, ICICI Securities, ICICI Prudential AMC, ICICI Prudential Life, ICICI HFC",
      "use_case": "Explain the sandbox integration pilot",
      "potential_impact": "Describe business impact (High/Medium/Low with rationale)",
      "relevance_score": 85
    }
  ]
}
"""
        try:
            prompt = Template(prompt_template).render(
                description=desc,
                products_text=products_text
            )
            extracted = call_ollama(prompt, json_format=True)
            
            state.market_intelligence["opportunity_mapping"] = {
                "value": extracted.get("opportunity_mapping", []),
                "confidence": 90
            }
            
            # Populate relevant entities lists in features
            entities = list(set([o.get("icici_entity") for o in extracted.get("opportunity_mapping", []) if o.get("icici_entity")]))
            state.startup_features.relevant_entities = entities
            
            self.log_audit(state, f"Mapped {len(entities)} strategic opportunities.")
        except Exception as e:
            self.log_audit(state, f"Opportunity mapping failed: {e}")
            
        return state
