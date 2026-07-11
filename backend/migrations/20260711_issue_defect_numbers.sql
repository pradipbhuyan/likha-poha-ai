-- ============================================================
-- Migration: product_issue_reports + defect_number system
-- Apply to: Supabase 2 (sjfjyzaaypfzyfhhggqw)
-- Idempotent: safe to run multiple times.
--
-- Run order:
--   1. This file FIRST on a fresh DB (creates table + defect_number)
--   2. On existing DB that already has the table: also safe (ADD COLUMN IF NOT EXISTS)
-- ============================================================

-- ── Step 1: Create the table if it doesn't exist yet ──────────────────────────
CREATE TABLE IF NOT EXISTS product_issue_reports (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_user_id     UUID REFERENCES auth.users(id),
    reporter_role        TEXT,
    issue_type           TEXT NOT NULL
                             CHECK (issue_type IN (
                                 'content_issue','wrong_explanation','missing_section',
                                 'wrong_formula','wrong_answer','broken_page',
                                 'login_issue','other'
                             )),
    severity             TEXT NOT NULL DEFAULT 'medium'
                             CHECK (severity IN ('low','medium','high','critical')),
    title                TEXT,
    description          TEXT NOT NULL,
    route                TEXT,
    grade                TEXT,
    subject              TEXT,
    chapter              TEXT,
    lesson_id            TEXT,
    lesson_step          TEXT,
    status               TEXT NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open','triaged','in_progress','fixed','wont_fix','duplicate')),
    admin_notes          TEXT,
    assigned_to_admin_id UUID REFERENCES auth.users(id),
    screenshot_url       TEXT,
    browser_info         JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at          TIMESTAMPTZ
);

-- Base indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_issues_status      ON product_issue_reports (status);
CREATE INDEX IF NOT EXISTS idx_issues_severity    ON product_issue_reports (severity);
CREATE INDEX IF NOT EXISTS idx_issues_issue_type  ON product_issue_reports (issue_type);
CREATE INDEX IF NOT EXISTS idx_issues_created_at  ON product_issue_reports (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issues_reporter    ON product_issue_reports (reporter_user_id);
CREATE INDEX IF NOT EXISTS idx_issues_grade       ON product_issue_reports (grade);

-- ── Step 2: Add defect_number column ──────────────────────────────────────────
ALTER TABLE product_issue_reports
  ADD COLUMN IF NOT EXISTS defect_number TEXT;

-- ── Step 3: Create global sequence for the numeric suffix ─────────────────────
CREATE SEQUENCE IF NOT EXISTS defect_number_seq
  START WITH 1
  INCREMENT BY 1
  NO CYCLE;

-- ── Step 4: Backfill existing rows that have no defect_number ─────────────────
DO $$
DECLARE
  rec RECORD;
  seq_val BIGINT;
BEGIN
  FOR rec IN
    SELECT id, created_at
    FROM product_issue_reports
    WHERE defect_number IS NULL
    ORDER BY created_at ASC
  LOOP
    seq_val := nextval('defect_number_seq');
    UPDATE product_issue_reports
    SET defect_number = 'DEF-' ||
        TO_CHAR(rec.created_at AT TIME ZONE 'UTC', 'YYYYMMDD') || '-' ||
        LPAD(seq_val::TEXT, 4, '0')
    WHERE id = rec.id;
  END LOOP;
END $$;

-- ── Step 5: Auto-generation trigger function ──────────────────────────────────
CREATE OR REPLACE FUNCTION fn_set_defect_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.defect_number IS NULL THEN
    NEW.defect_number :=
      'DEF-' ||
      TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYYMMDD') || '-' ||
      LPAD(nextval('defect_number_seq')::TEXT, 4, '0');
  END IF;
  RETURN NEW;
END;
$$;

-- ── Step 6: Attach trigger ────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_set_defect_number ON product_issue_reports;
CREATE TRIGGER trg_set_defect_number
  BEFORE INSERT ON product_issue_reports
  FOR EACH ROW EXECUTE FUNCTION fn_set_defect_number();

-- ── Step 7: Add constraints and index (skip if already exist) ─────────────────
DO $$
BEGIN
  -- NOT NULL
  BEGIN
    ALTER TABLE product_issue_reports ALTER COLUMN defect_number SET NOT NULL;
  EXCEPTION WHEN OTHERS THEN NULL;
  END;

  -- Unique constraint
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'uq_defect_number'
  ) THEN
    ALTER TABLE product_issue_reports
      ADD CONSTRAINT uq_defect_number UNIQUE (defect_number);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_issue_defect_number
  ON product_issue_reports (defect_number);

-- ── Verify ────────────────────────────────────────────────────────────────────
SELECT COUNT(*) AS total_issues,
       COUNT(defect_number) AS with_defect_number,
       MIN(defect_number) AS first_defect,
       MAX(defect_number) AS last_defect
FROM product_issue_reports;
