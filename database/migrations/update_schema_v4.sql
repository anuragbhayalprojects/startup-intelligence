-- Database Migration: Add Founder columns to startups and set triggers for startup_assignments
-- Run these statements in your Supabase SQL Editor:

-- 1. Add Founder Name and Founder LinkedIn URL columns to the startups table
ALTER TABLE startups ADD COLUMN IF NOT EXISTS founder_name TEXT;
ALTER TABLE startups ADD COLUMN IF NOT EXISTS founder_linkedin_url TEXT;

-- 2. Create trigger to autofill startup_name in startup_assignments
CREATE OR REPLACE FUNCTION autofill_startup_name()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.startup_name IS NULL OR NEW.startup_name = '' THEN
        SELECT startup_name INTO NEW.startup_name FROM startups WHERE id = NEW.startup_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_autofill_startup_name ON startup_assignments;
CREATE TRIGGER trg_autofill_startup_name
BEFORE INSERT OR UPDATE ON startup_assignments
FOR EACH ROW
EXECUTE FUNCTION autofill_startup_name();

-- 3. Create trigger to dynamically set assignment_status in startup_assignments based on owner assignment
CREATE OR REPLACE FUNCTION set_assignment_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.assigned_to_fpr1 IS NOT NULL AND NEW.assigned_to_fpr1 <> '' THEN
        IF NEW.assignment_status IS NULL OR NEW.assignment_status = 'pending' OR NEW.assignment_status = 'Pending' THEN
            NEW.assignment_status := 'Assigned to ' || NEW.assigned_to_fpr1;
        END IF;
    ELSE
        IF NEW.assignment_status IS NULL THEN
            NEW.assignment_status := 'pending';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_assignment_status ON startup_assignments;
CREATE TRIGGER trg_set_assignment_status
BEFORE INSERT OR UPDATE ON startup_assignments
FOR EACH ROW
EXECUTE FUNCTION set_assignment_status();
