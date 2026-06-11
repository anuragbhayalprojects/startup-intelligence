import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

FIT_CONFIG_PATH = "backend/config/strategic_fit.json"

class StrategicFitAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        # Check relevance gate
        if state.relevance.get("score", 0) < 50:
            self.log_audit(state, "Skipping Strategic Fit Assessment (Relevance score < 50 gate applied)")
            return state
            
        self.log_audit(state, "Starting Strategic Fit Assessment...")
        
        try:
            # 1. Load strategic fit weights
            weights = {
                "business_problem_relevance": 25,
                "entity_alignment": 15,
                "business_team_alignment": 10,
                "deployability": 15,
                "market_validation": 10,
                "innovation_differentiation": 5,
                "scalability": 5,
                "strategic_investment_potential": 5,
                "ecosystem_influence": 5
            }
            if os.path.exists(FIT_CONFIG_PATH):
                with open(FIT_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    weights = config.get("weights", weights)

            # 2. Get RAG context for strategic fit
            rag_context = get_rag_context(
                state.startup_name + " strategic fit evaluation dimensions", 
                category_filter="Scoring", 
                top_k=3
            )

            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/strategic_fit_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                rag_context=rag_context,
                sector=state.startup_features.sector,
                subsector=state.startup_features.subsector,
                business_problems=state.startup_features.business_problems,
                relevance_breakdown=state.relevance.get('breakdown', {}),
                description=state.article_data.get('description', '')
            )
            extraction = call_ollama(prompt, json_format=True)
            dimensions = extraction.get("dimensions", {})

            # 3. Calculate score deterministically in Python
            weighted_sum = 0.0
            weight_total = sum(weights.values())
            breakdown = {}
            reasons = []

            for key, weight in weights.items():
                dim_data = dimensions.get(key, {})
                dim_score = dim_data.get("score", 50)  # Default 50 if missing
                dim_reason = dim_data.get("reason", "No details provided.")
                
                weighted_sum += (dim_score * weight)
                breakdown[key] = {
                    "score": dim_score,
                    "weight": weight,
                    "reason": dim_reason
                }
                if dim_score >= 80:
                    reasons.append(f"{key.replace('_', ' ').capitalize()}: {dim_reason}")

            # Normalize to 100
            final_score = int(round(weighted_sum / weight_total)) if weight_total > 0 else 0
            
            # Update state features
            state.startup_features.scalability = "High" if dimensions.get("scalability", {}).get("score", 50) >= 80 else ("Medium" if dimensions.get("scalability", {}).get("score", 50) >= 40 else "Low")
            state.startup_features.investment_potential = "High" if dimensions.get("strategic_investment_potential", {}).get("score", 50) >= 80 else ("Medium" if dimensions.get("strategic_investment_potential", {}).get("score", 50) >= 40 else "Low")

            state.strategic_fit = {
                "score": final_score,
                "breakdown": breakdown,
                "reasons": reasons[:4] if reasons else ["Completed strategic fit assessment."]
            }

            self.log_audit(
                state,
                f"Calculated Strategic Fit score: {final_score}",
                metadata={
                    "strategic_fit_score": final_score,
                    "breakdown": breakdown
                }
            )

        except Exception as e:
            state.errors.append(f"StrategicFitAgent failed: {str(e)}")
            self.log_audit(state, f"StrategicFitAgent failed: {str(e)}", metadata={"error": True})

        return state
