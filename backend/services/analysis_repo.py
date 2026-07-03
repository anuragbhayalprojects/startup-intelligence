"""
backend/services/analysis_repo.py
-------------------------------------
Analysis repository — focused CRUD for startup_analysis table.

Extracted from backend/services/supabase_service.py as part of the modular
service layer refactor (feature/modular-company-intelligence-refactor).

All functions are re-exported via supabase_service.py for full backward compat.
New code should import directly from this module.

Provides:
  - save_startup_analysis()   — Full analysis_json upsert (existing)
  - save_funding_rounds()     — Funding rounds update in startup_analysis (existing)
  - get_startup_analysis()    — Fetch analysis by startup_id (new)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("startup_intelligence.services.analysis_repo")


def _get_supabase():
    from backend.services.supabase_service import supabase
    return supabase


def get_startup_analysis(startup_id: int) -> Optional[dict]:
    """
    Fetches the most recent startup_analysis record for a startup.
    New function — not in legacy supabase_service.py.
    """
    try:
        result = _get_supabase().table("startup_analysis").select("*").eq(
            "startup_id", startup_id
        ).order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"[AnalysisRepo] get_startup_analysis failed for startup_id={startup_id}: {e}")
    return None


def save_funding_rounds(startup_id: int, funding_data: dict, analysis_id: Optional[int] = None) -> Optional[list]:
    """
    Saves structured funding round data into the startup_analysis table.
    funding_data: {rounds: [...], total_funding: str, latest_stage: str, latest_date: str}
    Updates by analysis_id if provided, otherwise by startup_id.
    """
    try:
        sb = _get_supabase()
        rounds = funding_data.get("rounds", [])
        latest_stage = funding_data.get("latest_stage", "")
        if not latest_stage and rounds:
            latest_stage = rounds[0].get("stage", "")

        update_payload = {
            "funding_rounds": rounds,
            "total_funding": funding_data.get("total_funding", ""),
            "latest_round_stage": latest_stage,
            "latest_round_date": funding_data.get("latest_date", ""),
            "last_funding_enriched_at": datetime.now(timezone.utc).isoformat(),
        }

        if analysis_id:
            response = sb.table("startup_analysis").update(update_payload).eq("id", analysis_id).execute()
        else:
            response = sb.table("startup_analysis").update(update_payload).eq("startup_id", startup_id).execute()

        # Sync funding stage and total to startups table
        s_payload = {
            "total_funding": funding_data.get("total_funding", ""),
            "latest_round_stage": latest_stage,
        }
        if latest_stage and latest_stage != "Unknown":
            s_payload["funding_stage"] = latest_stage
        try:
            sb.table("startups").update(s_payload).eq("id", startup_id).execute()
        except Exception as se:
            logger.warning(f"[AnalysisRepo] Failed to sync funding to startups table: {se}")

        print(f"💰 Saved {len(rounds)} funding round(s) to startup_analysis for startup_id {startup_id}")
        return response.data
    except Exception as e:
        logger.warning(f"[AnalysisRepo] save_funding_rounds failed for startup_id={startup_id}: {e}")
        return None
