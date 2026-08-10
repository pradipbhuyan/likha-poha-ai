-- ─────────────────────────────────────────────────────────────────────────────
-- 20260809_teacher_lesson_plan_edits.sql
-- Per-teacher, private edited copies of lesson plans.
--
-- The system-generated lesson_plan_bank/*.json files on disk are NEVER
-- written to by this feature — they remain the single shared "system
-- version" for every teacher. A teacher who edits a plan gets their own
-- private row here instead; only that teacher's own edited copy is ever
-- returned to them (see app/services/teacher_lesson_plan_service.py).
--
-- One row per (teacher_id, grade, subject, chapter) — editing the same
-- chapter again overwrites the teacher's own prior edit (upsert), it does
-- not create a growing history. "Revert to System Version" just deletes
-- this row so the teacher falls back to the shared bank file again.
--
-- Idempotent: all objects use IF NOT EXISTS.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS teacher_lesson_plan_edits (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id              UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    grade                   TEXT NOT NULL,
    subject                 TEXT NOT NULL,
    chapter                 TEXT NOT NULL,
    lesson_plan_markdown    TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (teacher_id, grade, subject, chapter)
);

CREATE INDEX IF NOT EXISTS idx_tlpe_teacher_id
    ON teacher_lesson_plan_edits (teacher_id);

CREATE INDEX IF NOT EXISTS idx_tlpe_lookup
    ON teacher_lesson_plan_edits (teacher_id, grade, subject, chapter);

-- Row Level Security: a teacher may only ever see/modify their own edited
-- copies. The backend uses the Supabase service-role client (admin_client)
-- for all reads/writes and enforces teacher_id == authenticated user's id
-- in application code (see teacher_lesson_plan_service.py), but RLS is
-- enabled too as defense-in-depth in case this table is ever queried
-- directly with a user-scoped client.
ALTER TABLE teacher_lesson_plan_edits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "teachers manage their own lesson plan edits" ON teacher_lesson_plan_edits;
CREATE POLICY "teachers manage their own lesson plan edits"
    ON teacher_lesson_plan_edits
    FOR ALL
    USING (auth.uid() = teacher_id)
    WITH CHECK (auth.uid() = teacher_id);
