-- Database Migration Rollback v7
-- Run this in your Supabase SQL Editor if you need to rollback v7 schema changes.

ALTER TABLE startups
  DROP COLUMN IF EXISTS brand_name,
  DROP COLUMN IF EXISTS legal_name,
  DROP COLUMN IF EXISTS company_profile,
  DROP COLUMN IF EXISTS products_services,
  DROP COLUMN IF EXISTS identity_confidence,
  DROP COLUMN IF EXISTS startup_stage,
  DROP COLUMN IF EXISTS headquarters,
  DROP COLUMN IF EXISTS hq_city,
  DROP COLUMN IF EXISTS hq_country;

DROP INDEX IF EXISTS startups_brand_name_idx;
