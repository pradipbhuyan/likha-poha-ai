-- Migration: add time_taken_seconds to test_history
-- Run in Supabase SQL editor

ALTER TABLE test_history
  ADD COLUMN IF NOT EXISTS time_taken_seconds INTEGER DEFAULT NULL;

COMMENT ON COLUMN test_history.time_taken_seconds IS
  'Elapsed time in seconds from when questions were displayed to when the student submitted. NULL for tests taken before this field was added.';
