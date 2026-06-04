import os
import sys

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.append(PROJECT_ROOT)

from backend.services.supabase_service import supabase

def check_progress():
    print("--- Checking Startup Analysis DB Status ---")
    try:
        # Fetch startups
        s_res = supabase.table("startups").select("id, startup_name").execute()
        startups = {s["id"]: s["startup_name"] for s in (s_res.data or [])}
        
        # Fetch analyses
        a_res = supabase.table("startup_analysis").select("startup_id, ai_summary, analysis_json").execute()
        analyses = a_res.data or []
        
        print(f"Total startups in registry: {len(startups)}")
        print(f"Total enriched analyses: {len(analyses)}")
        
        for i, a in enumerate(analyses, 1):
            s_id = a.get("startup_id")
            s_name = startups.get(s_id, f"Unknown ID {s_id}")
            ai_sum = a.get("ai_summary", "")
            details = a.get("analysis_json", {})
            summary = details.get("summary", {})
            biz_model = summary.get("business_model", "")
            
            print(f"\n[{i}] Startup: {s_name} (ID: {s_id})")
            print(f"    One-liner: {ai_sum}")
            print(f"    Business Model Paragraph: {biz_model}")
            
    except Exception as e:
        print(f"Error checking progress: {e}")

if __name__ == "__main__":
    check_progress()
