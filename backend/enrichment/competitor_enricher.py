"""
backend/enrichment/competitor_enricher.py
-------------------------------------------
v2 Competitor Enricher — extracts competitor landscape for a startup.

Extracted fields:
  competitors: [{company_name, type, value_proposition, website, notes}]
  competitive_summary: str

Context sources:
  - crawled_pages: homepage, about (via BM25 competitor_query)
  - search_snippets: competitors field bucket

Fallback: triggered if competitors list is empty.

NOTE: IntelligenceEnricher also generates a competitors section but focuses on
BFSI strategic angles. CompetitorEnricher is market-focused and runs in parallel
with the other 4 enrichers. IntelligenceEnricher reads from CompetitorEnricher's
output as part of its synthesis.
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.competitor")


class CompetitorEnricher(BaseEnricher):
    """
    Extracts competitor landscape from crawled content and search snippets.

    section_name = "competitors" in enrichment_sections JSONB.
    """

    section_name = "competitors"
    ai_task = "enrichment_competitors"
    prompt_file = "enrichment_competitors_prompt.txt"
    critical_fields = ["competitors"]

    def enrich_v2(
        self,
        startup_name: str,
        crawled_pages: dict,
        all_snippets: dict,
        orchestrator=None,
        clean_name: str = "",
        brand_name: str = "",
    ) -> dict:
        """
        v2 enrichment: builds context from crawled_pages + competitors snippets,
        calls LLM, and runs fallback if competitors list is empty.
        """
        if orchestrator is None:
            from backend.utils.search import WebSearchOrchestrator
            orchestrator = WebSearchOrchestrator()

        start = time.perf_counter()
        self.log(f"enrich_v2 starting for '{startup_name}'")

        # 1. Build crawled page context (BM25 — homepage + about are most relevant)
        source_context = self._get_bm25_context(
            crawled_pages=crawled_pages,
            enricher_bm25_key="competitor_query",
            orchestrator=orchestrator,
            relevant_page_roles=["homepage", "about"],
        )

        # 2. Build snippet context (competitors field bucket)
        snippet_context = self._get_snippet_context(
            search_snippets=all_snippets,
            field_keys=["competitors"],
            max_chars=2500,
        )

        # 3. Render and call LLM
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context or "No crawled content available.",
            search_snippets=snippet_context or "No search snippets available.",
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=5000)
        duration_ms = (time.perf_counter() - start) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No competitor data returned for '{startup_name}'", level="warning")
            return {"competitors": [], "competitive_summary": None}

        result = self._normalize(raw)
        self.log_result(startup_name, result, duration_ms)

        # 4. Fallback: if competitors list is empty, fire targeted web search
        missing = self._detect_missing_fields(result)
        if missing:
            self.log(f"Empty competitors list — triggering fallback search")
            result = self._run_fallback(
                startup_name=startup_name,
                missing_field_keys=missing,
                orchestrator=orchestrator,
                clean_name=clean_name or startup_name,
                brand_name=brand_name,
                existing_result=result,
            )

        return result

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        """v1 bridge for backward compatibility."""
        self.log(f"enrich (v1 bridge) for '{startup_name}'")
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context or "No source content available.",
            search_snippets=kwargs.get("search_snippets", ""),
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=4096)
        if not raw or not isinstance(raw, dict):
            return {"competitors": [], "competitive_summary": None}
        return self._normalize(raw)

    def _normalize(self, raw: dict) -> dict:
        """Normalizes LLM output into the competitors section schema."""
        competitors = []
        for c in (raw.get("competitors") or []):
            if not isinstance(c, dict):
                continue
            name = c.get("company_name", "").strip()
            if not name:
                continue
            comp_type = c.get("type", "direct").lower()
            if comp_type not in ("direct", "indirect"):
                comp_type = "direct"
            competitors.append({
                "company_name": name,
                "type": comp_type,
                "value_proposition": c.get("value_proposition") or None,
                "website": c.get("website") or None,
                "notes": c.get("notes") or None,
            })

        return {
            "competitors": competitors,
            "competitive_summary": (raw.get("competitive_summary") or "")[:500] or None,
        }
