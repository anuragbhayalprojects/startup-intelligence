"""
backend/api/routes/news.py
--------------------------------
FastAPI routing handlers for the Startup News Dashboard.
"""

from __future__ import annotations
import re
import requests
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from backend.services.news_service import (
    get_filtered_articles,
    get_all_sources,
    add_custom_source
)
from backend.pipeline.news_processor import NewsProcessor
from backend.services.email_service import dispatch_gmail_digest
from backend.utils.tracing import generate_trace_id, set_trace_id, log_trace

import threading
from datetime import datetime

router = APIRouter(prefix="/news", tags=["news"])

# Thread-safe global news sync status for real-time console feedback
NEWS_SYNC_STATUS = {
    "active": False,
    "current_step": "Idle",
    "logs": [],
    "discovered_count": 0,
    "last_news_sync": None
}
news_status_lock = threading.Lock()

def add_news_sync_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with news_status_lock:
        NEWS_SYNC_STATUS["logs"].append(log_line)
        if len(NEWS_SYNC_STATUS["logs"]) > 200:
            NEWS_SYNC_STATUS["logs"].pop(0)

def update_news_sync_status(current_step: str = None, discovered_increment: int = 0, active: bool = None, last_news_sync: dict = None):
    with news_status_lock:
        if current_step is not None:
            NEWS_SYNC_STATUS["current_step"] = current_step
        if active is not None:
            NEWS_SYNC_STATUS["active"] = active
        if discovered_increment > 0:
            NEWS_SYNC_STATUS["discovered_count"] += discovered_increment
        if last_news_sync is not None:
            NEWS_SYNC_STATUS["last_news_sync"] = last_news_sync

@router.get("/sync/status")
def get_news_sync_status():
    """Returns the current news sync logs and active execution status."""
    with news_status_lock:
        return NEWS_SYNC_STATUS



class CustomSourcePayload(BaseModel):
    name: str
    url: str
    category: str


class DigestTriggerPayload(BaseModel):
    edition: Optional[str] = "Manual"


class TriggerIngestionPayload(BaseModel):
    limit_per_source: Optional[int] = None
    sources: Optional[List[str]] = None


@router.get("")
def read_news_articles(
    search: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    industry: Optional[str] = Query(default=None),
    startup: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Retrieves paginated, filtered canonical news articles."""
    try:
        result = get_filtered_articles(
            search=search,
            source=source,
            category=category,
            industry=industry,
            startup=startup,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
def read_news_sources():
    """Returns lists of configured RSS feed targets."""
    try:
        return get_all_sources()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources")
def create_custom_source(payload: CustomSourcePayload):
    """Validates and appends a new custom RSS scraping target."""
    name = payload.name.strip()
    url = payload.url.strip()
    category = payload.category.strip()

    if not name or not url or not category:
        raise HTTPException(status_code=400, detail="Name, URL, and Category are required fields.")

    # Basic URL structure check
    url_pattern = re.compile(
        r'^(https?:\/\/)?'
        r'([a-z0-9\-]+\.)+[a-z]{2,}'
        r'(:\d+)?(\/.*)?$', re.IGNORECASE
    )
    if not url_pattern.match(url):
        raise HTTPException(status_code=400, detail=f"Invalid URL structure: '{url}'. Please enter a full qualified HTTP/HTTPS RSS feed URL.")

    # Reachability validation
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code >= 400:
            raise Exception(f"HTTP Status {res.status_code}")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Target feed URL is unreachable: {e}. Please check the URL and try again."
        )

    # Append to configuration
    res = add_custom_source(name, url, category)
    if res["status"] == "exists":
        raise HTTPException(status_code=400, detail="Source with this name or feed URL already exists.")
    elif res["status"] == "error":
        raise HTTPException(status_code=500, detail=res["message"])
        
    return {"status": "success", "source": res["source"]}


def _run_ingestion_async(limit_per_source: Optional[int], sources_filter: Optional[List[str]]):
    """Runs the ingestion pipeline processor in a separate thread context inside a trace context."""
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    log_trace(startup_name="Global News Aggregator", article_url=None)
    
    try:
        # Pass callbacks directly to avoid circular import issues
        processor = NewsProcessor(
            log_fn=add_news_sync_log,
            status_fn=update_news_sync_status
        )
        if not limit_per_source:
            from backend.pipeline.scheduler import load_scheduler_config
            config = load_scheduler_config()
            limit_per_source = config.get("max_articles_per_source_run", 5)
        processor.run_ingestion_pipeline(limit_per_source=limit_per_source, sources_filter=sources_filter)
    except Exception as e:
        add_news_sync_log(f"❌ Background manual scraper trigger failed: {e}")
        update_news_sync_status(current_step="Failed", active=False)


@router.post("/trigger")
def trigger_news_ingestion(
    background_tasks: BackgroundTasks,
    payload: Optional[TriggerIngestionPayload] = Body(default=None)
):
    """Manually triggers the news ingestion pipeline scraper in the background."""
    if NEWS_SYNC_STATUS["active"]:
        raise HTTPException(status_code=400, detail="A news sync is already active. Please wait for it to complete.")

    limit = payload.limit_per_source if payload else None
    sources = payload.sources if payload else None
    
    with news_status_lock:
        NEWS_SYNC_STATUS["active"] = True
        NEWS_SYNC_STATUS["current_step"] = "Initiating news feed sync..."
        NEWS_SYNC_STATUS["logs"] = []
        NEWS_SYNC_STATUS["discovered_count"] = 0
        
    background_tasks.add_task(_run_ingestion_async, limit, sources)
    return {
        "status": "started",
        "message": "Startup News Pipeline ingestion initiated in the background."
    }


@router.post("/abort")
def abort_news_ingestion():
    """Interrupts and stops any running news sync ingestion."""
    from backend.pipeline.news_processor import set_ingestion_aborted
    set_ingestion_aborted(True)
    add_news_sync_log("🛑 User requested manual sync cancellation.")
    update_news_sync_status(current_step="Idle (Interrupted)", active=False)
    return {"status": "success", "message": "Interruption request sent."}




def _run_digest_async(edition: str):
    """Runs the email digest in a background worker context."""
    dispatch_gmail_digest(edition)


@router.post("/digest/trigger")
def trigger_digest_dispatch(background_tasks: BackgroundTasks, payload: Optional[DigestTriggerPayload] = None):
    """Manually triggers generation and Gmail SMTP dispatch of the HTML News Digest."""
    edition = (payload.edition if payload else "Manual") or "Manual"
    background_tasks.add_task(_run_digest_async, edition)
    return {
        "status": "started",
        "message": f"Gmail HTML digest generation and send ({edition} Edition) initiated in the background."
    }


class ResolveStartupPayload(BaseModel):
    article_id: int
    startup_name: str
    enrich: bool


def _update_news_articles_mentions(startup_name: str, startup_id: int, website: str):
    """Searches news_articles for any matching startup mention and updates its id/website."""
    from backend.services.supabase_service import supabase
    try:
        # Fetch all news articles
        res = supabase.table("news_articles").select("id, startups_mentioned").execute()
        if not res.data:
            return
            
        for art in res.data:
            mentions = art.get("startups_mentioned") or []
            updated = False
            for m in mentions:
                if m.get("name", "").lower() == startup_name.lower():
                    m["id"] = startup_id
                    m["website"] = website
                    updated = True
            if updated:
                supabase.table("news_articles").update({"startups_mentioned": mentions}).eq("id", art["id"]).execute()
    except Exception as e:
        print(f"Failed to update news article mentions for '{startup_name}': {e}")


def _enrich_single_startup_async(startup_id: int, startup_name: str, headline: str, summary: str, source: str, source_url: str):
    """Runs full multi-agent enrichment in a background worker context with proper tracing."""
    from backend.utils.tracing import generate_trace_id, set_trace_id, log_trace
    
    # 1. Establish trace context for this background worker thread
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    log_trace(startup_name=startup_name, article_url=source_url)
    
    raw_startup = {
        "startup_name": startup_name,
        "headline": headline,
        "description": summary,
        "source": source,
        "source_url": source_url
    }
    try:
        from backend.workflows.agent_orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        state = orchestrator.run_pipeline(raw_startup, resolution_only=False)
        if state.startup_id:
            web_val = ""
            if isinstance(state.identity.get("website"), dict):
                web_val = state.identity["website"].get("value") or ""
            elif isinstance(state.identity.get("website"), str):
                web_val = state.identity["website"]
            _update_news_articles_mentions(startup_name, state.startup_id, web_val)
    except Exception as e:
        print(f"Error in single startup enrichment background task: {e}")



@router.post("/resolve-startup")
async def resolve_startup_from_news(
    background_tasks: BackgroundTasks,
    payload: ResolveStartupPayload = Body(...)
):
    """Resolves or registers a startup from a news mention, optionally spawning background enrichment."""
    from backend.services.supabase_service import check_existing_startup
    from backend.services.news_repo import save_startup_news
    from backend.services.supabase_service import supabase
    from backend.api.routes.startups import assign_fprs_for_startup
    
    # 1. Fetch the news article context
    art_res = supabase.table("news_articles").select("*").eq("id", payload.article_id).execute()
    if not art_res.data:
        raise HTTPException(status_code=404, detail="News article not found")
        
    art = art_res.data[0]
    
    # 2. Check if startup already exists in DB
    existing = check_existing_startup(payload.startup_name)
    if existing:
        startup_id = existing["id"]
        website = existing.get("website", "")
    else:
        # Create a basic startup registry record
        ins = {
            "startup_name": payload.startup_name,
            "website": "",
            "description": art.get("summary") or art.get("headline", ""),
            "industry": "Financial Services",
            "sector": "Unknown",
            "subsector": "Unknown",
            "funding_stage": "Unknown",
            "business_models": [],
            "country": "India"
        }
        resp = supabase.table("startups").insert(ins).execute()
        if not resp.data:
            raise HTTPException(status_code=500, detail="Failed to insert startup record")
        startup_id = resp.data[0]["id"]
        website = ""
        assign_fprs_for_startup(startup_id)
        
    # 3. Handle enrichment vs basic insertion
    if payload.enrich:
        background_tasks.add_task(
            _enrich_single_startup_async,
            startup_id,
            payload.startup_name,
            art["headline"],
            art.get("summary") or art.get("description") or "",
            art["source"],
            art["source_url"]
        )
    else:
        # Update mentions in news_articles
        _update_news_articles_mentions(payload.startup_name, startup_id, website)
        # Link this article to the startup history in startup_news table
        try:
            save_startup_news(
                startup_id=startup_id,
                headline=art["headline"],
                summary=art.get("summary") or art.get("description") or "",
                source=art["source"],
                source_url=art["source_url"],
                published_at=art["published_at"]
            )
        except Exception as e:
            print(f"Failed to link news event: {e}")
            
    return {
        "status": "success",
        "startup_id": startup_id,
        "enriched": payload.enrich,
        "message": "Startup resolved successfully. Enrichment running in the background." if payload.enrich else "Startup resolved with basic details."
    }
