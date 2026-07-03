-- =============================================================================
-- Migration: 007_company_intelligence_jsonb.sql
-- Description: Adds company_intelligence JSONB and related metadata columns
--              to startups table. Adds source payload columns to startup_news.
--              Part of: feature/modular-company-intelligence-refactor
-- 
-- IMPORTANT: DO NOT AUTO-APPLY. Review and execute manually in Supabase SQL editor.
-- This migration is NON-DESTRUCTIVE — all ADD COLUMN IF NOT EXISTS.
-- Existing data is not modified.
--
-- Dual-write strategy:
--   - analysis_json (startup_analysis table) remains intact for backward compat
--   - company_intelligence (startups table) is the new canonical target
-- =============================================================================

-- -----------------------------------------------------------------------------
-- SECTION 1: startups table — Add Company Intelligence JSONB columns
-- -----------------------------------------------------------------------------

-- Primary canonical intelligence store (maps directly to frontend CI tab sections)
ALTER TABLE startups 
  ADD COLUMN IF NOT EXISTS company_intelligence JSONB DEFAULT '{}' NOT NULL;

-- Resolution and identity validation metadata
ALTER TABLE startups 
  ADD COLUMN IF NOT EXISTS validation_metadata JSONB DEFAULT '{}' NOT NULL;

-- Enrichment lifecycle metadata (timestamps, versions, section completion status)
ALTER TABLE startups 
  ADD COLUMN IF NOT EXISTS enrichment_metadata JSONB DEFAULT '{}' NOT NULL;

-- Known aliases and brand name variants
ALTER TABLE startups 
  ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]' NOT NULL;

-- -----------------------------------------------------------------------------
-- SECTION 2: startup_news table — Add Source Payload columns
-- -----------------------------------------------------------------------------

-- Structured startup name mentions extracted from article by AI Layer 1
ALTER TABLE startup_news
  ADD COLUMN IF NOT EXISTS startup_mentions JSONB DEFAULT '{}';

-- Raw HTML/text source collection payload (homepage, about, linkedin, snippets)
ALTER TABLE startup_news
  ADD COLUMN IF NOT EXISTS raw_source_payload JSONB DEFAULT '{}';

-- Cleaned and segmented content payload ready for AI enrichment
ALTER TABLE startup_news
  ADD COLUMN IF NOT EXISTS cleaned_source_payload JSONB DEFAULT '{}';

-- Website + LinkedIn resolution metadata and confidence scores
ALTER TABLE startup_news
  ADD COLUMN IF NOT EXISTS resolution_metadata JSONB DEFAULT '{}';

-- Pipeline processing state (stage, errors, retry counts, timestamps)
ALTER TABLE startup_news
  ADD COLUMN IF NOT EXISTS pipeline_status JSONB DEFAULT '{}';

-- -----------------------------------------------------------------------------
-- SECTION 3: Indexes for JSONB query performance
-- -----------------------------------------------------------------------------

-- GIN index on company_intelligence for fast key-path queries
CREATE INDEX IF NOT EXISTS idx_startups_company_intelligence 
  ON startups USING GIN (company_intelligence);

-- GIN index on enrichment_metadata for section completion queries
CREATE INDEX IF NOT EXISTS idx_startups_enrichment_metadata 
  ON startups USING GIN (enrichment_metadata);

-- GIN index on validation_metadata for resolution status queries
CREATE INDEX IF NOT EXISTS idx_startups_validation_metadata 
  ON startups USING GIN (validation_metadata);

-- GIN index on pipeline_status for monitoring/observability queries
CREATE INDEX IF NOT EXISTS idx_startup_news_pipeline_status 
  ON startup_news USING GIN (pipeline_status);

-- -----------------------------------------------------------------------------
-- SECTION 4: Comments for schema documentation
-- -----------------------------------------------------------------------------

COMMENT ON COLUMN startups.company_intelligence IS 
  'Canonical Company Intelligence JSONB. Structure: {basic_information, business_profile, founders_details, products_services, funding_details, competitors, digital_presence, validation_metadata, source_metadata}. Written by modular enrichment engine. Maps directly to frontend Company Intelligence tab.';

COMMENT ON COLUMN startups.validation_metadata IS 
  'Identity resolution validation results. Structure: {resolution_confidence, verification_status, last_resolved_at, resolution_source, mismatch_reason}.';

COMMENT ON COLUMN startups.enrichment_metadata IS 
  'Enrichment lifecycle tracking. Structure: {enrichment_version, last_enriched_at, sections_completed, section_timestamps, ai_calls_used, model_used, fallback_used}.';

COMMENT ON COLUMN startups.aliases IS 
  'Known alternative names and brand variants for this startup. Array of strings.';

COMMENT ON COLUMN startup_news.startup_mentions IS 
  'AI Layer 1 output: structured startup name extractions from the news article. Structure: [{startup_name, article_context, source_description}].';

COMMENT ON COLUMN startup_news.raw_source_payload IS 
  'Raw HTML/text collected from startup web sources. Structure: {homepage_html, about_page_html, products_page_html, team_page_html, linkedin_pages, search_snippets}.';

COMMENT ON COLUMN startup_news.cleaned_source_payload IS 
  'Cleaned and segmented content ready for AI enrichment. Structure: {homepage, about_page, products_services, founders_team, funding_investors, contact_us, social_presence, seo_metadata}.';

COMMENT ON COLUMN startup_news.resolution_metadata IS 
  'Website and LinkedIn resolution outcome. Structure: {canonical_startup_name, aliases, website_url, linkedin_url, confidence_scores, resolution_method}.';

COMMENT ON COLUMN startup_news.pipeline_status IS 
  'Pipeline processing state tracker. Structure: {stage, completed_stages, errors, retry_counts, started_at, completed_at}.';

-- -----------------------------------------------------------------------------
-- SECTION 5: Seed empty company_intelligence for existing rows (safe defaults)
-- NOTE: This does NOT overwrite any existing data.
-- Only updates rows where company_intelligence is still empty '{}'.
-- -----------------------------------------------------------------------------

-- Update existing rows to have the canonical schema structure as an empty scaffold
-- This allows frontend to detect schema version without needing a full re-enrichment.
UPDATE startups
SET company_intelligence = jsonb_build_object(
  'basic_information', '{}'::jsonb,
  'business_profile', '{}'::jsonb,
  'founders_details', '[]'::jsonb,
  'products_services', '[]'::jsonb,
  'funding_details', '{}'::jsonb,
  'competitors', '[]'::jsonb,
  'digital_presence', '{}'::jsonb,
  'validation_metadata', '{}'::jsonb,
  'source_metadata', jsonb_build_object(
    'schema_version', '1.0',
    'migration_applied_at', NOW()::text,
    'enrichment_sections_completed', '[]'::jsonb
  )
),
enrichment_metadata = jsonb_build_object(
  'enrichment_version', '3.0',
  'schema_migrated_at', NOW()::text,
  'sections_completed', '[]'::jsonb,
  'last_enriched_at', NULL
)
WHERE company_intelligence = '{}';

-- =============================================================================
-- END OF MIGRATION 007
-- Apply via Supabase SQL Editor or psql after manual review.
-- Rollback script: see database/migrations/rollback_007_company_intelligence.sql
-- =============================================================================
