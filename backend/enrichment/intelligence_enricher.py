"""
backend/enrichment/intelligence_enricher.py
----------------------------------------------
AI Layer 3 — Competitive & Strategic Intelligence Enrichment Module.

Enriches: competitors, bfsi_relevance, strategic_fit, scoring (for analysis_json compat)

Consolidates logic previously spread across:
  - CompetitorIntelligenceAgent (competitor mapping)
  - OpportunityMappingAgent (BFSI opportunity mapping)
  - RelevanceAgent (relevance scoring)
  - StrategicFitAgent (strategic fit scoring)
  - SignalAgent (signal detection)
  - RecommendationAgent (recommendation generation)

Uses a combined AI call to extract:
  - Competitor landscape
  - BFSI relevance score and use cases
  - Strategic fit assessment
  - Overall engagement recommendation

Supports standalone re-enrichment via /api/startups/{id}/enrich/competitors.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.intelligence")

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

_INTELLIGENCE_PROMPT_TEMPLATE = """You are a strategic startup intelligence analyst for an ICICI Group entity. Your task is to analyze "{startup_name}" and produce competitive and strategic intelligence.

SOURCE CONTEXT:
{source_context}

BUSINESS PROFILE:
{business_profile_summary}

BFSI CONTEXT (ICICI Group):
ICICI Group operates across banking, insurance (ICICI Prudential Life, ICICI Lombard), securities (ICICI Securities / iDirect), AMC (Prudential MF), home finance (ICICI HFC), and venture capital (ICICI Venture).

Extract as valid JSON. Be precise and analytical. Do NOT hallucinate.

{{
  "competitors": [
    {{
      "name": "Competitor company name",
      "positioning": "How they compare to {startup_name}",
      "category": "Direct / Indirect / Adjacent"
    }}
  ],
  "bfsi_relevance": {{
    "is_relevant": true,
    "relevance_score": 75,
    "relevance_reasoning": "Why is this relevant to BFSI/ICICI?",
    "use_cases": [
      {{
        "icici_entity": "ICICI Bank / ICICI Prudential / ICICI Securities / etc",
        "use_case": "Specific use case description",
        "potential_impact": "Expected business impact"
      }}
    ]
  }},
  "strategic_fit": {{
    "enterprise_readiness": 70,
    "partnership_opportunity": "Partnership / Investment / Monitor / Pass",
    "integration_feasibility": "High / Medium / Low",
    "key_risks": ["risk 1", "risk 2"]
  }},
  "scoring": {{
    "overall_priority_score": 65,
    "risk_assessment": "Low / Medium / High"
  }},
  "recommended_action": "Engage / Pilot / Monitor / Pass",
  "action_rationale": "1-2 sentence rationale for the recommendation"
}}

Return ONLY the JSON object. No explanations."""


class IntelligenceEnricher(BaseEnricher):
    """
    Intelligence Enricher — extracts competitors, BFSI relevance, strategic fit.

    Consolidates CompetitorIntelligenceAgent + OpportunityMappingAgent +
    RelevanceAgent + StrategicFitAgent + SignalAgent + RecommendationAgent
    into a single AI call. ~1 AI call per enrichment.
    """

    section_name = "intelligence"
    ai_task = "enrichment_intelligence"

    def _load_rag_context(self, startup_name: str, business_profile: dict) -> str:
        """Loads RAG context for BFSI problem/opportunity matching."""
        try:
            from backend.agents.utils import get_rag_context
            sector = business_profile.get("sector", "")
            query = f"{startup_name} {sector} BFSI use case"
            return get_rag_context(query, top_k=2)
        except Exception as e:
            logger.debug(f"[IntelligenceEnricher] RAG context failed: {e}")
            return ""

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        business_profile: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        """
        Extracts competitive and strategic intelligence from source context.

        Returns
        -------
        dict with keys: competitors, bfsi_relevance, strategic_fit, scoring, recommendation
        """
        start_time = time.perf_counter()
        self.log(f"Enriching intelligence for '{startup_name}'")

        bp = business_profile or (existing_data or {}).get("business_profile", {})
        business_profile_summary = (
            f"Sector: {bp.get('sector', 'Unknown')}\n"
            f"Business Model: {bp.get('business_model', 'Unknown')}\n"
            f"Description: {bp.get('description', '')[:300]}"
        )

        # Augment source context with RAG
        rag_context = self._load_rag_context(startup_name, bp)
        full_context = "\n\n".join(filter(None, [source_context[:1500], rag_context[:500]]))

        prompt = _INTELLIGENCE_PROMPT_TEMPLATE.format(
            startup_name=startup_name,
            source_context=full_context,
            business_profile_summary=business_profile_summary,
        )

        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=5000)

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No intelligence data returned for '{startup_name}'", level="warning")
            return {}

        result = self._map_to_ci_schema(startup_name, raw, existing_data or {})
        self.log_result(startup_name, result, duration_ms)
        return result

    def _map_to_ci_schema(self, startup_name: str, raw: dict, existing: dict) -> dict:
        """Maps AI output to company_intelligence and analysis_json compatible sections."""
        competitors = []
        for c in (raw.get("competitors") or []):
            if isinstance(c, dict) and c.get("name"):
                competitors.append({
                    "name": c.get("name", ""),
                    "positioning": c.get("positioning", ""),
                    "category": c.get("category", "Direct"),
                })

        bfsi_relevance = raw.get("bfsi_relevance") or {}
        strategic_fit = raw.get("strategic_fit") or {}
        scoring = raw.get("scoring") or {}

        # Normalize scores to valid range
        relevance_score = min(max(int(bfsi_relevance.get("relevance_score", 0)), 0), 100)
        priority_score = min(max(int(scoring.get("overall_priority_score", 0)), 0), 100)
        enterprise_readiness = min(max(int(strategic_fit.get("enterprise_readiness", 0)), 0), 100)

        return {
            "competitors": competitors,
            # These fields are stored in company_intelligence for the new architecture
            # AND also available for backward-compat in analysis_json via the orchestrator
            "_bfsi_relevance": {
                "is_relevant": bfsi_relevance.get("is_relevant", False),
                "relevance_score": relevance_score,
                "relevance_reasoning": bfsi_relevance.get("relevance_reasoning", ""),
                "use_cases": bfsi_relevance.get("use_cases") or [],
            },
            "_strategic_fit": {
                "enterprise_readiness": enterprise_readiness,
                "partnership_opportunity": strategic_fit.get("partnership_opportunity", "Monitor"),
                "integration_feasibility": strategic_fit.get("integration_feasibility", "Medium"),
                "key_risks": strategic_fit.get("key_risks") or [],
            },
            "_scoring": {
                "overall_priority_score": priority_score,
                "risk_assessment": scoring.get("risk_assessment", "Medium"),
            },
            "_recommendation": {
                "recommended_action": raw.get("recommended_action", "Monitor"),
                "action_rationale": raw.get("action_rationale", ""),
            },
        }

    def enrich_from_state(self, state) -> dict:
        """Compatibility bridge for AgentOrchestrator pipeline integration.

        Reads crawled content from both v2 (raw_source_payload.crawled_pages) and
        v1 (crawled_content) keys, preferring v2 when available (Bug 2 fix).
        """
        startup_name = state.startup_name

        # Bug 2 fix: v2 stores pages under raw_source_payload.crawled_pages.
        # Fall back to the v1 crawled_content key so this bridge works in both modes.
        raw_payload = state.article_data.get("raw_source_payload", {})
        crawled_v2  = raw_payload.get("crawled_pages", {})
        crawled_v1  = state.article_data.get("crawled_content", {})
        crawled     = crawled_v2 or crawled_v1

        context_parts = []
        _role_limits = {
            "homepage": 800,
            "about":    600,
            "products": 500,
            "solutions": 400,
            "team":     400,
        }
        for role, max_chars in _role_limits.items():
            page = crawled.get(role, {})
            text = page.get("text_content", "") or page.get("body_text", "")
            if text:
                context_parts.append(f"{role.upper()}:\n{text[:max_chars]}")

        article_desc = state.article_data.get("description", "")
        if article_desc:
            context_parts.append(f"NEWS ARTICLE:\n{article_desc[:400]}")

        source_context = "\n\n".join(context_parts)
        existing_ci = state.article_data.get("company_intelligence", {})
        business_profile = existing_ci.get("business_profile", {})

        # Also try startup_features
        if not business_profile.get("sector") and hasattr(state, "startup_features"):
            business_profile = {
                "sector": state.startup_features.sector or "",
                "business_model": (
                    state.startup_features.business_models[0]
                    if state.startup_features.business_models else ""
                ),
                "description": state.article_data.get("description", "")[:200],
            }

        return self.enrich(
            startup_name=startup_name,
            source_context=source_context,
            existing_data=existing_ci,
            business_profile=business_profile,
        )
