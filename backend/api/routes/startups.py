from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from supabase import create_client, PostgrestAPIError
from dotenv import load_dotenv
import os
from scrapers.scraper_manager import run_scraper

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
