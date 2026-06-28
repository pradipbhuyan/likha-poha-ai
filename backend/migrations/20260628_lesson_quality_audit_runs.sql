-- ─────────────────────────────────────────────────────────────────────────────
-- 20260628_lesson_quality_audit_runs.sql
-- Lesson Quality Audit run history — idempotent
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lesson_quality_audit_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode                TEXT NOT NULL DEFAULT 'sample',   -- sample|grade|subject|grade_subject|chapter|full
    grade               TEXT,
    subject             TEXT,
    chapter             TEXT,
    use_llm             BOOLEAN NOT NULL DEFAULT FALSE,
    use_e2e             BOOLEAN NOT NULL DEFAULT FALSE,
    fail_critical       BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT NOT NULL DEFAULT 'queued'    -- queued|running|completed|failed
                            CHECK (status IN ('queued','running','completed','failed')),
    overall_score       SMALLINT,
    critical_count      INT DEFAULT 0,
    high_count          INT DEFAULT 0,
    medium_count        INT DEFAULT 0,
    low_count           INT DEFAULT 0,
    lessons_audited     INT DEFAULT 0,
    report_json_path    TEXT,
    report_md_path      TEXT,
    report_csv_path     TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_by_admin_id UUID REFERENCES auth.users(id),
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_runs_status     ON lesson_quality_audit_runs (status);
CREATE INDEX IF NOT EXISTS idx_qa_runs_created_at ON lesson_quality_audit_runs (created_at DESC);
