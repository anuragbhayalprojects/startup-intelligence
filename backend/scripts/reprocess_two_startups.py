import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Ensure Ollama base URL and model are correct
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:3b"
os.environ["FORCE_STARTUP_PIPELINE_RUN"] = "true"

from backend.services.supabase_service import supabase
from backend.workflows.agent_orchestrator import AgentOrchestrator

def reprocess_startups():
    names = ["HyperNorm AI", "Bucketlistt"]
    orchestrator = AgentOrchestrator()
    
    for name in names:
        print(f"\n==============================================================")
        print(f"🚀 Reprocessing multi-agent workflow for '{name}'...")
        print(f"==============================================================")
        
        # Fetch startup details from database
        res = supabase.table("startups").select("*").eq("startup_name", name).execute()
        if not res.data:
            res = supabase.table("startups").select("*").ilike("startup_name", f"%{name}%").execute()
            
        if res.data:
            s = res.data[0]
            startup_id = s["id"]
            # Fetch latest news headline as actual headline if available
            headline = s["startup_name"]
            try:
                news_resp = supabase.table("startup_news").select("headline").eq("startup_id", startup_id).order("published_at", desc=True).limit(1).execute()
                if news_resp.data and news_resp.data[0].get("headline"):
                    headline = news_resp.data[0]["headline"]
            except Exception:
                pass

            raw_startup = {
                "startup_name": s["startup_name"],
                "headline": headline,
                "description": s["description"] or "",
                "source": s.get("source") or "Manual Recheck",
                "source_url": s.get("source_url") or ""
            }
            
            # Run the multi-agent pipeline
            # Note: run_pipeline automatically handles database persistence
            state = orchestrator.run_pipeline(raw_startup)
            
            print(f"\n✅ Pipeline finished for '{name}'!")
            print(f"   - Startup ID: {state.startup_id}")
            print(f"   - Relevance Score: {state.relevance.get('score')}")
            print(f"   - Strategic Fit Score: {state.strategic_fit.get('score')}")
            print(f"   - Confidence Score: {state.confidence_score}")
            print(f"   - Recommendation Score: {state.recommendation_score}")
            print(f"   - Priority Urgency Band: {state.priority_band}")
            print(f"   - Errors: {state.errors}")
        else:
            print(f"❌ Startup '{name}' not found in database.")

if __name__ == "__main__":
    reprocess_startups()
