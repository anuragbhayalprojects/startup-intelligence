"""
backend/enrichment/funding_enricher.py
-----------------------------------------
AI Layer 3 — Funding & Investor Enrichment Module.

Enriches: funding_details

Consolidates logic previously spread across:
  - FundingIntelligenceAgent (funding extraction)
  - startup_analyzer.collect_funding_snippets() (search-based funding discovery)
  - startup_analyzer.extract_funding_rounds() (LLM-based round parsing)

Uses targeted search queries + a single combined AI call to extract:
  - All known funding rounds (stage, amount, date, lead/co investors)
  - Total funding amount
  - Latest funding stage
  - Key investor list

Supports standalone re-enrichment via /api/startups/{id}/enrich/funding.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.funding")

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

_FUNDING_PROMPT_TEMPLATE = """You are a precise startup intelligence analyst specializing in funding and investor data.
Extract structured funding information for "{startup_name}" from the search snippets and source content below.

FUNDING SEARCH SNIPPETS:
{funding_snippets}

SOURCE CONTEXT:
{source_context}

Extract as valid JSON. Use null for any field you cannot confidently determine. Be precise about amounts and dates — do NOT hallucinate.

{{
  "latest_stage": "Most recent funding stage (e.g. Series A, Seed, Pre-Series A) or null",
  "total_funding": "Total funding raised across all rounds (e.g. $45M) or null",
  "latest_round_date": "Date of most recent round (YYYY-MM or YYYY) or null",
  "rounds": [
    {{
      "stage": "Series A",
      "amount": "$10M",
      "date": "2023-06",
      "lead_investor": "Investor Name or null",
      "co_investors": ["Co-investor 1", "Co-investor 2"],
      "valuation": "Post-money valuation or null"
    }}
  ],
  "key_investors": ["Notable investor names across all rounds"],
  "funding_source": "Source of this information"
}}

Return ONLY the JSON object. No explanations."""


class FundingEnricher(BaseEnricher):
    """
    Funding Enricher — extracts funding rounds, investors, and total raised.

    v2: enrich_v2() uses field-bucketed funding_details snippets + BM25 context.
    v1: enrich() / enrich_from_state() retained for backward compatibility.
    """

    section_name = "funding"
    ai_task = "enrichment_funding"
    prompt_file = "funding_extraction_prompt.txt"
    critical_fields = ["latest_stage"]

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
        v2 enrichment: builds context from funding_details snippet bucket + BM25 chunks.
        Calls LLM and runs fallback if latest_stage is null.
        """
        if orchestrator is None:
            from backend.utils.search import WebSearchOrchestrator
            orchestrator = WebSearchOrchestrator()

        start = time.perf_counter()
        self.log(f"enrich_v2 starting for '{startup_name}'")

        # BM25 over crawled pages (funding signals in homepage/about)
        bm25_context = self._get_bm25_context(
            crawled_pages=crawled_pages,
            enricher_bm25_key="funding_query",
            orchestrator=orchestrator,
            relevant_page_roles=["homepage", "about"],
        )
        # Field-bucketed funding snippets (primary source)
        snippet_context = self._get_snippet_context(
            search_snippets=all_snippets,
            field_keys=["funding_details"],
            max_chars=3000,
        )
        combined_context = "\n\n".join(filter(None, [snippet_context, bm25_context]))

        prompt = _FUNDING_PROMPT_TEMPLATE.format(
            startup_name=startup_name,
            funding_snippets=combined_context[:3500],
            source_context="",
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=6000)
        duration_ms = (time.perf_counter() - start) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No funding data returned for '{startup_name}'", level="warning")
            return {"latest_stage": None, "rounds": [], "key_investors": []}

        result = self._normalize_v2(raw)
        self.log_result(startup_name, result, duration_ms)

        missing = self._detect_missing_fields(result)
        if missing:
            self.log(f"Missing latest_stage — triggering fallback search")
            result = self._run_fallback(
                startup_name=startup_name,
                missing_field_keys=["funding_details"],
                orchestrator=orchestrator,
                clean_name=clean_name or startup_name,
                brand_name=brand_name,
                existing_result=result,
            )
        return result

    def _normalize_v2(self, raw: dict) -> dict:
        """Normalizes v2 funding output to flat section schema."""
        rounds = []
        for r in (raw.get("rounds") or []):
            if not isinstance(r, dict):
                continue
            rounds.append({
                "stage": r.get("stage") or "",
                "amount": r.get("amount") or "",
                "date": r.get("date") or r.get("latest_date") or "",
                "lead_investor": r.get("lead_investor") or "",
                "co_investors": r.get("co_investors") or [],
                "valuation": r.get("valuation") or None,
            })
        return {
            "latest_stage": raw.get("latest_stage") or None,
            "total_funding": raw.get("total_funding") or None,
            "latest_round_date": raw.get("latest_round_date") or raw.get("latest_date") or None,
            "rounds": rounds,
            "key_investors": raw.get("key_investors") or [],
        }


    section_name = "funding"
    ai_task = "enrichment_funding"
    prompt_file = "funding_extraction_prompt.txt"

    def _load_funding_sources_config(self) -> dict:
        """Loads funding_sources.json for search query configuration."""
        path = os.path.join(_CONFIG_DIR, "funding_sources.json")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _collect_funding_snippets(self, startup_name: str, website: str = "") -> str:
        """
        Collects funding-related search snippets via DuckDuckGo.
        Reuses existing collect_funding_snippets logic from startup_analyzer.py.
        """
        try:
            from backend.ai.startup_analyzer import collect_funding_snippets
            return collect_funding_snippets(startup_name, website)
        except Exception as e:
            logger.warning(f"[FundingEnricher] collect_funding_snippets failed: {e}")
            return ""

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        website_url: str = "",
        pre_collected_snippets: str = "",
        **kwargs,
    ) -> dict:
        """
        Extracts funding and investor information from search snippets + source context.

        Parameters
        ----------
        startup_name           : Clean brand name
        source_context         : Formatted source payload (used as secondary context)
        existing_data          : Existing company_intelligence for merge
        website_url            : Startup website URL (used for scoped funding search)
        pre_collected_snippets : Pre-collected funding snippets (skips search if provided)

        Returns
        -------
        dict with key: funding_details
        """
        start_time = time.perf_counter()
        self.log(f"Enriching funding for '{startup_name}'")

        # 1. Collect funding snippets (search or reuse pre-collected)
        funding_snippets = pre_collected_snippets
        if not funding_snippets:
            self.log(f"Collecting funding search snippets for '{startup_name}'")
            funding_snippets = self._collect_funding_snippets(startup_name, website_url)

        if len(funding_snippets.strip()) < 30:
            self.log(f"Insufficient funding snippets for '{startup_name}' — returning empty", level="warning")
            return {}

        # 2. Build prompt
        prompt = _FUNDING_PROMPT_TEMPLATE.format(
            startup_name=startup_name,
            funding_snippets=funding_snippets[:2000],
            source_context=source_context[:800],
        )

        # 3. Call AI
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=4000)

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No funding data returned for '{startup_name}'", level="warning")
            return {}

        result = self._map_to_ci_schema(startup_name, raw, existing_data or {})
        self.log_result(startup_name, result, duration_ms)
        return result

    def _map_to_ci_schema(self, startup_name: str, raw: dict, existing: dict) -> dict:
        """Maps AI output to company_intelligence funding_details section."""
        rounds = []
        for r in (raw.get("rounds") or []):
            if isinstance(r, dict):
                rounds.append({
                    "stage": r.get("stage") or "",
                    "amount": r.get("amount") or "",
                    "date": r.get("date") or "",
                    "lead_investor": r.get("lead_investor") or "",
                    "co_investors": r.get("co_investors") or [],
                    "valuation": r.get("valuation") or "",
                })

        # Deduplicate key_investors across rounds
        all_investors = list(raw.get("key_investors") or [])
        for r in rounds:
            if r.get("lead_investor"):
                all_investors.append(r["lead_investor"])
            all_investors.extend(r.get("co_investors") or [])
        key_investors = list(dict.fromkeys(i for i in all_investors if i))[:20]

        funding_details = {
            "latest_stage": raw.get("latest_stage") or "",
            "total_funding": raw.get("total_funding") or "",
            "latest_round_date": raw.get("latest_round_date") or "",
            "rounds": rounds,
            "key_investors": key_investors,
            "funding_source": raw.get("funding_source") or "ai_search_enrichment",
        }

        return {"funding_details": funding_details}

    def enrich_from_state(self, state) -> dict:
        """Compatibility bridge for AgentOrchestrator pipeline integration."""
        startup_name = state.startup_name
        website_field = state.identity.get("website")
        website = ""
        if isinstance(website_field, dict):
            website = website_field.get("value") or ""
        elif isinstance(website_field, str):
            website = website_field

        # Reuse funding context from state if already collected
        funding_context = state.article_data.get("funding_search_context", "")
        if not funding_context:
            funding_context = self._collect_funding_snippets(startup_name, website)
            state.article_data["funding_search_context"] = funding_context

        article_desc = state.article_data.get("description", "")

        return self.enrich(
            startup_name=startup_name,
            source_context=article_desc[:500],
            website_url=website,
            pre_collected_snippets=funding_context,
            existing_data=state.article_data.get("company_intelligence", {}),
        )
