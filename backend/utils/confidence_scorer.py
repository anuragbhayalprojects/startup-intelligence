"""
confidence_scorer.py
---------------------
Computes identity confidence scores using the confidence_rules.json config.

This module is the single source of truth for identity confidence calculation.
All agents and scripts should call compute_identity_confidence() rather than
hardcoding confidence values.
"""

import os
import json
from typing import Optional

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
_CONF_RULES_PATH = os.path.join(_CONFIG_DIR, "confidence_rules.json")


def _load_confidence_rules() -> dict:
    try:
        if os.path.exists(_CONF_RULES_PATH):
            with open(_CONF_RULES_PATH) as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ [ConfidenceScorer] Failed to load confidence_rules.json: {e}")
    return {}


_RULES = _load_confidence_rules()


def compute_identity_confidence(
    evidence_count: int,
    source: str,
    has_website: bool = False,
    has_linkedin: bool = False,
    has_founder: bool = False,
    extra_bonuses: Optional[list[str]] = None,
) -> float:
    """
    Computes the identity confidence score (0.0–1.0) using the configured rules.

    Parameters
    ----------
    evidence_count  : Number of independent evidence pieces corroborating the identity
    source          : Primary source string (e.g. 'canonical_overloads', 'search', etc.)
    has_website     : Whether a verified official website was found
    has_linkedin    : Whether a LinkedIn company URL was found
    has_founder     : Whether a primary founder name was resolved
    extra_bonuses   : List of bonus keys from confidence_rules.json cross_validation_bonuses

    Returns
    -------
    float : Clamped confidence score in [0.0, 1.0]
    """
    rules = _RULES
    source_weights = rules.get("source_quality_weights", {})
    multipliers = rules.get("evidence_multipliers", {})
    bonuses = rules.get("cross_validation_bonuses", {})

    # Base score from source quality
    base = source_weights.get(source, 0.50)

    # Evidence multiplier
    mult_key = str(evidence_count) if evidence_count <= 5 else "5+"
    multiplier = float(multipliers.get(mult_key, 1.0))
    score = base * multiplier

    # Cross-validation bonuses
    if has_website and has_linkedin:
        score += bonuses.get("website_and_linkedin_match", 0.10)
    if has_founder:
        score += bonuses.get("founder_corroborated", 0.05)

    for bonus_key in (extra_bonuses or []):
        score += bonuses.get(bonus_key, 0.0)

    # Clamp to [0.0, 1.0]
    return round(min(max(score, 0.0), 1.0), 4)


def get_confidence_band(confidence: float) -> dict:
    """
    Returns the confidence band label and recommended action for a given score.
    """
    bands = _RULES.get("confidence_bands", [
        {"min": 0.90, "max": 1.00, "label": "Verified", "action": "use_directly"},
        {"min": 0.70, "max": 0.89, "label": "High Confidence", "action": "use_with_flag"},
        {"min": 0.50, "max": 0.69, "label": "Medium Confidence", "action": "use_with_recheck"},
        {"min": 0.30, "max": 0.49, "label": "Low Confidence", "action": "manual_review"},
        {"min": 0.00, "max": 0.29, "label": "Uncertain", "action": "search_again"},
    ])

    for band in bands:
        if band["min"] <= confidence <= band["max"]:
            return band

    return {"min": 0.0, "max": 0.29, "label": "Uncertain", "action": "search_again"}
