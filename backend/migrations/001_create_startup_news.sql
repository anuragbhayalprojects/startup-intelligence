-- Migration: Create startup_news table
-- Run this in the Supabase SQL Editor to create the news history table.
-- Each row represents a single news article event mentioning a startup.

CREATE TABLE IF NOT EXISTS startup_news (
  id           bigserial PRIMARY KEY,
  startup_id   bigint NOT NULL REFERENCES startups(id) ON DELETE CASCADE,
  headline     text NOT NULL DEFAULT '',
  summary      text,           -- AI-generated, startup-specific 2-3 sentence summary
  source       text DEFAULT '',
  source_url   text DEFAULT '',
  published_at timestamptz NOT NULL DEFAULT now(),
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Index for fast per-startup lookups ordered by most recent
CREATE INDEX IF NOT EXISTS idx_startup_news_startup_id_published
  ON startup_news(startup_id, published_at DESC);

-- Optional: Row Level Security (allow read for authenticated users)
ALTER TABLE startup_news ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read for authenticated users"
  ON startup_news FOR SELECT
  USING (auth.role() = 'authenticated');
CREATE POLICY "Allow insert for authenticated users"
  ON startup_news FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');
