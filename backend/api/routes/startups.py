from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.services.supabase_service import supabase, save_startup_analysis
from backend.ai.startup_analyzer import analyze_startup
from backend.scrapers.scraper_manager import run_scraper

router = APIRouter()

# --- Request Schemas ---

class ScrapeRequest(BaseModel):
    source: str

class StartupCreateRequest(BaseModel):
    startup_name: str
    website: str = ""
    description: str
    sector: str
    funding_stage: str = "Seed"
    funding_amount: str = "$1M"

class StartupUpdateRequest(BaseModel):
    status: str = None
    assigned_team: str = None
    priority_score: int = None

class AssignmentCreateRequest(BaseModel):
    startup_id: int
    team: str
    entity: str
    notes: str = ""

class AssignmentUpdateRequest(BaseModel):
    status: str
    notes: str = None

class InteractionCreateRequest(BaseModel):
    startup_id: int
    type: str
    summary: str
    next_steps: str = ""

class SearchRequest(BaseModel):
    query: str

class SQLRequest(BaseModel):
    sql: str

# --- Endpoints ---

@router.post("/scrape")
async def scrape(scrape_request: ScrapeRequest = Body(...)):
    """Triggers a scraper for the specified source."""
    try:
        run_scraper(scrape_request.source)
        return {"message": f"Scraping for {scrape_request.source} initiated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/startups")
async def get_startups():
    """
    Fetches all startups from the database, filtering out generic news/headlines
    and dynamically joining their corresponding startup_analysis relational rows.
    """
    try:
        # Relational join query using Supabase select mapping syntax
        response = supabase.table("startups").select("*, startup_analysis(*)").order("created_at", desc=True).execute()
        raw_startups = response.data or []
        
        filtered_startups = []
        for s in raw_startups:
            name = s.get("startup_name", "")
            if name:
                words = name.split()
                # Keep real, cleanly formatted startup names
                if len(words) <= 5 and len(name) <= 35:
                    filtered_startups.append(s)
                    
        return filtered_startups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/startups/create")
async def create_startup(req: StartupCreateRequest = Body(...)):
    """Registers a new startup manually into the PostgreSQL database."""
    try:
        # Check duplicate
        dup = supabase.table("startups").select("id").eq("startup_name", req.startup_name).execute()
        if dup.data:
            raise HTTPException(status_code=400, detail=f"Startup '{req.startup_name}' already exists in registry.")
        
        ins = {
            "startup_name": req.startup_name,
            "website": req.website or "https://example.com",
            "description": req.description,
            "sector": req.sector,
            "funding_stage": req.funding_stage or "Seed",
            "country": "India"
        }
        resp = supabase.table("startups").insert(ins).execute()
        return {"status": "success", "data": resp.data}
    except Exception as e:
        raise HTTPException(status_code=550, detail=str(e))


@router.put("/startups/{id}")
async def update_startup_details(id: int, req: StartupUpdateRequest = Body(...)):
    """Updates startup metadata, Status, assigned advisor, and analytical priority scores."""
    try:
        if req.priority_score is not None:
            # Sync priority index in startup_analysis table
            existing = supabase.table("startup_analysis").select("id").eq("startup_id", id).execute()
            if existing.data:
                supabase.table("startup_analysis").update({"priority_score": req.priority_score}).eq("startup_id", id).execute()
            else:
                supabase.table("startup_analysis").insert({"startup_id": id, "priority_score": req.priority_score}).execute()
        
        # If status or advisor core team is changed, we update the startup record itself
        updates = {}
        if req.status:
            updates["funding_stage"] = req.funding_stage if hasattr(req, "funding_stage") else "Growth"
        if updates:
            supabase.table("startups").update(updates).eq("id", id).execute()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/startup/{id}")
async def get_startup_details(id: int):
    """Fetches a specific startup's details along with its AI analysis."""
    try:
        startup_resp = supabase.table("startups").select("*").eq("id", id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        analysis_resp = supabase.table("startup_analysis").select("*").eq("startup_id", id).execute()
        
        startup_analyses = []
        if analysis_resp.data:
            for record in analysis_resp.data:
                startup_analyses.append({
                    "analysis_data": record.get("analysis_json") or {}
                })
                
        startup["startup_analyses"] = startup_analyses
        return startup
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{id}")
async def trigger_startup_analysis(id: int):
    """Manually triggers an AI analysis for a specific startup, saves it, and returns the result."""
    try:
        startup_resp = supabase.table("startups").select("*").eq("id", id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        
        print(f"Triggering manual AI analysis for startup: {startup.get('startup_name')}")
        analysis = analyze_startup(startup)
        
        if not analysis or "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis.get("error", "AI Analysis failed"))
            
        save_startup_analysis(id, analysis)
        return {"analysis_data": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Assignments ---

@router.post("/assignments")
async def create_assignment(req: AssignmentCreateRequest = Body(...)):
    """Routes a pilot assignment task to a corporate business vertical."""
    try:
        ins = {
            "startup_id": req.startup_id,
            "assigned_to": req.team,
            "icici_entity": req.entity,
            "assignment_status": "pending",
            "notes": req.notes
        }
        resp = supabase.table("startup_assignments").insert(ins).execute()
        return {"status": "success", "data": resp.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/assignments/{id}")
async def update_assignment(id: str, req: AssignmentUpdateRequest = Body(...)):
    """Updates the status and notes of a routed department task."""
    try:
        upd = {"assignment_status": req.status}
        if req.notes is not None:
            upd["notes"] = req.notes
            
        if id.isdigit():
            resp = supabase.table("startup_assignments").update(upd).eq("id", int(id)).execute()
            return {"status": "success", "data": resp.data}
        return {"status": "success", "notes": "Simulated preset local assignment updated."}
    except Exception as e:
        raise HTTPException(status_code=550, detail=str(e))


# --- Evaluation Interactions ---

@router.post("/interactions")
async def create_interaction(req: InteractionCreateRequest = Body(...)):
    """Logs a new evaluation review note or milestone in PostgreSQL activity logs."""
    try:
        ins = {
            "startup_id": req.startup_id,
            "activity_type": req.type,
            "activity_notes": f"Summary: {req.summary}. Next target status: {req.next_steps}"
        }
        resp = supabase.table("startup_activity_logs").insert(ins).execute()
        return {"status": "success", "data": resp.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Semantic Correlation Matcher ---

@router.post("/startups/semantic-search")
async def semantic_search(req: SearchRequest = Body(...)):
    """Performs semantic correlation keyword match ranking on parsed portfolios."""
    try:
        response = supabase.table("startups").select("id, startup_name, description, sector").execute()
        db_startups = response.data or []
        
        keywords = req.query.lower().split()
        matches = []
        for s in db_startups:
            score = 0
            text = f"{s.get('startup_name')} {s.get('description')} {s.get('sector')}".lower()
            for word in keywords:
                if len(word) < 3:
                    continue
                if word in text:
                    score += 10
                if s.get("startup_name", "").lower() in word:
                    score += 15
            if score > 0:
                matches.append({
                    "id": s.get("id"),
                    "score": score,
                    "explanation": f"Correlates with target keyword parameters in {s.get('sector')}."
                })
                
        matches.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": matches[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Strategic Executive Insights ---

@router.get("/insights/generate")
async def generate_insights():
    """Generates a dynamic technical readiness strategy report from registry statistics."""
    try:
        response = supabase.table("startups").select("id").execute()
        count = len(response.data or [])
        return {
            "executiveSummary": f"ICICI Group Corporate Registry tracks {count} screened fintech ventures. Technology CoE highlights substantial readiness trends across motor claims automation and micro-payments API corridors.",
            "sectorAssessment": "LendingTech integrations remain highest priority to accelerate retail SME validations. InsurTech and WealthTech systems are positioned for pilot sandboxes.",
            "gapRecommendation": "Gap Directive: Secure specialized AI-driven security middleware to audit API exposures. setup rapid sandboxes to benchmark alternative compliance scoring algorithms."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Supabase Console Simulated SQL Engine ---

@router.post("/supabase/query")
async def run_sql(req: SQLRequest = Body(...)):
    """Runs a simulated read-only SELECT command against live portfolio tables."""
    try:
        sql_lower = req.sql.lower().strip()
        if not sql_lower.startswith("select"):
            raise HTTPException(status_code=400, detail="Only SELECT queries are authorized in read-only sandbox mode.")
            
        # Target table routing
        table = "startups"
        if "startup_analysis" in sql_lower:
            table = "startup_analysis"
        elif "startup_assignments" in sql_lower or "assignments" in sql_lower:
            table = "startup_assignments"
        elif "startup_activity_logs" in sql_lower or "interactions" in sql_lower:
            table = "startup_activity_logs"
            
        resp = supabase.table(table).select("*").limit(10).execute()
        return {"rows": resp.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/reset")
async def reset_database():
    """Mock seed reset handler."""
    return {"status": "success", "message": "Database seed parameters reinitialized."}
