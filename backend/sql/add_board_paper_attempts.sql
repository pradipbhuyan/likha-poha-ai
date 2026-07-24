-- Board Sample Papers — Timed Test attempt history
-- Run once in the Supabase SQL Editor for the PRIMARY project ONLY.
--
-- Unlike board_sample_papers / board_sample_paper_questions (which are
-- grade-routed — Grade 10 lives on the primary project, Grade 11/12 on a
-- second dedicated project, see app/services/grade_db_router.py), user-owned
-- history data in this codebase is never grade-routed. It is centralized on
-- the primary project, same convention as test_history
-- (see backend/app/services/test_history_service.py, which reads/writes via
-- admin_client directly and filters by username). board_paper_attempts
-- follows that same convention so one student's attempt history isn't split
-- across two Supabase projects even though the *papers* themselves might be.
--
-- Because a paper's row can live in a different Supabase project than this
-- table (Grade 12 papers), paper_id is intentionally NOT a foreign key.

CREATE TABLE IF NOT EXISTS board_paper_attempts (
    id                              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username                        TEXT NOT NULL,
    paper_id                        UUID NOT NULL,  -- no FK: paper may live in a different Supabase project (Grade 12)
    grade                           TEXT NOT NULL,
    board                           TEXT NOT NULL DEFAULT 'CBSE',
    academic_year                   TEXT NOT NULL,
    subject                         TEXT NOT NULL,
    subject_variant                 TEXT DEFAULT '',
    started_at                      TIMESTAMPTZ NOT NULL,
    submitted_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_taken_seconds              INTEGER,
    mcq_score                       NUMERIC DEFAULT 0,
    mcq_max_score                   NUMERIC DEFAULT 0,
    subjective_self_marked_correct  NUMERIC DEFAULT 0,
    subjective_max_score            NUMERIC DEFAULT 0,
    answers                         JSONB DEFAULT '{}',  -- {question_number: {selected: "..."} | {self_marked_correct: true|false}}
    created_at                      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_board_paper_attempts_user_paper ON board_paper_attempts(username, paper_id);

-- RLS: admin-only policy, matching add_unanswered_questions.sql's convention.
-- Actual per-user access (a student only ever seeing their own attempts) is
-- enforced in the Python service layer via admin_client + explicit
-- .eq("username", ...) filtering, not granular RLS — this is the
-- established pattern for user-history tables in this codebase.
ALTER TABLE board_paper_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_full_access" ON board_paper_attempts;
CREATE POLICY "admin_full_access" ON board_paper_attempts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

COMMENT ON TABLE board_paper_attempts IS
    'One row per Timed Test attempt on a Board Sample Paper. Scoring is
     computed client-side (MCQ auto-graded, subjective self-marked by the
     student) and simply persisted here — no server-side answer validation,
     no LLM call, matching Board Sample Papers'' bank-only serving
     philosophy. Always lives on the PRIMARY Supabase project regardless of
     the paper''s grade (see header comment above) — never grade-routed.';
