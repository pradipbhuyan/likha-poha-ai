-- ============================================================
-- Exam Prep Center — Database Tables
-- Migration: 20260707_exam_prep_center.sql
-- ============================================================

-- exam_prep_questions
CREATE TABLE IF NOT EXISTS exam_prep_questions (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_type            text         NOT NULL CHECK (exam_type IN ('jee_main','neet_ug','cuet_ug')),
    grade                text         NOT NULL CHECK (grade IN ('Grade 11','Grade 12')),
    subject              text         NOT NULL,
    chapter              text         NOT NULL,
    topic                text         NOT NULL,
    subtopic             text,
    question_text        text         NOT NULL,
    question_latex       text,
    options_json         jsonb        NOT NULL,
    correct_option       text         NOT NULL,
    detailed_explanation text         NOT NULL,
    solution_steps_json  jsonb,
    formula_used         text,
    ncert_reference      text,
    difficulty           text         NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
    estimated_time_seconds int        DEFAULT 120,
    marks                numeric(4,1) DEFAULT 4,
    negative_marks       numeric(4,1) DEFAULT 1,
    source_type          text         NOT NULL DEFAULT 'llm_generated'
                                      CHECK (source_type IN ('ncert_derived','llm_generated','previous_year','manual')),
    status               text         NOT NULL DEFAULT 'draft'
                                      CHECK (status IN ('draft','published','archived')),
    validation_score     numeric(4,2),
    validation_errors    jsonb,
    prewarm_job_id       uuid,
    created_at           timestamptz  DEFAULT now(),
    updated_at           timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_epq_exam_subject ON exam_prep_questions(exam_type, subject);
CREATE INDEX IF NOT EXISTS idx_epq_topic       ON exam_prep_questions(topic);
CREATE INDEX IF NOT EXISTS idx_epq_status      ON exam_prep_questions(status);
CREATE INDEX IF NOT EXISTS idx_epq_chapter     ON exam_prep_questions(chapter);

-- exam_prep_attempts
CREATE TABLE IF NOT EXISTS exam_prep_attempts (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid        NOT NULL,
    question_id        uuid        NOT NULL REFERENCES exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    time_taken_seconds int,
    attempted_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_epa_user     ON exam_prep_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_epa_question ON exam_prep_attempts(question_id);

-- exam_prep_simulated_tests
CREATE TABLE IF NOT EXISTS exam_prep_simulated_tests (
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

CREATE INDEX IF NOT EXISTS idx_epst_user   ON exam_prep_simulated_tests(user_id);
CREATE INDEX IF NOT EXISTS idx_epst_status ON exam_prep_simulated_tests(status);

-- exam_prep_simulated_test_answers
CREATE TABLE IF NOT EXISTS exam_prep_simulated_test_answers (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id            uuid         NOT NULL REFERENCES exam_prep_simulated_tests(id) ON DELETE CASCADE,
    question_id        uuid         NOT NULL REFERENCES exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    marks_awarded      numeric(4,1),
    time_taken_seconds int,
    answered_at        timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_epsta_test ON exam_prep_simulated_test_answers(test_id);

-- exam_prep_prewarm_jobs
CREATE TABLE IF NOT EXISTS exam_prep_prewarm_jobs (
    id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_by          text        NOT NULL,
    exam_type             text        NOT NULL,
    grade                 text        NOT NULL,
    subject               text,
    chapter               text,
    topic                 text,
    difficulty_mix        jsonb,
    question_count        int         DEFAULT 10,
    publish_mode          text        NOT NULL DEFAULT 'draft'
                                      CHECK (publish_mode IN ('draft','auto_publish')),
    status                text        NOT NULL DEFAULT 'pending'
                                      CHECK (status IN ('pending','running','completed','failed')),
    questions_generated   int         DEFAULT 0,
    questions_validated   int         DEFAULT 0,
    questions_published   int         DEFAULT 0,
    error_message         text,
    provider              text,
    model                 text,
    started_at            timestamptz,
    completed_at          timestamptz,
    created_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eppj_status ON exam_prep_prewarm_jobs(status);
