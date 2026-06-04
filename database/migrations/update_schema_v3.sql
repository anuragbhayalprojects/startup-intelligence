-- Database Migration: Update startup_assignments table schema and cascade constraints
-- Run these statements in your Supabase SQL Editor:

-- 1. Rename assigned_to to assigned_to_fpr1
ALTER TABLE startup_assignments RENAME COLUMN assigned_to TO assigned_to_fpr1;

-- 2. Add assigned_to_fpr2 column
ALTER TABLE startup_assignments ADD COLUMN IF NOT EXISTS assigned_to_fpr2 TEXT;

-- 3. Add startup_name column
ALTER TABLE startup_assignments ADD COLUMN IF NOT EXISTS startup_name TEXT;

-- 4. Add linkedin_reachout_message column
ALTER TABLE startup_assignments ADD COLUMN IF NOT EXISTS linkedin_reachout_message TEXT;

-- 5. Add email_reachout_message column
ALTER TABLE startup_assignments ADD COLUMN IF NOT EXISTS email_reachout_message TEXT;

-- 6. Update icici_entity to 'ICICI Bank' for all existing rows and make it default to 'ICICI Bank'
ALTER TABLE startup_assignments ALTER COLUMN icici_entity SET DEFAULT 'ICICI Bank';
UPDATE startup_assignments SET icici_entity = 'ICICI Bank';

-- 7. Recreate foreign key constraints with ON DELETE CASCADE to enable clean database deduplication
ALTER TABLE startup_analysis DROP CONSTRAINT IF EXISTS startup_analysis_startup_id_fkey;
ALTER TABLE startup_analysis ADD CONSTRAINT startup_analysis_startup_id_fkey 
    FOREIGN KEY (startup_id) REFERENCES startups(id) ON DELETE CASCADE;

ALTER TABLE startup_assignments DROP CONSTRAINT IF EXISTS startup_assignments_startup_id_fkey;
ALTER TABLE startup_assignments ADD CONSTRAINT startup_assignments_startup_id_fkey 
    FOREIGN KEY (startup_id) REFERENCES startups(id) ON DELETE CASCADE;

ALTER TABLE startup_activity_logs DROP CONSTRAINT IF EXISTS startup_activity_logs_startup_id_fkey;
ALTER TABLE startup_activity_logs ADD CONSTRAINT startup_activity_logs_startup_id_fkey 
    FOREIGN KEY (startup_id) REFERENCES startups(id) ON DELETE CASCADE;
