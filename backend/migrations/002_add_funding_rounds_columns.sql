-- Migration: Add funding rounds columns to startup_analysis
-- Run this in the Supabase SQL Editor before deploying backend changes.
-- These columns store the rich per-round funding data extracted by Pass 3.

ALTER TABLE startup_analysis
  ADD COLUMN IF NOT EXISTS funding_rounds           jsonb        DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS total_funding            text,
  ADD COLUMN IF NOT EXISTS latest_round_stage       text,
  ADD COLUMN IF NOT EXISTS latest_round_date        text,
  ADD COLUMN IF NOT EXISTS last_funding_enriched_at timestamptz;

-- Index to quickly find startups with stale or missing funding data
CREATE INDEX IF NOT EXISTS idx_startup_analysis_funding_enriched
  ON startup_analysis(last_funding_enriched_at NULLS FIRST);

COMMENT ON COLUMN startup_analysis.funding_rounds IS
  'JSONB array of funding rounds. Each element: {stage, amount, date, lead_investor, co_investors[]}';
COMMENT ON COLUMN startup_analysis.total_funding IS
  'Aggregated total funding raised across all known rounds, e.g. "$42M"';
COMMENT ON COLUMN startup_analysis.latest_round_stage IS
  'Stage of the most recent funding round, e.g. "Series C"';
COMMENT ON COLUMN startup_analysis.latest_round_date IS
  'Date of the most recent funding round, e.g. "Mar 2024"';
COMMENT ON COLUMN startup_analysis.last_funding_enriched_at IS
  'Timestamp of the last Pass 3 funding enrichment run. Used for 60-day staleness check.';
