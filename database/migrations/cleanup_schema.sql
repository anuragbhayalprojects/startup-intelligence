-- Database Migration: Schema Cleanup & Optimization
-- Run this in your Supabase SQL Editor.

-- 1. Drop redundant/unused columns from startups table
ALTER TABLE public.startups
  DROP COLUMN IF EXISTS hq_city,
  DROP COLUMN IF EXISTS hq_country,
  DROP COLUMN IF EXISTS startup_status,
  DROP COLUMN IF EXISTS startup_stage,
  DROP COLUMN IF EXISTS company_profile,
  DROP COLUMN IF EXISTS products_services,
  DROP COLUMN IF EXISTS dedup_hash;

-- 2. Drop legacy/redundant columns from startup_analysis table
ALTER TABLE public.startup_analysis
  DROP COLUMN IF EXISTS bfsi_relevance_score,
  DROP COLUMN IF EXISTS enterprise_readiness_score,
  DROP COLUMN IF EXISTS strategic_fit_score,
  DROP COLUMN IF EXISTS integration_feasibility_score;
