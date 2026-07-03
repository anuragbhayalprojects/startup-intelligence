"""
backend/enrichment/corporate_enricher.py
------------------------------------------
v2 Corporate Enricher — extracts corporate identity facts for a startup.

Extracted fields:
  canonical_name, legal_name, aliases, website_url, linkedin_url, twitter_url,
  founded_year, hq_city, hq_state, country, headquarters,
  one_liner_description, brief_description,
  business_model, target_audience, industry, sector, sub_sector

Context sources:
  - crawled_pages: homepage, about, contact, privacy (via BM25 corporate_query)
  - search_snippets: official_website, official_linkedin, headquarter, founded_year

Fallback: triggered if founded_year, headquarters, legal_name, or linkedin_url are null.
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.corporate")


class CorporateEnricher(BaseEnricher):
    """
    Extracts corporate identity facts from crawled website content and search snippets.

    section_name = "corporate" in enrichment_sections JSONB.
    """

    section_name = "corporate"
    ai_task = "enrichment_corporate"
    prompt_file = "enrichment_corporate_prompt.txt"
    critical_fields = ["founded_year", "headquarters", "legal_name", "linkedin_url"]

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
        v2 enrichment: builds context from crawled_pages + field-bucketed snippets,
        calls LLM, detects missing critical fields, and runs fallback if needed.

        Parameters
        ----------
        startup_name  : raw discovered startup name
        crawled_pages : dict of page_role -> page_record (from source_collector v2)
        all_snippets  : field-bucketed snippet dict (raw_source_payload.search_snippets)
        orchestrator  : WebSearchOrchestrator instance (for BM25 + fallback searches)
        clean_name    : resolved brand name for fallback queries
        brand_name    : confirmed brand name (defaults to clean_name)

        Returns
        -------
        dict — corporate section result
        """
        if orchestrator is None:
            from backend.utils.search import WebSearchOrchestrator
            orchestrator = WebSearchOrchestrator()

        start = time.perf_counter()
        self.log(f"enrich_v2 starting for '{startup_name}'")

        # 1. Build crawled page context (BM25 over corporate-relevant pages)
        source_context = self._get_bm25_context(
            crawled_pages=crawled_pages,
            enricher_bm25_key="corporate_query",
            orchestrator=orchestrator,
            relevant_page_roles=["homepage", "about", "contact", "privacy", "terms"],
        )

        # 2. Build snippet context (corporate field buckets)
        snippet_context = self._get_snippet_context(
            search_snippets=all_snippets,
            field_keys=["official_website", "official_linkedin", "headquarter", "founded_year"],
            max_chars=2000,
        )

        # 3. Resolve website URL from crawled homepage
        website_url = crawled_pages.get("homepage", {}).get("url", "")

        # 4. Render and call LLM
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context or "No crawled content available.",
            search_snippets=snippet_context or "No search snippets available.",
            website_url=website_url,
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=5000)
        duration_ms = (time.perf_counter() - start) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No corporate data returned for '{startup_name}'", level="warning")
            return {}

        result = self._normalize(raw)
        self.log_result(startup_name, result, duration_ms)

        # 5. Fallback: check critical fields
        missing = self._detect_missing_fields(result)
        if missing:
            self.log(f"Missing critical fields: {missing} — triggering fallback")
            result = self._run_fallback(
                startup_name=startup_name,
                missing_field_keys=missing,
                orchestrator=orchestrator,
                clean_name=clean_name or startup_name,
                brand_name=brand_name,
                existing_result=result,
            )

        return result

    # ---------------------------------------------------------------------------
    # Legacy v1 bridge (for backward-compat with old pipeline path)
    # ---------------------------------------------------------------------------

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        """
        v1 bridge: accepts pre-formatted source_context string and calls LLM.
        Used by old pipeline path; new code should call enrich_v2().
        """
        self.log(f"enrich (v1 bridge) for '{startup_name}'")
        website_url = kwargs.get("website_url", "")
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context or "No source content available.",
            search_snippets=kwargs.get("search_snippets", ""),
            website_url=website_url,
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=5000)
        if not raw or not isinstance(raw, dict):
            return {}
        return self._normalize(raw)

    # ---------------------------------------------------------------------------
    # Normalization
    # ---------------------------------------------------------------------------

    def _normalize(self, raw: dict) -> dict:
        """Normalizes and validates the LLM output into the corporate section schema."""
        founded_year = raw.get("founded_year")
        if founded_year is not None:
            try:
                founded_year = int(str(founded_year).strip()[:4])
                if not (1900 <= founded_year <= 2030):
                    founded_year = None
            except (ValueError, TypeError):
                founded_year = None

        # Enforce linkedin_url is /company/ and not /in/ (individual profile)
        linkedin_url = raw.get("linkedin_url") or None
        if linkedin_url and "/in/" in linkedin_url.lower():
            self.log("linkedin_url contains /in/ profile — stripping (must be /company/)", level="warning")
            linkedin_url = None

        return {
            "canonical_name": raw.get("canonical_name") or None,
            "legal_name": raw.get("legal_name") or None,
            "aliases": raw.get("aliases") or [],
            "founded_year": founded_year,
            "hq_city": raw.get("hq_city") or None,
            "hq_state": raw.get("hq_state") or None,
            "country": raw.get("country") or "India",
            "headquarters": raw.get("headquarters") or None,
            "website_url": raw.get("website_url") or None,
            "linkedin_url": linkedin_url,
            "twitter_url": raw.get("twitter_url") or None,
            "one_liner_description": raw.get("one_liner_description") or None,
            "brief_description": (raw.get("brief_description") or "")[:500] or None,
            "business_model": raw.get("business_model") or None,
            "target_audience": raw.get("target_audience") or None,
            "industry": raw.get("industry") or None,
            "sector": raw.get("sector") or None,
            "sub_sector": raw.get("sub_sector") or None,
        }
