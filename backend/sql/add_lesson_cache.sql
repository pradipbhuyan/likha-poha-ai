-- Lesson Cache Table
-- Run once in Supabase SQL Editor before triggering lesson pre-generation.
-- The lesson generation flow works without this table — all cache operations
-- fail silently and fall back to live LLM generation.

CREATE TABLE IF NOT EXISTS lesson_cache (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    cache_key           TEXT        UNIQUE NOT NULL,
    board               TEXT        NOT NULL,
    grade               TEXT        NOT NULL,
    subject             TEXT        NOT NULL,
    chapter             TEXT        NOT NULL,
    mode                TEXT        NOT NULL,
    step_title          TEXT        NOT NULL,
    teacher_persona     TEXT        DEFAULT '',
    lesson_content      TEXT        NOT NULL,
    practice_questions  JSONB       DEFAULT '[]',
    source_type         TEXT        DEFAULT 'LLM',
    status              TEXT        DEFAULT 'active',
    access_count        INTEGER     DEFAULT 1,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lesson_cache_key
    ON lesson_cache(cache_key);

CREATE INDEX IF NOT EXISTS idx_lesson_cache_chapter
    ON lesson_cache(board, grade, subject, chapter);

COMMENT ON TABLE lesson_cache IS
    'Pre-generated lesson steps and practice questions.
     Cache miss falls back to live LLM generation automatically.
     Invalidate a chapter cache when its RAG content is updated.
     Populate via: python3 backend/scripts/prewarm_lessons.py';
