-- Database Migration v6: Startup Identity Registry + Funding Columns
-- Run this in your Supabase SQL Editor after v5

-- =============================================================================
-- 1. Add funding round columns to startup_analysis (from Pass 3 enrichment)
-- =============================================================================
ALTER TABLE startup_analysis
  ADD COLUMN IF NOT EXISTS funding_rounds JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS total_funding TEXT,
  ADD COLUMN IF NOT EXISTS latest_round_stage TEXT,
  ADD COLUMN IF NOT EXISTS latest_round_date TEXT,
  ADD COLUMN IF NOT EXISTS last_funding_enriched_at TIMESTAMP;

-- =============================================================================
-- 2. Add missing operational columns to startups table
-- =============================================================================
ALTER TABLE startups
  ADD COLUMN IF NOT EXISTS priority_score INT,
  ADD COLUMN IF NOT EXISTS priority_band TEXT,
  ADD COLUMN IF NOT EXISTS recommended_action TEXT,
  ADD COLUMN IF NOT EXISTS ai_summary TEXT,
  ADD COLUMN IF NOT EXISTS relevance_score INT,
  ADD COLUMN IF NOT EXISTS signal_score INT,
  ADD COLUMN IF NOT EXISTS deployability_score INT,
  ADD COLUMN IF NOT EXISTS confidence_score INT,
  ADD COLUMN IF NOT EXISTS recommendation_score INT,
  ADD COLUMN IF NOT EXISTS matched_entities JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS matched_business_teams JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS market_intelligence JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS total_funding TEXT,
  ADD COLUMN IF NOT EXISTS latest_round_stage TEXT,
  ADD COLUMN IF NOT EXISTS assigned_team TEXT,
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Screening',
  ADD COLUMN IF NOT EXISTS entity_relevance TEXT,
  ADD COLUMN IF NOT EXISTS recent_news JSONB DEFAULT '[]'::jsonb;

-- =============================================================================
-- 3. Create startup_identity table (Identity Registry)
-- =============================================================================
CREATE TABLE IF NOT EXISTS startup_identity (
    id BIGSERIAL PRIMARY KEY,
    startup_id BIGINT REFERENCES startups(id) ON DELETE CASCADE,
    startup_name TEXT NOT NULL,
    brand_name TEXT,
    legal_name TEXT,
    aliases JSONB DEFAULT '[]'::jsonb,

    -- Web presence
    website TEXT,
    linkedin_company_url TEXT,
    linkedin_company_id TEXT,
    twitter_url TEXT,
    crunchbase_url TEXT,

    -- Founder/leadership
    primary_founder_name TEXT,
    primary_founder_linkedin TEXT,
    primary_founder_title TEXT,
    leadership JSONB DEFAULT '[]'::jsonb,

    -- Geographic identity
    headquarters TEXT,
    city TEXT,
    country TEXT DEFAULT 'India',

    -- Founded year
    founded_year INT,
    founded_year_confidence FLOAT DEFAULT 0.0,

    -- Identity confidence tracking (Decision 1)
    identity_confidence FLOAT DEFAULT 0.0,
    source TEXT,                        -- canonical_overloads | existing_database | tracxn | ...
    evidence_count INT DEFAULT 0,
    last_verified TIMESTAMP DEFAULT NOW(),
    verification_notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Unique constraint on startup_id (one identity record per startup)
CREATE UNIQUE INDEX IF NOT EXISTS startup_identity_startup_id_idx ON startup_identity(startup_id);

-- Fast lookup by name
CREATE INDEX IF NOT EXISTS startup_identity_name_idx ON startup_identity(startup_name);
CREATE INDEX IF NOT EXISTS startup_identity_brand_name_idx ON startup_identity(brand_name);
CREATE INDEX IF NOT EXISTS startup_identity_website_idx ON startup_identity(website);
CREATE INDEX IF NOT EXISTS startup_identity_linkedin_idx ON startup_identity(linkedin_company_url);

-- =============================================================================
-- 4. Create startup_news table (if not exists) for news history
-- =============================================================================
CREATE TABLE IF NOT EXISTS startup_news (
    id BIGSERIAL PRIMARY KEY,
    startup_id BIGINT REFERENCES startups(id) ON DELETE CASCADE,
    headline TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    source_url TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS startup_news_startup_id_idx ON startup_news(startup_id);
CREATE INDEX IF NOT EXISTS startup_news_published_at_idx ON startup_news(published_at DESC);

-- =============================================================================
-- Verification
-- =============================================================================
SELECT
  'startup_identity' as table_name,
  COUNT(*) as row_count
FROM startup_identity
UNION ALL
SELECT 'startup_news', COUNT(*) FROM startup_news;
