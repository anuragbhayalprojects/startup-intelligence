-- Migration: 009_create_news_articles.sql
-- Description: Creates canonical news_articles table for global news feed

CREATE TABLE IF NOT EXISTS news_articles (
    id            bigserial PRIMARY KEY,
    headline      text NOT NULL,
    summary       text,
    content       text,
    source        text NOT NULL DEFAULT '',
    source_url    text UNIQUE NOT NULL,
    published_at  timestamp with time zone,
    category      text NOT NULL,
    similar_sources JSONB DEFAULT '[]'::jsonb,
    startups_mentioned JSONB DEFAULT '[]'::jsonb,
    created_at    timestamp with time zone NOT NULL DEFAULT now()
);

-- GIN and standard indexes for performant querying and filtering
CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_articles_startups ON news_articles USING GIN (startups_mentioned);

-- Row Level Security (RLS) policies - Permissive for both anon and authenticated clients
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read" ON news_articles;
CREATE POLICY "Allow public read" ON news_articles FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public insert" ON news_articles;
CREATE POLICY "Allow public insert" ON news_articles FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow public update" ON news_articles;
CREATE POLICY "Allow public update" ON news_articles FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Allow public delete" ON news_articles;
CREATE POLICY "Allow public delete" ON news_articles FOR DELETE USING (true);
