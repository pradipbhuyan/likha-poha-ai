-- ============================================================
-- Migration: Add SAT, IELTS, TOEFL iBT to exam_prep_subscriptions
-- Apply to: Supabase main DB (dpivlbbyzlbpwnwgajso)
--
-- Purpose:
--   exam_prep_subscriptions.exam_type only allowed jee_main, neet_ug, cuet_ug,
--   so students could not purchase the new SAT / IELTS / TOEFL prep packs
--   (backend/app/routes/exam_prep_packs.py, backend/app/data/subscription_plans.py:
--   exam_prep_sat / exam_prep_ielts / exam_prep_toefl). This mirrors migration
--   20260711_exam_prep_add_sat_ielts_toefl.sql, which already extended the
--   exam_prep_questions constraint on the other Supabase project.
--
-- How to apply:
--   1. Open Supabase Dashboard (main project) → SQL Editor
--   2. Paste this entire file
--   3. Click Run
--   4. You should see: Success. No rows returned.
-- ============================================================

-- Drop the old constraint (only allows jee_main / neet_ug / cuet_ug)
ALTER TABLE exam_prep_subscriptions
  DROP CONSTRAINT IF EXISTS exam_prep_subscriptions_exam_type_check;

-- Add new constraint that also accepts sat, ielts, toefl_ibt
ALTER TABLE exam_prep_subscriptions
  ADD CONSTRAINT exam_prep_subscriptions_exam_type_check
  CHECK (exam_type IN ('jee_main', 'neet_ug', 'cuet_ug', 'sat', 'ielts', 'toefl_ibt'));

-- Verify (should return 0 rows if no invalid data exists):
-- SELECT exam_type, COUNT(*) FROM exam_prep_subscriptions
-- WHERE exam_type NOT IN ('jee_main','neet_ug','cuet_ug','sat','ielts','toefl_ibt')
-- GROUP BY exam_type;
