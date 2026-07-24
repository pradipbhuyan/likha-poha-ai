-- ============================================================================
-- Migration: Copy the remaining Grade 11/12 user-linked tables from
-- Supabase 2 into Supabase 1 (primary)
--
-- Follow-up to 20260723_migrate_grade1112_content_to_primary.sql. That
-- script covered every table on the "must not lose" list. This one covers
-- the tables exam_prep_service.py and study_planner_service.py also touch
-- via their own shared DB client (exam_prep_attempts, exam_prep_simulated_tests,
-- exam_prep_simulated_test_answers, study_plans, study_plan_tasks) — needed so
-- those two files can be fully cut over to primary without breaking any
-- attempt/simulated-test/study-plan code path.
--
-- Prerequisite: run this in the SAME Supabase 1 SQL Editor session as the
-- earlier script, i.e. after Step 0 there has already created the
-- grade1112_remote server + grade1112_src schema. If that FDW connection
-- was already dropped (Step 4 cleanup), redo Step 0 first with a fresh
-- IMPORT FOREIGN SCHEMA that includes these five tables.
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- STEP A — Import these five additional foreign tables
-- (skip this block if your grade1112_src schema already includes them)
-- ────────────────────────────────────────────────────────────────────────────

IMPORT FOREIGN SCHEMA public
    LIMIT TO (exam_prep_attempts, exam_prep_simulated_tests,
              exam_prep_simulated_test_answers, study_plans, study_plan_tasks)
    FROM SERVER grade1112_remote INTO grade1112_src;

-- See what's actually there before creating anything on primary:
SELECT 'exam_prep_attempts' AS t, count(*) FROM grade1112_src.exam_prep_attempts
UNION ALL SELECT 'exam_prep_simulated_tests',        count(*) FROM grade1112_src.exam_prep_simulated_tests
UNION ALL SELECT 'exam_prep_simulated_test_answers', count(*) FROM grade1112_src.exam_prep_simulated_test_answers
UNION ALL SELECT 'study_plans',                      count(*) FROM grade1112_src.study_plans
UNION ALL SELECT 'study_plan_tasks',                 count(*) FROM grade1112_src.study_plan_tasks;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP B — Create the tables on primary (they don't exist there yet) and
-- copy whatever's in them. UUID PKs — no id collision risk, straight copy.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.exam_prep_attempts (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid        NOT NULL,
    question_id        uuid        NOT NULL REFERENCES public.exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    time_taken_seconds int,
    attempted_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_epa_user     ON public.exam_prep_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_epa_question ON public.exam_prep_attempts(question_id);

CREATE TABLE IF NOT EXISTS public.exam_prep_simulated_tests (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid         NOT NULL,
    exam_type           text         NOT NULL,
    grade               text         NOT NULL,
    question_ids        jsonb        NOT NULL DEFAULT '[]',
    status              text         NOT NULL DEFAULT 'active'
                                     CHECK (status IN ('active','submitted','expired')),
    started_at          timestamptz  DEFAULT now(),
    submitted_at        timestamptz,
    duration_minutes    int          DEFAULT 180,
    score_raw           int,
    score_normalized    numeric(5,2),
    subject_scores      jsonb,
    topic_accuracy      jsonb,
    weak_topics         jsonb        DEFAULT '[]',
    time_spent_seconds  int,
    total_questions     int,
    attempted           int,
    correct             int,
    wrong               int,
    ai_recommendations  jsonb,
    created_at          timestamptz  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_epst_user   ON public.exam_prep_simulated_tests(user_id);
CREATE INDEX IF NOT EXISTS idx_epst_status ON public.exam_prep_simulated_tests(status);

CREATE TABLE IF NOT EXISTS public.exam_prep_simulated_test_answers (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id            uuid         NOT NULL REFERENCES public.exam_prep_simulated_tests(id) ON DELETE CASCADE,
    question_id        uuid         NOT NULL REFERENCES public.exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    marks_awarded      numeric(4,1),
    time_taken_seconds int,
    answered_at        timestamptz  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_epsta_test ON public.exam_prep_simulated_test_answers(test_id);

CREATE TABLE IF NOT EXISTS public.study_plans (
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
CREATE INDEX IF NOT EXISTS idx_study_plans_user_exam ON public.study_plans(user_id, exam_type);

CREATE TABLE IF NOT EXISTS public.study_plan_tasks (
  id               uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid    NOT NULL,
  exam_type        text    NOT NULL,
  plan_id          uuid    REFERENCES public.study_plans(id) ON DELETE CASCADE,
  week_number      int     NOT NULL DEFAULT 1,
  task_date        date,
  task_type        text    NOT NULL DEFAULT 'revise',
  subject          text    NOT NULL,
  topic            text    NOT NULL,
  description      text    DEFAULT '',
  duration_minutes int     DEFAULT 60,
  status           text    DEFAULT 'pending',
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_user_exam_date ON public.study_plan_tasks(user_id, exam_type, task_date);
CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_plan_id ON public.study_plan_tasks(plan_id);
CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_status ON public.study_plan_tasks(status, task_date);

ALTER TABLE public.exam_prep_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_prep_simulated_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_prep_simulated_test_answers ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_prep_attempts' AND policyname = 'service_full_epa') THEN
        EXECUTE 'CREATE POLICY "service_full_epa" ON public.exam_prep_attempts FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_prep_simulated_tests' AND policyname = 'service_full_epst') THEN
        EXECUTE 'CREATE POLICY "service_full_epst" ON public.exam_prep_simulated_tests FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_prep_simulated_test_answers' AND policyname = 'service_full_epsta') THEN
        EXECUTE 'CREATE POLICY "service_full_epsta" ON public.exam_prep_simulated_test_answers FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- Copy data — parent tables (exam_prep_simulated_tests, study_plans) first,
-- so the FK-referencing child tables (answers, tasks) don't fail.
INSERT INTO public.exam_prep_simulated_tests
    (id, user_id, exam_type, grade, question_ids, status, started_at, submitted_at,
     duration_minutes, score_raw, score_normalized, subject_scores, topic_accuracy,
     weak_topics, time_spent_seconds, total_questions, attempted, correct, wrong,
     ai_recommendations, created_at)
SELECT id, user_id, exam_type, grade, question_ids, status, started_at, submitted_at,
       duration_minutes, score_raw, score_normalized, subject_scores, topic_accuracy,
       weak_topics, time_spent_seconds, total_questions, attempted, correct, wrong,
       ai_recommendations, created_at
FROM grade1112_src.exam_prep_simulated_tests
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.study_plans
    (id, user_id, exam_type, exam_date, weeks_remaining, daily_hours, weak_topics,
     plan_json, version, generated_at, created_at)
SELECT id, user_id, exam_type, exam_date, weeks_remaining, daily_hours, weak_topics,
       plan_json, version, generated_at, created_at
FROM grade1112_src.study_plans
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.exam_prep_attempts
    (id, user_id, question_id, selected_option, is_correct, time_taken_seconds, attempted_at)
SELECT id, user_id, question_id, selected_option, is_correct, time_taken_seconds, attempted_at
FROM grade1112_src.exam_prep_attempts
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.exam_prep_simulated_test_answers
    (id, test_id, question_id, selected_option, is_correct, marks_awarded, time_taken_seconds, answered_at)
SELECT id, test_id, question_id, selected_option, is_correct, marks_awarded, time_taken_seconds, answered_at
FROM grade1112_src.exam_prep_simulated_test_answers
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.study_plan_tasks
    (id, user_id, exam_type, plan_id, week_number, task_date, task_type, subject,
     topic, description, duration_minutes, status, created_at, updated_at)
SELECT id, user_id, exam_type, plan_id, week_number, task_date, task_type, subject,
       topic, description, duration_minutes, status, created_at, updated_at
FROM grade1112_src.study_plan_tasks
ON CONFLICT (id) DO NOTHING;

-- Verify: each count must match Step A's source counts above.
SELECT 'exam_prep_attempts' AS t, count(*) FROM public.exam_prep_attempts
UNION ALL SELECT 'exam_prep_simulated_tests',        count(*) FROM public.exam_prep_simulated_tests
UNION ALL SELECT 'exam_prep_simulated_test_answers', count(*) FROM public.exam_prep_simulated_test_answers
UNION ALL SELECT 'study_plans',                      count(*) FROM public.study_plans
UNION ALL SELECT 'study_plan_tasks',                 count(*) FROM public.study_plan_tasks;
