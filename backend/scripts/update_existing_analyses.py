import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from backend.services.supabase_service import supabase, save_startup_analysis

def fix_startups():
    names = ["HyperNorm AI", "Bucketlistt"]
    for name in names:
        print(f"\nFixing analysis for '{name}'...")
        res = supabase.table("startups").select("id").eq("startup_name", name).execute()
        if not res.data:
            res = supabase.table("startups").select("id").ilike("startup_name", f"%{name}%").execute()
            
        if res.data:
            startup_id = res.data[0]["id"]
            print(f"Found Startup ID: {startup_id}")
            
            # Fetch current analysis
            ans_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", startup_id).execute()
            if ans_res.data:
                current_json = ans_res.data[0]["analysis_json"]
                
                # Re-run save_startup_analysis with the current analysis_json
                # This triggers our new fallback parser which will unpack and standardize it.
                save_startup_analysis(startup_id, current_json)
                print(f"Successfully fixed/standardized analysis for '{name}'!")
            else:
                print(f"No startup_analysis record found for ID: {startup_id}")
        else:
            print(f"Startup '{name}' not found in database.")

if __name__ == "__main__":
    fix_startups()
