"""
backend/enrichment/re_enrichment_service.py
----------------------------------------------
Section-wise re-enrichment service for Startup Intelligence OS.

Provides targeted re-enrichment of individual company_intelligence sections
without triggering a full pipeline run.

Supports:
  - Per-section re-enrichment: identity, products, funding, competitors (intelligence)
  - Full re-enrichment (all sections)
  - Source refresh option (re-crawl website before enriching)
  - Partial JSONB merge-patch update to startups.company_intelligence
  - enrichment_metadata tracking per section

Called by the new API endpoints in backend/api/routes/enrichment.py.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("startup_intelligence.re_enrichment")


# ---------------------------------------------------------------------------
# Startup loader
# ---------------------------------------------------------------------------

def _load_startup(startup_id: int) -> Optional[dict]:
    """Loads startup data and current company_intelligence from Supabase."""
    try:
        from backend.services.supabase_service import supabase
        res = supabase.table("startups").select(
            "id, startup_name, website, linkedin_company_url, company_intelligence, "
            "enrichment_metadata, industry, sector, description"
        ).eq("id", startup_id).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error(f"[ReEnrichment] Failed to load startup {startup_id}: {e}")
    return None


def _load_article_context(startup_id: int) -> dict:
    """Loads most recent news article context for this startup."""
    try:
        from backend.services.supabase_service import supabase
        res = supabase.table("startup_news").select(
            "headline, description, cleaned_source_payload, raw_source_payload"
        ).eq("startup_id", startup_id).order("created_at", desc=True).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.debug(f"[ReEnrichment] Failed to load news context for {startup_id}: {e}")
    return {}


def _collect_fresh_source(startup_name: str, website_url: str) -> str:
    """Collects fresh website content for re-enrichment with source refresh."""
    try:
        from backend.pipeline.source_collector import collect_source_payload, format_source_payload_for_prompt
        payload = collect_source_payload(startup_name, website_url=website_url)
        return format_source_payload_for_prompt(payload)
    except Exception as e:
        logger.warning(f"[ReEnrichment] Source refresh failed for '{startup_name}': {e}")
        return ""


def _apply_ci_patch(startup_id: int, ci_patch: dict, enrichment_meta_patch: dict):
    """Applies a partial JSONB merge-patch to startups.company_intelligence."""
    try:
        from backend.services.supabase_service import supabase

        # Fetch current company_intelligence
        res = supabase.table("startups").select("company_intelligence, enrichment_metadata").eq("id", startup_id).execute()
        if not res.data:
            logger.error(f"[ReEnrichment] Startup {startup_id} not found for JSONB update")
            return False

        current_ci = res.data[0].get("company_intelligence") or {}
        current_meta = res.data[0].get("enrichment_metadata") or {}

        # Merge patch
        updated_ci = {**current_ci, **ci_patch}
        updated_meta = {**current_meta, **enrichment_meta_patch}

        # Persist
        supabase.table("startups").update({
            "company_intelligence": updated_ci,
            "enrichment_metadata": updated_meta,
        }).eq("id", startup_id).execute()

        # Sync company_intelligence products & competitors with market_intelligence columns
        try:
            from backend.services.supabase_service import sync_company_intelligence_to_market_intelligence
            sync_company_intelligence_to_market_intelligence(startup_id)
        except Exception as sync_err:
            logger.warning(f"[ReEnrichment] Failed to sync CI to MI after patch: {sync_err}")

        logger.info(f"[ReEnrichment] Applied CI patch for startup {startup_id}: sections={list(ci_patch.keys())}")
        return True
    except Exception as e:
        logger.error(f"[ReEnrichment] JSONB patch failed for {startup_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Per-section re-enrichment entry points
# ---------------------------------------------------------------------------

def re_enrich_section(
    startup_id: int,
    section: str,
    refresh_source: bool = False,
) -> dict:
    """
    Re-enriches a single section of company_intelligence.

    Parameters
    ----------
    startup_id     : Supabase startups.id
    section        : One of: identity, products, funding, intelligence
    refresh_source : If True, re-crawls website before enriching

    Returns
    -------
    dict: {
        success: bool,
        section: str,
        startup_name: str,
        duration_ms: float,
        error: str | None,
        updated_section: dict
    }
    """
    start_time = time.perf_counter()
    logger.info(f"[ReEnrichment] Starting section='{section}' re-enrichment for startup_id={startup_id}")

    result = {
        "success": False,
        "section": section,
        "startup_id": startup_id,
        "startup_name": "",
        "duration_ms": 0.0,
        "error": None,
        "updated_section": {},
    }

    # 1. Load startup
    startup = _load_startup(startup_id)
    if not startup:
        result["error"] = f"Startup {startup_id} not found"
        return result

    startup_name = startup.get("startup_name", "")
    website_url = startup.get("website") or ""
    existing_ci = startup.get("company_intelligence") or {}
    result["startup_name"] = startup_name

    # 2. Build source context
    if refresh_source and website_url:
        logger.info(f"[ReEnrichment] Refreshing source for '{startup_name}' from {website_url}")
        source_context = _collect_fresh_source(startup_name, website_url)
    else:
        # Use cleaned_source_payload from most recent news article
        article_ctx = _load_article_context(startup_id)
        cleaned = article_ctx.get("cleaned_source_payload") or {}
        if cleaned:
            from backend.pipeline.content_segmenter import format_segmented_payload_for_enrichment
            source_context = format_segmented_payload_for_enrichment(cleaned)
        else:
            # Fallback: use description + existing CI context
            desc = startup.get("description", "")
            source_context = f"DESCRIPTION:\n{desc}\n\nHEADQUARTERS: {startup.get('headquarters', '')}"

    # 3. Run targeted enricher
    enricher_map = {
        "identity": "backend.enrichment.identity_enricher.IdentityEnricher",
        "products": "backend.enrichment.product_enricher.ProductEnricher",
        "funding": "backend.enrichment.funding_enricher.FundingEnricher",
        "intelligence": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
        "competitors": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    }

    enricher_path = enricher_map.get(section)
    if not enricher_path:
        result["error"] = f"Unknown section '{section}'. Valid: identity, products, funding, intelligence"
        return result

    try:
        module_path, class_name = enricher_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        enricher_cls = getattr(module, class_name)
        enricher = enricher_cls()

        # Build kwargs based on section
        enrich_kwargs = {
            "startup_name": startup_name,
            "source_context": source_context,
            "existing_data": existing_ci,
        }
        if section == "funding":
            enrich_kwargs["website_url"] = website_url
        if section in ("intelligence", "competitors"):
            enrich_kwargs["business_profile"] = existing_ci.get("business_profile", {})

        enrich_start = time.perf_counter()
        ci_patch = enricher.enrich(**enrich_kwargs)
        enrich_duration_ms = (time.perf_counter() - enrich_start) * 1000

        if not ci_patch:
            result["error"] = f"Enricher returned no data for section '{section}'"
            result["duration_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            return result

        # 4. Build metadata patch
        now = datetime.now(timezone.utc).isoformat()
        enrichment_meta_patch = {
            "last_enriched_at": now,
            f"section_{section}_completed_at": now,
            f"section_{section}_duration_ms": round(enrich_duration_ms),
            "enrichment_version": "3.0",
        }

        # Track completed sections
        existing_meta = startup.get("enrichment_metadata") or {}
        completed_sections = existing_meta.get("sections_completed") or []
        if section not in completed_sections:
            completed_sections.append(section)
        enrichment_meta_patch["sections_completed"] = completed_sections

        # 5. Apply JSONB patch
        success = _apply_ci_patch(startup_id, ci_patch, enrichment_meta_patch)

        result.update({
            "success": success,
            "updated_section": ci_patch,
            "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
        })

        logger.info(
            f"[ReEnrichment] Completed section='{section}' for '{startup_name}' "
            f"in {result['duration_ms']}ms (success={success})"
        )

    except Exception as e:
        logger.error(f"[ReEnrichment] Section '{section}' enrichment failed for {startup_id}: {e}")
        result["error"] = str(e)
        result["duration_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

    return result


def re_enrich_all(startup_id: int, refresh_source: bool = False) -> dict:
    """
    Re-enriches all sections in order: identity → products → funding → intelligence.

    Returns
    -------
    dict: {
        success: bool,
        startup_name: str,
        sections: {section: result_dict},
        total_duration_ms: float,
        sections_completed: list,
        errors: list
    }
    """
    start_time = time.perf_counter()
    sections = ["identity", "products", "funding", "intelligence"]
    results = {}
    errors = []
    completed = []

    startup = _load_startup(startup_id)
    startup_name = (startup or {}).get("startup_name", f"ID:{startup_id}")

    logger.info(f"[ReEnrichment] Starting full re-enrichment for '{startup_name}' (id={startup_id})")

    for section in sections:
        section_result = re_enrich_section(startup_id, section, refresh_source=refresh_source)
        results[section] = section_result
        if section_result.get("success"):
            completed.append(section)
        else:
            errors.append(f"{section}: {section_result.get('error', 'unknown error')}")

    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    logger.info(
        f"[ReEnrichment] Full re-enrichment for '{startup_name}' completed: "
        f"sections={completed}, errors={len(errors)}, total={total_duration_ms}ms"
    )

    return {
        "success": len(completed) > 0,
        "startup_id": startup_id,
        "startup_name": startup_name,
        "sections": results,
        "sections_completed": completed,
        "sections_failed": [s for s in sections if s not in completed],
        "errors": errors,
        "total_duration_ms": total_duration_ms,
    }
