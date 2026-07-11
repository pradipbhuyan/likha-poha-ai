-- ============================================================
-- Migration: Add SAT, IELTS, TOEFL iBT to exam_prep_questions
-- Apply to: Supabase 2 (grade_1112_client)
--   sjfjyzaaypfzyfhhggqw
--
-- Purpose:
--   The exam_type CHECK constraint only allowed jee_main, neet_ug, cuet_ug.
--   This migration extends it to allow sat, ielts, toefl_ibt so admins
--   can import SAT/IELTS/TOEFL practice questions via the Paste & Import
--   panel in Admin → Cache Management → Exam Prep QB.
--
-- How to apply:
--   1. Open Supabase 2 Dashboard → SQL Editor
--   2. Paste this entire file
--   3. Click Run
--   4. You should see: Success. No rows returned.
-- ============================================================

-- Drop the old constraint (only allows jee_main / neet_ug / cuet_ug)
ALTER TABLE exam_prep_questions
  DROP CONSTRAINT IF EXISTS exam_prep_questions_exam_type_check;

-- Add new constraint that also accepts sat, ielts, toefl_ibt
ALTER TABLE exam_prep_questions
  ADD CONSTRAINT exam_prep_questions_exam_type_check
  CHECK (exam_type IN ('jee_main', 'neet_ug', 'cuet_ug', 'sat', 'ielts', 'toefl_ibt'));

-- Verify (should return 0 rows if no invalid data exists):
-- SELECT exam_type, COUNT(*) FROM exam_prep_questions
-- WHERE exam_type NOT IN ('jee_main','neet_ug','cuet_ug','sat','ielts','toefl_ibt')
-- GROUP BY exam_type;
