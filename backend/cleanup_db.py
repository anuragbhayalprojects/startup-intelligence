import os
import sys
import re

# Ensure project root is in path
sys.path.append("/Users/anurag/Projects/startup-intelligence")

from backend.services.supabase_service import supabase
from backend.workflows.startup_pipeline import clean_string, get_clean_startup_name, get_clean_website

def cleanup_database():
    print("--- Starting Robust Supabase Database Cleanup ---")
    
    # 1. Fetch all startups
    response = supabase.table("startups").select("*").execute()
    startups = response.data
    
    if not startups:
        print("No startups found in the database.")
        return

    print(f"Found {len(startups)} startups in total. deduplicating and cleaning...\n")
    
    # --- PHASE 1: DEDUPLICATE BY SOURCE URL (Article-Level Deduplication) ---
    url_groups = {}
    for startup in startups:
        url = startup.get("source_url")
        if url:
            if url not in url_groups:
                url_groups[url] = []
            url_groups[url].append(startup)
            
    deduplicated_startups = []
    for url, group in url_groups.items():
        if len(group) > 1:
            print(f"\n⚡ Deduplicating by Source URL: '{url}' ({len(group)} entries):")
            # Sort entries by length of startup_name descending so that the full headline containing full context is kept
            group_sorted = sorted(group, key=lambda x: len(x.get("startup_name") or ""), reverse=True)
            keep_startup = group_sorted[0]
            keep_id = keep_startup["id"]
            print(f"   --> Keeping ID {keep_id} ('{keep_startup['startup_name']}')")
            
            for dup in group_sorted[1:]:
                dup_id = dup["id"]
                print(f"   --> Deleting duplicate ID {dup_id} ('{dup.get('startup_name')}')")
                try:
                    supabase.table("startup_analysis").delete().eq("startup_id", dup_id).execute()
                    supabase.table("startups").delete().eq("id", dup_id).execute()
                except Exception as e:
                    print(f"       Failed to delete duplicate ID {dup_id}: {e}")
            deduplicated_startups.append(keep_startup)
        else:
            deduplicated_startups.append(group[0])

    # --- PHASE 2: PURGE MACRO / GENERAL INDUSTRY REVEWS ---
    valid_startups = []
    
    macro_terms = [
        "indian startup funding", "funding and acquisitions", "real money gaming", 
        "weekly funding", "funding report", "industry report", "indian startups",
        "various startups", "indian startup", "funding", "acquisitions", "gaming",
        "real money", "stories", "months of", "after months", "funding and",
        "and", "to", "for", "with", "the", "months", "after months",
        "e2w", "ew", "e2w registrations", "electric two wheelers", 
        "electric two-wheeler", "electric two wheeler", "registrations"
    ]

    for startup in deduplicated_startups:
        startup_id = startup["id"]
        original_name = startup["startup_name"]
        
        # Fetch related AI analysis if it exists
        analysis_res = supabase.table("startup_analysis").select("analysis_json").eq("startup_id", startup_id).execute()
        analysis = {}
        if analysis_res.data and len(analysis_res.data) > 0:
            analysis = analysis_res.data[0].get("analysis_json") or {}

        # Get the clean name
        clean_name = get_clean_startup_name(original_name, analysis)
        
        is_macro = False
        if not clean_name:
            is_macro = True
        else:
            name_lower = clean_name.lower().strip()
            if name_lower in macro_terms or len(name_lower) <= 2:
                is_macro = True
            elif any(term in name_lower for term in ["startup funding", "funding report", "acquisitions in", "e2w", "electric two-wheeler"]):
                is_macro = True
                
        if is_macro:
            print(f"🗑️  [Macro/Generic] Purging ID {startup_id} - '{original_name}' (Clean Name: '{clean_name}')...")
            try:
                supabase.table("startup_analysis").delete().eq("startup_id", startup_id).execute()
                supabase.table("startups").delete().eq("id", startup_id).execute()
                print(f"   Successfully deleted.")
            except Exception as e:
                print(f"   Failed to delete: {e}")
            continue

        valid_startups.append((startup, clean_name, analysis))

    # --- PHASE 3: DEDUPLICATE BY CLEAN BRAND NAME ---
    grouped_startups = {}
    for entry in valid_startups:
        startup, clean_name, analysis = entry
        name_key = clean_name.lower().strip()
        if name_key not in grouped_startups:
            grouped_startups[name_key] = []
        grouped_startups[name_key].append(entry)

    for name_key, entries in list(grouped_startups.items()):
        if len(entries) > 1:
            print(f"\n⚡ Deduplicating group by clean brand name '{name_key}' ({len(entries)} entries):")
            
            best_entry = None
            for entry in entries:
                startup = entry[0]
                clean_name = entry[1]
                if startup["startup_name"] == clean_name:
                    best_entry = entry
                    break
            
            if not best_entry:
                entries_sorted = sorted(entries, key=lambda x: x[0]["id"])
                best_entry = entries_sorted[0]
                
            keep_startup, keep_clean_name, keep_analysis = best_entry
            keep_id = keep_startup["id"]
            print(f"   --> Keeping ID {keep_id} ('{keep_startup['startup_name']}')")
            
            for entry in entries:
                dup_startup = entry[0]
                dup_id = dup_startup["id"]
                if dup_id != keep_id:
                    print(f"   --> Deleting duplicate ID {dup_id} ('{dup_startup['startup_name']}')")
                    try:
                        supabase.table("startup_analysis").delete().eq("startup_id", dup_id).execute()
                        supabase.table("startups").delete().eq("id", dup_id).execute()
                    except Exception as e:
                        print(f"       Failed to delete duplicate ID {dup_id}: {e}")
            
            grouped_startups[name_key] = [best_entry]

    # --- PHASE 4: UPDATE REMAINING ENTRIES ---
    print("\n📝 Updating remaining records to their clean names and websites...")
    for name_key, entries in grouped_startups.items():
        if not entries:
            continue
        startup, clean_name, analysis = entries[0]
        startup_id = startup["id"]
        original_name = startup["startup_name"]
        
        clean_website = get_clean_website(clean_name, analysis)
        
        needs_update = False
        update_data = {}
        
        if original_name != clean_name:
            update_data["startup_name"] = clean_name
            needs_update = True
            
        if startup.get("website") != clean_website:
            update_data["website"] = clean_website
            needs_update = True
            
        if needs_update:
            print(f"📝 Updating ID {startup_id}:")
            if "startup_name" in update_data:
                print(f"   Name: '{original_name}' -> '{clean_name}'")
            if "website" in update_data:
                print(f"   Website: '{startup.get('website')}' -> '{clean_website}'")
            try:
                supabase.table("startups").update(update_data).eq("id", startup_id).execute()
                print(f"   Successfully updated in DB.")
            except Exception as e:
                print(f"   Failed to update ID {startup_id}: {e}")
        else:
            print(f"✅ ID {startup_id} ('{clean_name}') is already clean. (Web: '{clean_website}')")

    print("\n--- Database Cleanup Completed ---")

if __name__ == "__main__":
    cleanup_database()
