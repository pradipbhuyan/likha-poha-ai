-- Fix: DKB IVFFlat index causing false misses for semantic search
-- ================================================================
-- Problem: The IVFFlat index with lists=100 and default probes=1
-- only searches 1% of the index per query. With ~1000 DKB entries,
-- this causes true matches (e.g. "what is a cell" vs "What is a cell?")
-- to be missed even when cosine similarity is 0.75+.
--
-- Fix: Drop the approximate IVFFlat index and let PostgreSQL use a
-- sequential scan. With ≤10,000 rows a seq scan is fast (< 5ms)
-- and guarantees 100% recall — no more false misses.
--
-- Run this in the Supabase SQL editor.
-- ================================================================

-- 1. Drop the approximate IVFFlat index
DROP INDEX IF EXISTS doubt_kb_embedding_idx;

-- 2. Update match_doubt_kb to use exact cosine search (no index = seq scan)
CREATE OR REPLACE FUNCTION match_doubt_kb(
    query_embedding vector(1536),
    match_count     INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.50,
    filter_grade    TEXT DEFAULT NULL,
    filter_subject  TEXT DEFAULT NULL,
    filter_chapter  TEXT DEFAULT NULL,
    filter_mode     TEXT DEFAULT NULL
)
RETURNS TABLE (
    id          UUID,
    question    TEXT,
    answer      TEXT,
    subject     TEXT,
    chapter     TEXT,
    grade       TEXT,
    source      TEXT,
    hit_count   INTEGER,
    similarity  FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- No IVFFlat index → PostgreSQL uses a sequential scan = exact search
    -- For < 10,000 rows this runs in < 5ms on Supabase edge infrastructure
    RETURN QUERY
    SELECT
        dk.id,
        dk.question,
        dk.answer,
        dk.subject,
        dk.chapter,
        dk.grade,
        dk.source,
        dk.hit_count,
        1 - (dk.embedding <=> query_embedding) AS similarity
    FROM doubt_kb dk
    WHERE
        dk.status = 'active'
        AND (filter_grade   IS NULL OR dk.grade   = filter_grade)
        AND (filter_subject IS NULL OR dk.subject = filter_subject)
        AND (filter_chapter IS NULL OR dk.chapter = filter_chapter OR dk.chapter IS NULL)
        AND (filter_mode    IS NULL OR dk.mode    = filter_mode)
        AND 1 - (dk.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY dk.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 3. Verify: "what is a cell" should now find "What is a cell?" at ~0.75
-- Run this test query after applying the fix:
-- SELECT question, 1 - (embedding <=> (
--   SELECT embedding FROM doubt_kb WHERE question = 'What is a cell?' LIMIT 1
-- )) AS sim
-- FROM doubt_kb WHERE grade = 'Grade 9'
-- ORDER BY sim DESC LIMIT 5;
