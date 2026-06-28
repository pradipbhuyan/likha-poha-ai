-- ─────────────────────────────────────────────────────────────────────────────
-- 20260628_formula_sheets_v2.sql
-- Extend formula_sheets with rich fields for freemium learning feature
-- All ALTER TABLE statements are idempotent via DO blocks
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='topic') THEN
    ALTER TABLE formula_sheets ADD COLUMN topic TEXT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='variables') THEN
    ALTER TABLE formula_sheets ADD COLUMN variables TEXT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='solution_steps') THEN
    ALTER TABLE formula_sheets ADD COLUMN solution_steps TEXT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='memory_tip') THEN
    ALTER TABLE formula_sheets ADD COLUMN memory_tip TEXT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='tags') THEN
    ALTER TABLE formula_sheets ADD COLUMN tags TEXT[];
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='difficulty') THEN
    ALTER TABLE formula_sheets ADD COLUMN difficulty TEXT DEFAULT 'medium'
      CHECK (difficulty IN ('easy','medium','hard'));
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_name='formula_sheets' AND column_name='chapter_order') THEN
    ALTER TABLE formula_sheets ADD COLUMN chapter_order INT DEFAULT 0;
  END IF;
END $$;

-- Index for topic lookup
CREATE INDEX IF NOT EXISTS idx_formula_topic ON formula_sheets (topic);
