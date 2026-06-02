-- Database Migration: Add Master Taxonomy Columns to startups Table
-- Run these statements in your Supabase SQL Editor:

ALTER TABLE startups ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE startups ADD COLUMN IF NOT EXISTS business_models JSONB DEFAULT '[]'::jsonb;
ALTER TABLE startups ADD COLUMN IF NOT EXISTS industry_relevance JSONB DEFAULT '[]'::jsonb;
ALTER TABLE startups ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
