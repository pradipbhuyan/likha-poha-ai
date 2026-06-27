-- ─────────────────────────────────────────────────────────────────────────────
-- 20260627_teacher_classrooms.sql
-- Teacher Success Platform — Phase 1 migrations
-- Idempotent: all objects use IF NOT EXISTS / CREATE OR REPLACE
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Teacher Invitations ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_invitations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    student_name    TEXT NOT NULL,
    grade           TEXT NOT NULL DEFAULT 'Grade 9',
    email           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','accepted','expired','cancelled')),
    token           TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    accepted_at     TIMESTAMPTZ,
    student_id      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teacher_invitations_teacher_id
    ON teacher_invitations (teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_invitations_email
    ON teacher_invitations (email);
CREATE INDEX IF NOT EXISTS idx_teacher_invitations_status
    ON teacher_invitations (status);
CREATE INDEX IF NOT EXISTS idx_teacher_invitations_expires_at
    ON teacher_invitations (expires_at);

-- ── 2. Teacher Classrooms ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_classrooms (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id  UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'archived')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teacher_classrooms_teacher_id
    ON teacher_classrooms (teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_classrooms_status
    ON teacher_classrooms (status);

-- ── 3. Teacher Classroom Students ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_classroom_students (
    classroom_id    UUID NOT NULL REFERENCES teacher_classrooms(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (classroom_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_tcs_classroom_id
    ON teacher_classroom_students (classroom_id);
CREATE INDEX IF NOT EXISTS idx_tcs_student_id
    ON teacher_classroom_students (student_id);
CREATE INDEX IF NOT EXISTS idx_tcs_teacher_id
    ON teacher_classroom_students (teacher_id);

-- ── 4. Archived flag on teacher_student_assignments ──────────────────────────
-- Add archived_at column if it doesn't exist (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'teacher_student_assignments'
          AND column_name = 'archived_at'
    ) THEN
        ALTER TABLE teacher_student_assignments
            ADD COLUMN archived_at TIMESTAMPTZ DEFAULT NULL;
    END IF;
END $$;
