-- ═══════════════════════════════════════════════════════════════════════════
-- CLEANUP — SUPABASE 2 (GRADE 11/12) — "Likha Poha Class 11 and 12"
-- Based on audit: top consumers are rag_chunks (252 MB, 11.5% dead!),
-- doubt_kb (113 MB), question_bank (39 MB)
--
-- Run each block ONE AT A TIME in Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════════


-- ── STEP 1: VACUUM rag_chunks — 11.5% dead rows (29+ MB wasted) ──────────
-- This is the MOST IMPACTFUL action on this DB.
-- rag_chunks has 1,729 dead rows out of 13,294 = 29 MB of wasted bloat.
-- VACUUM FULL rewrites the table and reclaims that space immediately.
-- Takes ~2–5 minutes. Run FIRST.
-- NOTE: This locks the table briefly — run during off-peak hours.
VACUUM (FULL, ANALYZE) rag_chunks;


-- ── STEP 2: VACUUM lesson_cache — 13.3% dead rows ────────────────────────
-- 282 dead rows out of 1,835 in lesson_cache.
VACUUM (FULL, ANALYZE) lesson_cache;


-- ── STEP 3: Delete stale lesson_cache rows ────────────────────────────────
-- 'stale' = lower-quality duplicate lesson steps, safe to permanently delete.
-- IMPACT: Zero — only active rows serve students.
DELETE FROM lesson_cache WHERE status = 'stale';


-- ── STEP 4: Delete never-used prewarmed doubt_kb entries ─────────────────
-- 8,717 rows · 113 MB · each row has a 1536-dim vector embedding (~8 KB)
-- Check count first:
SELECT count(*) AS will_delete
FROM doubt_kb
WHERE hit_count = 0
  AND source = 'prewarmed'
  AND created_at < now() - interval '30 days';

-- Then delete:
DELETE FROM doubt_kb
WHERE hit_count = 0
  AND source = 'prewarmed'
  AND created_at < now() - interval '30 days';


-- ── STEP 5: VACUUM doubt_kb after deletion ────────────────────────────────
VACUUM (FULL, ANALYZE) doubt_kb;


-- ── STEP 6: VACUUM rag_documents — 20.9% dead rows ───────────────────────
-- Small table (224 kB) but 93 dead rows out of 353.
VACUUM (FULL, ANALYZE) rag_documents;


-- ── STEP 7: Final database-wide vacuum ───────────────────────────────────
VACUUM ANALYZE;


-- ── OPTIONAL: Verify space recovered ─────────────────────────────────────
SELECT
    tablename AS table_name,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS total_size,
    pg_total_relation_size('public.' || tablename) AS total_bytes
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('rag_chunks', 'doubt_kb', 'question_bank', 'lesson_cache',
                    'lesson_kb', 'exam_prep_questions')
ORDER BY total_bytes DESC;


-- ── TOTAL DATABASE SIZE AFTER CLEANUP ────────────────────────────────────
SELECT pg_size_pretty(pg_database_size(current_database())) AS total_db_size;
