-- ============================================================
-- Migration: match_rag_chunks — eliminate N+1 query pattern
-- Apply to: BOTH Supabase databases
--   Supabase 1 (primary):   dpivlbbyzlbpwnwgajso  (Grades 1–10)
--   Supabase 2 (grade11/12): sjfjyzaaypfzyfhhggqw (Grades 11–12)
--
-- Purpose:
--   The old function returned only chunk fields. Python then made
--   one rag_documents query PER chunk (N+1 pattern) to get board,
--   title, subject, chapter. With 60 chunks per call × 11,000 calls
--   this generated ~8 GB of Supabase egress in one billing cycle.
--
--   This migration adds doc_board, doc_title, doc_subject, doc_chapter,
--   doc_grade to the RETURNS TABLE so one RPC replaces 61 DB calls.
--
-- How to apply:
--   1. Open Supabase Dashboard → SQL Editor
--   2. Paste this entire file
--   3. Click Run
--   4. Repeat for the second Supabase project
--
-- Backward compatibility:
--   The Python code (rag_service.py) checks for "doc_board" in the
--   response. Until this SQL is applied, it falls back to the old
--   N+1 path automatically. No downtime or coordination needed.
-- ============================================================

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
    similarity  FLOAT,
    -- Document metadata (eliminates N+1 rag_documents queries in Python)
    doc_title   TEXT,
    doc_board   TEXT,
    doc_subject TEXT,
    doc_chapter TEXT,
    doc_grade   TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        rc.id,
        rc.document_id,
        rc.chunk_text,
        rc.chunk_index,
        1 - (rc.embedding <=> query_embedding) AS similarity,
        rd.title   AS doc_title,
        rd.board   AS doc_board,
        rd.subject AS doc_subject,
        rd.chapter AS doc_chapter,
        rd.grade   AS doc_grade
    FROM   rag_chunks    rc
    JOIN   rag_documents rd ON rd.id = rc.document_id
    WHERE  (filter_grade   IS NULL OR rd.grade   = filter_grade)
      AND  (filter_subject IS NULL OR rd.subject = filter_subject)
      AND  (filter_chapter IS NULL OR rd.chapter = filter_chapter)
    ORDER  BY rc.embedding <=> query_embedding
    LIMIT  match_count;
END; $$;

-- Verify it works (should return rows if you have RAG content):
-- SELECT id, chunk_text, doc_board, doc_title FROM match_rag_chunks(
--     array_fill(0::float, ARRAY[1536])::vector,
--     3, NULL, NULL, NULL
-- );
