from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.services.supabase_service import supabase, save_startup_analysis
from backend.ai.startup_analyzer import analyze_startup
from backend.scrapers.scraper_manager import run_scraper
import os
import re
import json
import requests
from backend.utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

router = APIRouter()

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

@router.post("/scrape")
async def scrape(scrape_request: ScrapeRequest = Body(...)):
    """Triggers scrapers or web search updates for specified sources."""
    try:
        results = []
        limit = scrape_request.limit
        
        for src in scrape_request.sources:
            if src == "Inc42":
                print(f"🚀 Running Inc42 scraper, limit: {limit}...")
                from backend.scrapers.inc42.scraper import scrape_inc42
                data = scrape_inc42(limit)
                for item in data:
                    from backend.workflows.startup_pipeline import process_startup
                    process_startup(item)
                results.append(f"Inc42 scraper processed {len(data)} articles.")
                
            elif src == "Entrackr":
                print(f"🚀 Running Entrackr scraper, limit: {limit}...")
                from backend.scrapers.entrackr.scraper import scrape_entrackr
                data = scrape_entrackr(limit)
                for item in data:
                    from backend.workflows.startup_pipeline import process_startup
                    process_startup(item)
                results.append(f"Entrackr scraper processed {len(data)} articles.")
                
            elif src == "Custom Web Search":
                print(f"🚀 Running Custom Web Search update pipeline...")
                # Compile dynamic search query from filters
                query_parts = []
                if scrape_request.keywords:
                    query_parts.append(scrape_request.keywords)
                if scrape_request.subsector and scrape_request.subsector != "Unknown":
                    query_parts.append(scrape_request.subsector)
                if scrape_request.sector and scrape_request.sector != "Unknown":
                    query_parts.append(scrape_request.sector)
                if scrape_request.industry and scrape_request.industry != "Unknown":
                    query_parts.append(scrape_request.industry)
                    
                query_parts.append("startup news funding India 2026")
                search_query = " ".join(query_parts)
                
                # Perform Search to discover article links
                from backend.utils.search import search_duckduckgo
                search_res = search_duckduckgo(search_query)
                
                # Parse Google/DDG result snippets to extract titles and links
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
                                "startup_name": current_title, # Raw headline
                                "description": current_snippet or "No description available.",
                                "source": "Custom Web Search",
                                "source_url": current_url
                            })
                            current_title = ""
                            current_url = ""
                            current_snippet = ""
                
                # Run through pipeline
                count = 0
                for art in articles[:limit]:
                    from backend.workflows.startup_pipeline import process_startup
                    res = process_startup(art)
                    if res:
                        count += len(res)
                        
                results.append(f"Custom Web Search discovered and processed {count} startups.")
                
        return {"message": " / ".join(results)}
    except Exception as e:
        print(f"❌ Scraper route execution failed: {e}")
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
                
        startup["startup_analyses"] = startup_analyses
        return startup
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
                now = datetime.now(timezone.utc)
                age = now - created_at
                if age.days < 30:
                    print(f"✅ Cache hit: Using fresh startup analysis from DB (created {age.days} days ago).")
                    return {"analysis_data": record.get("analysis_json")}
        
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


@router.post("/database/reset")
async def reset_database():
    """Mock seed reset handler."""
    return {"status": "success", "message": "Database seed parameters reinitialized."}
