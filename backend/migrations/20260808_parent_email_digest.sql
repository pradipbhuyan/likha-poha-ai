-- ─────────────────────────────────────────────────────────────────────────────
-- 20260808_parent_email_digest.sql
-- Weekly parent email digest opt-out flag
-- Idempotent: all objects use IF NOT EXISTS
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS email_digest_opt_out BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_profiles_digest_eligible
    ON profiles (role, email_digest_opt_out)
    WHERE role = 'parent';
