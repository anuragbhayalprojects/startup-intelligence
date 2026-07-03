"""
backend/enrichment/identity_enricher.py
------------------------------------------
v2 Identity Enricher — extracts founders and leadership team for a startup.

v2 scope (founders/leadership only):
  founders: [{name, role, linkedin_url, background}]
  leadership: [{name, designation, linkedin_url, brief_history}]

Corporate facts (legal_name, HQ, founded_year, website, linkedin) have
moved to CorporateEnricher.

Context sources:
  - crawled_pages: team, about, founders, leadership (via BM25 identity_query)
  - search_snippets: founders_and_leadership field bucket

Fallback: triggered if founders list is empty.

Legacy enrich_from_state() bridge retained for backward compatibility with
old AgentOrchestrator pipeline path.
"""

from __future__ import annotations

import time
import json
import logging
import re
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.identity")


class IdentityEnricher(BaseEnricher):
    """
    Identity Enricher — extracts founders and leadership team.

    v2: section_name = "identity" in enrichment_sections JSONB.
    v1 (legacy): also populates basic_information, digital_presence for backward compat.
    """

    section_name = "identity"
    ai_task = "enrichment_identity"
    prompt_file = "enrichment_identity_prompt.txt"
    critical_fields = ["founders"]

    # -----------------------------------------------------------------------
    # v2 entry point
    # -----------------------------------------------------------------------

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
        v2 enrichment: builds context from team/about pages + founders snippets,
        calls LLM for founders + leadership extraction, runs fallback if empty.
        """
        if orchestrator is None:
            from backend.utils.search import WebSearchOrchestrator
            orchestrator = WebSearchOrchestrator()

        start = time.perf_counter()
        self.log(f"enrich_v2 starting for '{startup_name}'")

        # 1. Build crawled page context (BM25 — team/about/founders pages)
        source_context = self._get_bm25_context(
            crawled_pages=crawled_pages,
            enricher_bm25_key="identity_query",
            orchestrator=orchestrator,
            relevant_page_roles=["team", "about", "founders", "leadership", "homepage"],
        )

        # 2. Build snippet context (founders_and_leadership field bucket)
        snippet_context = self._get_snippet_context(
            search_snippets=all_snippets,
            field_keys=["founders_and_leadership"],
            max_chars=2000,
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
            self.log(f"No identity data returned for '{startup_name}'", level="warning")
            return {"founders": [], "leadership": []}

        result = self._normalize_v2(raw)
        self.log_result(startup_name, result, duration_ms)

        # 4. Fallback: if founders list is empty, fire targeted web search
        missing = self._detect_missing_fields(result)
        if missing:
            self.log(f"Empty founders list — triggering fallback search")
            result = self._run_fallback(
                startup_name=startup_name,
                missing_field_keys=missing,
                orchestrator=orchestrator,
                clean_name=clean_name or startup_name,
                brand_name=brand_name,
                existing_result=result,
            )

        return result

    def _normalize_v2(self, raw: dict) -> dict:
        """Normalizes v2 LLM output into founders + leadership schema."""
        founders = []
        for f in (raw.get("founders") or []):
            if not isinstance(f, dict) or not f.get("name"):
                continue
            li_url = f.get("linkedin_url") or None
            # Enforce /in/ profile URL only — reject /company/ URLs
            if li_url and "/company/" in li_url.lower():
                li_url = None
            founders.append({
                "name": f["name"].strip(),
                "role": f.get("role") or "Founder",
                "linkedin_url": li_url,
                "background": (f.get("background") or "")[:300] or None,
            })

        leadership = []
        for l in (raw.get("leadership") or []):
            if not isinstance(l, dict) or not l.get("name"):
                continue
            li_url = l.get("linkedin_url") or None
            if li_url and "/company/" in li_url.lower():
                li_url = None
            leadership.append({
                "name": l["name"].strip(),
                "designation": l.get("designation") or "",
                "linkedin_url": li_url,
                "brief_history": (l.get("brief_history") or "")[:300] or None,
            })

        return {"founders": founders, "leadership": leadership}

    # -----------------------------------------------------------------------
    # v1 enrich() bridge — legacy pipeline path
    # -----------------------------------------------------------------------

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        search_snippets: Optional[str] = None,
        startup_state: Optional[object] = None,
        **kwargs,
    ) -> dict:
        """
        v1 bridge: accepts pre-formatted source_context string.
        Returns v1 CI schema: basic_information + founders_details + digital_presence.
        Called by old pipeline path; new code should call enrich_v2().
        """
        start_time = time.perf_counter()
        self.log(f"enrich (v1 bridge) for '{startup_name}'")

        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context[:2500],
            search_snippets=(search_snippets or "")[:800],
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=5000)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No identity data returned for '{startup_name}'", level="warning")
            return {}

        result = self._map_to_ci_schema_v1(startup_name, raw, existing_data or {})
        self.log_result(startup_name, result, duration_ms)
        return result

    def _map_to_ci_schema_v1(
        self, startup_name: str, raw: dict, existing: dict
    ) -> dict:
        """Maps AI output to v1 company_intelligence section schema (backward compat)."""
        founders = []
        for f in (raw.get("founders") or []):
            if isinstance(f, dict) and f.get("name"):
                li_url = f.get("linkedin_url") or ""
                if "/company/" in li_url.lower():
                    li_url = ""
                founders.append({
                    "name": f.get("name", ""),
                    "role": f.get("role", ""),
                    "linkedin_url": li_url,
                    "background": f.get("background") or "",
                    "brief_details": f.get("background") or "",
                    "source": "ai_enrichment",
                })

        return {
            "founders_details": founders,
            "leadership": raw.get("leadership") or [],
        }

    # -----------------------------------------------------------------------
    # enrich_from_state() — AgentOrchestrator compatibility bridge (v1 path)
    # -----------------------------------------------------------------------

    def enrich_from_state(self, state) -> dict:
        """
        Compatibility bridge — enriches from a StartupState object.
        Called by the v1 AgentOrchestrator pipeline.
        v2 pipeline calls enrich_v2() directly.
        """
        startup_name = state.startup_name

        # Check if new dynamic website extractor already ran
        profile = state.article_data.get("company_profile")
        if profile:
            self.log(f"Using pre-extracted company_profile for '{startup_name}'")
            raw = {
                "founders": [
                    {
                        "name": getattr(leader, "name", ""),
                        "role": getattr(leader, "role", ""),
                        "linkedin_url": getattr(leader, "linkedin_url", ""),
                        "background": getattr(leader, "brief_background", "")
                    }
                    for leader in getattr(profile, "leadership", [])
                ]
            }

            # Fallback: extract founders from news article if not found on website
            if not raw["founders"]:
                self.log("No founders found in website profile — extracting from news article")
                news_text = state.article_data.get("text_content") or state.article_data.get("description") or ""
                if news_text:
                    prompt = (
                        f"From the news article below, extract the list of founders and leadership for '{startup_name}'.\n\n"
                        f"News Article:\n{news_text[:2000]}\n\n"
                        f"Return ONLY a valid JSON list matching this schema:\n"
                        f"[\n  {{\n    \"name\": \"string\",\n    \"role\": \"string\",\n"
                        f"    \"linkedin_url\": \"string or null\",\n    \"background\": \"string or null\"\n  }}\n]"
                    )
                    try:
                        raw_founders = self.call_ai(prompt=prompt, json_format=True, num_ctx=4000)
                        if isinstance(raw_founders, list):
                            raw["founders"] = raw_founders
                        elif isinstance(raw_founders, dict) and "founders" in raw_founders:
                            raw["founders"] = raw_founders["founders"]
                    except Exception as e:
                        self.log(f"News article founder fallback failed: {e}", level="warning")

            # Match individual founders with LinkedIn /in/ profiles from cached snippets
            snippets = state.article_data.get("discovered_snippets") or {}
            cached_in_links = []
            if isinstance(snippets, dict):
                for cat, records in snippets.items():
                    if isinstance(records, list):
                        for r in records:
                            if isinstance(r, dict) and r.get("url"):
                                url_clean = r["url"].strip()
                                if "linkedin.com/in/" in url_clean and url_clean not in cached_in_links:
                                    cached_in_links.append(url_clean)

            if cached_in_links and raw.get("founders"):
                for founder in raw["founders"]:
                    if not founder.get("linkedin_url"):
                        name = founder.get("name")
                        if name:
                            name_clean = re.sub(r"[^a-z0-9]", "", name.lower())
                            parts = [p.lower() for p in name.split() if len(p) > 2]
                            for link in cached_in_links:
                                link_lower = link.lower()
                                if name_clean in link_lower or (parts and all(part in link_lower for part in parts)):
                                    founder["linkedin_url"] = link
                                    self.log(f"Matched founder '{name}' LinkedIn URL: {link}")
                                    break

            return self._map_to_ci_schema_v1(startup_name, raw, state.article_data.get("company_intelligence", {}))

        # Legacy crawled content path
        from backend.pipeline.source_collector import format_source_payload_for_prompt

        crawled = state.article_data.get("crawled_content", {})
        source_context_parts = []

        headline = state.article_data.get("headline", "")
        news_text = state.article_data.get("text_content") or state.article_data.get("description") or ""
        if news_text:
            source_context_parts.append(f"NEWS ARTICLE HEADLINE: {headline}\nNEWS ARTICLE TEXT:\n{news_text[:2000]}")

        website_url = state.identity.get("website") or ""
        if isinstance(website_url, dict):
            website_url = website_url.get("value") or ""
        if website_url:
            source_context_parts.append(f"TARGET WEBSITE URL BEING CRAWLED:\n{website_url}")

        if isinstance(crawled, dict):
            for key in ("team", "about", "founders", "leadership", "homepage"):
                page_data = crawled.get(key, {})
                if not isinstance(page_data, dict):
                    continue
                text = page_data.get("text_content", "")
                footer = page_data.get("footer_text", "")
                socials = page_data.get("social_links", {})
                if text:
                    source_context_parts.append(f"{key.upper()}:\n{text[:1500]}")
                if footer:
                    source_context_parts.append(f"[FOOTER {key.upper()}]: {footer[:400]}")
                if socials:
                    source_context_parts.append(f"[SOCIAL LINKS {key.upper()}]: {json.dumps({k: v for k, v in socials.items() if v})}")

        source_context = "\n\n".join(source_context_parts)

        snippets = state.article_data.get("discovered_snippets", {})
        snippet_parts = []
        if isinstance(snippets, dict):
            for cat, records in snippets.items():
                if records and isinstance(records, list):
                    snippet_parts.append(f"--- {cat.upper()} SEARCH SNIPPETS ---")
                    for r in records[:3]:
                        snippet_parts.append(f"- {r.get('title', '')}: {r.get('snippet', '')} (URL: {r.get('url', '')})")

        return self.enrich(
            startup_name=startup_name,
            source_context=source_context,
            search_snippets="\n".join(snippet_parts),
            existing_data=state.article_data.get("company_intelligence", {}),
        )
