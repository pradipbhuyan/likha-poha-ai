-- Subjective Question Bank Table
-- Run once in Supabase SQL Editor (mirrors add_question_bank.sql) before
-- ingesting GPT-5.5-authored subjective questions for Create Test Paper.
-- Sibling of question_bank: that table holds MCQs (options A-D), this one
-- holds short/long-answer questions with a marks-scaled model answer.

CREATE TABLE IF NOT EXISTS subjective_question_bank (
    id                UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    board             TEXT        NOT NULL,
    grade             TEXT        NOT NULL,
    subject           TEXT        NOT NULL,
    chapter           TEXT        DEFAULT '',
    difficulty        TEXT        DEFAULT 'Medium',
    question          TEXT        NOT NULL,
    marks             INTEGER     DEFAULT 3,
    model_answer      TEXT        DEFAULT '',
    expected_keywords JSONB       DEFAULT '[]',
    status            TEXT        DEFAULT 'active',
    times_shown       INTEGER     DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subjbank_lookup
    ON subjective_question_bank(grade, subject, chapter, difficulty, status);

CREATE INDEX IF NOT EXISTS idx_subjbank_board_grade
    ON subjective_question_bank(board, grade, subject);

COMMENT ON TABLE subjective_question_bank IS
    'Pre-authored subjective (short/long-answer) test-paper questions, sampled
     randomly per request. No live LLM fallback — Create Test Paper reports a
     friendly "still being prepared" message when a chapter has too few.
     Populate via: backend/scripts/prepare_gpt55_subjective_question_prompts.py
     + backend/scripts/ingest_gpt55_subjective_question_bank_output.py
     (see docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md)';
