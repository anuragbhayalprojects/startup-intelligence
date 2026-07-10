"""
backend/services/startup_repo.py
-----------------------------------
Startup repository — focused CRUD for the startups table.

Extracted from backend/services/supabase_service.py as part of the modular
service layer refactor (feature/modular-company-intelligence-refactor).

All functions are re-exported via supabase_service.py for full backward compat.
New code should import directly from this module.

Provides:
  - check_existing_startup()     — Lookup by name
  - insert_startup()             — Insert new record
  - update_startup()             — Update by ID
  - upsert_startup()             — Insert-or-update
  - upsert_company_intelligence() — JSONB patch write (new)
  - upsert_enrichment_metadata()  — Metadata patch write (new)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("startup_intelligence.services.startup_repo")


def _get_supabase():
    """Lazy import to avoid circular dependency at module load."""
    from backend.services.supabase_service import supabase
    return supabase


def _map_startup_data(raw_data: dict) -> dict:
    """Maps raw startup dictionary keys to match exact database schema columns."""
    return {
        "startup_name": raw_data.get("startup_name"),
        "website": raw_data.get("website"),
        "linkedin_url": raw_data.get("linkedin_url") or raw_data.get("linkedin_company_url"),
        "linkedin_company_url": raw_data.get("linkedin_company_url") or raw_data.get("linkedin_url"),
        "city": raw_data.get("city") or "Unknown",
        "state": raw_data.get("state") or "Unknown",
        "country": raw_data.get("country") or "India",
        "industry": raw_data.get("industry") or "Financial Services",
        "sector": raw_data.get("sector") or "Unknown",
        "subsector": raw_data.get("subsector") or "Unknown",
        "business_models": raw_data.get("business_models") or [],
        "industry_relevance": raw_data.get("industry_relevance") or [],
        "tags": raw_data.get("tags") or [],
        "funding_stage": (
            raw_data.get("funding_stage")
            or raw_data.get("startup_stage")
            or raw_data.get("stage")
            or "Unknown"
        ),
        "founded_year": raw_data.get("founded_year"),
        "description": raw_data.get("description", ""),
        "source": raw_data.get("source", "Unknown"),
        "source_url": raw_data.get("source_url", ""),
        "headquarters": raw_data.get("headquarters") or "Unknown",
        "brand_name": raw_data.get("brand_name") or raw_data.get("startup_name"),
        "legal_name": raw_data.get("legal_name") or "",
        "identity_confidence": raw_data.get("identity_confidence") or 0.0,
        "status": raw_data.get("status") or raw_data.get("startup_status") or "Screening",
        "verification_notes": raw_data.get("verification_notes") or "",
    }


def check_existing_startup(startup_name: str) -> Optional[dict]:
    """Looks up a startup by name. Returns the first matching row or None."""
    try:
        response = _get_supabase().table("startups").select("*").eq(
            "startup_name", startup_name
        ).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"[StartupRepo] check_existing_startup failed for '{startup_name}': {e}")
    return None


def insert_startup(data: dict) -> Optional[list]:
    """Inserts a new startup row. Auto-assigns FPRs on success."""
    try:
        response = _get_supabase().table("startups").insert(data).execute()
        print(f"Inserted startup: {data.get('startup_name')}")
        if response.data:
            try:
                from backend.api.routes.startups import assign_fprs_for_startup
                assign_fprs_for_startup(response.data[0]["id"])
            except Exception as e:
                print(f"⚠️ Failed to auto-assign FPRs on insert: {e}")
        return response.data
    except Exception as e:
        logger.error(f"[StartupRepo] insert_startup failed: {e}")
        return None


def update_startup(startup_id: int, data: dict) -> Optional[list]:
    """Updates a startup row by ID."""
    try:
        response = _get_supabase().table("startups").update(data).eq("id", startup_id).execute()
        print(f"Updated startup: {data.get('startup_name')}")
        return response.data
    except Exception as e:
        logger.error(f"[StartupRepo] update_startup failed for id={startup_id}: {e}")
        return None


def upsert_startup(data: dict) -> Optional[list]:
    """Insert-or-update a startup by name."""
    mapped_data = _map_startup_data(data)
    existing = check_existing_startup(mapped_data.get("startup_name"))
    if existing:
        print(f"Startup already exists. Updating: {mapped_data.get('startup_name')}")
        
        # Retain the validated startup name! Do not overwrite it.
        mapped_data["startup_name"] = existing.get("startup_name") or mapped_data["startup_name"]
        
        # Keep adding/merging the sources instead of overwriting
        existing_source = existing.get("source") or ""
        new_source = mapped_data.get("source") or ""
        if new_source and new_source not in existing_source:
            if existing_source:
                mapped_data["source"] = f"{existing_source}, {new_source}"
            else:
                mapped_data["source"] = new_source
        else:
            mapped_data["source"] = existing_source or "Unknown"

        # Keep adding/merging the source URLs
        existing_url = existing.get("source_url") or ""
        new_url = mapped_data.get("source_url") or ""
        if new_url and new_url not in existing_url:
            if existing_url:
                mapped_data["source_url"] = f"{existing_url}, {new_url}"
            else:
                mapped_data["source_url"] = new_url
        else:
            mapped_data["source_url"] = existing_url

        return update_startup(existing["id"], mapped_data)
        
    print(f"New startup detected. Inserting: {mapped_data.get('startup_name')}")
    return insert_startup(mapped_data)


def upsert_company_intelligence(startup_id: int, ci_patch: dict) -> bool:
    """
    Applies a partial JSONB merge-patch to startups.company_intelligence.
    New modular function — not in legacy supabase_service.py.
    """
    try:
        sb = _get_supabase()
        current = sb.table("startups").select("company_intelligence").eq("id", startup_id).execute()
        current_ci = (current.data[0] if current.data else {}).get("company_intelligence") or {}
        merged = {**current_ci, **ci_patch}
        sb.table("startups").update({"company_intelligence": merged}).eq("id", startup_id).execute()
        return True
    except Exception as e:
        logger.error(f"[StartupRepo] upsert_company_intelligence failed for id={startup_id}: {e}")
        return False


def upsert_enrichment_metadata(startup_id: int, meta_patch: dict) -> bool:
    """
    Applies a partial merge-patch to startups.enrichment_metadata.
    New modular function — not in legacy supabase_service.py.
    """
    try:
        sb = _get_supabase()
        current = sb.table("startups").select("enrichment_metadata").eq("id", startup_id).execute()
        current_meta = (current.data[0] if current.data else {}).get("enrichment_metadata") or {}
        merged = {**current_meta, **meta_patch}
        sb.table("startups").update({"enrichment_metadata": merged}).eq("id", startup_id).execute()
        return True
    except Exception as e:
        logger.error(f"[StartupRepo] upsert_enrichment_metadata failed for id={startup_id}: {e}")
        return False
