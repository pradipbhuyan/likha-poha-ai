-- ============================================================
-- Migration: Add defect_number to product_issue_reports
-- Apply to: Supabase 2 (sjfjyzaaypfzyfhhggqw)
-- Purpose:  Human-readable DEF-YYYYMMDD-NNNN identifier for
--           every bug report. Used in Git commit messages to
--           make each fix traceable to the exact defect.
-- Format:   DEF-20260711-0001
-- ============================================================

-- 1. Add the column (nullable first so we can backfill)
ALTER TABLE product_issue_reports
  ADD COLUMN IF NOT EXISTS defect_number TEXT;

-- 2. Create a global sequence for the numeric suffix
CREATE SEQUENCE IF NOT EXISTS defect_number_seq
  START WITH 1
  INCREMENT BY 1
  NO CYCLE;

-- 3. Backfill existing rows in chronological order
--    (assigns DEF-<original_date>-NNNN preserving creation order)
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

-- 4. Auto-generation trigger function
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

-- 5. Attach trigger to table
DROP TRIGGER IF EXISTS trg_set_defect_number ON product_issue_reports;
CREATE TRIGGER trg_set_defect_number
  BEFORE INSERT ON product_issue_reports
  FOR EACH ROW EXECUTE FUNCTION fn_set_defect_number();

-- 6. Add unique + NOT NULL constraints once backfill is done
ALTER TABLE product_issue_reports
  ALTER COLUMN defect_number SET NOT NULL,
  ADD CONSTRAINT uq_defect_number UNIQUE (defect_number);

-- 7. Index for fast lookup by defect number (used by auto-fix, admin search)
CREATE INDEX IF NOT EXISTS idx_issue_defect_number
  ON product_issue_reports (defect_number);

-- Verify
SELECT COUNT(*) AS total_issues,
       COUNT(defect_number) AS with_defect_number
FROM product_issue_reports;
