-- ─────────────────────────────────────────────────────────────────────────────
-- 20260818_tech_debt_items.sql
-- Admin-approval-gated backlog. Fed by user_feedback (and, in future, by
-- product_issue_reports) via POST /api/admin/tech-debt. Idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tech_debt_items (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                 TEXT NOT NULL,
    description           TEXT,
    source_type           TEXT NOT NULL DEFAULT 'manual'
                              CHECK (source_type IN ('feedback','issue','manual')),
    source_feedback_ids   UUID[] NOT NULL DEFAULT '{}',
    criticality_score     NUMERIC(6,2) NOT NULL DEFAULT 0,
    criticality_tier      TEXT NOT NULL DEFAULT 'low'
                              CHECK (criticality_tier IN ('low','medium','high','critical')),
    status                TEXT NOT NULL DEFAULT 'proposed'
                              CHECK (status IN ('proposed','approved','rejected','in_progress','done')),
    rejection_reason      TEXT,
    reviewed_by_admin_id  UUID REFERENCES auth.users(id),
    reviewed_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tech_debt_status         ON tech_debt_items (status);
CREATE INDEX IF NOT EXISTS idx_tech_debt_tier           ON tech_debt_items (criticality_tier);
CREATE INDEX IF NOT EXISTS idx_tech_debt_score          ON tech_debt_items (criticality_score DESC);
CREATE INDEX IF NOT EXISTS idx_tech_debt_created_at     ON tech_debt_items (created_at DESC);
