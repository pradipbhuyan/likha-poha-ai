-- Migration: mock_test_wrong_answers
-- Stores per-question wrong answers from submitted mock tests.
-- Used to identify weak chapters and drive the retest reminder feature.

create table if not exists mock_test_wrong_answers (
    id              bigserial primary key,
    username        text        not null,
    grade           text        not null,
    mode            text        not null,
    subject         text        not null,
    chapter         text        not null,
    question_id     text,
    question        text,
    selected_answer text,
    correct_answer  text,
    options         jsonb,
    explanation     text,
    section         text,
    marks           numeric     default 1,
    created_at      timestamptz default now()
);

-- Index for fast per-student queries
create index if not exists idx_mtwа_username
    on mock_test_wrong_answers (username);

-- Index for subject/chapter aggregation
create index if not exists idx_mtwа_subject_chapter
    on mock_test_wrong_answers (username, subject, chapter);

-- Row-level security: students can only read/insert their own rows;
-- service_role bypasses RLS so the backend can do admin inserts.
alter table mock_test_wrong_answers enable row level security;

create policy "students_own_wrong_answers"
    on mock_test_wrong_answers
    for all
    using  (username = auth.jwt() ->> 'username')
    with check (username = auth.jwt() ->> 'username');
