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
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

TAXONOMY_PATH = "backend/config/startup_taxonomy.json"

class ClassificationAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Classification process...")
        
        try:
            # 1. Load taxonomy JSON
            taxonomy_str = "{}"
            if os.path.exists(TAXONOMY_PATH):
                with open(TAXONOMY_PATH, "r") as f:
                    taxonomy_str = f.read()
                    
            # 2. Get RAG context for sector classifications
            rag_context = get_rag_context(state.startup_name, category_filter="Knowledge", top_k=2)
            
            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/classification_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                taxonomy_str=taxonomy_str,
                rag_context=rag_context,
                headline=state.article_data.get('headline', ''),
                description=state.article_data.get('description', '')
            )
            classification = call_ollama(prompt, json_format=True)
            
            # 3. Populate state features
            state.startup_features.industry = classification.get("industry") or "Financial Services"
            state.startup_features.sector = classification.get("sector") or "Unknown"
            state.startup_features.subsector = classification.get("subsector") or "Unknown"
            state.startup_features.business_models = classification.get("business_models") or []
            state.startup_features.tags = classification.get("tags") or []
            
            # Store full classification under state metadata or logs
            self.log_audit(
                state, 
                f"Classified '{state.startup_name}' under Industry: '{state.startup_features.industry}', Sector: '{state.startup_features.sector}', Subsector: '{state.startup_features.subsector}'",
                metadata={
                    "classification": classification
                }
            )

        except Exception as e:
            state.errors.append(f"ClassificationAgent failed: {str(e)}")
            self.log_audit(state, f"ClassificationAgent failed: {str(e)}", metadata={"error": True})

        return state
