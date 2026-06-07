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

            prompt = f"""You are the ICICI Relevance Feature Extractor.
Your job is to assess the relevance parameters for the startup '{state.startup_name}'.

First, evaluate these six specific scoring dimensions on a scale of 0 to 100 based on the startup details:
1. Strategic Relevance: How well the startup aligns with BFSI or ICICI target business problems.
2. Deployability: Enterprise readiness, API maturity, and integration feasibility.
3. Traction: Customer count, partnerships, and market presence.
4. Growth Signals: Rapid scaling, hiring, or expansion.
5. Team Quality: Experience of founders (e.g., pedigree, domain expertise).
6. Funding Signals: Recent capital raised and quality of venture investors.

Second, evaluate individual relevance scores (0 to 100) for each of the following six ICICI Group companies:
- ICICI Bank
- ICICI Lombard
- ICICI Securities
- ICICI Prudential AMC
- ICICI Prudential Life
- ICICI HFC

RAG Reference Context:
{rag_context}

Startup Details:
Sector: {state.startup_features.sector}
Subsector: {state.startup_features.subsector}
Matched Business Problems: {state.startup_features.business_problems}
Enriched Website / Details: {state.article_data.get('enriched_raw', {})}
Description: {state.article_data.get('description', '')}

For each dimension, extract/estimate a raw feature score (0 to 100) and provide a concise, factual explanation for the score. Do not calculate the final weighted score.
For each ICICI entity, assign a relevance score (0 to 100) based on how directly its business model applies to that specific entity.

Return ONLY a valid JSON object matching the schema below. Do not add notes, wrappers, or explanations.

JSON Schema:
{{
  "dimensions": {{
    "strategic_relevance": {{ "score": 85, "reason": "Aligns directly with lending credit risk problem." }},
    "deployability": {{ "score": 60, "reason": "Requires moderate custom integration API work." }},
    "traction": {{ "score": 70, "reason": "Has 10+ paying corporate customers." }},
    "growth_signals": {{ "score": 80, "reason": "Recently opened new regional offices." }},
    "team_quality": {{ "score": 75, "reason": "Founders have previous technical startup exits." }},
    "funding_signals": {{ "score": 90, "reason": "Backed by tier-1 institutional investors." }}
  }},
  "entity_relevance": {{
    "ICICI Bank": 85,
    "ICICI Lombard": 40,
    "ICICI Securities": 30,
    "ICICI Prudential AMC": 0,
    "ICICI Prudential Life": 0,
    "ICICI HFC": 0
  }}
}}
"""
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
            
            # Gating rule: if no business problems were matched, cap final relevance score to 25
            if not state.startup_features.business_problems:
                relevance_score = min(relevance_score, 25)
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
                "gating_bypassed": relevance_score < 50
            }


            self.log_audit(
                state,
                f"Calculated relevance score: {relevance_score} (Threshold check: {'Proceed' if relevance_score >= 50 else 'Gated/Ignore'})",
                metadata={
                    "relevance_score": relevance_score,
                    "breakdown": breakdown
                }
            )

        except Exception as e:
            state.errors.append(f"RelevanceAgent failed: {str(e)}")
            self.log_audit(state, f"RelevanceAgent failed: {str(e)}", metadata={"error": True})

        return state
