-- Question Bank Table
-- Run once in Supabase SQL Editor before triggering question bank population.
-- The mock test generation flow works without this table — all bank operations
-- fail silently and fall back to live LLM generation.

CREATE TABLE IF NOT EXISTS question_bank (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    board           TEXT        NOT NULL,
    grade           TEXT        NOT NULL,
    subject         TEXT        NOT NULL,
    chapter         TEXT        DEFAULT '',
    exam_type       TEXT        DEFAULT 'General',
    difficulty      TEXT        DEFAULT 'Medium',
    section         TEXT        DEFAULT '',
    question        TEXT        NOT NULL,
    options         JSONB       DEFAULT '{}',
    answer          TEXT        NOT NULL,
    explanation     TEXT        DEFAULT '',
    marks           INTEGER     DEFAULT 1,
    status          TEXT        DEFAULT 'active',
    times_shown     INTEGER     DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qbank_lookup
    ON question_bank(grade, subject, chapter, difficulty, status);

CREATE INDEX IF NOT EXISTS idx_qbank_board_grade
    ON question_bank(board, grade, subject);

COMMENT ON TABLE question_bank IS
    'Pre-generated mock test questions sampled randomly per test request.
     Bank miss falls back to live LLM generation automatically.
     Invalidate a chapter when its RAG content is updated (set status=needs_review).
     Populate via: python3 backend/scripts/build_question_bank.py';
