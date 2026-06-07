-- Database Migration: Upgrade Workspace Schemas
-- Run this in your Supabase SQL Editor:

-- 1. Update startups table
ALTER TABLE startups 
  ADD COLUMN IF NOT EXISTS startup_status TEXT,
  ADD COLUMN IF NOT EXISTS headquarters TEXT,
  ADD COLUMN IF NOT EXISTS startup_stage TEXT;

-- 2. Update startup_analysis table
ALTER TABLE startup_analysis 
  ADD COLUMN IF NOT EXISTS relevance_score INT,
  ADD COLUMN IF NOT EXISTS signal_score INT,
  ADD COLUMN IF NOT EXISTS deployability_score INT,
  ADD COLUMN IF NOT EXISTS recommendation_score INT,
  ADD COLUMN IF NOT EXISTS confidence_score INT,
  ADD COLUMN IF NOT EXISTS recommended_action TEXT,
  ADD COLUMN IF NOT EXISTS priority_band TEXT,
  ADD COLUMN IF NOT EXISTS matched_entities JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS matched_business_teams JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS matched_business_problems JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS positive_signals JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS negative_signals JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS audit_summary JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS knowledge_version TEXT,
  ADD COLUMN IF NOT EXISTS analysis_version TEXT;

-- 3. Update startup_assignments table
ALTER TABLE startup_assignments 
  ADD COLUMN IF NOT EXISTS business_team TEXT,
  ADD COLUMN IF NOT EXISTS engagement_stage TEXT DEFAULT 'New',
  ADD COLUMN IF NOT EXISTS assignment_score INT,
  ADD COLUMN IF NOT EXISTS assignment_band TEXT,
  ADD COLUMN IF NOT EXISTS assignment_score_manual_override INT,
  ADD COLUMN IF NOT EXISTS assignment_score_override_reason TEXT,
  ADD COLUMN IF NOT EXISTS last_followup_date TIMESTAMP;

-- 4. Update startup_activity_logs table
ALTER TABLE startup_activity_logs 
  ADD COLUMN IF NOT EXISTS activity_source TEXT,
  ADD COLUMN IF NOT EXISTS activity_json JSONB DEFAULT '{}'::jsonb;
