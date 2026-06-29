-- 20260629_can_report_issues.sql
-- Adds can_report_issues flag to profiles table
-- Run in Supabase Studio SQL Editor

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS can_report_issues BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_profiles_can_report_issues ON profiles (can_report_issues) WHERE can_report_issues = TRUE;
