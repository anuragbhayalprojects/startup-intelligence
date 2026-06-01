from supabase import create_client
from backend.utils.config import SUPABASE_URL, SUPABASE_KEY
import logging

print("SUPABASE_URL:", SUPABASE_URL)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def map_startup_data(raw_data):
    """Maps raw startup dictionary keys to match exact database schema columns."""
    return {
        "startup_name": raw_data.get("startup_name"),
        "website": raw_data.get("website"),
        "city": raw_data.get("city") or raw_data.get("hq_city") or "Unknown",
        "state": raw_data.get("state") or raw_data.get("hq_state") or "Unknown",
        "country": raw_data.get("country") or raw_data.get("hq_country") or "India",
        "sector": raw_data.get("sector") or "Unknown",
        "subsector": raw_data.get("subsector") or "Unknown",
        "funding_stage": raw_data.get("funding_stage") or raw_data.get("stage") or "Unknown",
        "founded_year": raw_data.get("founded_year"),
        "description": raw_data.get("description", ""),
        "source": raw_data.get("source", "Unknown"),
        "source_url": raw_data.get("source_url", "")
    }


def check_existing_startup(startup_name):

    response = (
        supabase
        .table("startups")
        .select("*")
        .eq("startup_name", startup_name)
        .execute()
    )

    if response.data and len(response.data) > 0:
        return response.data[0]

    return None


def insert_startup(data):

    response = (
        supabase
        .table("startups")
        .insert(data)
        .execute()
    )

    print(f"Inserted startup: {data.get('startup_name')}")

    return response.data


def update_startup(startup_id, data):

    response = (
        supabase
        .table("startups")
        .update(data)
        .eq("id", startup_id)
        .execute()
    )

    print(f"Updated startup: {data.get('startup_name')}")

    return response.data


def upsert_startup(data):

    mapped_data = map_startup_data(data)
    existing = check_existing_startup(
        mapped_data.get("startup_name")
    )

    if existing:

        print(
            f"Startup already exists. Updating: "
            f"{mapped_data.get('startup_name')}"
        )

        return update_startup(
            existing["id"],
            mapped_data
        )

    print(
        f"New startup detected. Inserting: "
        f"{mapped_data.get('startup_name')}"
    )

    return insert_startup(mapped_data)


def save_startup_analysis(startup_id, analysis_json):
    """
    Saves the structured AI analysis for a startup in the startup_analysis table.
    """
    if not analysis_json or "error" in analysis_json:
        logging.warning(f"Skipping analysis insert for startup_id {startup_id} due to invalid analysis_json.")
        return None

    # Parse nested fields from the analysis JSON
    summary = analysis_json.get("summary", {})
    bfsi = analysis_json.get("bfsi_relevance", {})
    fit = analysis_json.get("strategic_fit", {})
    scoring = analysis_json.get("scoring", {})
    classification = analysis_json.get("classification", {})
    
    # Map integration feasibility string to score
    feasibility_map = {"high": 100, "medium": 50, "low": 10}
    feasibility_str = str(fit.get("integration_feasibility", "Medium")).lower()
    feasibility_score = feasibility_map.get(feasibility_str, 50)
    
    # Extract primary ICICI entity
    use_cases = bfsi.get("use_cases", [])
    primary_entity = use_cases[0].get("icici_entity", "ICICI Bank") if use_cases else "ICICI Bank"
    
    def to_int(val, default=0):
        try:
            return int(val)
        except Exception:
            return default

    analysis_data = {
        "startup_id": startup_id,
        "ai_summary": summary.get("one_liner", "") or summary.get("business_model", ""),
        "bfsi_relevance_score": to_int(bfsi.get("relevance_score")),
        "enterprise_readiness_score": to_int(fit.get("enterprise_readiness")),
        "strategic_fit_score": to_int(fit.get("enterprise_readiness")), # Fallback mapping
        "integration_feasibility_score": feasibility_score,
        "priority_score": to_int(scoring.get("overall_priority_score")),
        "icici_primary_entity": primary_entity,
        "use_cases": use_cases,
        "co_creation_opportunities": [fit.get("partnership_opportunity")] if fit.get("partnership_opportunity") else [],
        "analysis_json": analysis_json
    }
    
    # Check if analysis already exists for this startup
    existing = (
        supabase
        .table("startup_analysis")
        .select("id")
        .eq("startup_id", startup_id)
        .execute()
    )
    
    if existing.data and len(existing.data) > 0:
        response = (
            supabase
            .table("startup_analysis")
            .update(analysis_data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        print(f"Updated startup analysis in DB for ID: {startup_id}")
    else:
        response = (
            supabase
            .table("startup_analysis")
            .insert(analysis_data)
            .execute()
        )
        print(f"Inserted new startup analysis in DB for ID: {startup_id}")
        
    return response.data