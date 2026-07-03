"""
backend/enrichment/base_enricher.py
--------------------------------------
Base class for all modular enrichment modules.

All enrichers inherit from BaseEnricher which provides:
  - Standardized run() interface
  - AI call routing via backend.ai.router.call_ai()
  - Prompt loading from backend/prompts/
  - Enrichment metadata tracking
  - Section-wise JSONB partial update helpers
  - Observability logging
  - v2: Per-enricher fallback detection + targeted re-extraction
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Any, Optional
from jinja2 import Template

logger = logging.getLogger("startup_intelligence.enrichment")

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")


class BaseEnricher:
    """
    Base class for all modular enrichment modules.

    Subclasses must implement:
        enrich(startup_name, source_context, existing_data) -> dict

    The returned dict is a partial company_intelligence update (merge-patch ready).

    v2 subclasses also implement:
        enrich_v2(startup_name, crawled_pages, all_snippets) -> dict
    """

    #: Section name in company_intelligence JSONB (override in subclasses)
    section_name: str = "base"

    #: AI routing task key (must match model_routing.json task names)
    ai_task: str = "enrichment_products"

    #: Prompt template filename (in backend/prompts/)
    prompt_file: Optional[str] = None

    #: v2: Fields this enricher considers critical (triggers fallback if empty/null)
    critical_fields: list[str] = []

    def __init__(self):
        self._prompt_template: Optional[Template] = None

    # -----------------------------------------------------------------------
    # Prompt loading
    # -----------------------------------------------------------------------

    def load_prompt(self, prompt_file: Optional[str] = None) -> Template:
        """Loads and caches the Jinja2 prompt template for this enricher."""
        fname = prompt_file or self.prompt_file
        if not fname:
            raise ValueError(f"[{self.__class__.__name__}] No prompt_file configured.")
        path = os.path.join(_PROMPTS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return Template(f.read())
        except FileNotFoundError:
            raise RuntimeError(f"[{self.__class__.__name__}] Prompt not found: {path}")

    def render_prompt(self, **kwargs) -> str:
        """Renders the prompt template with the given context variables."""
        if self._prompt_template is None:
            self._prompt_template = self.load_prompt()
        return self._prompt_template.render(**kwargs)

    # -----------------------------------------------------------------------
    # AI call
    # -----------------------------------------------------------------------

    def call_ai(self, prompt: str, json_format: bool = True, num_ctx: int = 4096) -> Any:
        """
        Routes an AI call via the centralized AI router.
        OpenRouter primary, Ollama fallback, fully transparent.
        """
        from backend.ai.router import call_ai as router_call_ai
        return router_call_ai(
            prompt=prompt,
            task=self.ai_task,
            json_format=json_format,
            num_ctx=num_ctx,
            temperature=0.0,
        )

    # -----------------------------------------------------------------------
    # Main interface (override in subclasses)
    # -----------------------------------------------------------------------

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        """
        Runs enrichment for this section.

        Parameters
        ----------
        startup_name   : Clean brand name
        source_context : Formatted source payload text for LLM context
        existing_data  : Existing company_intelligence data (for incremental update)
        **kwargs       : Additional enricher-specific parameters

        Returns
        -------
        dict
            Partial company_intelligence update. Keys should be section names.
            Example: {"founders_details": [...], "basic_information": {...}}
        """
        raise NotImplementedError(f"[{self.__class__.__name__}] enrich() must be implemented")

    # -----------------------------------------------------------------------
    # v2: Fallback detection and targeted re-extraction
    # -----------------------------------------------------------------------

    def _detect_missing_fields(
        self, result: dict, required_fields: Optional[list[str]] = None
    ) -> list[str]:
        """
        Detects which critical fields are missing or empty in the enricher's output.

        Parameters
        ----------
        result          : output dict from the enricher's main LLM call
        required_fields : fields to check; defaults to self.critical_fields

        Returns
        -------
        list[str] — field keys that are null, empty string, or empty list
        """
        fields_to_check = required_fields or self.critical_fields
        missing = []
        for field in fields_to_check:
            val = result.get(field)
            if val is None or val == "" or val == [] or val == {}:
                missing.append(field)
        return missing

    def _get_snippet_context(
        self,
        search_snippets: dict,
        field_keys: list[str],
        max_chars: int = 2000,
    ) -> str:
        """
        Formats a subset of field-bucketed search snippets into a prompt-ready string.

        Parameters
        ----------
        search_snippets : field-bucketed dict (raw_source_payload.search_snippets)
        field_keys      : which field buckets to include
        max_chars       : maximum total characters
        """
        parts = []
        for field_key in field_keys:
            records = search_snippets.get(field_key, [])
            if not records:
                continue
            parts.append(f"--- {field_key.upper().replace('_', ' ')} SNIPPETS ---")
            for rec in records[:5]:
                title = rec.get("title", "")
                url = rec.get("url", "")
                snippet = rec.get("snippet", "")
                phase = rec.get("phase", "")
                parts.append(f"[{phase.upper()}] {title}\nURL: {url}\n{snippet}")
        combined = "\n\n".join(parts)
        return combined[:max_chars]

    def _get_bm25_context(
        self,
        crawled_pages: dict,
        enricher_bm25_key: str,
        orchestrator=None,
        relevant_page_roles: Optional[list[str]] = None,
    ) -> str:
        """
        Runs BM25 selection over crawled pages for this enricher.

        Parameters
        ----------
        crawled_pages       : dict of page_role -> page_record
        enricher_bm25_key   : BM25 query key (corporate_query | identity_query | ...)
        orchestrator        : optional WebSearchOrchestrator instance
        relevant_page_roles : optional list of page role prefixes to restrict BM25 to
        """
        from backend.pipeline.content_segmenter import segment_for_enricher
        return segment_for_enricher(
            crawled_pages=crawled_pages,
            enricher_key=enricher_bm25_key,
            orchestrator=orchestrator,
            relevant_page_roles=relevant_page_roles,
        )

    def _run_fallback(
        self,
        startup_name: str,
        missing_field_keys: list[str],
        orchestrator,
        clean_name: str = "",
        brand_name: str = "",
        existing_result: Optional[dict] = None,
    ) -> dict:
        """
        Fires fallback web searches for missing fields and runs a slim targeted
        re-extraction LLM call to fill only those missing fields.

        Parameters
        ----------
        startup_name       : raw startup name
        missing_field_keys : list of field keys that are empty (from _detect_missing_fields)
        orchestrator       : WebSearchOrchestrator instance
        clean_name         : resolved brand name for query formatting (defaults to startup_name)
        brand_name         : confirmed brand name (defaults to clean_name)
        existing_result    : the enricher's existing output dict (to merge into)

        Returns
        -------
        dict — merged result with fallback-filled fields
        """
        _clean = clean_name or startup_name
        _brand = brand_name or _clean
        combined = dict(existing_result or {})
        fallback_snippets_by_field: dict[str, list[dict]] = {}

        for field_key in missing_field_keys:
            self.log(f"Fallback: running search for missing field='{field_key}'")
            records = orchestrator.run_fallback_for_field(
                enricher_key=field_key,
                clean_name=_clean,
                brand_name=_brand,
            )
            if records:
                fallback_snippets_by_field[field_key] = records

        if not fallback_snippets_by_field:
            self.log("Fallback: no snippets found for any missing field", level="warning")
            return combined

        # Build a slim targeted re-extraction prompt
        snippets_text = self._get_snippet_context(
            search_snippets=fallback_snippets_by_field,
            field_keys=list(fallback_snippets_by_field.keys()),
            max_chars=2500,
        )
        target_fields = {k: None for k in missing_field_keys}
        prompt = (
            f"You are a startup intelligence analyst. For startup '{startup_name}', extract ONLY the "
            f"following missing fields using the search snippets below. Return a JSON object with ONLY "
            f"these keys: {list(missing_field_keys)}.\n\n"
            f"FALLBACK SEARCH SNIPPETS:\n{snippets_text}\n\n"
            f"Return ONLY a valid JSON object. Do NOT hallucinate. Use null if not found.\n"
            f"Target keys: {json.dumps(target_fields)}"
        )

        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=3000)
        if raw and isinstance(raw, dict):
            for field_key in missing_field_keys:
                val = raw.get(field_key)
                if val is not None and val != "" and val != [] and val != {}:
                    combined[field_key] = val
                    self.log(f"Fallback filled field='{field_key}'")
        else:
            self.log("Fallback re-extraction returned no usable data", level="warning")

        return combined

    # -----------------------------------------------------------------------
    # Enrichment metadata helpers
    # -----------------------------------------------------------------------

    def build_enrichment_metadata_patch(
        self,
        section: str,
        duration_ms: float,
        model_used: str = "",
        fallback_used: bool = False,
        error: Optional[str] = None,
    ) -> dict:
        """Builds the enrichment_metadata partial update for this section."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        return {
            "last_enriched_at": now,
            f"section_{section}_completed_at": now,
            f"section_{section}_duration_ms": round(duration_ms),
            f"section_{section}_model": model_used,
            f"section_{section}_fallback_used": fallback_used,
            f"section_{section}_error": error,
        }

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------

    def log(self, message: str, level: str = "info"):
        """Logs a message with enricher-prefixed context."""
        full_msg = f"[{self.__class__.__name__}] {message}"
        getattr(logger, level, logger.info)(full_msg)

    def log_result(self, startup_name: str, result: dict, duration_ms: float):
        """Logs enrichment result summary."""
        section_keys = list(result.keys()) if isinstance(result, dict) else []
        self.log(
            f"Enriched '{startup_name}' → sections={section_keys}, "
            f"duration={round(duration_ms)}ms"
        )
