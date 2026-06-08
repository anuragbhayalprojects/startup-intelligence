-- Rollback for Database Migration v6
-- Run this to undo v6 changes

-- Drop indexes first
DROP INDEX IF EXISTS startup_identity_startup_id_idx;
DROP INDEX IF EXISTS startup_identity_name_idx;
DROP INDEX IF EXISTS startup_identity_brand_name_idx;
DROP INDEX IF EXISTS startup_identity_website_idx;
DROP INDEX IF EXISTS startup_identity_linkedin_idx;
DROP INDEX IF EXISTS startup_news_startup_id_idx;
DROP INDEX IF EXISTS startup_news_published_at_idx;

-- Drop new tables
DROP TABLE IF EXISTS startup_identity CASCADE;
DROP TABLE IF EXISTS startup_news CASCADE;

-- Remove v6 columns from startup_analysis
ALTER TABLE startup_analysis
  DROP COLUMN IF EXISTS funding_rounds,
  DROP COLUMN IF EXISTS total_funding,
  DROP COLUMN IF EXISTS latest_round_stage,
  DROP COLUMN IF EXISTS latest_round_date,
  DROP COLUMN IF EXISTS last_funding_enriched_at;

-- Remove v6 columns from startups
ALTER TABLE startups
  DROP COLUMN IF EXISTS priority_score,
  DROP COLUMN IF EXISTS priority_band,
  DROP COLUMN IF EXISTS recommended_action,
  DROP COLUMN IF EXISTS ai_summary,
  DROP COLUMN IF EXISTS relevance_score,
  DROP COLUMN IF EXISTS signal_score,
  DROP COLUMN IF EXISTS deployability_score,
  DROP COLUMN IF EXISTS confidence_score,
  DROP COLUMN IF EXISTS recommendation_score,
  DROP COLUMN IF EXISTS matched_entities,
  DROP COLUMN IF EXISTS matched_business_teams,
  DROP COLUMN IF EXISTS market_intelligence,
  DROP COLUMN IF EXISTS total_funding,
  DROP COLUMN IF EXISTS latest_round_stage,
  DROP COLUMN IF EXISTS assigned_team,
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS entity_relevance,
  DROP COLUMN IF EXISTS recent_news;
