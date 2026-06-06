from supabase import create_client
from backend.utils.config import SUPABASE_URL, SUPABASE_KEY
import logging

def format_outreach_message(msg):
    if not msg:
        return None
    if isinstance(msg, dict):
        if "subject_line" in msg and "body" in msg:
            return f"Subject: {msg['subject_line']}\n\n{msg['body']}"
        elif "subject" in msg and "body" in msg:
            return f"Subject: {msg['subject']}\n\n{msg['body']}"
        else:
            return "\n".join(f"{k.capitalize()}: {v}" for k, v in msg.items())
    return str(msg)


try:
    from backend.utils.taxonomy_mapper import normalize_taxonomy, normalize_business_models, normalize_industry_relevance, get_canonical_tags, get_canonical_founders
except ImportError:
    # Safe fallbacks if running in standalone scripts
    def normalize_taxonomy(name, i, s, sub): return i, s, sub
    def normalize_business_models(name, bm): return bm
    def normalize_industry_relevance(name, ir): return ir
    def get_canonical_tags(name, tags): return tags
    def get_canonical_founders(name): return None

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
        "industry": raw_data.get("industry") or "Financial Services",
        "sector": raw_data.get("sector") or "Unknown",
        "subsector": raw_data.get("subsector") or "Unknown",
        "business_models": raw_data.get("business_models") or [],
        "industry_relevance": raw_data.get("industry_relevance") or [],
        "tags": raw_data.get("tags") or [],
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
    
    if response.data:
        try:
            from backend.api.routes.startups import assign_fprs_for_startup
            assign_fprs_for_startup(response.data[0]["id"])
        except Exception as e:
            print(f"⚠️ Failed to auto-assign FPRs on insert: {e}")

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

    # Fetch actual startup brand name to apply high-precision overrides
    startup_name = ""
    try:
        s_res = supabase.table("startups").select("startup_name").eq("id", startup_id).execute()
        if s_res.data:
            startup_name = s_res.data[0].get("startup_name") or ""
    except Exception as ne:
        logging.warning(f"Failed to fetch startup name: {ne}")

    # Override founders and taxonomy with canonical values if available
    canonical_founders = get_canonical_founders(startup_name)
    if canonical_founders:
        analysis_json["founders"] = canonical_founders

    if startup_name:
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
        name_clean = startup_name.strip().lower()
        matched_over = None
        if name_clean in CANONICAL_OVERLOADS:
            matched_over = CANONICAL_OVERLOADS[name_clean]
        else:
            for k, v in CANONICAL_OVERLOADS.items():
                if k in name_clean or name_clean in k:
                    matched_over = v
                    break
        if matched_over:
            if "classification" not in analysis_json:
                analysis_json["classification"] = {}
            analysis_json["classification"]["industry"] = matched_over["industry"]
            analysis_json["classification"]["sector"] = matched_over["sector"]
            analysis_json["classification"]["subsector"] = matched_over["subsector"]

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
    
    # Extract and normalize ICICI entities to prevent general entities (e.g. Government of India)
    use_cases = bfsi.get("use_cases", [])
    valid_entities = {"ICICI Bank", "ICICI Lombard", "ICICI Securities", "ICICI Prudential AMC", "ICICI Prudential Life", "ICICI HFC"}
    
    normalized_use_cases = []
    primary_entity = "Not Relevant to any of the ICICI Group Companies"
    
    if use_cases and isinstance(use_cases, list):
        for uc in use_cases:
            if not isinstance(uc, dict):
                continue
            entity = str(uc.get("icici_entity") or "").strip()
            matched_entity = next((ve for ve in valid_entities if ve.lower() == entity.lower()), None)
            if matched_entity:
                uc["icici_entity"] = matched_entity
                normalized_use_cases.append(uc)
            else:
                uc["icici_entity"] = "Not Relevant to any of the ICICI Group Companies"
                normalized_use_cases.append(uc)
        bfsi["use_cases"] = normalized_use_cases
        if normalized_use_cases:
            primary_entity = normalized_use_cases[0]["icici_entity"]
    else:
        primary_entity = "Not Relevant to any of the ICICI Group Companies"
    
    def to_int(val, default=0):
        try:
            return int(val)
        except Exception:
            return default

    analysis_data = {
        "startup_id": startup_id,
        "ai_summary": summary.get("one_liner", ""),
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
        
    # Synchronize core startup registry columns from the parsed AI intelligence results
    startup_updates = {}
    
    raw_industry = classification.get("industry")
    raw_sector = classification.get("sector") or classification.get("primary_sector") or "Unknown"
    raw_subsector = classification.get("subsector") or "Unknown"
    
    industry, sector, subsector = normalize_taxonomy(startup_name, raw_industry, raw_sector, raw_subsector)
    
    if industry and industry != "Unknown":
        startup_updates["industry"] = industry
        
    if sector and sector != "Unknown":
        startup_updates["sector"] = sector
        
    if subsector and subsector != "Unknown":
        startup_updates["subsector"] = subsector
        
    business_models = classification.get("business_models")
    if business_models:
        startup_updates["business_models"] = normalize_business_models(startup_name, business_models)
        
    industry_relevance = classification.get("industry_relevance")
    if industry_relevance:
        startup_updates["industry_relevance"] = normalize_industry_relevance(startup_name, industry_relevance)
        
    tags = classification.get("tags")
    if tags:
        startup_updates["tags"] = get_canonical_tags(startup_name, tags)
        
    funding_stages_info = analysis_json.get("funding_stages", {})
    series = funding_stages_info.get("series")
    if series and series != "Unknown":
        startup_updates["funding_stage"] = series
        
    # Apply canonical funding stage overrides if present in taxonomy mapper overloads
    if startup_name:
        name_clean = startup_name.strip().lower()
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
        if name_clean in CANONICAL_OVERLOADS and "funding_stage" in CANONICAL_OVERLOADS[name_clean]:
            startup_updates["funding_stage"] = CANONICAL_OVERLOADS[name_clean]["funding_stage"]
        else:
            # Check substrings
            for key, over in CANONICAL_OVERLOADS.items():
                if (key in name_clean or name_clean in key) and "funding_stage" in over:
                    startup_updates["funding_stage"] = over["funding_stage"]
                    break
        
    website = analysis_json.get("startup_website")
    if website and "example.com" not in website:
        startup_updates["website"] = website
        
    if "founded_year" in analysis_json:
        founded_yr = analysis_json.get("founded_year")
        try:
            startup_updates["founded_year"] = int(founded_yr) if founded_yr else None
        except Exception:
            pass

    # Extract primary founder information to store on startup
    founders = analysis_json.get("founders", [])
    if founders and isinstance(founders, list):
        primary_founder = founders[0]
        if isinstance(primary_founder, dict):
            f_name = primary_founder.get("name")
            f_linkedin = primary_founder.get("linkedin_url") or primary_founder.get("linkedin")
            if f_name:
                startup_updates["founder_name"] = f_name
            if f_linkedin:
                startup_updates["founder_linkedin_url"] = f_linkedin

    if startup_updates:
        try:
            supabase.table("startups").update(startup_updates).eq("id", startup_id).execute()
            print(f"Synchronized core startup registry columns in DB for ID: {startup_id}")
        except Exception as se:
            print(f"⚠️ Failed to sync core startup columns for ID {startup_id}: {se}")
            
    # Synchronize startup assignments with custom outreach messages and startup name
    try:
        asg_res = supabase.table("startup_assignments").select("id").eq("startup_id", startup_id).execute()
        if asg_res.data:
            linkedin_msg = format_outreach_message(analysis_json.get("linkedin_reachout_message"))
            email_msg = format_outreach_message(analysis_json.get("email_reachout_message"))
            
            asg_updates = {}
            if linkedin_msg:
                asg_updates["linkedin_reachout_message"] = linkedin_msg
            if email_msg:
                asg_updates["email_reachout_message"] = email_msg
            if startup_name:
                asg_updates["startup_name"] = startup_name
                
            if asg_updates:
                supabase.table("startup_assignments").update(asg_updates).eq("startup_id", startup_id).execute()
                print(f"✅ Synchronized startup_assignments outreach messages for startup ID {startup_id}")
    except Exception as e:
        print(f"⚠️ Failed to sync outreach messages in startup_assignments for ID {startup_id}: {e}")

    return response.data


# --- Startup News History ---

def save_startup_news(startup_id: int, headline: str, summary: str, source: str = "", source_url: str = "", published_at: str = None):
    """
    Saves a news event for a startup into the startup_news table.
    Called after every ingestion pass (new startup or cache hit) so that
    each article appearance is logged with a startup-specific summary.
    """
    try:
        data = {
            "startup_id": startup_id,
            "headline": headline or "",
            "summary": summary or "",
            "source": source or "",
            "source_url": source_url or "",
        }
        if published_at:
            data["published_at"] = published_at
        response = supabase.table("startup_news").insert(data).execute()
        return response.data
    except Exception as e:
        logging.warning(f"Failed to save startup news for startup_id {startup_id}: {e}")
        return None


def get_startup_news(startup_id: int) -> list:
    """
    Fetches the news history for a startup from the startup_news table,
    ordered by most recent first. Returns a list of news row dicts.
    """
    try:
        response = (
            supabase
            .table("startup_news")
            .select("id, headline, summary, source, source_url, published_at")
            .eq("startup_id", startup_id)
            .order("published_at", desc=True)
            .limit(20)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logging.warning(f"Failed to fetch startup news for startup_id {startup_id}: {e}")
        return []


# --- Funding Rounds ---

def save_funding_rounds(startup_id: int, funding_data: dict, analysis_id: int = None):
    """
    Saves structured funding round data into the startup_analysis table.
    funding_data: {rounds: [...], total_funding: str, latest_stage: str, latest_date: str}
    Updates by analysis_id if provided, otherwise by startup_id.
    """
    from datetime import datetime, timezone
    try:
        rounds = funding_data.get("rounds", [])
        latest_stage = funding_data.get("latest_stage", "")
        # Derive latest_stage from rounds[0] if not explicitly set
        if not latest_stage and rounds:
            latest_stage = rounds[0].get("stage", "")

        update_payload = {
            "funding_rounds": rounds,
            "total_funding": funding_data.get("total_funding", ""),
            "latest_round_stage": latest_stage,
            "latest_round_date": funding_data.get("latest_date", ""),
            "last_funding_enriched_at": datetime.now(timezone.utc).isoformat()
        }

        if analysis_id:
            response = (
                supabase
                .table("startup_analysis")
                .update(update_payload)
                .eq("id", analysis_id)
                .execute()
            )
        else:
            response = (
                supabase
                .table("startup_analysis")
                .update(update_payload)
                .eq("startup_id", startup_id)
                .execute()
            )

        print(f"💰 Saved {len(rounds)} funding round(s) to startup_analysis for startup_id {startup_id}")
        return response.data
    except Exception as e:
        logging.warning(f"Failed to save funding rounds for startup_id {startup_id}: {e}")
        return None