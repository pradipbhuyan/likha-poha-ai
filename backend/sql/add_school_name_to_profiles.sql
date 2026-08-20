-- Add school_name column to profiles table
-- Run this in Supabase SQL Editor
--
-- Several backend routes already read/write profiles.school_name —
-- POST /api/auth/teacher-signup, POST /api/auth/oauth/complete-profile
-- (teacher role), GET /api/admin/support/pending-teachers, and
-- admin_onboarding.py's teacher creation — but no migration ever added the
-- column to the profiles table (add_teacher_dashboard.sql only added
-- school_name to the separate teacher_profiles table). Every one of those
-- code paths has been failing with PGRST204 "Could not find the
-- 'school_name' column of 'profiles' in the schema cache" in production.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS school_name TEXT;

-- PostgREST caches the schema; Supabase usually reloads it automatically on
-- DDL, but if requests still 404/PGRST204 on this column afterward, force it:
NOTIFY pgrst, 'reload schema';
