-- ─────────────────────────────────────────────────────────────────────────────
-- subscription_plan_feature_flags migration
-- Adds DB-driven fields to subscription_plan_settings so the admin panel
-- can control:
--   1. duration_days     — exact expiry days (replaces billing_label→days lookup)
--   2. access_exam_prep  — whether this plan includes Exam Prep Center
--   3. access_exemplar   — whether this plan includes Exemplar access
--
-- Run in Supabase SQL Editor (safe to re-run).
-- ─────────────────────────────────────────────────────────────────────────────

-- Add duration_days if not present
ALTER TABLE subscription_plan_settings
  ADD COLUMN IF NOT EXISTS duration_days integer DEFAULT NULL;

-- Add feature flags if not present
ALTER TABLE subscription_plan_settings
  ADD COLUMN IF NOT EXISTS access_exam_prep boolean NOT NULL DEFAULT false;

ALTER TABLE subscription_plan_settings
  ADD COLUMN IF NOT EXISTS access_exemplar boolean NOT NULL DEFAULT true;

-- Seed duration_days from known billing_label values for existing rows
UPDATE subscription_plan_settings SET duration_days = 8    WHERE key = 'free'             AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 30   WHERE key = 'starter'          AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 30   WHERE key = 'premium'          AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 30   WHERE key = 'family_premium'   AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 184  WHERE key = 'standard_6month'  AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 366  WHERE key = 'standard_annual'  AND duration_days IS NULL;
UPDATE subscription_plan_settings SET duration_days = 366  WHERE key = 'family_annual'    AND duration_days IS NULL;

-- Seed access_exam_prep for paid plans (free tier stays false)
UPDATE subscription_plan_settings SET access_exam_prep = true
  WHERE key IN ('starter','premium','family_premium','standard_6month','standard_annual','family_annual','free');

-- free_tier stays access_exam_prep = false (default)

COMMENT ON COLUMN subscription_plan_settings.duration_days IS
  'Exact subscription validity in days. Overrides billing_label→days lookup if set.';
COMMENT ON COLUMN subscription_plan_settings.access_exam_prep IS
  'Whether this plan includes access to the Exam Prep Center (JEE/NEET/CUET).';
COMMENT ON COLUMN subscription_plan_settings.access_exemplar IS
  'Whether this plan includes access to Exemplar Research and Lessons.';
