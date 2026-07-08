-- ═══════════════════════════════════════════════════════════════════════════
-- SIZE AUDIT — SUPABASE 1 (MAIN) — Grades 1–10 + all user/auth data
-- Paste into: Supabase Dashboard → [Main project] → SQL Editor → Run each query separately
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Q1: TOP 20 TABLES BY SIZE ─────────────────────────────────────────────
SELECT
    tablename                                                              AS table_name,
    pg_size_pretty(pg_total_relation_size('public.' || tablename))        AS total_size,
    pg_size_pretty(pg_relation_size('public.' || tablename))              AS data_size,
    pg_size_pretty(pg_indexes_size('public.' || tablename))               AS index_size,
    pg_total_relation_size('public.' || tablename)                        AS total_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY total_bytes DESC
LIMIT 20;


-- ── Q2: TOTAL DATABASE SIZE ───────────────────────────────────────────────
SELECT pg_size_pretty(pg_database_size(current_database())) AS total_db_size,
       current_database() AS db_name;


-- ── Q3: LESSON CACHE ─────────────────────────────────────────────────────
SELECT status, grade, count(*) AS rows,
       pg_size_pretty(sum(length(lesson_content::text))) AS approx_text_size
FROM lesson_cache
GROUP BY status, grade
ORDER BY status, grade;


-- ── Q4: DOUBT KB ─────────────────────────────────────────────────────────
SELECT grade,
       count(*) AS total_rows,
       count(*) FILTER (WHERE embedding IS NOT NULL) AS with_embeddings,
       count(*) FILTER (WHERE hit_count = 0) AS never_used,
       count(*) FILTER (WHERE source = 'prewarmed') AS prewarmed
FROM doubt_kb
GROUP BY grade ORDER BY grade;


-- ── Q5: RAG CHUNKS + DOCUMENTS ───────────────────────────────────────────
SELECT t.tablename AS table_name,
       pg_size_pretty(pg_total_relation_size('public.' || t.tablename)) AS total_size,
       pg_size_pretty(pg_indexes_size('public.' || t.tablename)) AS index_size
FROM pg_tables t
WHERE t.schemaname = 'public'
  AND t.tablename IN ('rag_chunks', 'rag_documents')
ORDER BY pg_total_relation_size('public.' || t.tablename) DESC;


-- ── Q6: LESSON AUDIO CACHE ───────────────────────────────────────────────
SELECT grade, status, count(*) AS files,
       pg_size_pretty(sum(file_size_bytes)) AS file_size
FROM lesson_audio_cache
GROUP BY grade, status ORDER BY grade;


-- ── Q7: QUESTION BANK ────────────────────────────────────────────────────
SELECT grade, subject, count(*) AS questions
FROM question_bank
GROUP BY grade, subject ORDER BY grade, subject;


-- ── Q8: PLATFORM AUDIT LOGS ──────────────────────────────────────────────
SELECT count(*) AS total_rows,
       pg_size_pretty(pg_total_relation_size('public.platform_audit_logs')) AS table_size,
       min(created_at)::date AS oldest_entry,
       max(created_at)::date AS newest_entry
FROM platform_audit_logs;


-- ── Q9: LESSON KB (LKB chips) ────────────────────────────────────────────
SELECT grade, count(*) AS chips
FROM lesson_kb
GROUP BY grade ORDER BY grade;


-- ── Q10: DEAD TUPLE BLOAT ────────────────────────────────────────────────
SELECT relname AS table_name, n_live_tup AS live_rows, n_dead_tup AS dead_rows,
       CASE WHEN n_live_tup + n_dead_tup > 0
            THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
            ELSE 0 END AS dead_pct,
       pg_size_pretty(pg_total_relation_size('public.' || relname)) AS total_size,
       last_vacuum::date, last_autovacuum::date
FROM pg_stat_user_tables
WHERE schemaname = 'public' AND (n_dead_tup > 100 OR n_live_tup > 100)
ORDER BY n_dead_tup DESC LIMIT 15;
