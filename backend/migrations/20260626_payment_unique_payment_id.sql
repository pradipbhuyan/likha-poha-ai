-- Migration: unique partial index on razorpay_payment_id
-- Prevents the same Razorpay payment_id from being used on two different orders
-- (payment_id reuse / replay attack mitigation).
-- Partial: NULL values are excluded so "created" (unverified) rows don't conflict.
--
-- Safe: existing rows with NULL payment_id are unaffected.
-- If duplicate non-null payment_ids exist, investigate before running.

CREATE UNIQUE INDEX IF NOT EXISTS subscription_payments_payment_id_uniq
  ON public.subscription_payments (razorpay_payment_id)
  WHERE razorpay_payment_id IS NOT NULL;

COMMENT ON INDEX public.subscription_payments_payment_id_uniq IS
  'Prevents the same razorpay_payment_id from being applied twice (replay protection). '
  'Partial — NULL (unverified) rows excluded.';
