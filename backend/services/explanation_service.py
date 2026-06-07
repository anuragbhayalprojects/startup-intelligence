from typing import List, Dict, Any
from backend.models.startup_state import StartupState

class ExplanationService:
    @staticmethod
    def generate_explanations(state: StartupState) -> Dict[str, Any]:
        """
        Compiles structured explanations for the relevance, strategic fit, and signal scores,
        ensuring explainability for every score calculated by the system.
        """
        relevance_score = state.relevance.get("score", 0)
        fit_score = state.strategic_fit.get("score", 0)
        signal_score = state.signals.get("score", 0)
        
        # 1. Relevance reasons
        relevance_reasons = state.relevance.get("reasons", [])
        if not relevance_reasons:
            relevance_reasons = [f"Relevance scored at {relevance_score} based on sector alignment."]

        # 2. Strategic fit reasons
        fit_reasons = state.strategic_fit.get("reasons", [])
        if relevance_score < 50:
            fit_reasons = ["Bypassed strategic fit evaluation due to low relevance score (< 50)."]
        elif not fit_reasons:
            fit_reasons = [f"Strategic fit scored at {fit_score} based on corporate alignment rules."]

        # 3. Signal reasons
        signal_reasons = state.signals.get("reasons", [])
        if relevance_score < 50:
            signal_reasons = ["Bypassed signal detection due to low relevance score (< 50)."]
        elif not signal_reasons:
            signal_reasons = [f"Momentum signals evaluated at score {signal_score}."]

        return {
            "relevance": {
                "score": relevance_score,
                "reasons": relevance_reasons
            },
            "strategic_fit": {
                "score": fit_score,
                "reasons": fit_reasons
            },
            "signals": {
                "score": signal_score,
                "reasons": signal_reasons
            }
        }
