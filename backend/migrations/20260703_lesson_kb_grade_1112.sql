-- ─────────────────────────────────────────────────────────────────────────────
-- 20260703_lesson_kb_grade_1112.sql
-- Create lesson_kb table on the Grade 11/12 Supabase project.
-- Run this in the SQL editor at: https://sjfjyzaaypfzyfhhggqw.supabase.co
-- ─────────────────────────────────────────────────────────────────────────────

-- Main LKB table (no vector embedding needed — exact key lookup)
CREATE TABLE IF NOT EXISTS lesson_kb (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    chapter     TEXT NOT NULL,
    step_title  TEXT NOT NULL,
    question    TEXT NOT NULL,
    -- Answer formatted as 6-10 NCERT-grounded bullet points
    answer      TEXT NOT NULL,
    -- 'prewarmed' = admin generated | 'llm' = auto-stored from LLM follow-up
    source      TEXT NOT NULL DEFAULT 'prewarmed',
    hit_count   INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    status      TEXT NOT NULL DEFAULT 'active'   -- active | archived
);

-- Index for fast exact lookup by grade/subject/chapter/step
CREATE INDEX IF NOT EXISTS lesson_kb_lookup_idx
    ON lesson_kb (grade, subject, chapter, step_title, status);

-- Index for admin reporting
CREATE INDEX IF NOT EXISTS lesson_kb_grade_idx
    ON lesson_kb (grade, status);

-- Enable Row Level Security
ALTER TABLE lesson_kb ENABLE ROW LEVEL SECURITY;

-- Service role has full access (idempotent — skip if policy already exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'lesson_kb'
          AND policyname = 'service_role_full_access'
    ) THEN
        EXECUTE 'CREATE POLICY "service_role_full_access" ON lesson_kb
            FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;
