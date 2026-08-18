-- ─────────────────────────────────────────────────────────────────────────────
-- 20260818_user_feedback.sql
-- General-purpose user feedback (bugs, feature ideas, content suggestions,
-- praise) — separate from product_issue_reports, which is bug-report-shaped.
-- Idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_feedback (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES auth.users(id),
    user_role           TEXT,
    username            TEXT,
    feedback_type       TEXT NOT NULL
                            CHECK (feedback_type IN (
                                'bug','feature_request','content_suggestion','praise','other'
                            )),
    rating              SMALLINT
                            CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
    message             TEXT NOT NULL,
    trigger_event       TEXT,   -- which completion event prompted this, e.g. 'lesson_completed'
    route               TEXT,
    grade               TEXT,
    subject             TEXT,
    chapter             TEXT,
    criticality_score   NUMERIC(6,2) NOT NULL DEFAULT 0,
    criticality_tier    TEXT NOT NULL DEFAULT 'low'
                            CHECK (criticality_tier IN ('low','medium','high','critical')),
    status              TEXT NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new','reviewed','converted','dismissed')),
    admin_notes         TEXT,
    linked_tech_debt_id UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_status      ON user_feedback (status);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type        ON user_feedback (feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_tier        ON user_feedback (criticality_tier);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at  ON user_feedback (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user        ON user_feedback (user_id);
