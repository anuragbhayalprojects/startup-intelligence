import os
import sys
import json
import time

# Ensure project root is in python path
PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.append(PROJECT_ROOT)

from backend.services.supabase_service import supabase, save_startup_analysis
from backend.ai.startup_analyzer import analyze_startup
from backend.workflows.startup_pipeline import get_clean_startup_name, get_clean_website, upsert_startup

def enrich_all_startups():
    print("==============================================================")
    print("🚀 Starting Master Taxonomy AI Enrichment & Backfill Script")
    print("Ollama Model: qwen2.5:3b")
    print("==============================================================")

    # 1. Fetch all startups from Supabase
    try:
        response = supabase.table("startups").select("*").execute()
        startups = response.data
    except Exception as e:
        print(f"❌ Failed to fetch startups from Supabase: {e}")
        return

    if not startups:
        print("ℹ️ No startups found in the database.")
        return

    total = len(startups)
    print(f"📋 Found {total} startups in database to evaluate and enrich.")

    success_count = 0
    fail_count = 0

    for i, s in enumerate(startups, 1):
        startup_id = s.get("id")
        original_name = s.get("startup_name")
        print(f"\n[{i}/{total}] Processing: '{original_name}' (ID: {startup_id})...")
        
        # Prepare startup payload for analyzer
        startup_payload = {
            "startup_name": original_name,
            "description": s.get("description") or "",
            "source": s.get("source") or "Database Backfill",
            "source_url": s.get("source_url") or ""
        }

        # 2. Run LLM Taxonomy Analysis using local qwen2.5:3b
        try:
            print(f"   🤖 Calling local qwen2.5:3b for taxonomy classification...")
            start_time = time.time()
            analysis_result = analyze_startup(startup_payload)
            duration = time.time() - start_time
            print(f"   ⏱️ AI Analysis finished in {duration:.2f} seconds.")
        except Exception as ae:
            print(f"   ❌ AI analyzer failed for {original_name}: {ae}")
            fail_count += 1
            continue

        if not analysis_result or "error" in analysis_result:
            error_msg = analysis_result.get("error", "Unknown error") if analysis_result else "Null response"
            print(f"   ⚠️ Skipping: AI analysis returned an error: {error_msg}")
            fail_count += 1
            continue

        # Extract name and website updates
        clean_name = get_clean_startup_name(original_name, analysis_result)
        website = get_clean_website(clean_name, analysis_result)

        # 3. Save the structured AI analysis and synchronize core taxonomy columns
        try:
            print(f"   💾 Storing taxonomy details to Supabase...")
            
            # Sync name/website if updated
            s_updates = {}
            if clean_name and clean_name != original_name:
                s_updates["startup_name"] = clean_name
            if website and website != s.get("website"):
                s_updates["website"] = website
                
            if s_updates:
                supabase.table("startups").update(s_updates).eq("id", startup_id).execute()
                print(f"   ✅ Updated metadata (Name: {clean_name}, Website: {website})")

            # Save detailed analysis (which automatically parses & synchronizes industry, sector, subsector, business_models, industry_relevance, tags)
            save_startup_analysis(startup_id, analysis_result)
            
            print(f"   🎉 Successfully enriched '{clean_name or original_name}'!")
            
            # Print the classifications saved
            classification = analysis_result.get("classification", {})
            print(f"      - Industry: {classification.get('industry')}")
            print(f"      - Sector: {classification.get('sector')}")
            print(f"      - Subsector: {classification.get('subsector')}")
            print(f"      - Business Models: {classification.get('business_models')}")
            print(f"      - Industry Relevance: {classification.get('industry_relevance')}")
            print(f"      - Tags: {classification.get('tags')}")
            
            success_count += 1
        except Exception as se:
            print(f"   ❌ Failed to write backfill data to Supabase: {se}")
            fail_count += 1

    print("\n==============================================================")
    print("📈 Enrichment & Backfill Completed!")
    print(f"   - Successfully Enriched: {success_count}/{total}")
    print(f"   - Failed: {fail_count}/{total}")
    print("==============================================================")

if __name__ == "__main__":
    enrich_all_startups()
