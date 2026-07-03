"""
backend/api/routes/observability.py
--------------------------------------
Observability API routes for Startup Intelligence OS.

NOTE: Existing observability endpoints in main.py are preserved for full
backward compatibility. This module adds NEW observability endpoints:

  GET  /api/observability/prompt-ledger    — AI call log with provider/model/fallback info
  GET  /api/observability/enrichment-stats — Per-section enrichment performance stats
  GET  /api/observability/ai-routing       — AI routing decision history
  GET  /api/observability/health           — System health (AI provider, DB, pipeline)

Future: As stabilization completes, /api/observability/traces/* will migrate here
from main.py.
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging
import os

logger = logging.getLogger("startup_intelligence.api.observability")
router = APIRouter()


@router.get("/observability/prompt-ledger")
async def get_prompt_ledger(
    limit: int = Query(default=50, ge=1, le=200),
    agent_name: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Returns recent AI prompt ledger entries with routing metadata.
    Filters by agent_name or provider (openrouter / ollama) if specified.
    """
    try:
        from backend.services.supabase_service import supabase
        query = supabase.table("obs_prompt_ledger").select("*").order(
            "created_at", desc=True
        ).limit(limit)
        result = query.execute()
        rows = result.data or []

        # Filter by provider from parsed_response._routing.provider
        if provider:
            filtered = []
            for row in rows:
                parsed = row.get("parsed_response") or {}
                routing = parsed.get("_routing", {}) if isinstance(parsed, dict) else {}
                if routing.get("provider", "").lower() == provider.lower():
                    filtered.append(row)
            rows = filtered

        if agent_name:
            rows = [r for r in rows if (r.get("agent_name") or "").lower() == agent_name.lower()]

        return {
            "status": "ok",
            "count": len(rows),
            "entries": rows,
        }
    except Exception as e:
        logger.error(f"[ObservabilityAPI] prompt-ledger failed: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/observability/enrichment-stats")
async def get_enrichment_stats(
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Returns enrichment performance statistics per startup.
    Reads enrichment_metadata from the startups table.
    """
    try:
        from backend.services.supabase_service import supabase
        result = supabase.table("startups").select(
            "id, startup_name, enrichment_metadata, company_intelligence"
        ).order("updated_at", desc=True).limit(limit).execute()

        rows = result.data or []
        stats = []
        for row in rows:
            meta = row.get("enrichment_metadata") or {}
            ci = row.get("company_intelligence") or {}
            sections_done = meta.get("sections_completed") or []
            stats.append({
                "startup_id": row["id"],
                "startup_name": row.get("startup_name", ""),
                "enrichment_version": meta.get("enrichment_version", ""),
                "last_enriched_at": meta.get("last_enriched_at"),
                "sections_completed": sections_done,
                "sections_count": len(sections_done),
                "ci_has_basic_info": bool(ci.get("basic_information", {}).get("canonical_name")),
                "ci_has_products": bool(ci.get("products_services")),
                "ci_has_funding": bool(ci.get("funding_details", {}).get("latest_stage")),
                "ci_has_competitors": bool(ci.get("competitors")),
            })

        return {
            "status": "ok",
            "count": len(stats),
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"[ObservabilityAPI] enrichment-stats failed: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/observability/ai-routing")
async def get_ai_routing_history(
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Returns AI routing decision history — which calls went to OpenRouter vs Ollama.
    Parsed from obs_prompt_ledger._routing metadata.
    """
    try:
        from backend.services.supabase_service import supabase
        result = supabase.table("obs_prompt_ledger").select(
            "created_at, agent_name, parsed_response, duration_ms"
        ).order("created_at", desc=True).limit(limit).execute()

        rows = result.data or []
        routing_entries = []
        for row in rows:
            parsed = row.get("parsed_response") or {}
            routing = parsed.get("_routing", {}) if isinstance(parsed, dict) else {}
            if routing:
                routing_entries.append({
                    "created_at": row.get("created_at"),
                    "agent_name": row.get("agent_name", ""),
                    "provider": routing.get("provider", "unknown"),
                    "model": routing.get("model", ""),
                    "fallback_used": routing.get("fallback_used", False),
                    "fallback_reason": routing.get("fallback_reason"),
                    "duration_ms": row.get("duration_ms", 0),
                })

        # Summary stats
        openrouter_count = sum(1 for e in routing_entries if e["provider"] == "openrouter")
        ollama_count = sum(1 for e in routing_entries if e["provider"] == "ollama")
        fallback_count = sum(1 for e in routing_entries if e["fallback_used"])

        return {
            "status": "ok",
            "summary": {
                "total_calls": len(routing_entries),
                "openrouter_calls": openrouter_count,
                "ollama_calls": ollama_count,
                "fallback_triggered": fallback_count,
            },
            "entries": routing_entries,
        }
    except Exception as e:
        logger.error(f"[ObservabilityAPI] ai-routing failed: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/observability/health")
async def get_system_health():
    """
    Returns system health status for AI provider, database, and pipeline.
    Safe to call frequently — minimal DB load (single row reads).
    """
    health: dict = {
        "status": "ok",
        "components": {},
        "timestamp": None,
    }

    from datetime import datetime, timezone
    health["timestamp"] = datetime.now(timezone.utc).isoformat()

    # 1. AI routing status
    try:
        from backend.ai.router import get_routing_status
        routing = get_routing_status()
        health["components"]["ai_router"] = {
            "status": "ok",
            "active_provider": routing.get("active_provider", "unknown"),
            "openrouter_enabled": routing.get("openrouter_enabled", False),
            "openrouter_key_configured": routing.get("openrouter_key_configured", False),
        }
    except Exception as e:
        health["components"]["ai_router"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"

    # 2. Supabase connectivity
    try:
        from backend.services.supabase_service import supabase
        supabase.table("startups").select("id").limit(1).execute()
        health["components"]["database"] = {"status": "ok", "provider": "supabase"}
    except Exception as e:
        health["components"]["database"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"

    # 3. Pipeline config
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "pipeline_config.json"
        )
        with open(config_path) as f:
            import json
            cfg = json.load(f)
        health["components"]["pipeline"] = {
            "status": "ok",
            "version": cfg.get("pipeline_version", ""),
            "modular_enrichment": cfg.get("feature_flags", {}).get("use_modular_enrichment", False),
            "company_intelligence_jsonb": cfg.get("feature_flags", {}).get("use_company_intelligence_jsonb", False),
        }
    except Exception as e:
        health["components"]["pipeline"] = {"status": "error", "error": str(e)}

    return health
