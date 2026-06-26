-- Migration: subscription_timeline table
-- Append-only history of subscription state transitions.
-- Used for support, analytics, and debugging — never for access control.

CREATE TABLE IF NOT EXISTS public.subscription_timeline (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL,
  event_type        text        NOT NULL,   -- e.g. FREE_TIER.assigned, NANO.activated, plan.expired
  from_plan         text,                   -- canonical plan key before transition
  to_plan           text,                   -- canonical plan key after transition
  source            text,                   -- PAID | OFFER_CODE | ADMIN_GRANT | EXPIRY | SIGNUP
  payment_id        text,                   -- razorpay_payment_id for PAID events
  order_id          text,                   -- razorpay_order_id for PAID events
  expires_at        timestamptz,            -- subscription_expires_at applied
  idempotency_key   text,                   -- prevents duplicate events on retry
  metadata          jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- Append-only — no UPDATE or DELETE
ALTER TABLE public.subscription_timeline ENABLE ROW LEVEL SECURITY;

-- No permissive SELECT policy. service_role bypasses RLS automatically.
-- Normal users cannot read subscription history.
-- Idempotent: drop old permissive policy if it exists from a prior run.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'subscription_timeline'
      AND policyname = 'timeline_service_read'
  ) THEN
    DROP POLICY "timeline_service_read" ON public.subscription_timeline;
  END IF;
END;
$$;

-- Idempotency: prevent duplicate events for the same payment
CREATE UNIQUE INDEX IF NOT EXISTS subscription_timeline_idempotency_uniq
  ON public.subscription_timeline (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS timeline_user_idx       ON public.subscription_timeline (user_id);
CREATE INDEX IF NOT EXISTS timeline_event_idx      ON public.subscription_timeline (event_type);
CREATE INDEX IF NOT EXISTS timeline_created_idx    ON public.subscription_timeline (created_at DESC);
CREATE INDEX IF NOT EXISTS timeline_payment_idx    ON public.subscription_timeline (payment_id)
  WHERE payment_id IS NOT NULL;

COMMENT ON TABLE public.subscription_timeline IS
  'Append-only history of subscription state changes. '
  'Read-only for analytics — never used for access control decisions.';
