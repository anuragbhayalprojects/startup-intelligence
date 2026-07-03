"""
backend/api/routes/scraping.py
---------------------------------
Scraping management API routes for Startup Intelligence OS.

NOTE: Core scraping endpoints (/api/scrape, /api/scrape/status, /api/scrape/sources)
remain in startups.py for full backward compatibility per the phased refactor strategy.

This module adds NEW scraping-specific management endpoints:
  GET  /api/scrape/pipeline-config   — Returns active pipeline_config.json
  GET  /api/scrape/routing-config    — Returns model_routing.json (safe subset)
  POST /api/scrape/logs/clear        — Clears the in-memory scrape log
  GET  /api/scrape/logs              — Returns current scrape logs (paginated)

Future: as stabilization completes, /api/scrape/*, /api/scrape/sources/* will
migrate here from startups.py.
"""

from fastapi import APIRouter, Query
from typing import Optional
import os
import json
import logging

logger = logging.getLogger("startup_intelligence.api.scraping")
router = APIRouter()

_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config"
)


@router.get("/scrape/pipeline-config")
async def get_pipeline_config():
    """Returns the active pipeline_config.json feature flags."""
    try:
        path = os.path.join(_CONFIG_DIR, "pipeline_config.json")
        with open(path, "r") as f:
            cfg = json.load(f)
        # Strip internal comment keys before returning
        cfg.pop("_comment", None)
        return {"status": "ok", "config": cfg}
    except FileNotFoundError:
        return {"status": "not_found", "config": {}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/scrape/routing-config")
async def get_routing_config():
    """
    Returns the active AI model routing configuration (safe public subset).
    Does not expose API keys — only provider, model names, and routing rules.
    """
    try:
        path = os.path.join(_CONFIG_DIR, "model_routing.json")
        with open(path, "r") as f:
            cfg = json.load(f)
        # Return only safe public fields
        safe = {
            "routing": cfg.get("routing", {}),
            "openrouter_models": cfg.get("openrouter", {}).get("models", {}),
            "ollama_models": cfg.get("ollama", {}).get("models", {}),
            "fallback_triggers": cfg.get("fallback_triggers", []),
        }
        return {"status": "ok", "config": safe}
    except FileNotFoundError:
        return {"status": "not_found", "config": {}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/scrape/logs/clear")
async def clear_scrape_logs():
    """Clears the in-memory scrape log buffer."""
    try:
        from backend.api.routes.startups import SCRAPE_STATUS, status_lock
        with status_lock:
            SCRAPE_STATUS["logs"] = []
        return {"status": "cleared"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/scrape/logs")
async def get_scrape_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Returns paginated current scrape logs from the in-memory buffer."""
    try:
        from backend.api.routes.startups import SCRAPE_STATUS, status_lock
        with status_lock:
            all_logs = list(SCRAPE_STATUS.get("logs", []))
        paginated = all_logs[offset: offset + limit]
        return {
            "status": "ok",
            "total": len(all_logs),
            "offset": offset,
            "limit": limit,
            "logs": paginated,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
