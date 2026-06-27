-- ─────────────────────────────────────────────────────────────────────────────
-- 20260627_teacher_phase2.sql
-- Teacher Success Platform — Phase 2 tables
-- Idempotent: all objects use IF NOT EXISTS
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Teacher Tasks ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    student_id      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','completed','dismissed')),
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('critical','medium','low')),
    due_date        DATE,
    source          TEXT NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual','intervention','system')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_teacher_tasks_teacher_id  ON teacher_tasks (teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_tasks_student_id  ON teacher_tasks (student_id);
CREATE INDEX IF NOT EXISTS idx_teacher_tasks_status      ON teacher_tasks (status);
CREATE INDEX IF NOT EXISTS idx_teacher_tasks_priority    ON teacher_tasks (priority);
CREATE INDEX IF NOT EXISTS idx_teacher_tasks_created_at  ON teacher_tasks (created_at DESC);

-- ── 2. Teacher Student Notes ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_student_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    note            TEXT NOT NULL,
    visibility      TEXT NOT NULL DEFAULT 'teacher_private'
                        CHECK (visibility IN ('teacher_private','admin_visible')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tsn_teacher_id  ON teacher_student_notes (teacher_id);
CREATE INDEX IF NOT EXISTS idx_tsn_student_id  ON teacher_student_notes (student_id);
CREATE INDEX IF NOT EXISTS idx_tsn_deleted_at  ON teacher_student_notes (deleted_at);

-- ── 3. Teacher Parent Messages ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_parent_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    subject         TEXT NOT NULL DEFAULT '',
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('sent','draft','failed','no_email')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tpm_teacher_id  ON teacher_parent_messages (teacher_id);
CREATE INDEX IF NOT EXISTS idx_tpm_student_id  ON teacher_parent_messages (student_id);
CREATE INDEX IF NOT EXISTS idx_tpm_parent_id   ON teacher_parent_messages (parent_id);
CREATE INDEX IF NOT EXISTS idx_tpm_status      ON teacher_parent_messages (status);
