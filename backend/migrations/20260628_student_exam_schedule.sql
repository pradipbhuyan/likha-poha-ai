-- ─────────────────────────────────────────────────────────────────────────────
-- 20260628_student_exam_schedule.sql
-- Student Exam Schedule table — idempotent
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS student_exam_schedule (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    subject             TEXT NOT NULL,
    exam_date           DATE NOT NULL,
    exam_type           TEXT,                        -- e.g. 'Unit Test', 'Final', 'Board'
    notes               TEXT,
    created_by_user_id  UUID NOT NULL REFERENCES auth.users(id),
    created_by_role     TEXT NOT NULL CHECK (created_by_role IN ('student','parent','teacher','admin')),
    status              TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','cancelled','completed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_student_id   ON student_exam_schedule (student_id);
CREATE INDEX IF NOT EXISTS idx_exam_date         ON student_exam_schedule (exam_date);
CREATE INDEX IF NOT EXISTS idx_exam_status       ON student_exam_schedule (status);
