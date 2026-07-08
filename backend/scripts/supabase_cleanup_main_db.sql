-- ═══════════════════════════════════════════════════════════════════════════
-- CLEANUP — SUPABASE 1 (MAIN) — Grades 1–10
-- Based on audit: top consumers are rag_chunks (122 MB), doubt_kb (114 MB),
-- question_bank (46 MB), lesson_repair_tasks (11 MB), ai_usage_logs (10 MB)
--
-- Run each block ONE AT A TIME in Supabase SQL Editor.
-- ALL actions are safe — no student data or active content removed.
-- ═══════════════════════════════════════════════════════════════════════════


-- ── STEP 1: Delete old AI usage logs (keep last 30 days) ─────────────────
-- 44,004 rows · 10 MB · safe to delete old entries
-- Estimated saving: ~8 MB
DELETE FROM ai_usage_logs
WHERE created_at < now() - interval '30 days';


-- ── STEP 2: Delete completed/failed lesson repair tasks ───────────────────
-- 1,998 rows · 11 MB · one-off job records not needed after completion
-- Estimated saving: ~8–10 MB
DELETE FROM lesson_repair_tasks
WHERE status IN ('completed', 'failed')
  AND updated_at < now() - interval '7 days';


-- ── STEP 3: Delete stale lesson_cache rows ────────────────────────────────
-- 2,395 rows · 8 MB · 10.5% dead rows
-- 'stale' = lower-quality duplicates superseded by better cached content.
-- IMPACT: Zero — only active rows serve students.
DELETE FROM lesson_cache WHERE status = 'stale';


-- ── STEP 4: Delete never-used prewarmed doubt_kb entries ─────────────────
-- 13,987 rows · 114 MB · each row = ~8 KB (1536-dim vector + Q&A text)
-- These are pre-warmed entries that no student ever queried.
-- IMPACT: Low — students re-trigger LLM for that specific doubt (tiny cost).
-- Run the count first to see how many will be deleted:
SELECT count(*) AS will_delete
FROM doubt_kb
WHERE hit_count = 0
  AND source = 'prewarmed'
  AND created_at < now() - interval '30 days';

-- Then run the delete:
DELETE FROM doubt_kb
WHERE hit_count = 0
  AND source = 'prewarmed'
  AND created_at < now() - interval '30 days';


-- ── STEP 5: VACUUM — reclaim space freed by all the deletes above ─────────
-- MUST be run AFTER steps 1–4. This is what physically releases disk space.
-- Takes ~1–3 minutes. Run each line separately.

VACUUM (FULL, ANALYZE) ai_usage_logs;
VACUUM (FULL, ANALYZE) lesson_repair_tasks;
VACUUM (FULL, ANALYZE) lesson_cache;
VACUUM (FULL, ANALYZE) doubt_kb;

-- Final full-database vacuum to update statistics:
VACUUM ANALYZE;


-- ── OPTIONAL: Check how much space was reclaimed ──────────────────────────
SELECT
    tablename AS table_name,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS total_size,
    pg_total_relation_size('public.' || tablename) AS total_bytes
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('ai_usage_logs', 'lesson_repair_tasks', 'lesson_cache', 'doubt_kb',
                    'rag_chunks', 'question_bank')
ORDER BY total_bytes DESC;
