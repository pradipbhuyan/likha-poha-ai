-- ============================================================
-- Migration: Influencer Tracking for Offer Codes
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================
-- Adds influencer metadata and discount/incentive fields to
-- the offer_codes table so each code can be attributed to
-- an influencer and tracked in the admin console.
-- ============================================================

ALTER TABLE public.offer_codes
  ADD COLUMN IF NOT EXISTS influencer_name    TEXT    NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS influencer_email   TEXT    NOT NULL DEFAULT '',
  -- 'free_trial': free platform access for validity window (existing behaviour)
  -- 'discount':   X% off first paid subscription via Razorpay
  ADD COLUMN IF NOT EXISTS code_type          TEXT    NOT NULL DEFAULT 'free_trial'
                            CHECK (code_type IN ('free_trial', 'discount')),
  -- 0 for free_trial; 5-10 for discount codes
  ADD COLUMN IF NOT EXISTS discount_percent   INTEGER NOT NULL DEFAULT 0
                            CHECK (discount_percent >= 0 AND discount_percent <= 100),
  -- INR admin agrees to pay the influencer per confirmed redemption
  ADD COLUMN IF NOT EXISTS incentive_inr      INTEGER NOT NULL DEFAULT 0
                            CHECK (incentive_inr >= 0),
  -- Set to true once admin has paid this influencer's incentives
  ADD COLUMN IF NOT EXISTS incentive_paid     BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS incentive_paid_at  TIMESTAMPTZ;

-- Index for fast influencer dashboard queries
CREATE INDEX IF NOT EXISTS idx_offer_codes_influencer
  ON public.offer_codes (influencer_name)
  WHERE influencer_name <> '';
