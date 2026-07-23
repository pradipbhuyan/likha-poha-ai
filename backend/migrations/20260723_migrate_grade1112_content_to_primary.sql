-- ============================================================================
-- Migration: Copy Grade 11/12 content from Supabase 2 into Supabase 1 (primary)
--
-- Run this ENTIRELY inside Supabase 1 (primary, dpivlbbyzlbpwnwgajso)'s
-- SQL Editor. It reaches into Supabase 2 via postgres_fdw and pulls the six
-- content tables over. Run section by section (each "STEP" is one paste +
-- Run), checking the verification query at the end of each step before
-- moving to the next. Nothing here deletes anything from Supabase 2 — this
-- is copy-only. Cutting the app's traffic over to primary is a separate,
-- later step (change grade_db_router.py), not part of this script.
--
-- Scope (content only — no user-linked tables):
--   rag_documents, rag_chunks (+ match_rag_chunks RPC)
--   lesson_kb
--   doubt_kb (+ match_doubt_kb, get_doubt_kb_suggestions RPCs)
--   lesson_cache
--   question_bank
--   exam_prep_questions, exam_prep_prewarm_jobs
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 0 — Connect to Supabase 2 via postgres_fdw
--
-- Get Supabase 2's DIRECT (non-pooled) connection info from:
--   Supabase 2 project → Project Settings → Database → Connection string → "Direct connection"
-- It looks like: postgresql://postgres:[PASSWORD]@db.sjfjyzaaypfzyfhhggqw.supabase.co:5432/postgres
--
-- Replace the placeholders below with the real host and password, then run
-- this block. The password is only ever pasted here, in Supabase 1's own SQL
-- editor — it is never sent through this chat.
-- ────────────────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DROP SERVER IF EXISTS grade1112_remote CASCADE;

CREATE SERVER grade1112_remote
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host '<GRADE1112_DB_HOST>', port '5432', dbname 'postgres');

CREATE USER MAPPING FOR CURRENT_USER
    SERVER grade1112_remote
    OPTIONS (user 'postgres', password '<GRADE1112_DB_PASSWORD>');

DROP SCHEMA IF EXISTS grade1112_src CASCADE;
CREATE SCHEMA grade1112_src;

IMPORT FOREIGN SCHEMA public
    LIMIT TO (rag_documents, rag_chunks, lesson_kb, doubt_kb, lesson_cache,
              question_bank, exam_prep_questions, exam_prep_prewarm_jobs)
    FROM SERVER grade1112_remote INTO grade1112_src;

-- Verify the connection worked and see what we're about to copy:
SELECT 'rag_documents' AS t, count(*) FROM grade1112_src.rag_documents
UNION ALL SELECT 'rag_chunks',       count(*) FROM grade1112_src.rag_chunks
UNION ALL SELECT 'lesson_kb',        count(*) FROM grade1112_src.lesson_kb
UNION ALL SELECT 'doubt_kb',         count(*) FROM grade1112_src.doubt_kb
UNION ALL SELECT 'lesson_cache',     count(*) FROM grade1112_src.lesson_cache
UNION ALL SELECT 'question_bank',    count(*) FROM grade1112_src.question_bank
UNION ALL SELECT 'exam_prep_questions',    count(*) FROM grade1112_src.exam_prep_questions
UNION ALL SELECT 'exam_prep_prewarm_jobs', count(*) FROM grade1112_src.exam_prep_prewarm_jobs;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 1 — rag_documents + rag_chunks (BIGSERIAL ids — need remapping)
--
-- Primary already has its own Grade 1-10 rag_documents/rag_chunks rows using
-- the same BIGSERIAL sequence, so we cannot copy Supabase 2's ids as-is —
-- they'd collide. We insert fresh rows (letting primary's sequence assign
-- new ids) while temporarily tagging each new row with its old id via a
-- _legacy_id column, use that to correctly rewire rag_chunks.document_id,
-- then drop the temporary column once verified.
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.rag_documents ADD COLUMN IF NOT EXISTS _legacy_id bigint;
ALTER TABLE public.rag_chunks    ADD COLUMN IF NOT EXISTS _legacy_id bigint;

INSERT INTO public.rag_documents
    (uploaded_by, board, grade, subject, chapter, title, source_type, created_at, _legacy_id)
SELECT uploaded_by, board, grade, subject, chapter, title, source_type, created_at, id
FROM grade1112_src.rag_documents;

INSERT INTO public.rag_chunks
    (document_id, chunk_text, chunk_index, embedding, created_at, _legacy_id)
SELECT rd_new.id, src.chunk_text, src.chunk_index, src.embedding, src.created_at, src.id
FROM grade1112_src.rag_chunks src
JOIN public.rag_documents rd_new ON rd_new._legacy_id = src.document_id;

-- Verify: both counts must match Step 0's counts for these two tables, and
-- the "unmatched_chunks" count must be 0.
SELECT
    (SELECT count(*) FROM public.rag_documents WHERE _legacy_id IS NOT NULL) AS docs_copied,
    (SELECT count(*) FROM public.rag_chunks    WHERE _legacy_id IS NOT NULL) AS chunks_copied,
    (SELECT count(*) FROM grade1112_src.rag_chunks) -
        (SELECT count(*) FROM public.rag_chunks WHERE _legacy_id IS NOT NULL) AS unmatched_chunks;

-- Spot-check a few rows side by side before dropping the bridge column:
SELECT rd._legacy_id, rd.title, rd.grade, rd.subject, count(rc.id) AS chunk_count
FROM public.rag_documents rd
LEFT JOIN public.rag_chunks rc ON rc.document_id = rd.id
WHERE rd._legacy_id IS NOT NULL
GROUP BY rd._legacy_id, rd.title, rd.grade, rd.subject
ORDER BY rd._legacy_id
LIMIT 10;

-- Only after the counts above look right, drop the bridge columns:
-- ALTER TABLE public.rag_documents DROP COLUMN _legacy_id;
-- ALTER TABLE public.rag_chunks    DROP COLUMN _legacy_id;

-- Rebuild the embedding index sized for the new combined row count (replace
-- <N> with the result of `SELECT count(*) FROM public.rag_chunks`; lists is
-- commonly chosen as roughly sqrt(N) for tables in the tens/hundreds of
-- thousands of rows):
-- DROP INDEX IF EXISTS rag_chunks_embedding_idx;
-- CREATE INDEX rag_chunks_embedding_idx ON public.rag_chunks
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = <sqrt(N)>);

-- Confirm match_rag_chunks already exists on primary with the doc_* columns
-- (from 20260711_match_rag_chunks_no_n1.sql). If this returns no rows, that
-- migration was never applied here — apply it before relying on Grade 11/12
-- RAG search against primary.
SELECT routine_name FROM information_schema.routines
WHERE routine_name = 'match_rag_chunks' AND routine_schema = 'public';


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 2 — lesson_kb, doubt_kb, lesson_cache, question_bank (UUID ids —
-- globally unique, no remapping needed, straight copy keeping the same id)
-- ────────────────────────────────────────────────────────────────────────────

INSERT INTO public.lesson_kb
    (id, grade, subject, chapter, step_title, question, answer, source, hit_count,
     created_at, updated_at, status)
SELECT id, grade, subject, chapter, step_title, question, answer, source, hit_count,
       created_at, updated_at, status
FROM grade1112_src.lesson_kb
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.doubt_kb
    (id, grade, board, mode, subject, chapter, question, answer, embedding, source,
     hit_count, created_at, last_hit_at, status)
SELECT id, grade, board, mode, subject, chapter, question, answer, embedding, source,
       hit_count, created_at, last_hit_at, status
FROM grade1112_src.doubt_kb
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.lesson_cache
    (id, cache_key, board, grade, subject, chapter, mode, step_title, teacher_persona,
     lesson_content, practice_questions, source_type, status, access_count,
     created_at, last_accessed_at)
SELECT id, cache_key, board, grade, subject, chapter, mode, step_title, teacher_persona,
       lesson_content, practice_questions, source_type, status, access_count,
       created_at, last_accessed_at
FROM grade1112_src.lesson_cache
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.question_bank
    (id, board, grade, subject, chapter, exam_type, difficulty, section, question,
     options, answer, explanation, marks, status, times_shown, created_at)
SELECT id, board, grade, subject, chapter, exam_type, difficulty, section, question,
       options, answer, explanation, marks, status, times_shown, created_at
FROM grade1112_src.question_bank
ON CONFLICT (id) DO NOTHING;

-- Verify: each of these four counts must match Step 0's counts.
SELECT 'lesson_kb' AS t, count(*) FROM public.lesson_kb
UNION ALL SELECT 'doubt_kb',      count(*) FROM public.doubt_kb
UNION ALL SELECT 'lesson_cache',  count(*) FROM public.lesson_cache
UNION ALL SELECT 'question_bank', count(*) FROM public.question_bank;

-- Confirm the DKB RPCs exist on primary (they should already, since primary
-- serves Grade 1-10 doubt_kb today):
SELECT routine_name FROM information_schema.routines
WHERE routine_name IN ('match_doubt_kb', 'get_doubt_kb_suggestions')
  AND routine_schema = 'public';

-- Rebuild doubt_kb's embedding index the same way as rag_chunks above, sized
-- for the new combined row count:
-- DROP INDEX IF EXISTS doubt_kb_embedding_idx;
-- CREATE INDEX doubt_kb_embedding_idx ON public.doubt_kb
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = <sqrt(N)>);


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 3 — exam_prep_questions, exam_prep_prewarm_jobs
--
-- These tables have never existed on primary (exam_prep_service.py always
-- routed to Supabase 2 for them) — create them here first, matching
-- 20260707_exam_prep_center.sql and 20260711_exam_prep_add_sat_ielts_toefl.sql
-- exactly, then copy the data.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.exam_prep_questions (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_type            text         NOT NULL CHECK (exam_type IN
                                      ('jee_main','neet_ug','cuet_ug','sat','ielts','toefl_ibt')),
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

CREATE INDEX IF NOT EXISTS idx_epq_exam_subject ON public.exam_prep_questions(exam_type, subject);
CREATE INDEX IF NOT EXISTS idx_epq_topic       ON public.exam_prep_questions(topic);
CREATE INDEX IF NOT EXISTS idx_epq_status      ON public.exam_prep_questions(status);
CREATE INDEX IF NOT EXISTS idx_epq_chapter     ON public.exam_prep_questions(chapter);

CREATE TABLE IF NOT EXISTS public.exam_prep_prewarm_jobs (
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

CREATE INDEX IF NOT EXISTS idx_eppj_status ON public.exam_prep_prewarm_jobs(status);

ALTER TABLE public.exam_prep_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_prep_prewarm_jobs ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_prep_questions' AND policyname = 'service_full_epq') THEN
        EXECUTE 'CREATE POLICY "service_full_epq" ON public.exam_prep_questions FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_prep_prewarm_jobs' AND policyname = 'service_full_eppj') THEN
        EXECUTE 'CREATE POLICY "service_full_eppj" ON public.exam_prep_prewarm_jobs FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- Prewarm jobs first (exam_prep_questions.prewarm_job_id has no FK constraint
-- in the original schema, but insert in this order to keep it meaningful):
INSERT INTO public.exam_prep_prewarm_jobs
    (id, triggered_by, exam_type, grade, subject, chapter, topic, difficulty_mix,
     question_count, publish_mode, status, questions_generated, questions_validated,
     questions_published, error_message, provider, model, started_at, completed_at, created_at)
SELECT id, triggered_by, exam_type, grade, subject, chapter, topic, difficulty_mix,
       question_count, publish_mode, status, questions_generated, questions_validated,
       questions_published, error_message, provider, model, started_at, completed_at, created_at
FROM grade1112_src.exam_prep_prewarm_jobs
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.exam_prep_questions
    (id, exam_type, grade, subject, chapter, topic, subtopic, question_text, question_latex,
     options_json, correct_option, detailed_explanation, solution_steps_json, formula_used,
     ncert_reference, difficulty, estimated_time_seconds, marks, negative_marks, source_type,
     status, validation_score, validation_errors, prewarm_job_id, created_at, updated_at)
SELECT id, exam_type, grade, subject, chapter, topic, subtopic, question_text, question_latex,
       options_json, correct_option, detailed_explanation, solution_steps_json, formula_used,
       ncert_reference, difficulty, estimated_time_seconds, marks, negative_marks, source_type,
       status, validation_score, validation_errors, prewarm_job_id, created_at, updated_at
FROM grade1112_src.exam_prep_questions
ON CONFLICT (id) DO NOTHING;

-- Verify: both counts must match Step 0's counts.
SELECT 'exam_prep_questions' AS t, count(*) FROM public.exam_prep_questions
UNION ALL SELECT 'exam_prep_prewarm_jobs', count(*) FROM public.exam_prep_prewarm_jobs;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 4 — Cleanup (only after every count above has been checked and
-- matches, and you have separately confirmed a full pg_dump backup of
-- Supabase 2 exists somewhere durable)
-- ────────────────────────────────────────────────────────────────────────────

-- DROP SCHEMA IF EXISTS grade1112_src CASCADE;
-- DROP SERVER IF EXISTS grade1112_remote CASCADE;
-- (Rotating Supabase 2's database password afterward is good hygiene, since
-- it was typed into Supabase 1's SQL editor during this migration.)
