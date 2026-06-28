-- ─────────────────────────────────────────────────────────────────────────────
-- 20260628_formula_sheets.sql
-- Formula Sheets reference table — idempotent
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS formula_sheets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade           TEXT NOT NULL,          -- e.g. "Grade 9"
    subject         TEXT NOT NULL,          -- e.g. "Mathematics"
    chapter         TEXT,                   -- e.g. "Triangles" (nullable = applies to whole subject)
    section_title   TEXT NOT NULL,          -- e.g. "Area Formulas"
    formula_name    TEXT NOT NULL,          -- e.g. "Area of Triangle"
    expression      TEXT NOT NULL,          -- e.g. "A = (1/2) × base × height"
    explanation     TEXT,                   -- plain-English explanation
    example         TEXT,                   -- worked example (optional)
    display_order   INT  NOT NULL DEFAULT 0,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_formula_grade_subject ON formula_sheets (grade, subject);
CREATE INDEX IF NOT EXISTS idx_formula_chapter       ON formula_sheets (chapter);
CREATE INDEX IF NOT EXISTS idx_formula_active        ON formula_sheets (active);
