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

router = APIRouter(prefix="/news", tags=["news"])


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
        processor = NewsProcessor()
        if not limit_per_source:
            from backend.pipeline.scheduler import load_scheduler_config
            config = load_scheduler_config()
            limit_per_source = config.get("max_articles_per_source_run", 5)
        processor.run_ingestion_pipeline(limit_per_source=limit_per_source, sources_filter=sources_filter)
    except Exception as e:
        print(f"❌ Background manual scraper trigger failed: {e}")


@router.post("/trigger")
def trigger_news_ingestion(
    background_tasks: BackgroundTasks,
    payload: Optional[TriggerIngestionPayload] = Body(default=None)
):
    """Manually triggers the news ingestion pipeline scraper in the background."""
    limit = payload.limit_per_source if payload else None
    sources = payload.sources if payload else None
    background_tasks.add_task(_run_ingestion_async, limit, sources)
    return {
        "status": "started",
        "message": "Startup News Pipeline ingestion initiated in the background."
    }


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
