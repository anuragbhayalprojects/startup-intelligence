import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

SIGNAL_CONFIG_PATH = "backend/config/startup_signal_framework.json"

class SignalAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        # Check relevance gate
        if state.relevance.get("score", 0) < 50:
            self.log_audit(state, "Skipping Signal Assessment (Relevance score < 50 gate applied)")
            return state
            
        self.log_audit(state, "Starting Momentum Signal Detection...")
        
        try:
            # 1. Load signal framework weights
            framework = {
                "positive_signals": {
                    "enterprise_customer_wins": 10,
                    "revenue_growth": 10,
                    "product_adoption": 9,
                    "strategic_partnerships": 9,
                    "geographic_expansion": 8,
                    "leadership_hiring": 7,
                    "funding_round": 6,
                    "accelerator_participation": 5,
                    "patent_activity": 5,
                    "awards_recognition": 3
                },
                "negative_signals": {
                    "leadership_exits": -5,
                    "layoffs": -6,
                    "regulatory_issues": -9,
                    "product_failure": -8,
                    "major_customer_loss": -8,
                    "data_breach": -10
                }
            }
            if os.path.exists(SIGNAL_CONFIG_PATH):
                with open(SIGNAL_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    framework["positive_signals"] = config.get("positive_signals", framework["positive_signals"])
                    framework["negative_signals"] = config.get("negative_signals", framework["negative_signals"])

            # 2. Get RAG context for signal detection
            rag_context = get_rag_context(
                state.startup_name + " momentum signals", 
                category_filter="Knowledge", 
                top_k=1
            )

            prompt = f"""You are the ICICI Startup Signal Detector.
Your job is to identify momentum signals for the startup '{state.startup_name}'.

Here are the target positive signals you must scan for:
{list(framework["positive_signals"].keys())}

Here are the target negative signals you must scan for:
{list(framework["negative_signals"].keys())}

Startup Details:
Sector: {state.startup_features.sector}
Subsector: {state.startup_features.subsector}
Article Headline: {state.article_data.get('headline', '')}
Article Description / Summary: {state.article_data.get('description', '')}
Enriched Raw Details: {state.article_data.get('enriched_raw', {})}
RAG Reference Context:
{rag_context}

Analyze all text context. For each positive or negative signal identified:
1. Specify the signal key name.
2. Provide direct text quote from the context as evidence.

Return ONLY a valid JSON object matching the schema below. Do not add notes, wrappers, or explanations.

JSON Schema:
{{
  "detected_signals": [
    {{
      "signal_key": "funding_round",
      "type": "positive",
      "evidence": "Raised $60 million in recent Series B round."
    }},
    {{
      "signal_key": "layoffs",
      "type": "negative",
      "evidence": "Reduced headcount by 10% in recent reorganization."
    }}
  ]
}}
"""
            detection = call_ollama(prompt, json_format=True)
            detected_list = detection.get("detected_signals", [])

            # 3. Calculate signal score in Python
            pos_score = 0
            neg_score = 0
            pos_list = []
            neg_list = []
            reasons = []

            for d in detected_list:
                key = d.get("signal_key")
                sig_type = d.get("type")
                evidence = d.get("evidence", "")

                if sig_type == "positive" and key in framework["positive_signals"]:
                    weight = framework["positive_signals"][key]
                    pos_score += weight
                    pos_list.append(key)
                    reasons.append(f"🟢 Detected {key.replace('_', ' ')}: {evidence}")
                elif sig_type == "negative" and key in framework["negative_signals"]:
                    weight = framework["negative_signals"][key]
                    # weight is negative in json (e.g. -5), so we add it or subtract absolute value
                    neg_score += abs(weight)
                    neg_list.append(key)
                    reasons.append(f"🔴 Detected {key.replace('_', ' ')}: {evidence}")

            # Signal Score = Sum(Positive) - Sum(abs(Negative))
            final_signal_score = pos_score - neg_score
            
            # Map momentum band
            bands = [
                {"min": -100, "max": 20, "label": "Weak Momentum"},
                {"min": 21, "max": 40, "label": "Moderate Momentum"},
                {"min": 41, "max": 60, "label": "Strong Momentum"},
                {"min": 61, "max": 200, "label": "Exceptional Momentum"}
            ]
            if os.path.exists(SIGNAL_CONFIG_PATH):
                with open(SIGNAL_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    bands = config.get("bands", bands)

            momentum_label = "Weak Momentum"
            for b in bands:
                if b["min"] <= final_signal_score <= b["max"]:
                    momentum_label = b["label"]
                    break

            # Update state features
            state.startup_features.positive_signals = pos_list
            state.startup_features.negative_signals = neg_list

            state.signals = {
                "score": final_signal_score,
                "label": momentum_label,
                "list_detected": detected_list,
                "reasons": reasons[:4] if reasons else ["Completed signal assessment."]
            }

            self.log_audit(
                state,
                f"Calculated Signal score: {final_signal_score} ({momentum_label})",
                metadata={
                    "score": final_signal_score,
                    "label": momentum_label,
                    "detected": detected_list
                }
            )

        except Exception as e:
            state.errors.append(f"SignalAgent failed: {str(e)}")
            self.log_audit(state, f"SignalAgent failed: {str(e)}", metadata={"error": True})

        return state
