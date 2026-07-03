-- =============================================================================
-- Rollback: rollback_007_company_intelligence.sql
-- Reverses migration 007_company_intelligence_jsonb.sql
-- IMPORTANT: Only run if migration needs to be rolled back. Will DROP columns.
-- =============================================================================

-- Drop indexes first
DROP INDEX IF EXISTS idx_startups_company_intelligence;
DROP INDEX IF EXISTS idx_startups_enrichment_metadata;
DROP INDEX IF EXISTS idx_startups_validation_metadata;
DROP INDEX IF EXISTS idx_startup_news_pipeline_status;

-- Drop startups columns
ALTER TABLE startups DROP COLUMN IF EXISTS company_intelligence;
ALTER TABLE startups DROP COLUMN IF EXISTS validation_metadata;
ALTER TABLE startups DROP COLUMN IF EXISTS enrichment_metadata;
ALTER TABLE startups DROP COLUMN IF EXISTS aliases;

-- Drop startup_news columns
ALTER TABLE startup_news DROP COLUMN IF EXISTS startup_mentions;
ALTER TABLE startup_news DROP COLUMN IF EXISTS raw_source_payload;
ALTER TABLE startup_news DROP COLUMN IF EXISTS cleaned_source_payload;
ALTER TABLE startup_news DROP COLUMN IF EXISTS resolution_metadata;
ALTER TABLE startup_news DROP COLUMN IF EXISTS pipeline_status;
