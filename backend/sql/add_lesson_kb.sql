-- Lesson Knowledge Base (LKB)
-- ==============================
-- Pre-warmed Q&A chips for lesson follow-up suggestions.
-- Each entry contains a question + 6-10 bullet point NCERT-grounded answer
-- for a specific grade / subject / chapter / lesson step combination.
--
-- Chips are served to students instantly (zero LLM cost).
-- Admin pre-warms via Cache & Question Bank Management panel:
--   POST /api/admin/cache/build-lkb/{grade-slug}
--
-- Run in Supabase SQL editor before enabling.

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

-- Service role has full access
CREATE POLICY "service_role_full_access" ON lesson_kb
    FOR ALL TO service_role USING (true) WITH CHECK (true);
