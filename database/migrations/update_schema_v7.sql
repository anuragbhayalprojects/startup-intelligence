-- Database Migration v7: Update startups table with brand_name, legal_name, company_profile, products_services, identity_confidence, headquarters, and stage columns.
-- Run this in your Supabase SQL Editor.

ALTER TABLE startups
  ADD COLUMN IF NOT EXISTS brand_name TEXT,
  ADD COLUMN IF NOT EXISTS legal_name TEXT,
  ADD COLUMN IF NOT EXISTS company_profile TEXT,
  ADD COLUMN IF NOT EXISTS products_services TEXT,
  ADD COLUMN IF NOT EXISTS identity_confidence FLOAT DEFAULT 0.0,
  ADD COLUMN IF NOT EXISTS startup_stage TEXT,
  ADD COLUMN IF NOT EXISTS headquarters TEXT,
  ADD COLUMN IF NOT EXISTS hq_city TEXT,
  ADD COLUMN IF NOT EXISTS hq_country TEXT;

-- Create index for brand_name fast lookup
CREATE INDEX IF NOT EXISTS startups_brand_name_idx ON startups(brand_name);
