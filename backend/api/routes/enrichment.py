"""
backend/api/routes/enrichment.py
-----------------------------------
Re-enrichment API endpoints for Startup Intelligence OS.

Provides section-wise re-enrichment of individual company_intelligence sections
without requiring a full pipeline run.

Endpoints:
  POST /api/startups/{id}/enrich/identity      — Re-run identity enricher
  POST /api/startups/{id}/enrich/products      — Re-run product enricher
  POST /api/startups/{id}/enrich/funding       — Re-run funding enricher
  POST /api/startups/{id}/enrich/competitors   — Re-run intelligence enricher
  POST /api/startups/{id}/enrich/all           — Full re-enrichment (all sections)
  GET  /api/startups/{id}/enrichment/status    — Check enrichment metadata
  GET  /api/ai/routing-status                  — Check active AI provider status
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Literal
import logging

logger = logging.getLogger("startup_intelligence.api.enrichment")

router = APIRouter()

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EnrichmentRequest(BaseModel):
    refresh_source: bool = False  # If True, re-crawls website before enriching
    force: bool = False           # If True, re-enriches even if recently enriched


class EnrichAllRequest(BaseModel):
    refresh_source: bool = False
    sections: Optional[list] = None  # None = all sections


# ---------------------------------------------------------------------------
# Section-wise re-enrichment endpoints
# ---------------------------------------------------------------------------

VALID_SECTIONS = {"identity", "products", "funding", "intelligence", "competitors"}


@router.post("/startups/{startup_id}/enrich/{section}")
async def enrich_section(
    startup_id: int,
    section: str,
    request: EnrichmentRequest = EnrichmentRequest(),
    background_tasks: BackgroundTasks = None,
):
    """
    Re-enriches a single section of company_intelligence for a startup.

    Path params:
      startup_id  : Supabase startups.id
      section     : identity | products | funding | intelligence | competitors

    Body params:
      refresh_source : Re-crawl website before enriching (default: false)
      force          : Skip recency check (default: false)
    """
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{section}'. Valid sections: {sorted(VALID_SECTIONS)}"
        )

    try:
        from backend.enrichment.re_enrichment_service import re_enrich_section
        result = re_enrich_section(
            startup_id=startup_id,
            section=section,
            refresh_source=request.refresh_source,
        )

        if not result.get("success") and result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "status": "success" if result.get("success") else "partial",
            "startup_id": startup_id,
            "startup_name": result.get("startup_name", ""),
            "section": section,
            "duration_ms": result.get("duration_ms", 0),
            "updated_fields": list(result.get("updated_section", {}).keys()),
            "error": result.get("error"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EnrichmentAPI] Section '{section}' failed for startup {startup_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/startups/{startup_id}/enrich/all")
async def enrich_all_sections(
    startup_id: int,
    request: EnrichAllRequest = EnrichAllRequest(),
):
    """
    Runs full re-enrichment of all company_intelligence sections for a startup.
    Runs: identity → products → funding → intelligence in order.
    """
    try:
        from backend.enrichment.re_enrichment_service import re_enrich_all
        result = re_enrich_all(
            startup_id=startup_id,
            refresh_source=request.refresh_source,
        )

        return {
            "status": "success" if result.get("success") else "partial",
            "startup_id": startup_id,
            "startup_name": result.get("startup_name", ""),
            "sections_completed": result.get("sections_completed", []),
            "sections_failed": result.get("sections_failed", []),
            "total_duration_ms": result.get("total_duration_ms", 0),
            "errors": result.get("errors", []),
        }
    except Exception as e:
        logger.error(f"[EnrichmentAPI] Full re-enrichment failed for startup {startup_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Enrichment status endpoint
# ---------------------------------------------------------------------------

@router.get("/startups/{startup_id}/enrichment/status")
async def get_enrichment_status(startup_id: int):
    """
    Returns current enrichment metadata and company_intelligence completion status.
    """
    try:
        from backend.services.supabase_service import supabase
        res = supabase.table("startups").select(
            "id, startup_name, company_intelligence, enrichment_metadata, validation_metadata"
        ).eq("id", startup_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail=f"Startup {startup_id} not found")

        startup = res.data[0]
        enrichment_meta = startup.get("enrichment_metadata") or {}
        ci = startup.get("company_intelligence") or {}
        validation = startup.get("validation_metadata") or {}

        # Calculate completion
        sections_completed = enrichment_meta.get("sections_completed") or []
        all_sections = ["identity", "products", "funding", "intelligence"]
        sections_pending = [s for s in all_sections if s not in sections_completed]

        # Check CI section non-emptiness
        ci_populated = {
            "basic_information": bool(ci.get("basic_information", {}).get("canonical_name")),
            "founders_details": bool(ci.get("founders_details")),
            "business_profile": bool(ci.get("business_profile", {}).get("one_liner")),
            "products_services": bool(ci.get("products_services")),
            "funding_details": bool(ci.get("funding_details", {}).get("latest_stage")),
            "competitors": bool(ci.get("competitors")),
        }

        return {
            "startup_id": startup_id,
            "startup_name": startup.get("startup_name", ""),
            "enrichment_version": enrichment_meta.get("enrichment_version", ""),
            "last_enriched_at": enrichment_meta.get("last_enriched_at"),
            "sections_completed": sections_completed,
            "sections_pending": sections_pending,
            "ci_sections_populated": ci_populated,
            "resolution_confidence": validation.get("resolution_confidence", 0),
            "verification_status": validation.get("verification_status", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EnrichmentAPI] Status check failed for {startup_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# AI routing status endpoint
# ---------------------------------------------------------------------------

@router.get("/ai/routing-status")
async def get_ai_routing_status():
    """
    Returns the current AI routing configuration and active provider.
    Useful for verifying OpenRouter/Ollama routing without running an enrichment.
    """
    try:
        from backend.ai.router import get_routing_status
        return get_routing_status()
    except Exception as e:
        return {
            "error": str(e),
            "active_provider": "unknown",
            "openrouter_enabled": False,
        }
