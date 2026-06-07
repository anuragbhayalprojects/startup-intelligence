import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

ACTION_CONFIG_PATH = "backend/config/action_framework.json"

class RecommendationAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Recommendation and Reach-out Generation...")
        
        try:
            # 1. Relevance Gate short-circuit
            relevance_score = state.relevance.get("score", 0)
            if relevance_score < 50:
                self.log_audit(state, "Relevance Score < 50: Deterministic gating set recommended action to 'Ignore / Monitor'")
                state.recommendation = {
                    "recommended_action": "Ignore / Monitor",
                    "target_teams": [],
                    "target_entities": [],
                    "use_cases": [],
                    "email_reachout_message": "",
                    "linkedin_reachout_message": ""
                }
                return state

            # 2. Get parameters for mapping
            fit_score = state.strategic_fit.get("score", 0)
            deployability = state.startup_features.deployability  # High, Medium, Low
            
            # Map fit score to band name
            if fit_score <= 30:
                fit_band = "Low"
            elif fit_score <= 70:
                fit_band = "Medium"
            elif fit_score <= 85:
                fit_band = "High"
            else:
                fit_band = "Very High"

            # 3. Mapped action via decision matrix
            recommended_action = "Monitor"
            matrix = [
                {"strategic_fit": "Low", "deployability": "Low", "action": "Ignore"},
                {"strategic_fit": "Medium", "deployability": "Low", "action": "Monitor"},
                {"strategic_fit": "Medium", "deployability": "Medium", "action": "Founder Meeting"},
                {"strategic_fit": "High", "deployability": "Medium", "action": "Business Introduction"},
                {"strategic_fit": "High", "deployability": "High", "action": "POC"},
                {"strategic_fit": "Very High", "deployability": "High", "action": "Strategic Investment Review"}
            ]
            
            if os.path.exists(ACTION_CONFIG_PATH):
                with open(ACTION_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    matrix = config.get("decision_matrix", matrix)

            for entry in matrix:
                if entry["strategic_fit"].lower() == fit_band.lower() and entry["deployability"].lower() == deployability.lower():
                    recommended_action = entry["action"]
                    break

            # 4. Request Ollama to generate reachout messages and use cases
            rag_context = get_rag_context(
                state.startup_name + " reachout message templates", 
                category_filter="Context", 
                top_k=1
            )

            prompt = f"""You are the ICICI CoE Reachout Copywriter.
Your job is to write a highly professional corporate reachout email and a short LinkedIn connection message for the startup '{state.startup_name}'.

The email should outline a proposed integration pilot/use case tailored to the startup's capabilities and matched business problems.
The LinkedIn message should be a warm, concise 2-sentence invitation to connect.

RAG Reference Context:
{rag_context}

Startup Details:
Sector: {state.startup_features.sector}
Subsector: {state.startup_features.subsector}
Matched Business Problems: {state.startup_features.business_problems}
Target Entities: {state.startup_features.relevant_entities}
Target Business Teams: {state.startup_features.business_teams}
Strategic Fit Score: {fit_score}

Create:
1. Proposed use cases list (each having 'use_case', 'icici_entity', and 'potential_impact').
2. An Email reachout draft with a subject line and body.
3. A LinkedIn connection message.

Return ONLY a valid JSON object matching the schema below. Do not add notes, wrappers, or explanations.

JSON Schema:
{{
  "use_cases": [
    {{
      "use_case": "Automated Claims underwriting pilot.",
      "icici_entity": "ICICI Lombard",
      "potential_impact": "Reduce turnaround time for claim processing."
    }}
  ],
  "email_reachout_message": {{
    "subject": "Proposed Collaboration: ICICI Group & [Startup Name]",
    "body": "Dear [Founder], we observed your solution in claims automation..."
  }},
  "linkedin_reachout_message": "Hello [Founder], I am reaching out from ICICI Group. I followed your company's progress and would love to connect."
}}
"""
            extraction = call_ollama(prompt, json_format=True)
            
            use_cases = extraction.get("use_cases", [])
            email_msg = extraction.get("email_reachout_message", {})
            linkedin_msg = extraction.get("linkedin_reachout_message", "")

            # If email_msg is dict, format it to string for DB columns compatibility
            if isinstance(email_msg, dict):
                email_text = f"Subject: {email_msg.get('subject', '')}\n\n{email_msg.get('body', '')}"
            else:
                email_text = str(email_msg)

            state.recommendation = {
                "recommended_action": recommended_action,
                "target_teams": state.startup_features.business_teams,
                "target_entities": state.startup_features.relevant_entities,
                "use_cases": use_cases,
                "email_reachout_message": email_text,
                "linkedin_reachout_message": linkedin_msg
            }

            self.log_audit(
                state,
                f"Completed recommendation mapping. Final action: '{recommended_action}'",
                metadata={
                    "recommended_action": recommended_action,
                    "target_teams": state.startup_features.business_teams,
                    "target_entities": state.startup_features.relevant_entities
                }
            )

        except Exception as e:
            state.errors.append(f"RecommendationAgent failed: {str(e)}")
            self.log_audit(state, f"RecommendationAgent failed: {str(e)}", metadata={"error": True})

        return state
