-- Database Migration v8: Unify startup identity registry into startups table
-- Run this in your Supabase SQL Editor.

-- =============================================================================
-- 1. Add missing identity registry columns to startups table
-- =============================================================================
ALTER TABLE startups
  ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS linkedin_company_url TEXT,
  ADD COLUMN IF NOT EXISTS linkedin_company_id TEXT,
  ADD COLUMN IF NOT EXISTS twitter_url TEXT,
  ADD COLUMN IF NOT EXISTS crunchbase_url TEXT,
  ADD COLUMN IF NOT EXISTS primary_founder_name TEXT,
  ADD COLUMN IF NOT EXISTS primary_founder_linkedin TEXT,
  ADD COLUMN IF NOT EXISTS primary_founder_title TEXT,
  ADD COLUMN IF NOT EXISTS leadership JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS founded_year_confidence FLOAT DEFAULT 0.0,
  ADD COLUMN IF NOT EXISTS evidence_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_verified TIMESTAMP DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS verification_notes TEXT;

-- =============================================================================
-- 2. Migrate existing data from startup_identity to startups table
-- =============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'startup_identity') THEN
    UPDATE startups s
    SET
      aliases = COALESCE(s.aliases, si.aliases),
      brand_name = COALESCE(s.brand_name, si.brand_name),
      legal_name = COALESCE(s.legal_name, si.legal_name),
      website = COALESCE(s.website, si.website),
      linkedin_url = COALESCE(s.linkedin_url, si.linkedin_company_url),
      linkedin_company_url = COALESCE(s.linkedin_company_url, si.linkedin_company_url),
      linkedin_company_id = COALESCE(s.linkedin_company_id, si.linkedin_company_id),
      twitter_url = COALESCE(s.twitter_url, si.twitter_url),
      crunchbase_url = COALESCE(s.crunchbase_url, si.crunchbase_url),
      founder_name = COALESCE(s.founder_name, si.primary_founder_name),
      primary_founder_name = COALESCE(s.primary_founder_name, si.primary_founder_name),
      founder_linkedin_url = COALESCE(s.founder_linkedin_url, si.primary_founder_linkedin),
      primary_founder_linkedin = COALESCE(s.primary_founder_linkedin, si.primary_founder_linkedin),
      primary_founder_title = COALESCE(s.primary_founder_title, si.primary_founder_title),
      leadership = COALESCE(s.leadership, si.leadership),
      headquarters = COALESCE(s.headquarters, si.headquarters),
      city = COALESCE(s.city, si.city),
      country = COALESCE(s.country, si.country),
      founded_year = COALESCE(s.founded_year, si.founded_year),
      founded_year_confidence = COALESCE(s.founded_year_confidence, si.founded_year_confidence),
      identity_confidence = COALESCE(s.identity_confidence, si.identity_confidence),
      source = COALESCE(s.source, si.source),
      evidence_count = COALESCE(s.evidence_count, si.evidence_count),
      last_verified = COALESCE(s.last_verified, si.last_verified),
      verification_notes = COALESCE(s.verification_notes, si.verification_notes)
    FROM startup_identity si
    WHERE s.id = si.startup_id;

    -- Drop the startup_identity table as it is now obsolete
    DROP TABLE IF EXISTS startup_identity CASCADE;
  END IF;
END $$;

-- =============================================================================
-- 3. Create indexes on startups table for fast lookup of new columns
-- =============================================================================
CREATE INDEX IF NOT EXISTS startups_brand_name_idx ON startups(brand_name);
CREATE INDEX IF NOT EXISTS startups_website_idx ON startups(website);
CREATE INDEX IF NOT EXISTS startups_linkedin_company_url_idx ON startups(linkedin_company_url);
CREATE INDEX IF NOT EXISTS startups_linkedin_url_idx ON startups(linkedin_url);
