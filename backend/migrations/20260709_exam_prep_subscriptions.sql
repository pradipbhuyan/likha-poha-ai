-- ─────────────────────────────────────────────────────────────────────────────
-- exam_prep_subscriptions migration
-- Adds a separate subscription table for JEE / NEET / CUET exam prep packs.
--
-- These packs are independent of the CBSE subscription:
--   - Free tier students CAN buy exam prep packs
--   - Premium students do NOT automatically get exam prep (separate purchase)
--   - Each pack is per-exam: jee_main | neet_ug | cuet_ug
--   - A student can own 1, 2, or all 3 packs
--   - Season-based validity (duration_days set by admin)
--
-- Run in Supabase SQL Editor on dpivlbbyzlbpwnwgajso (main DB). Safe to re-run.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS exam_prep_subscriptions (
    id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              uuid        NOT NULL,
    exam_type            text        NOT NULL
                                     CHECK (exam_type IN ('jee_main','neet_ug','cuet_ug')),
    status               text        NOT NULL DEFAULT 'active'
                                     CHECK (status IN ('active','expired','revoked')),
    expires_at           timestamptz,
    plan_key             text,               -- e.g. 'exam_prep_jee'
    razorpay_order_id    text,
    razorpay_payment_id  text,
    amount_paid          int,                -- rupees
    created_at           timestamptz DEFAULT now(),
    updated_at           timestamptz DEFAULT now(),
    UNIQUE(user_id, exam_type)               -- one active pack per exam per user
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS exam_prep_subs_user_idx
    ON exam_prep_subscriptions(user_id);

-- RLS: users can only read their own rows; admin full access
ALTER TABLE exam_prep_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Users read own exam prep subs"
    ON exam_prep_subscriptions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role full access exam prep subs"
    ON exam_prep_subscriptions FOR ALL
    USING (true);

COMMENT ON TABLE exam_prep_subscriptions IS
    'Tracks JEE/NEET/CUET exam prep pack purchases. Independent of CBSE subscription.';
