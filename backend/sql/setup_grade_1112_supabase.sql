-- ============================================================
-- Grade 11 & 12 Supabase Schema
-- Run this entire file in the SQL Editor of the SECOND Supabase
-- project (Settings → SQL Editor → New query → paste → Run).
--
-- Tables created:
--   rag_documents, rag_chunks, match_rag_chunks RPC
--   doubt_kb, match_doubt_kb RPC, get_doubt_kb_suggestions RPC
--   lesson_cache, question_bank
-- ============================================================

-- 0. pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────
-- 1. RAG Documents
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rag_documents (
    id          BIGSERIAL   PRIMARY KEY,
    uploaded_by TEXT,
    board       TEXT        NOT NULL DEFAULT 'CBSE',
    grade       TEXT,
    subject     TEXT,
    chapter     TEXT,
    title       TEXT,
    source_type TEXT        DEFAULT 'text',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 2. RAG Chunks (vector embeddings)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rag_chunks (
    id          BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_text  TEXT,
    chunk_index INTEGER,
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS rag_documents_lookup_idx
    ON rag_documents (board, grade, subject, chapter);

-- ─────────────────────────────────────────────────────────────
-- 3. match_rag_chunks RPC
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION match_rag_chunks(
    query_embedding vector(1536),
    match_count     INT  DEFAULT 5,
    filter_grade    TEXT DEFAULT NULL,
    filter_subject  TEXT DEFAULT NULL,
    filter_chapter  TEXT DEFAULT NULL
)
RETURNS TABLE (
    id          BIGINT,
    document_id BIGINT,
    chunk_text  TEXT,
    chunk_index INTEGER,
    similarity  FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT rc.id, rc.document_id, rc.chunk_text, rc.chunk_index,
           1 - (rc.embedding <=> query_embedding) AS similarity
    FROM   rag_chunks    rc
    JOIN   rag_documents rd ON rd.id = rc.document_id
    WHERE  (filter_grade   IS NULL OR rd.grade   = filter_grade)
      AND  (filter_subject IS NULL OR rd.subject = filter_subject)
      AND  (filter_chapter IS NULL OR rd.chapter = filter_chapter)
    ORDER  BY rc.embedding <=> query_embedding
    LIMIT  match_count;
END; $$;

-- ─────────────────────────────────────────────────────────────
-- 4. RLS for RAG tables
-- ─────────────────────────────────────────────────────────────
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_full_docs"   ON rag_documents FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_full_chunks" ON rag_chunks    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "anon_read_docs"      ON rag_documents FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_chunks"    ON rag_chunks    FOR SELECT TO anon USING (true);

-- ─────────────────────────────────────────────────────────────
-- 5. Doubt Knowledge Base
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS doubt_kb (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    grade       TEXT        NOT NULL,
    board       TEXT        NOT NULL DEFAULT 'CBSE',
    mode        TEXT        NOT NULL DEFAULT 'CBSE',
    subject     TEXT        NOT NULL,
    chapter     TEXT,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    embedding   vector(1536),
    source      TEXT        NOT NULL DEFAULT 'llm',
    hit_count   INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_hit_at TIMESTAMPTZ,
    status      TEXT        NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS doubt_kb_embedding_idx
    ON doubt_kb USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS doubt_kb_grade_subject_idx
    ON doubt_kb (grade, subject, chapter);

CREATE OR REPLACE FUNCTION match_doubt_kb(
    query_embedding      vector(1536),
    match_count          INT   DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.80,
    filter_grade         TEXT  DEFAULT NULL,
    filter_subject       TEXT  DEFAULT NULL,
    filter_chapter       TEXT  DEFAULT NULL,
    filter_mode          TEXT  DEFAULT NULL
)
RETURNS TABLE (
    id UUID, question TEXT, answer TEXT, subject TEXT, chapter TEXT,
    grade TEXT, source TEXT, hit_count INTEGER, similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT dk.id, dk.question, dk.answer, dk.subject, dk.chapter,
           dk.grade, dk.source, dk.hit_count,
           1 - (dk.embedding <=> query_embedding) AS similarity
    FROM   doubt_kb dk
    WHERE  dk.status = 'active'
      AND  (filter_grade   IS NULL OR dk.grade   = filter_grade)
      AND  (filter_subject IS NULL OR dk.subject = filter_subject)
      AND  (filter_chapter IS NULL OR dk.chapter = filter_chapter OR dk.chapter IS NULL)
      AND  (filter_mode    IS NULL OR dk.mode    = filter_mode)
      AND  1 - (dk.embedding <=> query_embedding) >= similarity_threshold
    ORDER  BY dk.embedding <=> query_embedding
    LIMIT  match_count;
END; $$;

CREATE OR REPLACE FUNCTION get_doubt_kb_suggestions(
    p_grade TEXT, p_subject TEXT, p_chapter TEXT,
    p_mode TEXT DEFAULT 'CBSE', p_limit INT DEFAULT 8
)
RETURNS TABLE (id UUID, question TEXT, hit_count INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT dk.id, dk.question, dk.hit_count
    FROM   doubt_kb dk
    WHERE  dk.status  = 'active'
      AND  dk.grade   = p_grade
      AND  dk.subject = p_subject
      AND  dk.mode    = p_mode
      AND  (dk.chapter = p_chapter OR dk.chapter IS NULL)
    ORDER  BY dk.hit_count DESC, dk.created_at DESC
    LIMIT  p_limit;
END; $$;

ALTER TABLE doubt_kb ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_full_dkb" ON doubt_kb FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────
-- 6. Lesson Cache
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lesson_cache (
    id                 UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    cache_key          TEXT        UNIQUE NOT NULL,
    board              TEXT        NOT NULL,
    grade              TEXT        NOT NULL,
    subject            TEXT        NOT NULL,
    chapter            TEXT        NOT NULL,
    mode               TEXT        NOT NULL,
    step_title         TEXT        NOT NULL,
    teacher_persona    TEXT        DEFAULT '',
    lesson_content     TEXT        NOT NULL,
    practice_questions JSONB       DEFAULT '[]',
    source_type        TEXT        DEFAULT 'LLM',
    status             TEXT        DEFAULT 'active',
    access_count       INTEGER     DEFAULT 1,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lesson_cache_key     ON lesson_cache (cache_key);
CREATE INDEX IF NOT EXISTS idx_lesson_cache_chapter ON lesson_cache (board, grade, subject, chapter);

ALTER TABLE lesson_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_full_lesson_cache" ON lesson_cache FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "anon_read_lesson_cache"    ON lesson_cache FOR SELECT TO anon USING (true);

-- ─────────────────────────────────────────────────────────────
-- 7. Question Bank
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_bank (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    board       TEXT        NOT NULL,
    grade       TEXT        NOT NULL,
    subject     TEXT        NOT NULL,
    chapter     TEXT        DEFAULT '',
    exam_type   TEXT        DEFAULT 'General',
    difficulty  TEXT        DEFAULT 'Medium',
    section     TEXT        DEFAULT '',
    question    TEXT        NOT NULL,
    options     JSONB       DEFAULT '{}',
    answer      TEXT        NOT NULL,
    explanation TEXT        DEFAULT '',
    marks       INTEGER     DEFAULT 1,
    status      TEXT        DEFAULT 'active',
    times_shown INTEGER     DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qbank_lookup     ON question_bank (grade, subject, chapter, difficulty, status);
CREATE INDEX IF NOT EXISTS idx_qbank_board_grade ON question_bank (board, grade, subject);

ALTER TABLE question_bank ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_full_qbank" ON question_bank FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "anon_read_qbank"    ON question_bank FOR SELECT TO anon USING (true);

-- ─────────────────────────────────────────────────────────────
-- Done. Verify with:
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public';
-- ─────────────────────────────────────────────────────────────
