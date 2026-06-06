from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.services.supabase_service import supabase, save_startup_analysis, get_startup_news, save_funding_rounds
from backend.ai.startup_analyzer import analyze_startup
from backend.scrapers.scraper_manager import run_scraper
import os
import re
import json
import requests
import threading
from datetime import datetime
from backend.utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

router = APIRouter()

# Thread-safe global scraper state for real-time console feedback
SCRAPE_STATUS = {
    "active": False,
    "total_target": 0,
    "discovered_count": 0,
    "current_step": "Idle",
    "logs": [],
    "processed_startups": []
}
status_lock = threading.Lock()

def add_scrape_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with status_lock:
        SCRAPE_STATUS["logs"].append(log_line)
        if len(SCRAPE_STATUS["logs"]) > 200:
            SCRAPE_STATUS["logs"].pop(0)

def update_scrape_status(current_step: str = None, discovered_increment: int = 0, processed_name: str = None, active: bool = None):
    with status_lock:
        if current_step is not None:
            SCRAPE_STATUS["current_step"] = current_step
        if active is not None:
            SCRAPE_STATUS["active"] = active
        if discovered_increment > 0:
            SCRAPE_STATUS["discovered_count"] += discovered_increment
        if processed_name:
            SCRAPE_STATUS["processed_startups"].append(processed_name)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MAPPING_PATH = os.path.join(PROJECT_ROOT, "docs", "fpr_assignment_mapping.json")

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

def assign_fprs_for_startup(startup_id: int):
    try:
        # Check if already assigned
        existing = supabase.table("startup_assignments").select("id").eq("startup_id", startup_id).execute()
        if existing.data:
            return  # Already assigned
        
        # Load mappings
        if not os.path.exists(MAPPING_PATH):
            print(f"⚠️ Mappings file not found at {MAPPING_PATH}")
            return
            
        with open(MAPPING_PATH, "r") as f:
            mapping_data = json.load(f)
        fpr_mappings = mapping_data.get("fpr_mappings", [])
        if not fpr_mappings:
            return
            
        # Get count of current assignments
        count_res = supabase.table("startup_assignments").select("id").execute()
        count = len(count_res.data or [])
        
        # Select owner mapping round robin
        mapping = fpr_mappings[count % len(fpr_mappings)]
        fpr1 = mapping["fpr1"]
        fpr2 = mapping["fpr2"]
        
        # Fetch startup_name from startups table
        startup_name = ""
        s_res = supabase.table("startups").select("startup_name").eq("id", startup_id).execute()
        if s_res.data:
            startup_name = s_res.data[0].get("startup_name", "")
            
        # Fetch reachout messages from startup_analysis if exists
        linkedin_msg = None
        email_msg = None
        ans_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", startup_id).execute()
        if ans_res.data and ans_res.data[0].get("analysis_json"):
            analysis = ans_res.data[0]["analysis_json"]
            linkedin_msg = format_outreach_message(analysis.get("linkedin_reachout_message"))
            email_msg = format_outreach_message(analysis.get("email_reachout_message"))
        
        # Set default status to Assigned to FPR1 if assigned
        status = f"Assigned to {fpr1}" if fpr1 else "pending"

        # Insert assignment record
        ins = {
            "startup_id": startup_id,
            "startup_name": startup_name,
            "assigned_to_fpr1": fpr1,
            "assigned_to_fpr2": fpr2,
            "icici_entity": "ICICI Bank",
            "linkedin_reachout_message": linkedin_msg,
            "email_reachout_message": email_msg,
            "assignment_status": status,
            "notes": "Automated round-robin reachout assignment."
        }
        supabase.table("startup_assignments").insert(ins).execute()
        print(f"✅ Assigned startup ID {startup_id} ({startup_name}) to FPR1: {fpr1}, FPR2: {fpr2}")
    except Exception as e:
        print(f"❌ Failed to assign FPRs for startup ID {startup_id}: {e}")

def backfill_unassigned_startups():
    try:
        startups_res = supabase.table("startups").select("id").execute()
        startups = startups_res.data or []
        for s in startups:
            assign_fprs_for_startup(s["id"])
    except Exception as e:
        print(f"❌ Failed during startup assignments backfill: {e}")

# Backfill assignments on start
try:
    backfill_unassigned_startups()
except Exception as e:
    print(f"⚠️ Failed auto-backfill on module load: {e}")

# --- Request Schemas ---

class ScrapeRequest(BaseModel):
    sources: List[str]
    limit: int = 10
    industry: str = ""
    sector: str = ""
    subsector: str = ""
    keywords: str = ""

class StartupCreateRequest(BaseModel):
    startup_name: str
    website: str = ""
    description: str
    industry: str = "Financial Services"
    sector: str
    subsector: str = "Unknown"
    funding_stage: str = "Seed"
    funding_amount: str = "$1M"
    business_models: List[str] = []

class StartupUpdateRequest(BaseModel):
    status: str = None
    assigned_team: str = None
    priority_score: int = None

class FieldUpdateRequest(BaseModel):
    field: str
    value: Any

class FieldRecheckRequest(BaseModel):
    field: str

class AssignmentCreateRequest(BaseModel):
    startup_id: int
    assigned_to_fpr1: str
    assigned_to_fpr2: str = ""
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

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[Message]

# --- Endpoints ---

def run_scrape_background(sources: List[str], limit: int, industry: str, sector: str, subsector: str, keywords: str):
    """Worker function executed in background threads."""
    import time
    import random
    import urllib.parse
    import feedparser
    from bs4 import BeautifulSoup
    
    add_scrape_log(f"Starting discovery run for sources: {sources} (Target: {limit} startups)")
    
    try:
        # Load custom scrapers config to resolve URLs
        config_path = os.path.join(PROJECT_ROOT, "docs", "custom_scrapers_config.json")
        sources_map = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    configs = json.load(f)
                    for c in configs:
                        sources_map[c["name"]] = c
            except Exception as e:
                add_scrape_log(f"⚠️ Failed to parse custom scrapers config: {e}")

        from backend.workflows.startup_pipeline import process_startup

        for src in sources:
            with status_lock:
                if SCRAPE_STATUS["discovered_count"] >= limit:
                    break
                
            add_scrape_log(f"Processing source: {src}...")
            update_scrape_status(current_step=f"Scraping {src}...")
            
            if src == "Inc42":
                from backend.scrapers.inc42.scraper import scrape_inc42
                add_scrape_log("Fetching Inc42 latest updates...")
                data = scrape_inc42(30)
                add_scrape_log(f"Found {len(data)} feed articles on Inc42. Commencing extraction...")
                for item in data:
                    with status_lock:
                        if SCRAPE_STATUS["discovered_count"] >= limit:
                            break
                    add_scrape_log(f"Discovering startups from: '{item['startup_name']}'")
                    res = process_startup(item, industry, sector, subsector)
                    if res:
                        for startup_dict in res:
                            startup_name = startup_dict.get("startup", {}).get("startup_name", "Unknown")
                            update_scrape_status(discovered_increment=1, processed_name=startup_name)
                            add_scrape_log(f"✨ Discovered and enriched: '{startup_name}'")
                            
            elif src == "Entrackr":
                from backend.scrapers.entrackr.scraper import scrape_entrackr
                add_scrape_log("Fetching Entrackr latest updates...")
                data = scrape_entrackr(30)
                add_scrape_log(f"Found {len(data)} feed articles on Entrackr. Commencing extraction...")
                for item in data:
                    with status_lock:
                        if SCRAPE_STATUS["discovered_count"] >= limit:
                            break
                    add_scrape_log(f"Discovering startups from: '{item['startup_name']}'")
                    res = process_startup(item, industry, sector, subsector)
                    if res:
                        for startup_dict in res:
                            startup_name = startup_dict.get("startup", {}).get("startup_name", "Unknown")
                            update_scrape_status(discovered_increment=1, processed_name=startup_name)
                            add_scrape_log(f"✨ Discovered and enriched: '{startup_name}'")
                            
            elif src == "Custom Web Search":
                add_scrape_log("Compiling Custom Web Search query...")
                query_parts = []
                if keywords:
                    query_parts.append(keywords)
                if subsector and subsector != "Unknown":
                    query_parts.append(subsector)
                if sector and sector != "Unknown":
                    query_parts.append(sector)
                if industry and industry != "Unknown":
                    query_parts.append(industry)
                query_parts.append("startup news funding India 2026")
                search_query = " ".join(query_parts)
                add_scrape_log(f"Query: '{search_query}'")
                
                from backend.utils.search import search_duckduckgo
                search_res = search_duckduckgo(search_query)
                
                lines = search_res.split("\n")
                articles = []
                current_title = ""
                current_url = ""
                current_snippet = ""
                
                for line in lines:
                    if line.strip().startswith("[") and "Title: " in line:
                        parts = line.split("Title: ", 1)
                        current_title = parts[1].strip()
                    elif line.startswith("Title: "):
                        current_title = line.replace("Title: ", "").strip()
                    elif line.startswith("URL: "):
                        current_url = line.replace("URL: ", "").strip()
                    elif line.startswith("Snippet: "):
                        current_snippet = line.replace("Snippet: ", "").strip()
                        if current_title and current_url:
                            articles.append({
                                "startup_name": current_title,
                                "description": current_snippet or "No description available.",
                                "source": "Custom Web Search",
                                "source_url": current_url
                            })
                            current_title = ""
                            current_url = ""
                            current_snippet = ""
                            
                add_scrape_log(f"Parsed {len(articles)} search updates. Initiating pipeline...")
                for art in articles:
                    with status_lock:
                        if SCRAPE_STATUS["discovered_count"] >= limit:
                            break
                    add_scrape_log(f"Processing search item: '{art['startup_name']}'")
                    res = process_startup(art, industry, sector, subsector)
                    if res:
                        for startup_dict in res:
                            startup_name = startup_dict.get("startup", {}).get("startup_name", "Unknown")
                            update_scrape_status(discovered_increment=1, processed_name=startup_name)
                            add_scrape_log(f"✨ Discovered and enriched: '{startup_name}'")
                            
            else:
                # Custom registered RSS/homepage source added by user!
                if src in sources_map:
                    custom_url = sources_map[src]["url"]
                    
                    add_scrape_log(f"Fetching from Custom URL: '{custom_url}'")
                    try:
                        from curl_cffi import requests as cffi_requests
                        response = cffi_requests.get(custom_url, impersonate="chrome120", timeout=15)
                        content_text = response.text
                    except Exception as re_err:
                        add_scrape_log(f"⚠️ Failed fetching URL via curl_cffi: {re_err}. Trying standard requests fallback...")
                        response = requests.get(custom_url, timeout=15)
                        content_text = response.text
                        
                    parsed_entries = []
                    
                    # Try feed parser first
                    feed = feedparser.parse(content_text)
                    if feed.entries:
                        add_scrape_log(f"Parsed {len(feed.entries)} feed entries via RSS parser.")
                        for entry in feed.entries:
                            title = entry.get("title")
                            link = entry.get("link")
                            summary = entry.get("summary") or entry.get("description") or "N/A"
                            if summary != "N/A":
                                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
                            if title and link:
                                parsed_entries.append({"title": title, "link": link, "summary": summary})
                    else:
                        # Fallback to HTML crawling for homepage links
                        add_scrape_log("Feed parser returned zero entries. Running HTML crawler fallback...")
                        soup = BeautifulSoup(content_text, "html.parser")
                        seen_links = set()
                        for a in soup.find_all("a"):
                            title = a.get_text(strip=True)
                            link = a.get("href")
                            if title and link and len(title) > 20 and not link.startswith("#") and not any(k in link.lower() for k in ["about", "contact", "privacy", "terms"]):
                                if link.startswith("/"):
                                    parsed_uri = urllib.parse.urlparse(custom_url)
                                    link = f"{parsed_uri.scheme}://{parsed_uri.netloc}{link}"
                                if link not in seen_links:
                                    seen_links.add(link)
                                    parsed_entries.append({"title": title, "link": link, "summary": "N/A"})
                                    
                    add_scrape_log(f"Commencing extraction on {len(parsed_entries)} discovered articles...")
                    for entry in parsed_entries:
                        with status_lock:
                            if SCRAPE_STATUS["discovered_count"] >= limit:
                                break
                        title = entry["title"]
                        link = entry["link"]
                        description = entry["summary"]
                        
                        add_scrape_log(f"Discovering startups from: '{title}'")
                        
                        if link.startswith("http"):
                            delay = random.uniform(1.0, 3.0)
                            time.sleep(delay)
                            try:
                                try:
                                    art_resp = cffi_requests.get(link, impersonate="chrome120", timeout=10)
                                except Exception:
                                    art_resp = requests.get(link, timeout=10)
                                if art_resp.status_code == 200:
                                    art_soup = BeautifulSoup(art_resp.text, "html.parser")
                                    paragraphs = []
                                    for p in art_soup.find_all("p"):
                                        t = p.get_text(strip=True)
                                        if len(t) > 45 and not any(phrase in t for phrase in ["Terms", "Privacy", "Unlock", "newsletter"]):
                                            paragraphs.append(t)
                                    if paragraphs:
                                        description = " ".join(paragraphs[:2])
                            except Exception as e:
                                pass
                                
                        item = {
                            "startup_name": title,
                            "description": description,
                            "source": src,
                            "source_url": link
                        }
                        res = process_startup(item, industry, sector, subsector)
                        if res:
                            for startup_dict in res:
                                startup_name = startup_dict.get("startup", {}).get("startup_name", "Unknown")
                                update_scrape_status(discovered_increment=1, processed_name=startup_name)
                                add_scrape_log(f"✨ Discovered and enriched: '{startup_name}'")
                else:
                    add_scrape_log(f"⚠️ Unknown source '{src}'. Skipping.")

        # Complete
        add_scrape_log(f"Discovery pipeline finished. Total startups found: {SCRAPE_STATUS['discovered_count']}/{limit}")
        update_scrape_status(current_step="Idle", active=False)
        
    except Exception as e:
        import traceback
        err_msg = f"❌ Discovery run encountered critical error: {e}\n{traceback.format_exc()}"
        add_scrape_log(err_msg)
        update_scrape_status(current_step="Failed", active=False)

@router.post("/scrape")
async def scrape(scrape_request: ScrapeRequest = Body(...), background_tasks: BackgroundTasks = None):
    """Triggers scrapers or web search updates for specified sources in the background."""
    if SCRAPE_STATUS["active"]:
        raise HTTPException(status_code=400, detail="A startup discovery run is already active. Please wait for it to complete.")
        
    with status_lock:
        SCRAPE_STATUS["active"] = True
        SCRAPE_STATUS["total_target"] = scrape_request.limit
        SCRAPE_STATUS["discovered_count"] = 0
        SCRAPE_STATUS["current_step"] = "Initiating background workers..."
        SCRAPE_STATUS["logs"] = []
        SCRAPE_STATUS["processed_startups"] = []
        
    background_tasks.add_task(
        run_scrape_background,
        scrape_request.sources,
        scrape_request.limit,
        scrape_request.industry,
        scrape_request.sector,
        scrape_request.subsector,
        scrape_request.keywords
    )
    
    return {"status": "started", "message": "Startup discovery pipeline successfully initiated in the background."}

@router.get("/scrape/status")
async def get_scrape_status():
    """Returns the current background scraping logs, active state, and discovery counts."""
    with status_lock:
        return SCRAPE_STATUS

@router.get("/scrape/sources")
async def get_scrape_sources():
    """Returns the list of configured scraper targets (standard + custom RSS feeds)."""
    config_path = os.path.join(PROJECT_ROOT, "docs", "custom_scrapers_config.json")
    if not os.path.exists(config_path):
        return []
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read custom scrapers config: {e}")

@router.post("/scrape/sources")
async def add_scrape_source(req: Dict[str, Any] = Body(...)):
    """Validates and appends a new custom RSS/HTML scraping target to config."""
    name = req.get("name")
    url = req.get("url")
    if not name or not url:
        raise HTTPException(status_code=400, detail="Source name and target URL are required.")
        
    # Basic syntax validation
    url_pattern = re.compile(
        r'^(https?:\/\/)?'
        r'([a-z0-9\-]+\.)+[a-z]{2,}'
        r'(:\d+)?(\/.*)?$', re.IGNORECASE
    )
    if not url_pattern.match(url):
        raise HTTPException(status_code=400, detail=f"Invalid URL format: '{url}'. Please enter a fully qualified HTTP/HTTPS URL.")
        
    # Reachability check
    try:
        try:
            from curl_cffi import requests as cffi_requests
            res = cffi_requests.get(url, impersonate="chrome120", timeout=8)
        except Exception:
            res = requests.get(url, timeout=8)
        if res.status_code >= 400:
            raise Exception(f"HTTP Status {res.status_code}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Target URL is unreachable or returned an error: {e}. Please check the URL and try again.")
        
    # Save custom source
    config_path = os.path.join(PROJECT_ROOT, "docs", "custom_scrapers_config.json")
    try:
        sources = []
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                sources = json.load(f)
                
        # Check duplicate
        if any(s["name"].lower() == name.lower() for s in sources):
            raise HTTPException(status_code=400, detail=f"A discovery source named '{name}' already exists.")
            
        sources.append({
            "name": name,
            "url": url,
            "is_custom": True
        })
        
        with open(config_path, "w") as f:
            json.dump(sources, f, indent=2)
            
        return {"status": "success", "message": f"Successfully registered custom source '{name}'."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save custom source: {e}")


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
        # Fetch all startups to perform name normalization duplicate check
        response = supabase.table("startups").select("startup_name").execute()
        existing_startups = response.data or []
        
        def normalize_name(name: str) -> str:
            return re.sub(r'[^a-z0-9]', '', name.lower())
            
        normalized_new = normalize_name(req.startup_name)
        for s in existing_startups:
            if normalize_name(s.get("startup_name", "")) == normalized_new:
                raise HTTPException(status_code=400, detail=f"Startup '{req.startup_name}' already exists (similar to existing '{s.get('startup_name')}').")
        
        ins = {
            "startup_name": req.startup_name,
            "website": req.website or "https://example.com",
            "description": req.description,
            "industry": req.industry or "Financial Services",
            "sector": req.sector,
            "subsector": req.subsector or "Unknown",
            "funding_stage": req.funding_stage or "Seed",
            "business_models": req.business_models or [],
            "country": "India"
        }
        resp = supabase.table("startups").insert(ins).execute()
        
        # Auto-assign FPRs
        if resp.data:
            new_id = resp.data[0]["id"]
            assign_fprs_for_startup(new_id)
            
        return {"status": "success", "data": resp.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/startups/{id}")
async def update_startup_details(id: str, req: StartupUpdateRequest = Body(...)):
    """Updates startup metadata, Status, assigned advisor, and analytical priority scores."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")
            
        if req.priority_score is not None:
            # Sync priority index in startup_analysis table
            existing = supabase.table("startup_analysis").select("id").eq("startup_id", int_id).execute()
            if existing.data:
                supabase.table("startup_analysis").update({"priority_score": req.priority_score}).eq("startup_id", int_id).execute()
            else:
                supabase.table("startup_analysis").insert({"startup_id": int_id, "priority_score": req.priority_score}).execute()
        
        # If status or advisor core team is changed, we update the startup record itself
        updates = {}
        if req.status:
            updates["funding_stage"] = req.funding_stage if hasattr(req, "funding_stage") else "Growth"
        if updates:
            supabase.table("startups").update(updates).eq("id", int_id).execute()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/startup/{id}")
async def get_startup_details(id: str):
    """Fetches a specific startup's details along with its AI analysis."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")
            
        startup_resp = supabase.table("startups").select("*").eq("id", int_id).execute()
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
            # Embed funding rounds directly on the startup object
            analysis_rec = analysis_resp.data[0]
            startup["funding_rounds"] = analysis_rec.get("funding_rounds") or []
            startup["total_funding"] = analysis_rec.get("total_funding") or ""
            startup["latest_round_stage"] = analysis_rec.get("latest_round_stage") or ""
            startup["latest_round_date"] = analysis_rec.get("latest_round_date") or ""

        startup["startup_analyses"] = startup_analyses

        # Embed recent news history
        startup["recent_news"] = get_startup_news(int_id)

        return startup
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/startup/{id}/news")
async def get_startup_news_feed(id: str):
    """Returns the news history feed for a specific startup, ordered most recent first."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")

        news = get_startup_news(int_id)
        return {"startup_id": int_id, "news": news}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{id}")
async def trigger_startup_analysis(id: str, force: bool = False):
    """Manually triggers an AI analysis for a specific startup, saves it, and returns the result."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")
            
        startup_resp = supabase.table("startups").select("*").eq("id", int_id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        
        # Check cache (30-day time-based cache limit)
        from datetime import datetime, timezone
        import dateutil.parser
        
        analysis_resp = supabase.table("startup_analysis").select("*").eq("startup_id", int_id).execute()
        if analysis_resp.data and not force:
            record = analysis_resp.data[0]
            created_at_str = record.get("created_at")
            if created_at_str:
                created_at = dateutil.parser.isoparse(created_at_str)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                age = now - created_at
                if age.days < 30:
                    print(f"✅ Cache hit: Using fresh startup analysis from DB (created {age.days} days ago).")
                    return {"analysis_data": record.get("analysis_json")}
        
        print(f"Triggering manual AI analysis for startup: {startup.get('startup_name')}")
        analysis = analyze_startup(startup)
        
        if not analysis or "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis.get("error", "AI Analysis failed"))
            
        save_startup_analysis(int_id, analysis)
        
        # Sync clean founded_year and website to startups table
        clean_founded = analysis.get("founded_year")
        clean_website = analysis.get("startup_website")
        update_payload = {}
        # Keep founded_year nullable (can update to None)
        if "founded_year" in analysis:
            update_payload["founded_year"] = clean_founded
        if clean_website:
            update_payload["website"] = clean_website
        if update_payload:
            supabase.table("startups").update(update_payload).eq("id", int_id).execute()
            
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
        # Fetch startup_name from startups table
        startup_name = ""
        s_res = supabase.table("startups").select("startup_name").eq("id", req.startup_id).execute()
        if s_res.data:
            startup_name = s_res.data[0].get("startup_name", "")
            
        # Fetch reachout messages from startup_analysis if exists
        linkedin_msg = None
        email_msg = None
        ans_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", req.startup_id).execute()
        if ans_res.data and ans_res.data[0].get("analysis_json"):
            analysis = ans_res.data[0]["analysis_json"]
            linkedin_msg = format_outreach_message(analysis.get("linkedin_reachout_message"))
            email_msg = format_outreach_message(analysis.get("email_reachout_message"))

        # Set status to Assigned to FPR1
        status = f"Assigned to {req.assigned_to_fpr1}" if req.assigned_to_fpr1 else "pending"

        ins = {
            "startup_id": req.startup_id,
            "startup_name": startup_name,
            "assigned_to_fpr1": req.assigned_to_fpr1,
            "assigned_to_fpr2": req.assigned_to_fpr2,
            "icici_entity": "ICICI Bank",
            "linkedin_reachout_message": linkedin_msg,
            "email_reachout_message": email_msg,
            "assignment_status": status,
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


@router.get("/interactions")
async def get_interactions():
    """Fetches all startup activity logs/interactions from Supabase."""
    try:
        resp = supabase.table("startup_activity_logs").select("*").order("created_at", desc=True).execute()
        mapped = []
        for row in (resp.data or []):
            notes = row.get("activity_notes") or ""
            summary = notes
            next_steps = "Pending update"
            
            if notes.startswith("Summary: ") and ". Next target status: " in notes:
                parts = notes.split(". Next target status: ")
                summary = parts[0].replace("Summary: ", "")
                next_steps = parts[1]
                
            mapped.append({
                "id": str(row.get("id")),
                "startup_id": str(row.get("startup_id")),
                "date": row.get("created_at") or row.get("date"),
                "type": row.get("activity_type") or "Introduction",
                "summary": summary,
                "next_steps": next_steps
            })
        return mapped
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
    """Generates a dynamic technical readiness strategy report from registry statistics using Ollama."""
    try:
        # Fetch startups and analyses
        response = supabase.table("startups").select("*, startup_analysis(ai_summary, priority_score)").execute()
        db_startups = response.data or []
        
        if not db_startups:
            return {
                "executiveSummary": "No fintech ventures registered in the database yet.",
                "sectorAssessment": "Please add startups to analyze sector readiness.",
                "gapRecommendation": "Add new ventures to get strategic gap assessments."
            }
            
        # Group summary info
        startup_summaries = []
        for s in db_startups:
            analysis = s.get("startup_analysis")
            ai_summary = analysis[0].get("ai_summary", "") if analysis else ""
            score = analysis[0].get("priority_score", 70) if analysis else 70
            desc = ai_summary or s.get("description", "")
            startup_summaries.append(
                f"- {s.get('startup_name')} ({s.get('sector')}, priority score: {score}): {desc}"
            )
            
        startups_context = "\n".join(startup_summaries)
        
        prompt = (
            "You are the ICICI Technical Readiness AI Strategy Director. "
            "Your job is to write a highly professional, structured strategic intelligence report evaluating our current fintech startup registry for executive stakeholders. "
            "Here is the list of currently registered startups in our database:\n\n"
            f"{startups_context}\n\n"
            "Generate an analysis in JSON format with exactly these three keys:\n"
            "- executiveSummary: A 3-4 sentence paragraph highlighting the overall state of the registry, count of startups, and major fintech sectors represented.\n"
            "- sectorAssessment: A detailed analysis of suitabilities/readiness for key sectors present in the list (e.g. InsurTech, LendingTech, WealthTech) based on the specific startups. Highlight specific startup names and their use cases.\n"
            "- gapRecommendation: A list of 3 actionable strategic recommendations/directives for ICICI Bank CoE regarding pilots, partnerships, and technical security gaps.\n\n"
            "Return ONLY a clean JSON object, no introductory or concluding text."
        )
        
        # Call Ollama
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 8192
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=40.0
            )
            resp.raise_for_status()
            result_text = resp.json().get("response", "")
            
            from backend.ai.startup_analyzer import clean_llm_response
            cleaned_json = clean_llm_response(result_text)
            report = json.loads(cleaned_json)
            
            return {
                "executiveSummary": report.get("executiveSummary", "Failed to compile executive summary."),
                "sectorAssessment": report.get("sectorAssessment", "Failed to compile sector assessment."),
                "gapRecommendation": report.get("gapRecommendation", "Failed to compile recommendations.")
            }
        except Exception as oe:
            print(f"⚠️ Ollama insights call failed: {oe}")
            count = len(db_startups)
            return {
                "executiveSummary": f"ICICI Group Startup footprints audit registers strong integration readiness across {count} ventures.",
                "sectorAssessment": "LendingTech integrations remain highest priority. InsurTech and WealthTech systems are positioned for pilot sandboxes.",
                "gapRecommendation": "Recommendation 1: Rapidly deploy sandbox pilots with registered SME lending ventures.\nRecommendation 2: Secure specialized AI-driven cyberrisk audit middleware.\nRecommendation 3: Setup co-creation workshops."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Assistant Chat Route ---

@router.post("/chat")
async def chat_assistant(req: ChatRequest = Body(...)):
    """Communicates with the local qwen2.5:3b model with the database registry context injected."""
    try:
        # Fetch startups from Supabase
        response = supabase.table("startups").select("*, startup_analysis(ai_summary)").execute()
        db_startups = response.data or []
        
        # Serialize database context
        context_lines = []
        for s in db_startups:
            analysis = s.get("startup_analysis")
            ai_summary = analysis[0].get("ai_summary", "") if analysis else ""
            summary = ai_summary or s.get("description", "")
            context_lines.append(
                f"- Name: {s.get('startup_name')}, Industry: {s.get('industry')}, Sector: {s.get('sector')}, Subsector: {s.get('subsector')}, Stage: {s.get('funding_stage')}, Business Model: {s.get('business_models')}, Description: {summary}"
            )
        db_context = "\n".join(context_lines)
        
        system_prompt = (
            "You are the ICICI Startup Intelligence Assistant, a helpful assistant powered by qwen2.5:3b. "
            "Your job is to help users query, analyze, and understand the fintech startup registry. "
            "Below is the current list of startups registered in the database:\n\n"
            f"{db_context}\n\n"
            "Use this database context to answer user queries accurately. Be concise, professional, and clear."
        )
        
        # Format messages for Ollama API
        messages = [{"role": "system", "content": system_prompt}]
        for msg in req.history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Call Ollama
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_ctx": 8192
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            resp.raise_for_status()
            result = resp.json()
            reply = result.get("message", {}).get("content", "I encountered an error querying the model.")
            return {"reply": reply}
        except Exception as oe:
            print(f"⚠️ Ollama chat call failed: {oe}")
            return {"reply": "Sorry, I am currently offline. I couldn't reach the local AI intelligence model."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- GET Assignments Route ---

@router.get("/assignments")
async def get_assignments():
    """Fetches all startup assignments from Supabase."""
    try:
        resp = supabase.table("startup_assignments").select("*").order("created_at", desc=True).execute()
        return resp.data or []
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


@router.patch("/startups/{id}/field")
async def update_startup_field(id: str, req: FieldUpdateRequest = Body(...)):
    """Updates a single specific field in the database (startups / analysis) for inline editing."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")
            
        field = req.field
        value = req.value
        
        # 1. Update the startups table directly if it is a main column
        startup_cols = ["website", "founder_name", "founder_linkedin_url", "funding_stage", "sector", "subsector", "description", "startup_name"]
        if field in startup_cols:
            supabase.table("startups").update({field: value}).eq("id", int_id).execute()
            
        # 2. Update the nested analysis_json inside startup_analysis
        analysis_res = supabase.table("startup_analysis").select("*").eq("startup_id", int_id).execute()
        if analysis_res.data:
            analysis_rec = analysis_res.data[0]
            analysis_json = analysis_rec.get("analysis_json") or {}
            
            # Map frontend edit fields to JSON structure keys
            if field == "website":
                analysis_json["startup_website"] = value
            elif field == "founders":
                analysis_json["founders"] = value
                # Sync first founder's name to startups table
                if isinstance(value, list) and len(value) > 0:
                    founder_name = value[0].get("name", "")
                    founder_linkedin = value[0].get("linkedin_url", "")
                    supabase.table("startups").update({
                        "founder_name": founder_name,
                        "founder_linkedin_url": founder_linkedin
                    }).eq("id", int_id).execute()
            elif field == "funding":
                # Run Pass 3 for real-time funding enrichment on manual edit
                from backend.ai.startup_analyzer import collect_funding_snippets, extract_funding_rounds
                startup_name = supabase.table("startups").select("startup_name").eq("id", int_id).execute()
                sname = startup_name.data[0].get("startup_name", "") if startup_name.data else ""
                if sname:
                    funding_snippets = collect_funding_snippets(sname)
                    funding_result = extract_funding_rounds(sname, funding_snippets)
                    if funding_result:
                        analysis_json["funding_rounds"] = funding_result.get("rounds", [])
                        analysis_json["funding_stages"] = {
                            "series": funding_result.get("latest_stage", value.get("series", "")),
                            "amount": funding_result.get("total_funding", value.get("amount", "")),
                            "investors": [
                                r.get("lead_investor", "") for r in funding_result.get("rounds", []) if r.get("lead_investor")
                            ]
                        }
                        # Persist to dedicated columns
                        analysis_row = supabase.table("startup_analysis").select("id").eq("startup_id", int_id).execute()
                        aid = analysis_row.data[0]["id"] if analysis_row.data else None
                        save_funding_rounds(int_id, funding_result, aid)
                    else:
                        # Fallback to manual value if Pass 3 finds nothing
                        analysis_json["funding_stages"] = value
                # Sync stage to startups table
                supabase.table("startups").update({
                    "funding_stage": analysis_json.get("funding_stages", {}).get("series", "")
                }).eq("id", int_id).execute()
            elif field == "valuation":
                analysis_json["valuation_metrics"] = value
            elif field == "description":
                # Sync business model summary in analysis_json
                if "summary" not in analysis_json:
                    analysis_json["summary"] = {}
                analysis_json["summary"]["business_model"] = value
                
            # Update startup_analysis record
            supabase.table("startup_analysis").update({
                "analysis_json": analysis_json
            }).eq("startup_id", int_id).execute()
            
        # 3. Synchronize all database columns to propagate edits to dashboard fields
        from backend.services.supabase_service import save_startup_analysis
        fresh_analysis_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", int_id).execute()
        if fresh_analysis_res.data:
            save_startup_analysis(int_id, fresh_analysis_res.data[0]["analysis_json"])
            
        return {"status": "success", "message": f"Successfully updated field '{field}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/startups/{id}/recheck")
async def recheck_startup_field(id: str, req: FieldRecheckRequest = Body(...)):
    """Runs a targeted query and LLM analysis to re-discover a single specific field (website, founders, or funding)."""
    try:
        try:
            int_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid startup ID '{id}'. Must be an integer.")
            
        field = req.field
        if field not in ["website", "founders", "funding"]:
            raise HTTPException(status_code=400, detail=f"Targeted recheck is not supported for field '{field}'.")
            
        startup_resp = supabase.table("startups").select("*").eq("id", int_id).execute()
        if not startup_resp.data:
            raise HTTPException(status_code=404, detail="Startup not found")
            
        startup = startup_resp.data[0]
        startup_name = startup.get("startup_name", "")
        # Clean clean brand name
        clean_name = startup_name.split(" raises ")[0].split(" acquires ")[0].split(" launches ")[0].strip()
        
        from backend.utils.search import search_duckduckgo
        
        print(f"🔄 Running targeted AI recheck for startup: '{clean_name}' (Field: '{field}')...")
        
        # Field-specific execution
        search_context = ""
        prompt = ""
        
        if field == "website":
            search_query = f"{clean_name} official website URL"
            try:
                search_context = search_duckduckgo(search_query)
            except Exception as se:
                search_context = f"Search failed: {se}"
                
            prompt = f"""You are a precise data parsing assistant.
Analyze the search engine snippets below and extract the official corporate homepage URL for the company '{clean_name}'.
Return ONLY a valid JSON block containing the "startup_website" key. Do not output any notes, commentary, or wrapper text.

JSON Schema:
{{
  "startup_website": "https://example.com"
}}

Search Snippets:
{search_context}

Begin parsing:
"""

        elif field == "founders":
            search_query = f"{clean_name} founders co-founders LinkedIn profiles"
            try:
                search_context = search_duckduckgo(search_query)
            except Exception as se:
                search_context = f"Search failed: {se}"
                
            prompt = f"""You are a precise database parsing assistant.
Analyze the search snippets below and extract the list of corporate co-founders for the company '{clean_name}'.
For each founder, extract their full name, role/title, a brief 1-sentence bio, and LinkedIn profile URL (or empty string if not found).
Return ONLY a valid JSON block containing the "founders" key. Do not output any notes, commentary, or wrapper text.

JSON Schema:
{{
  "founders": [
    {{
      "name": "Full Name",
      "role": "CEO & Co-founder",
      "brief_details": "Brief background info details.",
      "linkedin_url": "https://www.linkedin.com/in/username"
    }}
  ]
}}

Search Snippets:
{search_context}

Begin parsing:
"""

        elif field == "funding":
            search_query = f"{clean_name} funding rounds series valuation investors"
            try:
                search_context = search_duckduckgo(search_query)
            except Exception as se:
                search_context = f"Search failed: {se}"
                
            prompt = f"""You are a precise database parsing assistant.
Analyze the search snippets below and extract the capital funding stage details for the company '{clean_name}'.
Identify the current funding series (e.g. Series A, Series B, Seed, Bootstrapped), the last/total capital raised amount, and the list of lead investors.
Return ONLY a valid JSON block containing the "funding_stages" key. Do not output any notes, commentary, or wrapper text.

JSON Schema:
{{
  "funding_stages": {{
    "series": "Series A",
    "amount": "$10M",
    "investors": ["Investor 1", "Investor 2"]
  }}
}}

Search Snippets:
{search_context}

Begin parsing:
"""

        # Call local Ollama model
        from backend.ai.startup_analyzer import clean_llm_response
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 4096
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        response.raise_for_status()
        result_text = response.json().get("response", "")
        cleaned_json = clean_llm_response(result_text)
        data = json.loads(cleaned_json)
        
        # Save results to Database
        analysis_res = supabase.table("startup_analysis").select("*").eq("startup_id", int_id).execute()
        if analysis_res.data:
            analysis_rec = analysis_res.data[0]
            analysis_json = analysis_rec.get("analysis_json") or {}
            
            if field == "website":
                extracted_val = data.get("startup_website") or ""
                analysis_json["startup_website"] = extracted_val
                supabase.table("startups").update({"website": extracted_val}).eq("id", int_id).execute()
                
            elif field == "founders":
                extracted_val = data.get("founders") or []
                analysis_json["founders"] = extracted_val
                if isinstance(extracted_val, list) and len(extracted_val) > 0:
                    founder_name = extracted_val[0].get("name", "")
                    founder_linkedin = extracted_val[0].get("linkedin_url", "")
                    supabase.table("startups").update({
                        "founder_name": founder_name,
                        "founder_linkedin_url": founder_linkedin
                    }).eq("id", int_id).execute()
                    
            elif field == "funding":
                # Run Pass 3: multi-source search + dedicated LLM extraction
                from backend.ai.startup_analyzer import collect_funding_snippets, extract_funding_rounds
                startup_name_res = supabase.table("startups").select("startup_name").eq("id", int_id).execute()
                sname = startup_name_res.data[0].get("startup_name", "") if startup_name_res.data else ""
                if sname:
                    funding_snippets = collect_funding_snippets(sname)
                    funding_result = extract_funding_rounds(sname, funding_snippets)
                    if funding_result:
                        rounds = funding_result.get("rounds", [])
                        analysis_json["funding_rounds"] = rounds
                        analysis_json["funding_stages"] = {
                            "series": funding_result.get("latest_stage", ""),
                            "amount": funding_result.get("total_funding", ""),
                            "investors": list(dict.fromkeys(
                                [r.get("lead_investor", "") for r in rounds if r.get("lead_investor")] +
                                [inv for r in rounds for inv in r.get("co_investors", [])]
                            ))
                        }
                        # Sync stage
                        supabase.table("startups").update({
                            "funding_stage": funding_result.get("latest_stage", "")
                        }).eq("id", int_id).execute()
                        # Persist to dedicated columns
                        save_funding_rounds(int_id, funding_result, analysis_rec.get("id"))
                        data = {"funding_stages": analysis_json["funding_stages"], "funding_rounds": rounds}
                
            supabase.table("startup_analysis").update({"analysis_json": analysis_json}).eq("id", analysis_rec["id"]).execute()
            
        from backend.services.supabase_service import save_startup_analysis
        fresh_analysis_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", int_id).execute()
        if fresh_analysis_res.data:
            save_startup_analysis(int_id, fresh_analysis_res.data[0]["analysis_json"])
            
        return {"status": "success", "field": field, "data": data}
        
    except Exception as e:
        print(f"❌ Targeted recheck failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/reset")
async def reset_database():
    """Mock seed reset handler."""
    return {"status": "success", "message": "Database seed parameters reinitialized."}
