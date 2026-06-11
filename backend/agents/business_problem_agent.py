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

            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/business_problem_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                problems_serialized=problems_serialized,
                rag_context=rag_context,
                sector=state.startup_features.sector,
                subsector=state.startup_features.subsector,
                headline=state.article_data.get('headline', ''),
                description=state.article_data.get('description', '')
            )
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

            # Fallback heuristic: if no problems matched/validated, check keywords directly
            if not valid_mappings:
                desc = state.article_data.get("description", "")
                for prob_cfg in problems_list:
                    prob_id = prob_cfg["problem_id"]
                    keywords = [kw.lower() for kw in prob_cfg.get("keywords", [])]
                    desc_lower = desc.lower()
                    name_lower = state.startup_name.lower()
                    
                    has_kw_match = any(kw in desc_lower or kw in name_lower for kw in keywords)
                    if has_kw_match:
                        allowed_cats = [cat.lower() for cat in prob_cfg.get("startup_categories", [])]
                        sect = state.startup_features.sector.lower()
                        sub = state.startup_features.subsector.lower()
                        
                        is_valid = False
                        for cat in allowed_cats:
                            if cat in sect or sect in cat or cat in sub or sub in cat:
                                is_valid = True
                                break
                                
                        if is_valid:
                            matched_problems.append(prob_id)
                            matching_kw = [kw for kw in keywords if kw in desc_lower or kw in name_lower][0]
                            valid_mappings.append({
                                "problem_id": prob_id,
                                "entity": prob_cfg.get("entity", "ICICI Bank"),
                                "business_team": prob_cfg.get("business_team", "Unknown"),
                                "explanation": f"Auto-matched via keyword correlation: '{matching_kw}'"
                            })

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
