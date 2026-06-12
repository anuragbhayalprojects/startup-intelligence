#!/usr/bin/env python3
"""
seed_identity_registry.py
--------------------------
Seeds the startup_identity table from multiple sources in priority order:

  Priority 1: CANONICAL_OVERLOADS (taxonomy_mapper.py) — highest confidence (0.98)
  Priority 2: Existing startup_analysis records (analysis_json) — confidence 0.80
  Priority 3: Existing startups table records — confidence 0.70
  Priority 4: Verified domain registry (website_resolver.KNOWN_DOMAINS) — confidence 0.88
  Priority 5: Known founder registry (leadership_resolver.KNOWN_FOUNDERS) — confidence 0.85

Each record stores: source, confidence, evidence_count, last_verified
Records are UPSERTED (not duplicated) based on startup_id uniqueness.

Usage:
  cd /Users/anurag/Projects/startup-intelligence
  python -m backend.scripts.seed_identity_registry [--dry-run] [--force]

Options:
  --dry-run  : Preview what would be seeded, no DB writes
  --force    : Re-seed all records even if already seeded
  --verbose  : Print detailed per-record output
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services.supabase_service import supabase
from backend.utils.website_resolver import KNOWN_DOMAINS, resolve_website
from backend.utils.leadership_resolver import KNOWN_FOUNDERS


def get_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str, verbose: bool = True):
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def upsert_identity_record(record: dict, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Upserts a single identity record directly to the startups table.
    Returns True if a record was created/updated.
    """
    startup_id = record.get("startup_id")
    if not startup_id:
        return False

    if dry_run:
        log(f"  [DRY-RUN] Would upsert identity for startup_id={startup_id}: {record.get('startup_name')}", verbose)
        return True

    try:
        # Check if record exists in startups
        existing = supabase.table("startups").select("id, identity_confidence, evidence_count").eq("id", startup_id).execute()

        record = dict(record)
        record["updated_at"] = get_now_iso()
        record.pop("startup_id", None)
        record.pop("id", None)

        # Synchronize duplicate/aliased columns
        if "linkedin_company_url" in record and record["linkedin_company_url"]:
            record["linkedin_url"] = record["linkedin_company_url"]
        elif "linkedin_url" in record and record["linkedin_url"]:
            record["linkedin_company_url"] = record["linkedin_url"]

        if "primary_founder_name" in record and record["primary_founder_name"]:
            record["founder_name"] = record["primary_founder_name"]
        elif "founder_name" in record and record["founder_name"]:
            record["primary_founder_name"] = record["founder_name"]

        if "primary_founder_linkedin" in record and record["primary_founder_linkedin"]:
            record["founder_linkedin_url"] = record["primary_founder_linkedin"]
        elif "founder_linkedin_url" in record and record["founder_linkedin_url"]:
            record["primary_founder_linkedin"] = record["founder_linkedin_url"]

        if existing.data:
            existing_rec = existing.data[0]
            # Only update if new confidence is higher OR force flag is set
            if (record.get("identity_confidence") or 0.0) >= (existing_rec.get("identity_confidence") or 0.0):
                # Merge evidence_count
                record["evidence_count"] = max(
                    record.get("evidence_count", 1) or 1,
                    existing_rec.get("evidence_count", 0) or 0
                )
                supabase.table("startups").update(record).eq("id", existing_rec["id"]).execute()
                log(f"  ✅ Updated: {record.get('startup_name')} (startup_id={startup_id})", verbose)
            else:
                log(f"  ⏭️  Skipped (lower confidence): {record.get('startup_name')}", verbose)
                return False
        else:
            record["id"] = startup_id
            record["created_at"] = get_now_iso()
            supabase.table("startups").insert(record).execute()
            log(f"  ✨ Inserted: {record.get('startup_name')} (startup_id={startup_id})", verbose)

        return True
    except Exception as e:
        log(f"  ❌ Failed for startup_id={startup_id}: {e}", True)
        return False


def seed_from_canonical_overloads(dry_run: bool, verbose: bool) -> int:
    """
    Priority 1: Seeds from CANONICAL_OVERLOADS in taxonomy_mapper.py.
    Confidence: 0.98 — highest quality, manually curated.
    """
    print("\n📚 [Priority 1] Seeding from CANONICAL_OVERLOADS...")
    count = 0

    try:
        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
    except ImportError as e:
        print(f"  ❌ Could not import CANONICAL_OVERLOADS: {e}")
        return 0

    # Get all startups for name matching
    startups_resp = supabase.table("startups").select("id, startup_name, website, founder_name, founder_linkedin_url").execute()
    startups = {s["startup_name"].strip().lower(): s for s in (startups_resp.data or [])}

    for canonical_key, overload in CANONICAL_OVERLOADS.items():
        # Find matching startup in DB
        matched_startup = None
        for sname_lower, startup in startups.items():
            if canonical_key in sname_lower or sname_lower in canonical_key or sname_lower == canonical_key:
                matched_startup = startup
                break

        if not matched_startup:
            log(f"  ⚠️  No DB match for canonical key: '{canonical_key}'", verbose)
            continue

        # Build identity record
        founders_info = overload.get("founders", [])
        primary_founder = founders_info[0] if founders_info else {}

        record = {
            "startup_id": matched_startup["id"],
            "startup_name": matched_startup["startup_name"],
            "brand_name": canonical_key,
            "aliases": [canonical_key],
            "website": overload.get("website", matched_startup.get("website", "")),
            "primary_founder_name": primary_founder.get("name", matched_startup.get("founder_name", "")),
            "primary_founder_linkedin": primary_founder.get("linkedin_url", matched_startup.get("founder_linkedin_url", "")),
            "primary_founder_title": primary_founder.get("role", "Founder"),
            "leadership": founders_info,
            "headquarters": overload.get("headquarters", ""),
            "founded_year": overload.get("founded_year"),
            "founded_year_confidence": 0.95 if overload.get("founded_year") else 0.0,
            "identity_confidence": 0.98,
            "source": "canonical_overloads",
            "evidence_count": 4,
            "last_verified": get_now_iso(),
            "verification_notes": "Seeded from CANONICAL_OVERLOADS (manually curated).",
        }

        if upsert_identity_record(record, dry_run, verbose):
            count += 1

    print(f"  → Seeded {count} records from CANONICAL_OVERLOADS.")
    return count


def seed_from_startup_analysis(dry_run: bool, verbose: bool) -> int:
    """
    Priority 2: Seeds from existing startup_analysis records.
    Confidence: 0.80 — AI-generated, may have errors.
    """
    print("\n🤖 [Priority 2] Seeding from startup_analysis records...")
    count = 0

    analysis_resp = supabase.table("startup_analysis").select("startup_id, analysis_json").execute()
    if not analysis_resp.data:
        print("  → No startup_analysis records found.")
        return 0

    for rec in analysis_resp.data:
        startup_id = rec.get("startup_id")
        analysis_json = rec.get("analysis_json") or {}

        if not startup_id or not analysis_json:
            continue

        # Fetch startup name
        s_resp = supabase.table("startups").select("startup_name, website, founder_name, founder_linkedin_url").eq("id", startup_id).execute()
        if not s_resp.data:
            continue
        startup = s_resp.data[0]

        founders = analysis_json.get("founders", [])
        primary_founder = founders[0] if founders else {}
        website = analysis_json.get("startup_website", "") or startup.get("website", "")
        headquarters = analysis_json.get("headquarters", "")
        founded_year = analysis_json.get("founded_year")

        record = {
            "startup_id": startup_id,
            "startup_name": startup["startup_name"],
            "brand_name": startup["startup_name"].strip().lower(),
            "website": website,
            "primary_founder_name": primary_founder.get("name", startup.get("founder_name", "")),
            "primary_founder_linkedin": primary_founder.get("linkedin_url", startup.get("founder_linkedin_url", "")),
            "primary_founder_title": primary_founder.get("role", "Founder"),
            "leadership": founders,
            "headquarters": headquarters,
            "founded_year": int(founded_year) if founded_year and str(founded_year).isdigit() else None,
            "founded_year_confidence": 0.70 if founded_year else 0.0,
            "identity_confidence": 0.80,
            "source": "startup_analysis",
            "evidence_count": 2,
            "last_verified": get_now_iso(),
            "verification_notes": "Seeded from AI startup_analysis JSON.",
        }

        if upsert_identity_record(record, dry_run, verbose):
            count += 1

    print(f"  → Seeded {count} records from startup_analysis.")
    return count


def seed_from_startups_table(dry_run: bool, verbose: bool) -> int:
    """
    Priority 3: Seeds from existing startups table records.
    Confidence: 0.70 — direct DB data, may be incomplete.
    """
    print("\n🗄️  [Priority 3] Seeding from startups table...")
    count = 0

    startups_resp = supabase.table("startups").select("*").execute()
    if not startups_resp.data:
        print("  → No startups found.")
        return 0

    for startup in startups_resp.data:
        startup_id = startup.get("id")
        if not startup_id:
            continue

        record = {
            "startup_id": startup_id,
            "startup_name": startup.get("startup_name", ""),
            "brand_name": startup.get("startup_name", "").strip().lower(),
            "website": startup.get("website", ""),
            "primary_founder_name": startup.get("founder_name", ""),
            "primary_founder_linkedin": startup.get("founder_linkedin_url", ""),
            "primary_founder_title": "Founder",
            "headquarters": startup.get("headquarters", ""),
            "city": startup.get("city", ""),
            "country": startup.get("country", "India"),
            "founded_year": startup.get("founded_year"),
            "founded_year_confidence": 0.75 if startup.get("founded_year") else 0.0,
            "identity_confidence": 0.70,
            "source": "existing_database",
            "evidence_count": 1,
            "last_verified": get_now_iso(),
            "verification_notes": "Seeded from startups table.",
        }

        if upsert_identity_record(record, dry_run, verbose):
            count += 1

    print(f"  → Seeded {count} records from startups table.")
    return count


def seed_from_known_domain_registry(dry_run: bool, verbose: bool) -> int:
    """
    Priority 4: Seeds website from KNOWN_DOMAINS registry.
    Only enriches existing identity records with missing websites.
    """
    print("\n🌐 [Priority 4] Enriching from KNOWN_DOMAINS registry...")
    count = 0

    identity_resp = supabase.table("startups").select("id, startup_name, website, identity_confidence").execute()
    if not identity_resp.data:
        print("  → No identity records to enrich.")
        return 0

    for rec in identity_resp.data:
        if rec.get("website"):
            continue  # Already has a website

        name_lower = rec.get("startup_name", "").strip().lower()
        for key, url in KNOWN_DOMAINS.items():
            if key == name_lower or key in name_lower:
                if not dry_run:
                    supabase.table("startups").update({
                        "website": url,
                        "identity_confidence": max(rec.get("identity_confidence", 0.70) or 0.70, 0.88),
                        "source": "known_domain_registry",
                        "updated_at": get_now_iso(),
                    }).eq("id", rec["id"]).execute()
                log(f"  🌐 Enriched website for: {rec['startup_name']} → {url}", verbose)
                count += 1
                break

    print(f"  → Enriched {count} records with known domain websites.")
    return count


def seed_from_known_founders(dry_run: bool, verbose: bool) -> int:
    """
    Priority 5: Seeds founder data from KNOWN_FOUNDERS registry.
    Only enriches existing identity records with missing founders.
    """
    print("\n👥 [Priority 5] Enriching from KNOWN_FOUNDERS registry...")
    count = 0

    identity_resp = supabase.table("startups").select("id, startup_name, primary_founder_name, founder_name").execute()
    if not identity_resp.data:
        print("  → No identity records to enrich.")
        return 0

    for rec in identity_resp.data:
        if rec.get("primary_founder_name") or rec.get("founder_name"):
            continue  # Already has a founder

        name_lower = rec.get("startup_name", "").strip().lower()
        for key, founders in KNOWN_FOUNDERS.items():
            if key == name_lower or key in name_lower:
                primary = founders[0]
                if not dry_run:
                    supabase.table("startups").update({
                        "primary_founder_name": primary.get("name", ""),
                        "founder_name": primary.get("name", ""),
                        "primary_founder_linkedin": primary.get("linkedin_url", ""),
                        "founder_linkedin_url": primary.get("linkedin_url", ""),
                        "primary_founder_title": primary.get("role", "Founder"),
                        "leadership": founders,
                        "updated_at": get_now_iso(),
                    }).eq("id", rec["id"]).execute()
                log(f"  👥 Enriched founder for: {rec['startup_name']} → {primary.get('name')}", verbose)
                count += 1
                break

    print(f"  → Enriched {count} records with known founders.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Seed the startup identity registry.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes.")
    parser.add_argument("--force", action="store_true", help="Re-seed even if records exist.")
    parser.add_argument("--verbose", action="store_true", help="Verbose per-record output.")
    args = parser.parse_args()

    dry_run = args.dry_run
    verbose = args.verbose

    print("=" * 60)
    print("🚀 STARTUP IDENTITY REGISTRY SEEDER")
    print(f"   Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE'}")
    print("=" * 60)

    total = 0

    # Run all seed phases in priority order
    total += seed_from_canonical_overloads(dry_run, verbose)
    total += seed_from_startup_analysis(dry_run, verbose)
    total += seed_from_startups_table(dry_run, verbose)
    total += seed_from_known_domain_registry(dry_run, verbose)
    total += seed_from_known_founders(dry_run, verbose)

    print("\n" + "=" * 60)
    print(f"✅ SEEDING COMPLETE: {total} total records processed.")
    if dry_run:
        print("   (DRY RUN — no actual DB changes were made)")
    print("=" * 60)


if __name__ == "__main__":
    main()
