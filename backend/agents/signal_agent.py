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
                    "awards_recognition": 3,
                    "product_launch": 7,
                    "mergers_and_acquisitions": 8,
                    "technology_innovation": 7,
                    "valuation_increase": 8,
                    "general_expansion_or_growth": 5,
                    "positive_market_sentiment": 5,
                    "sustainability_initiative": 6
                },
                "negative_signals": {
                    "leadership_exits": -5,
                    "layoffs": -6,
                    "regulatory_issues": -9,
                    "product_failure": -8,
                    "major_customer_loss": -8,
                    "data_breach": -10,
                    "legal_dispute": -8,
                    "security_incident": -8,
                    "financial_losses": -6,
                    "valuation_markdown": -7,
                    "negative_market_sentiment": -4,
                    "operational_halts": -7
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

            # Load prompt from external file
            from jinja2 import Template
            prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/signal_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = Template(f.read())
            prompt = prompt_template.render(
                startup_name=state.startup_name,
                positive_signals=list(framework["positive_signals"].keys()),
                negative_signals=list(framework["negative_signals"].keys()),
                sector=state.startup_features.sector,
                subsector=state.startup_features.subsector,
                headline=state.article_data.get('headline', ''),
                description=state.article_data.get('description', ''),
                enriched_raw=state.article_data.get('enriched_raw', {}),
                rag_context=rag_context
            )
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
