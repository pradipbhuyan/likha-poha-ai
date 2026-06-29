-- ─────────────────────────────────────────────────────────────────────────────
-- 20260629_product_issue_reports.sql
-- Student/user issue reporting — idempotent
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS product_issue_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_user_id    UUID REFERENCES auth.users(id),
    reporter_role       TEXT,
    issue_type          TEXT NOT NULL
                            CHECK (issue_type IN (
                                'content_issue','wrong_explanation','missing_section',
                                'wrong_formula','wrong_answer','broken_page',
                                'login_issue','other'
                            )),
    severity            TEXT NOT NULL DEFAULT 'medium'
                            CHECK (severity IN ('low','medium','high','critical')),
    title               TEXT,
    description         TEXT NOT NULL,
    route               TEXT,
    grade               TEXT,
    subject             TEXT,
    chapter             TEXT,
    lesson_id           TEXT,
    lesson_step         TEXT,
    status              TEXT NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open','triaged','in_progress','fixed','wont_fix','duplicate')),
    admin_notes         TEXT,
    assigned_to_admin_id UUID REFERENCES auth.users(id),
    screenshot_url      TEXT,
    browser_info        JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_issues_status      ON product_issue_reports (status);
CREATE INDEX IF NOT EXISTS idx_issues_severity    ON product_issue_reports (severity);
CREATE INDEX IF NOT EXISTS idx_issues_issue_type  ON product_issue_reports (issue_type);
CREATE INDEX IF NOT EXISTS idx_issues_created_at  ON product_issue_reports (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issues_reporter    ON product_issue_reports (reporter_user_id);
CREATE INDEX IF NOT EXISTS idx_issues_grade       ON product_issue_reports (grade);
