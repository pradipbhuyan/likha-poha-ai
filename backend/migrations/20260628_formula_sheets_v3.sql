-- ─────────────────────────────────────────────────────────────────────────────
-- 20260628_formula_sheets_v3.sql
-- Rich content model fields for Formula Sheet
-- Idempotent via ADD COLUMN IF NOT EXISTS
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS expression_latex TEXT;
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS variables_json  JSONB;
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS use_when        TEXT;
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS mcqs_json       JSONB;
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS source_type     TEXT DEFAULT 'seeded'
  CHECK (source_type IN ('seeded','manual','llm_generated','admin_reviewed'));
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS status          TEXT DEFAULT 'published'
  CHECK (status IN ('draft','published','archived'));
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS quality_score   SMALLINT;
ALTER TABLE formula_sheets ADD COLUMN IF NOT EXISTS updated_at      TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_formula_status      ON formula_sheets (status);
CREATE INDEX IF NOT EXISTS idx_formula_source_type ON formula_sheets (source_type);
