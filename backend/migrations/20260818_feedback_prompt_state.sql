-- ─────────────────────────────────────────────────────────────────────────────
-- 20260818_feedback_prompt_state.sql
-- Tracks the last time a user was shown the contextual "share feedback"
-- prompt, so the frontend can enforce a cooldown between prompts. Idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS last_feedback_prompt_at TIMESTAMPTZ;
