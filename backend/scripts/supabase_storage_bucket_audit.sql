-- ═══════════════════════════════════════════════════════════════════════════
-- SUPABASE STORAGE BUCKET SIZE AUDIT
-- Run on BOTH Supabase projects in SQL Editor.
-- This queries the internal storage.objects table — safe, read-only.
-- ═══════════════════════════════════════════════════════════════════════════


-- ── Q1: Storage bucket sizes — which bucket is using the most space ───────
SELECT
    bucket_id,
    count(*)                                                            AS file_count,
    pg_size_pretty(sum((metadata->>'size')::bigint))                    AS total_size,
    sum((metadata->>'size')::bigint)                                    AS total_bytes
FROM storage.objects
WHERE (metadata->>'size') IS NOT NULL
GROUP BY bucket_id
ORDER BY total_bytes DESC;


-- ── Q2: Total storage used across ALL buckets ─────────────────────────────
SELECT
    count(*)                                                            AS total_files,
    pg_size_pretty(sum((metadata->>'size')::bigint))                    AS total_storage_used
FROM storage.objects
WHERE (metadata->>'size') IS NOT NULL;


-- ── Q3: Breakdown by bucket + folder (top-level path prefix) ─────────────
-- Shows which sub-folder in each bucket is using the most space.
SELECT
    bucket_id,
    split_part(name, '/', 1)                                            AS folder,
    count(*)                                                            AS files,
    pg_size_pretty(sum((metadata->>'size')::bigint))                    AS size
FROM storage.objects
WHERE (metadata->>'size') IS NOT NULL
GROUP BY bucket_id, split_part(name, '/', 1)
ORDER BY sum((metadata->>'size')::bigint) DESC
LIMIT 30;


-- ── Q4: List all storage buckets configured ───────────────────────────────
SELECT id AS bucket_name, public, created_at, updated_at
FROM storage.buckets
ORDER BY created_at;
