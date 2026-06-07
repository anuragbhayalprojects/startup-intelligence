import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

PROBLEMS_CONFIG_PATH = "backend/config/business_problems.json"

class BusinessProblemAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Business Problem Mapping...")
        
        try:
            # 1. Load active business problems config
            problems_data = {}
            if os.path.exists(PROBLEMS_CONFIG_PATH):
                with open(PROBLEMS_CONFIG_PATH, "r") as f:
                    problems_data = json.load(f)
            
            problems_list = problems_data.get("problems", [])
            problems_serialized = json.dumps(problems_list, indent=2)

            # 2. Get RAG context from the business problem files
            rag_context = get_rag_context(
                state.startup_name + " business problem mapping", 
                category_filter="Knowledge", 
                top_k=3
            )

            prompt = f"""You are the ICICI Business Problem Mapping Agent.
Your job is to identify which internal ICICI Bank or Group business problems are solved by the startup '{state.startup_name}'.

Here is the list of structured business problems:
{problems_serialized}

Here is additional RAG context regarding corporate challenges:
{rag_context}

Startup Details:
Sector: {state.startup_features.sector}
Subsector: {state.startup_features.subsector}
Headline: {state.article_data.get('headline', '')}
Summary: {state.article_data.get('description', '')}

Evaluate which business problems from the JSON list are directly addressed by this startup's core product/service.
CRITICAL CONSTRAINT: Do not make creative leaps to find remote relevance (e.g., matching a food recipe generator to customer intelligence, or a travel app to data leakage). Only match if the startup's core business matches. If none match, return empty business_problems and mappings.

For each match:
1. Provide the exact `problem_id`.
2. Extract the matching `entity` and `business_team`.
3. Provide a clear, factual explanation of how the startup resolves it.

Return ONLY a valid JSON object matching the schema below. Do not add notes, wrappers, or explanations.

JSON Schema:
{{
  "business_problems": ["problem_id_1", "problem_id_2"],
  "confidence": 0.85,
  "mappings": [
    {{
      "problem_id": "problem_id_1",
      "entity": "ICICI Bank",
      "business_team": "Retail Banking",
      "explanation": "Provides digital onboarding KYC to lower drop-off rates."
    }}
  ]
}}
"""
            result = call_ollama(prompt, json_format=True)
            
            # 3. Filter matched problems and mappings in Python to avoid hallucinations
            matched_problems = []
            valid_mappings = []
            
            raw_mappings = result.get("mappings", [])
            for m in raw_mappings:
                prob_id = m.get("problem_id")
                # Find problem config definition
                prob_cfg = next((p for p in problems_list if p["problem_id"] == prob_id), None)
                if prob_cfg:
                    allowed_cats = [cat.lower() for cat in prob_cfg.get("startup_categories", [])]
                    sect = state.startup_features.sector.lower()
                    sub = state.startup_features.subsector.lower()
                    
                    # Verify category compatibility (sub-string check)
                    is_valid = False
                    for cat in allowed_cats:
                        if cat in sect or sect in cat or cat in sub or sub in cat:
                            is_valid = True
                            break
                            
                    if is_valid:
                        matched_problems.append(prob_id)
                        valid_mappings.append(m)
                    else:
                        print(f"🚫 Discarding matched problem '{prob_id}' for startup '{state.startup_name}' due to category mismatch. Allowed: {allowed_cats}, Sector: '{sect}'")

            state.startup_features.business_problems = matched_problems
            
            # Extract target business teams and entities from mappings
            teams = []
            entities = []
            for m in valid_mappings:
                if m.get("business_team") and m["business_team"] not in teams:
                    teams.append(m["business_team"])
                if m.get("entity") and m["entity"] not in entities:
                    entities.append(m["entity"])
            
            state.startup_features.business_teams = teams
            state.startup_features.relevant_entities = entities
            
            self.log_audit(
                state,
                f"Mapped startup to {len(state.startup_features.business_problems)} business problems. Confidence: {result.get('confidence', 0.5)}",
                metadata={
                    "problem_mappings": valid_mappings,
                    "confidence": result.get('confidence', 0.0)
                }
            )

        except Exception as e:
            state.errors.append(f"BusinessProblemAgent failed: {str(e)}")
            self.log_audit(state, f"BusinessProblemAgent failed: {str(e)}", metadata={"error": True})

        return state
