import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.supabase_service import supabase

tables = [
    "startup_assignments",
    "startup_activity_logs",
    "startup_analysis",
    "startup_news",
    "startups",
    "obs_frontend_events",
    "obs_graph_mutations",
    "obs_db_mutations",
    "obs_prompt_ledger",
    "obs_agent_executions",
    "obs_api_calls",
    "obs_traces"
]

print("Starting database cleanup...")
for table in tables:
    try:
        print(f"Clearing table: {table}...")
        res = supabase.table(table).delete().neq("id", -1).execute()
        count = len(res.data) if res.data else 0
        print(f"✅ Successfully cleared {table}: removed {count} rows.")
    except Exception as e:
        print(f"❌ Error clearing {table}: {e}")

print("Database cleanup completed!")
