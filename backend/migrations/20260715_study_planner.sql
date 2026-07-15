-- ============================================================
-- Study Planner — DB Migration
-- Phase 1 + 2 + 3: AI-generated weekly plan + daily task checklist
-- Run once in Supabase SQL Editor (safe to re-run — uses IF NOT EXISTS)
-- ============================================================

-- ── study_plans: stores the LLM-generated weekly plan ────────────────────────
CREATE TABLE IF NOT EXISTS study_plans (
  id                uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id           uuid    NOT NULL,
  exam_type         text    NOT NULL,
  exam_date         date,
  weeks_remaining   int     NOT NULL DEFAULT 0,
  daily_hours       int     NOT NULL DEFAULT 4,
  weak_topics       text[]  DEFAULT '{}',
  plan_json         jsonb   DEFAULT '[]'::jsonb,
  version           int     DEFAULT 1,
  generated_at      timestamptz DEFAULT now(),
  created_at        timestamptz DEFAULT now()
);

-- ── study_plan_tasks: daily checklist items derived from the plan ─────────────
CREATE TABLE IF NOT EXISTS study_plan_tasks (
  id               uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid    NOT NULL,
  exam_type        text    NOT NULL,
  plan_id          uuid    REFERENCES study_plans(id) ON DELETE CASCADE,
  week_number      int     NOT NULL DEFAULT 1,
  task_date        date,
  task_type        text    NOT NULL DEFAULT 'revise',
  -- task_type: 'revise' | 'practice' | 'formula_review' | 'mock_test' | 'light_revision'
  subject          text    NOT NULL,
  topic            text    NOT NULL,
  description      text    DEFAULT '',
  duration_minutes int     DEFAULT 60,
  status           text    DEFAULT 'pending',
  -- status: 'pending' | 'done' | 'skipped'
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_study_plans_user_exam
  ON study_plans(user_id, exam_type);

CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_user_exam_date
  ON study_plan_tasks(user_id, exam_type, task_date);

CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_plan_id
  ON study_plan_tasks(plan_id);

CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_status
  ON study_plan_tasks(status, task_date);

-- ── Enable Row Level Security (optional — Supabase best practice) ─────────────
-- ALTER TABLE study_plans ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE study_plan_tasks ENABLE ROW LEVEL SECURITY;
-- (Add policies as needed if using Supabase RLS)

COMMENT ON TABLE study_plans IS 'LLM-generated weekly study plans per student × exam';
COMMENT ON TABLE study_plan_tasks IS 'Daily task checklist items derived from study plans';
COMMENT ON COLUMN study_plan_tasks.task_type IS 'revise | practice | formula_review | mock_test | light_revision';
COMMENT ON COLUMN study_plan_tasks.status IS 'pending | done | skipped';
