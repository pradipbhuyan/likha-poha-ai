-- Migration: add subscription_expires_at to profiles
-- Run in Supabase SQL editor
-- This column tracks when a time-limited subscription expires (e.g. ₹99 / 8-day Premium Nano plan)

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN profiles.subscription_expires_at IS
  'When the current paid plan expires. NULL = no expiry (unlimited). '
  'When this date passes, access_cbse and other access flags are revoked automatically.';

-- Index for efficient expiry queries
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_expires_at
  ON profiles (subscription_expires_at)
  WHERE subscription_expires_at IS NOT NULL;
