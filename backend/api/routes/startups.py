from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.services.supabase_service import supabase, save_startup_analysis
from backend.ai.startup_analyzer import analyze_startup
from backend.scrapers.scraper_manager import run_scraper

router = APIRouter()

class ScrapeRequest(BaseModel):
    source: str

@router.post("/scrape")
async def scrape(scrape_request: ScrapeRequest = Body(...)):
    """
    Triggers a scraper for the specified source.
    """
    try:
        run_scraper(scrape_request.source)
        return {"message": f"Scraping for {scrape_request.source} initiated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/startups")
async def get_startups():
    """
    Fetches all startups from the database, filtering out generic news/headlines
    to return only actual clean startup names.
    """
    try:
        response = supabase.table("startups").select("*").order("created_at", desc=True).execute()
        raw_startups = response.data or []
        
        # Filter: Keep only actual clean startup names (short, non-sentence names)
        filtered_startups = []
        for s in raw_startups:
            name = s.get("startup_name", "")
            if name:
                words = name.split()
                # Actual startup names are short (usually 1-3 words) and under 25 chars
                if len(words) <= 3 and len(name) <= 25:
                    filtered_startups.append(s)
                    
        return filtered_startups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/startup/{id}")
async def get_startup_details(id: int):
    """
    Fetches a specific startup's details along with its AI analysis.
    """
    try:
        # Get startup record
        startup_resp = supabase.table("startups").select("*").eq("id", id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        
        # Get corresponding analysis records
        analysis_resp = supabase.table("startup_analysis").select("*").eq("startup_id", id).execute()
        
        # Map to the format the frontend typescript interfaces expect:
        # startup_analyses: { analysis_data: StartupAnalysis }[]
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
    """
    Manually triggers an AI analysis for a specific startup, saves it, and returns the result.
    """
    try:
        # Get startup record
        startup_resp = supabase.table("startups").select("*").eq("id", id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        
        # Run AI analysis
        print(f"Triggering manual AI analysis for startup: {startup.get('startup_name')}")
        analysis = analyze_startup(startup)
        
        if not analysis or "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis.get("error", "AI Analysis failed"))
            
        # Save analysis to DB
        save_startup_analysis(id, analysis)
        
        return {"analysis_data": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
