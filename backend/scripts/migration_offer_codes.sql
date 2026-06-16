-- ============================================================
-- Migration: Offer Codes & Redemptions
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================

-- Table 1: offer_codes
-- Admin creates 8-char alphanumeric codes with a validity window.
CREATE TABLE IF NOT EXISTS offer_codes (
  id            UUID          DEFAULT gen_random_uuid() PRIMARY KEY,
  code          VARCHAR(8)    NOT NULL UNIQUE,
  description   TEXT,
  valid_from    TIMESTAMPTZ   NOT NULL DEFAULT now(),
  valid_until   TIMESTAMPTZ   NOT NULL,
  max_uses      INTEGER       NOT NULL DEFAULT 100,
  uses_count    INTEGER       NOT NULL DEFAULT 0,
  created_by    UUID          REFERENCES profiles(id) ON DELETE SET NULL,
  is_active     BOOLEAN       NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ   DEFAULT now()
);

-- Table 2: offer_redemptions
-- Tracks which user redeemed which code, and until when they have access.
CREATE TABLE IF NOT EXISTS offer_redemptions (
  id            UUID          DEFAULT gen_random_uuid() PRIMARY KEY,
  code_id       UUID          NOT NULL REFERENCES offer_codes(id) ON DELETE CASCADE,
  user_id       UUID          NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  redeemed_at   TIMESTAMPTZ   DEFAULT now(),
  valid_until   TIMESTAMPTZ   NOT NULL,
  UNIQUE (user_id, code_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_offer_codes_code      ON offer_codes (code);
CREATE INDEX IF NOT EXISTS idx_offer_redemptions_user ON offer_redemptions (user_id);

-- RLS: admin can do everything; students can only read their own redemptions
ALTER TABLE offer_codes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE offer_redemptions  ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS — backend uses service_role key so no policies needed.
-- If you want anon/authenticated policies add them here.

-- Allow service role full access (already bypasses RLS, but explicit for clarity)
CREATE POLICY "service_role_all_offer_codes"
  ON offer_codes FOR ALL
  TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_offer_redemptions"
  ON offer_redemptions FOR ALL
  TO service_role USING (true) WITH CHECK (true);
