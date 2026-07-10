import os
import sys
import time
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# Add 'backend' and 'repo root' directories to PYTHONPATH dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.routes import startups
from api.routes import enrichment as enrichment_routes
from api.routes import scraping as scraping_routes
from api.routes import observability as observability_routes
from api.routes import news as news_routes

from backend.utils.tracing import (
    set_trace_id,
    reset_trace_id,
    generate_trace_id,
    log_api_call,
    log_trace,
    log_frontend_event,
    wrap_supabase_client
)

load_dotenv()

app = FastAPI()

# Configure CORS Middleware with explicit origins and expose X-Trace-ID header
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "https://startup-intelligence.vercel.app",
        "https://startup-intelligence-teal.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID"],
)

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    # Don't trace static/docs, options, scrape status polling, or observability event logging to prevent connection/write bottlenecks
    if (
        request.method == "OPTIONS"
        or request.url.path.startswith("/docs")
        or request.url.path.startswith("/openapi.json")
        or request.url.path == "/api/scrape/status"
        or request.url.path.startswith("/api/observability")
    ):
        return await call_next(request)

    # Retrieve X-Trace-ID or generate one
    trace_id = request.headers.get("x-trace-id") or request.headers.get("X-Trace-ID")
    if not trace_id:
        trace_id = generate_trace_id()
    
    token = set_trace_id(trace_id)
    log_trace()  # Log the root trace
    
    start_time = time.perf_counter()
    
    # Safely extract payload for non-GET requests
    payload = {}
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.body()
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive
            if body:
                payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {"error": "Could not parse request body"}
            
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Trace-ID"] = trace_id
        
        log_api_call(
            route=request.url.path,
            method=request.method,
            payload=payload,
            response={"status_code": response.status_code},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        return response
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        log_api_call(
            route=request.url.path,
            method=request.method,
            payload=payload,
            response={"error": str(e)},
            status_code=500,
            duration_ms=duration_ms
        )
        raise e
    finally:
        reset_trace_id(token)

# Route router registrations
app.include_router(startups.router, prefix="/api")
app.include_router(enrichment_routes.router, prefix="/api")    # New: section-wise re-enrichment endpoints
app.include_router(scraping_routes.router, prefix="/api")      # New: scraping config + log management
app.include_router(observability_routes.router, prefix="/api") # New: enrichment stats, routing history, health
app.include_router(news_routes.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    from backend.pipeline.scheduler import start_background_scheduler
    start_background_scheduler(app)


# Observability endpoints
class FrontendEvent(BaseModel):
    page: str
    component: str
    action: str
    payload: dict = {}

@app.post("/api/observability/event")
def record_frontend_event(event: FrontendEvent):
    log_frontend_event(
        page=event.page,
        component=event.component,
        action=event.action,
        payload=event.payload
    )
    return {"status": "logged"}

@app.get("/api/observability/traces")
def list_traces():
    from backend.services.supabase_service import supabase
    res = supabase.table("obs_traces").select("*").order("created_at", desc=True).limit(50).execute()
    return res.data or []

@app.get("/api/observability/traces/{trace_id}")
def get_trace_details(trace_id: str):
    from backend.services.supabase_service import supabase
    traces = supabase.table("obs_traces").select("*").eq("trace_id", trace_id).execute()
    api_calls = supabase.table("obs_api_calls").select("*").eq("trace_id", trace_id).order("created_at").execute()
    agent_executions = supabase.table("obs_agent_executions").select("*").eq("trace_id", trace_id).order("created_at").execute()
    prompts = supabase.table("obs_prompt_ledger").select("*").eq("trace_id", trace_id).order("created_at").execute()
    db_mutations = supabase.table("obs_db_mutations").select("*").eq("trace_id", trace_id).order("created_at").execute()
    graph_mutations = supabase.table("obs_graph_mutations").select("*").eq("trace_id", trace_id).order("created_at").execute()
    frontend_events = supabase.table("obs_frontend_events").select("*").eq("trace_id", trace_id).order("created_at").execute()
    
    return {
        "trace": traces.data[0] if traces.data else {"trace_id": trace_id},
        "api_calls": api_calls.data or [],
        "agent_executions": agent_executions.data or [],
        "prompts": prompts.data or [],
        "db_mutations": db_mutations.data or [],
        "graph_mutations": graph_mutations.data or [],
        "frontend_events": frontend_events.data or []
    }

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = wrap_supabase_client(create_client(supabase_url, supabase_key))

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Startup Intelligence OS API"}

