-- Unanswered Questions Review Tables
-- Run this in Supabase SQL Editor

-- Table: unanswered_questions
-- Stores questions that hit the default fallback in chatbot, doubt, or lesson follow-up
CREATE TABLE IF NOT EXISTS unanswered_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question        TEXT NOT NULL,
    source          TEXT NOT NULL,           -- 'chatbot' | 'doubt' | 'lesson_followup'
    grade           TEXT,
    subject         TEXT,
    chapter         TEXT,
    mode            TEXT,
    username        TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    approved_answer TEXT,
    approved_by     TEXT,
    target          TEXT,                    -- 'dkb' | 'chatbot'
    target_id       TEXT,                    -- ID in the target table after approval
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for fast admin queries
CREATE INDEX IF NOT EXISTS idx_unanswered_status ON unanswered_questions(status);
CREATE INDEX IF NOT EXISTS idx_unanswered_source ON unanswered_questions(source);
CREATE INDEX IF NOT EXISTS idx_unanswered_created ON unanswered_questions(created_at DESC);

-- RLS: only admins can read/write (service role bypasses for logging)
ALTER TABLE unanswered_questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_full_access" ON unanswered_questions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- Table: chatbot_approved_qa
-- Stores admin-approved Q&A pairs for the chatbot knowledge base
CREATE TABLE IF NOT EXISTS chatbot_approved_qa (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    approved_by TEXT,
    status      TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'inactive'
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_qa_status ON chatbot_approved_qa(status);

ALTER TABLE chatbot_approved_qa ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_full_access_chatbot_qa" ON chatbot_approved_qa
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- Also add 'admin_approved' as valid source in doubt_kb
-- (no schema change needed — it's a text field that accepts any value)
