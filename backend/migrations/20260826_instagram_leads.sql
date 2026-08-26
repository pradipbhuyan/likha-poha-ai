-- ─────────────────────────────────────────────────────────────────────────────
-- 20260826_instagram_leads.sql
-- Leads captured from the "Learn More" questionnaire linked in the
-- Instagram bio (github.io/likha-poha-promo-assets/interest/). Public,
-- unauthenticated submissions — no user_id, no RLS-protected read path.
-- Idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS instagram_leads (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role          TEXT NOT NULL
                    CHECK (role IN ('student', 'parent', 'teacher')),
    name          TEXT NOT NULL,
    phone         TEXT NOT NULL,
    grade         TEXT,
    student_count TEXT,
    source        TEXT NOT NULL DEFAULT 'instagram_bio_link',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instagram_leads_created_at ON instagram_leads (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_instagram_leads_role        ON instagram_leads (role);
