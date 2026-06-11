import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from backend.services.supabase_service import supabase

print("=== CHECKING STARTUPS IN DB ===")
for name in ["FinBox", "Incuspaze"]:
    print(f"\n🔎 Querying database for: {name}")
    s_res = supabase.table("startups").select("*").ilike("startup_name", f"%{name}%").execute()
    if s_res.data:
        for row in s_res.data:
            print(f"ID: {row.get('id')}")
            print(f"Name: {row.get('startup_name')}")
            print(f"Created At: {row.get('created_at')}")
            print(f"HQ: {row.get('headquarters')}")
            print(f"Stage: {row.get('funding_stage')}")
    else:
        print(f"❌ '{name}' not found in startups table.")
