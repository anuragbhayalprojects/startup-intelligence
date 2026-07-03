# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.intelligence_enricher.IntelligenceEnricher
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

RELEVANCE_CONFIG_PATH = "backend/config/relevance_scoring.json"

class RelevanceAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Relevance Assessment...")
        
        try:
            # 1. Load relevance weights
            weights = {
                "strategic_relevance": 40,
                "deployability": 20,
                "traction": 15,
                "growth_signals": 10,
                "team_quality": 10,
                "funding_signals": 5
            }
            if os.path.exists(RELEVANCE_CONFIG_PATH):
                with open(RELEVANCE_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    weights = config.get("weights", weights)

            # 2. Get RAG context for relevance dimensions
            rag_context = get_rag_context(
                state.startup_name + " relevance scoring dimensions", 
                category_filter="Scoring", 
                top_k=2
            )

            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/relevance_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                rag_context=rag_context,
                sector=state.startup_features.sector,
                subsector=state.startup_features.subsector,
                business_problems=state.startup_features.business_problems,
                enriched_raw=state.article_data.get('enriched_raw', {}),
                description=state.article_data.get('description', '')
            )
            extraction = call_ollama(prompt, json_format=True)
            dimensions = extraction.get("dimensions", {})
            entity_relevance = extraction.get("entity_relevance", {})

            # 3. Calculate score deterministically in Python
            total_score = 0.0
            reasons = []
            breakdown = {}
            
            for key, weight in weights.items():
                dim_data = dimensions.get(key, {})
                dim_score = dim_data.get("score", 50)  # Default 50 if missing
                dim_reason = dim_data.get("reason", "No details provided.")
                
                total_score += (dim_score * (weight / 100.0))
                breakdown[key] = {
                    "score": dim_score,
                    "weight": weight,
                    "reason": dim_reason
                }
                if dim_score >= 70:
                    reasons.append(f"{key.replace('_', ' ').capitalize()}: {dim_reason}")

            relevance_score = int(round(total_score))
            
            # Gating rule: if no business problems were matched, cap final relevance score to 15
            if not state.startup_features.business_problems:
                relevance_score = min(relevance_score, 15)
                reasons = ["No ICICI Group business problems were matched by the agent."] + reasons

            # Update state features
            state.startup_features.deployability = "High" if dimensions.get("deployability", {}).get("score", 50) >= 80 else ("Medium" if dimensions.get("deployability", {}).get("score", 50) >= 40 else "Low")
            state.startup_features.market_validation = "High" if dimensions.get("traction", {}).get("score", 50) >= 80 else ("Medium" if dimensions.get("traction", {}).get("score", 50) >= 40 else "Low")
            state.startup_features.innovation = "High" if dimensions.get("strategic_relevance", {}).get("score", 50) >= 80 else ("Medium" if dimensions.get("strategic_relevance", {}).get("score", 50) >= 40 else "Low")

            # Update relevance dict
            state.relevance = {
                "score": relevance_score,
                "reasons": reasons[:4] if reasons else ["Completed relevance assessment."],
                "breakdown": breakdown,
                "entity_relevance": entity_relevance,
                "gating_bypassed": relevance_score < 20
            }


            self.log_audit(
                state,
                f"Calculated relevance score: {relevance_score} (Threshold check: {'Proceed' if relevance_score >= 20 else 'Gated/Ignore'})",
                metadata={
                    "relevance_score": relevance_score,
                    "breakdown": breakdown
                }
            )

        except Exception as e:
            state.errors.append(f"RelevanceAgent failed: {str(e)}")
            self.log_audit(state, f"RelevanceAgent failed: {str(e)}", metadata={"error": True})

        return state
