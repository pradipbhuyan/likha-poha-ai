-- ============================================================
-- Remove SOF (Olympiad) — DB Migration
-- SOF is no longer a supported product mode. This migration drops the
-- access_sof_* columns from profiles and purges SOF-tagged question_bank
-- and rag_documents rows.
--
-- Run manually in the Supabase SQL Editor for BOTH projects:
--   1. Primary project      (Grade 1-10 + auth/user data) — run all 4 steps
--   2. Grade 11/12 project  (SUPABASE_GRADE_1112_URL)      — profiles table
--      does not exist here; skip step 3 (it will simply no-op/error on a
--      missing table — run steps 1, 2, 4 only)
--
-- Not auto-applied by the app or CI — review before running. This is a
-- destructive, one-way migration: back up profiles/question_bank/
-- rag_documents first if you want to keep the option to roll back.
-- Confirmed before writing this migration: no user currently holds paid
-- SOF access (access_sof_science/maths/english were all False in
-- subscription_plans.py before this change).
-- ============================================================

-- ── 1. Purge SOF question_bank rows (subject is an Olympiad subject) ────────
DELETE FROM question_bank
WHERE subject IN ('Science Olympiad', 'Maths Olympiad', 'English Olympiad');

-- ── 2. Purge SOF rag_documents rows (uploaded Olympiad book content) ────────
DELETE FROM rag_documents
WHERE subject IN ('Science Olympiad', 'Maths Olympiad', 'English Olympiad');

-- ── 3. Drop the per-subject SOF access flags from profiles ──────────────────
ALTER TABLE profiles DROP COLUMN IF EXISTS access_sof_science;
ALTER TABLE profiles DROP COLUMN IF EXISTS access_sof_maths;
ALTER TABLE profiles DROP COLUMN IF EXISTS access_sof_english;

-- ── 4. Clean up any saved syllabus review overrides for SOF mode ────────────
-- (fetch_subject_overrides / fetch_syllabus_overrides in syllabus.py key rows
--  by (grade, mode) / (grade, mode, subject); SOF rows are now dead data)
DELETE FROM syllabus_subject_overrides WHERE mode = 'SOF';
DELETE FROM syllabus_chapter_overrides WHERE mode = 'SOF';
