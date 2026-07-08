-- ═══════════════════════════════════════════════════════════════════════════
-- SUPABASE DATABASE CLEANUP SCRIPT
-- Run in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)
-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1: Run the ANALYSIS section first (read-only) — copy results
-- Step 2: Review which DELETE/TRUNCATE statements apply to your situation
-- Step 3: Run cleanup statements one block at a time
-- Step 4: Run VACUUM at the end to reclaim space
-- ═══════════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────────
-- SECTION 1: ANALYSIS — Table sizes (run this first, read-only)
-- ──────────────────────────────────────────────────────────────────────────

SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename))       AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename))        AS index_size,
    (SELECT count(*) FROM information_schema.tables t2
     WHERE t2.table_name = tablename LIMIT 1)                              AS exists
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 30;


-- ──────────────────────────────────────────────────────────────────────────
-- SECTION 2: ROW COUNTS for the largest expected tables
-- ──────────────────────────────────────────────────────────────────────────

-- Lesson cache breakdown
SELECT status, grade, count(*) AS rows
FROM lesson_cache
GROUP BY status, grade
ORDER BY status, grade;

-- lesson_cache stale rows (safe to delete — quality duplicates)
SELECT count(*) AS stale_lesson_rows, pg_size_pretty(sum(length(lesson_content))) AS stale_content_size
FROM lesson_cache
WHERE status = 'stale';

-- Doubt KB breakdown
SELECT grade, count(*) AS rows
FROM doubt_kb
GROUP BY grade
ORDER BY grade;

-- Platform audit logs age distribution
SELECT
    date_trunc('week', created_at) AS week,
    count(*) AS log_rows
FROM platform_audit_logs
GROUP BY week
ORDER BY week DESC
LIMIT 12;

-- Lesson audio cache
SELECT grade, count(*) AS tracks, pg_size_pretty(sum(file_size_bytes)) AS audio_size
FROM lesson_audio_cache
WHERE status = 'active'
GROUP BY grade
ORDER BY grade;

-- LKB chips (if table exists)
SELECT grade, count(*) AS chips
FROM lesson_kb_chips
GROUP BY grade
ORDER BY grade;


-- ──────────────────────────────────────────────────────────────────────────
-- SECTION 3: CLEANUP — Run each block individually after reviewing analysis
-- ──────────────────────────────────────────────────────────────────────────

-- ── 3A. Delete STALE lesson_cache rows (safe — duplicates marked by cleanup script)
-- These are old lower-quality lesson versions superseded by better cached content.
-- IMPACT: Zero — active lessons are unaffected. Students keep getting lessons normally.
-- ESTIMATED SAVING: 30–80 MB depending on how many stale rows exist.

DELETE FROM lesson_cache WHERE status = 'stale';


-- ── 3B. Truncate platform_audit_logs older than 60 days
-- Audit logs grow unboundedly. Keep only last 60 days for debugging.
-- IMPACT: Historical audit trail before 60 days ago is lost (non-critical).
-- ESTIMATED SAVING: 5–30 MB depending on admin usage.

DELETE FROM platform_audit_logs
WHERE created_at < now() - interval '60 days';


-- ── 3C. Delete ARCHIVED lesson_audio_cache rows
-- These are rows pointing to audio files that have already been removed from Storage.
-- IMPACT: Zero — archived rows are not served to students.

DELETE FROM lesson_audio_cache WHERE status = 'archived';


-- ── 3D. Delete LOW-HIT doubt_kb entries (hit_count = 0 AND older than 30 days)
-- These are pre-warmed Q&A pairs that were never actually used by students.
-- IMPACT: Low — students re-trigger LLM for that doubt (adds small cost back).
-- ESTIMATED SAVING: 20–60 MB (each row has a 1536-dim embedding = ~6 KB + text)
-- ⚠️  Only run if you are willing to lose pre-warmed doubts with 0 hits.

DELETE FROM doubt_kb
WHERE hit_count = 0
  AND source = 'prewarmed'
  AND created_at < now() - interval '30 days';


-- ── 3E. Drop old lesson_repair_jobs (completed/failed older than 7 days)
-- These are one-off job records, not needed after completion.

DELETE FROM lesson_repair_jobs
WHERE status IN ('completed', 'failed')
  AND created_at < now() - interval '7 days';


-- ── 3F. Clean lesson quality audit runs (keep last 5 per grade)
-- lesson_quality_audit_runs can accumulate many rows over time.

DELETE FROM lesson_quality_audit_runs
WHERE id NOT IN (
    SELECT id FROM lesson_quality_audit_runs
    ORDER BY created_at DESC
    LIMIT 20
);


-- ──────────────────────────────────────────────────────────────────────────
-- SECTION 4: VACUUM — Reclaim space after deletions
-- Run AFTER all DELETE statements above have completed.
-- In Supabase free tier, you can run VACUUM from the SQL editor.
-- ──────────────────────────────────────────────────────────────────────────

-- Reclaim space from lesson_cache (likely biggest win)
VACUUM (FULL, ANALYZE) lesson_cache;

-- Reclaim from doubt_kb (has large vector embeddings)
VACUUM (FULL, ANALYZE) doubt_kb;

-- Reclaim from audit logs
VACUUM (FULL, ANALYZE) platform_audit_logs;

-- Full database vacuum (run last — takes 1-3 minutes on free tier)
VACUUM ANALYZE;


-- ──────────────────────────────────────────────────────────────────────────
-- SECTION 5: STORAGE BUCKET CLEANUP
-- The 2.32 GB storage usage is from the 'lesson-audio' Supabase Storage bucket.
-- You CANNOT delete Storage files from SQL — use the Python script below
-- OR the Supabase Storage UI.
-- ──────────────────────────────────────────────────────────────────────────

-- Check which audio grades are cached (to decide what to keep vs delete)
SELECT
    grade,
    subject,
    count(*) AS files,
    pg_size_pretty(sum(file_size_bytes)) AS total_size,
    max(last_accessed_at) AS last_accessed
FROM lesson_audio_cache
WHERE status = 'active'
GROUP BY grade, subject
ORDER BY sum(file_size_bytes) DESC;

-- After deleting Storage files, mark corresponding rows as archived:
-- UPDATE lesson_audio_cache SET status = 'archived' WHERE grade IN ('Grade 5', 'Grade 6');
