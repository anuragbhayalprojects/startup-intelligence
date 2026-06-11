-- Migration: Rename ai_summary to relevance_summary in startups table
ALTER TABLE public.startups RENAME COLUMN ai_summary TO relevance_summary;
