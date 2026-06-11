import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

class MarketIntelligenceAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Market Intelligence Extraction...")

        try:
            # 1. Get RAG context for market intelligence
            rag_context = get_rag_context(
                state.startup_name + " market intelligence products competitors valuation", 
                category_filter="Knowledge", 
                top_k=2
            )

            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/market_intelligence_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                rag_context=rag_context,
                sector=state.startup_features.sector,
                subsector=state.startup_features.subsector,
                enriched_raw=state.article_data.get('enriched_raw', {}),
                description=state.article_data.get('description', '')
            )
            extraction = call_ollama(prompt, json_format=True)

            # Store results in the state's market_intelligence field
            state.market_intelligence = {
                "products": extraction.get("products", []),
                "competitors": extraction.get("competitors", []),
                "valuation": extraction.get("valuation", {}),
                "investors": extraction.get("investors", []),
                "strategic_positioning": extraction.get("strategic_positioning", "")
            }

            self.log_audit(
                state,
                f"Successfully extracted market intelligence details.",
                metadata={
                    "products_count": len(state.market_intelligence["products"]),
                    "competitors_count": len(state.market_intelligence["competitors"]),
                    "has_valuation": "Not Publicly" not in str(state.market_intelligence["valuation"].get("estimated_valuation"))
                }
            )

        except Exception as e:
            state.errors.append(f"MarketIntelligenceAgent failed: {str(e)}")
            self.log_audit(state, f"MarketIntelligenceAgent failed: {str(e)}", metadata={"error": True})

        return state
