"""
backend/services/news_repo.py
--------------------------------
News repository — focused CRUD for startup_news and related tables.

Extracted from backend/services/supabase_service.py as part of the modular
service layer refactor (feature/modular-company-intelligence-refactor).

All functions are re-exported via supabase_service.py for full backward compat.
New code should import directly from this module.

Provides:
  - save_startup_news()                — Insert a news record
  - get_startup_news()                 — Fetch news for a startup
  - save_source_payload()              — Save raw/cleaned source payload (new)
  - save_resolution_metadata()         — Save resolution metadata (new)
  - save_pipeline_status()             — Update pipeline_status JSONB (new)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("startup_intelligence.services.news_repo")


def _get_supabase():
    from backend.services.supabase_service import supabase
    return supabase


def save_startup_news(
    startup_id: int,
    headline: str,
    summary: str,
    source: str = "",
    source_url: str = "",
    published_at: Optional[str] = None,
    startup_mentions: Optional[list] = None,
    raw_source_payload: Optional[dict] = None,
    cleaned_source_payload: Optional[dict] = None,
    resolution_metadata: Optional[dict] = None,
    pipeline_status: Optional[dict] = None,
) -> Optional[dict]:
    """
    Inserts or updates a news record for a startup in startup_news table.
    Checks for URL deduplication before inserting.
    """
    try:
        sb = _get_supabase()
        # Check for duplicate by source_url
        if source_url:
            existing = sb.table("startup_news").select("id").eq(
                "source_url", source_url
            ).execute()
            if existing.data:
                logger.debug(f"[NewsRepo] Skipping duplicate news URL: {source_url}")
                return existing.data[0]

        record = {
            "startup_id": startup_id,
            "headline": headline,
            "summary": summary,
            "source": source,
            "source_url": source_url,
            "published_at": published_at or datetime.now(timezone.utc).isoformat(),
            "startup_mentions": startup_mentions or [],
            "raw_source_payload": raw_source_payload or {},
            "cleaned_source_payload": cleaned_source_payload or {},
            "resolution_metadata": resolution_metadata or {},
            "pipeline_status": pipeline_status or {},
        }
        result = sb.table("startup_news").insert(record).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"[NewsRepo] save_startup_news failed for startup_id={startup_id}: {e}")
    return None


def get_startup_news(startup_id: int) -> list:
    """Returns all news records for a startup, ordered newest first."""
    try:
        result = _get_supabase().table("startup_news").select("*").eq(
            "startup_id", startup_id
        ).order("published_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[NewsRepo] get_startup_news failed for startup_id={startup_id}: {e}")
        return []


def save_source_payload(
    news_id: int,
    raw_payload: Optional[dict] = None,
    cleaned_payload: Optional[dict] = None,
) -> bool:
    """
    Saves raw_source_payload and/or cleaned_source_payload to a startup_news row.
    New function — not in legacy supabase_service.py.
    """
    if not news_id:
        return False
    try:
        update_data: dict = {}
        if raw_payload is not None:
            update_data["raw_source_payload"] = raw_payload
        if cleaned_payload is not None:
            update_data["cleaned_source_payload"] = cleaned_payload
        if not update_data:
            return True
        _get_supabase().table("startup_news").update(update_data).eq("id", news_id).execute()
        return True
    except Exception as e:
        logger.error(f"[NewsRepo] save_source_payload failed for news_id={news_id}: {e}")
        return False


def save_resolution_metadata(news_id: int, resolution_metadata: dict) -> bool:
    """
    Saves resolution_metadata to a startup_news row.
    New function — not in legacy supabase_service.py.
    """
    try:
        _get_supabase().table("startup_news").update(
            {"resolution_metadata": resolution_metadata}
        ).eq("id", news_id).execute()
        return True
    except Exception as e:
        logger.error(f"[NewsRepo] save_resolution_metadata failed for news_id={news_id}: {e}")
        return False


def save_pipeline_status(news_id: int, stage: str, error: Optional[str] = None, extra: Optional[dict] = None) -> bool:
    """
    Updates the pipeline_status JSONB field for a startup_news row.
    New function — tracks current pipeline processing stage per article.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        current = _get_supabase().table("startup_news").select("pipeline_status").eq("id", news_id).execute()
        current_status = (current.data[0] if current.data else {}).get("pipeline_status") or {}
        completed = current_status.get("completed_stages", [])
        if stage not in completed:
            completed.append(stage)

        updated_status = {
            **current_status,
            "stage": stage,
            "completed_stages": completed,
            "last_updated_at": now,
            **({"error": error} if error else {}),
            **(extra or {}),
        }
        _get_supabase().table("startup_news").update(
            {"pipeline_status": updated_status}
        ).eq("id", news_id).execute()
        return True
    except Exception as e:
        logger.error(f"[NewsRepo] save_pipeline_status failed for news_id={news_id}: {e}")
        return False
