-- Migration: Lesson Repair Jobs and Tasks
-- Run once in Supabase SQL Editor.
--
-- Creates two tables for the Admin Lesson Repair workflow:
--   lesson_repair_jobs  — one record per admin-triggered repair run
--   lesson_repair_tasks — one record per lesson that needs repair
--
-- Safety rules enforced here:
--   - Only admin users can insert/update via service role key in backend
--   - original_content_json is always preserved for rollback
--   - repaired_content_json is a draft; published flag gates final write-through

-- ── lesson_repair_jobs ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lesson_repair_jobs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by_admin_id UUID      NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'queued',
        -- queued | running | completed | failed | cancelled
    mode                TEXT        NOT NULL DEFAULT 'sample',
        -- sample | filtered | all
    grade               TEXT,
    subject             TEXT,
    chapter             TEXT,
    use_llm             BOOLEAN     NOT NULL DEFAULT FALSE,
    total_tasks         INTEGER     NOT NULL DEFAULT 0,
    completed_tasks     INTEGER     NOT NULL DEFAULT 0,
    failed_tasks        INTEGER     NOT NULL DEFAULT 0,
    approved_tasks      INTEGER     NOT NULL DEFAULT 0,
    published_tasks     INTEGER     NOT NULL DEFAULT 0,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    error_summary       TEXT,
    report_json         JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── lesson_repair_tasks ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lesson_repair_tasks (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                  UUID        NOT NULL REFERENCES public.lesson_repair_jobs(id) ON DELETE CASCADE,
    grade                   TEXT        NOT NULL,
    subject                 TEXT        NOT NULL,
    chapter                 TEXT        NOT NULL,
    step_title              TEXT        NOT NULL,
    -- Reference to original lesson in lesson_cache table (if available)
    original_lesson_cache_id TEXT,
    status                  TEXT        NOT NULL DEFAULT 'queued',
        -- queued | running | repaired | validation_failed | ready_for_review |
        -- approved | published | failed | rejected
    issues_json             JSONB,          -- issues found by audit
    original_content_json   JSONB,          -- NEVER overwritten after creation
    repaired_content_json   JSONB,          -- draft repaired content
    validation_result_json  JSONB,          -- result of re-audit on repaired draft
    audit_before_score      INTEGER,        -- overall score before repair
    audit_after_score       INTEGER,        -- overall score after repair (if validated)
    error_message           TEXT,           -- error detail if status=failed
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_repair_jobs_status
    ON public.lesson_repair_jobs(status);
CREATE INDEX IF NOT EXISTS idx_repair_jobs_created_at
    ON public.lesson_repair_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_repair_tasks_job_id
    ON public.lesson_repair_tasks(job_id);
CREATE INDEX IF NOT EXISTS idx_repair_tasks_status
    ON public.lesson_repair_tasks(status);
CREATE INDEX IF NOT EXISTS idx_repair_tasks_grade_subject
    ON public.lesson_repair_tasks(grade, subject);

-- ── updated_at auto-trigger ───────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_repair_jobs_updated_at ON public.lesson_repair_jobs;
CREATE TRIGGER trg_repair_jobs_updated_at
    BEFORE UPDATE ON public.lesson_repair_jobs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_repair_tasks_updated_at ON public.lesson_repair_tasks;
CREATE TRIGGER trg_repair_tasks_updated_at
    BEFORE UPDATE ON public.lesson_repair_tasks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
