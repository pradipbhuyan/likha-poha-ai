-- ============================================================
-- Migration: Sales Lead Claims
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================
-- This table replaces manual admin-driven sales_student_attributions
-- for the self-service sales lead claim flow.
--
-- Flow:
--   1. Sales person submits a lead (student email + name)
--   2. Student signs up and pays → complete_signup auto-confirms the claim
--   3. Commission is auto-calculated and recorded
--   4. Admin does one monthly batch-pay click → all confirmed → paid
-- ============================================================

CREATE TABLE IF NOT EXISTS public.sales_lead_claims (
  id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  sales_person_id   UUID          NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,

  -- Lead information (submitted by salesperson)
  student_email     TEXT          NOT NULL,
  student_name      TEXT          NOT NULL DEFAULT '',
  student_phone     TEXT          NOT NULL DEFAULT '',
  grade             TEXT          NOT NULL DEFAULT 'Grade 9',
  package_key       TEXT          NOT NULL DEFAULT 'starter',

  -- Status lifecycle (system-managed, salesperson cannot edit)
  -- claimed   → submitted, awaiting student payment
  -- confirmed → student paid (auto-set by payment hook)
  -- paid      → admin batch-marked commission as paid
  -- expired   → 30 days passed with no payment
  status            TEXT          NOT NULL DEFAULT 'claimed'
                    CHECK (status IN ('claimed','confirmed','paid','expired')),

  -- Auto-filled when student pays
  student_id        UUID          REFERENCES public.profiles(id) ON DELETE SET NULL,
  package_amount    INTEGER       NOT NULL DEFAULT 0,
  incentive_percent NUMERIC(5,2)  NOT NULL DEFAULT 5
                    CHECK (incentive_percent >= 5 AND incentive_percent <= 10),
  commission_amount NUMERIC(10,2) NOT NULL DEFAULT 0,

  -- Timestamps
  claimed_at        TIMESTAMPTZ   NOT NULL DEFAULT now(),
  confirmed_at      TIMESTAMPTZ,   -- set automatically on payment match
  paid_at           TIMESTAMPTZ,   -- set by admin batch-pay action

  -- Admin notes (for disputes only)
  admin_notes       TEXT          NOT NULL DEFAULT '',

  -- Constraints
  UNIQUE (student_email)   -- first-claim-wins, DB-enforced
);

-- Index for fast lookup by salesperson and status
CREATE INDEX IF NOT EXISTS idx_sales_lead_claims_salesperson
  ON public.sales_lead_claims (sales_person_id, status);

CREATE INDEX IF NOT EXISTS idx_sales_lead_claims_email
  ON public.sales_lead_claims (student_email);

-- Auto-expire claims older than 30 days (checked lazily on load)
-- No cron needed — the backend marks expired on fetch.

-- RLS
ALTER TABLE public.sales_lead_claims ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS
CREATE POLICY "service_role_all_lead_claims"
  ON public.sales_lead_claims FOR ALL
  TO service_role USING (true) WITH CHECK (true);
