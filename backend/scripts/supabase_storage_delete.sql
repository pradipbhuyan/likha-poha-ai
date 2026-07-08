-- ═══════════════════════════════════════════════════════════════════════════
-- STORAGE DELETION — Run in Supabase SQL Editor
-- Deleting from storage.objects removes both the DB row AND the actual file.
-- ═══════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────
-- ON SUPABASE 2 (Likha Poha Class 11 and 12)
-- ─────────────────────────────────────────────────────────────────────────

-- STEP 1: Preview what will be deleted (run first — safe, read-only)
SELECT bucket_id, count(*) AS files,
       pg_size_pretty(sum((metadata->>'size')::bigint)) AS total_size
FROM storage.objects
WHERE bucket_id = 'lesson-audio'
GROUP BY bucket_id;

-- STEP 2: Delete ALL lesson-audio files on Supabase 2
-- Frees: 1,045 MB  |  Audio can be regenerated via Admin → Build Audio Cache
-- IMPACT: Grade 11/12 audio playback falls back to browser TTS until rebuilt.
DELETE FROM storage.objects WHERE bucket_id = 'lesson-audio';

-- STEP 3: Mark DB rows as archived so the cache layer knows audio is gone
UPDATE lesson_audio_cache SET status = 'archived' WHERE status = 'active';


-- ─────────────────────────────────────────────────────────────────────────
-- ON SUPABASE 1 (Main — Grades 1–10)
-- ─────────────────────────────────────────────────────────────────────────

-- STEP 4: Preview rag-visuals bucket (480 MB — PDF page images for visual RAG)
-- ⚠️  WARNING: Deleting rag-visuals will break visual asset display in lessons
--              for Grades 1–10 until you re-upload the PDFs.
--              Only delete if you are okay rebuilding RAG visuals later.
SELECT bucket_id, count(*) AS files,
       pg_size_pretty(sum((metadata->>'size')::bigint)) AS total_size
FROM storage.objects
WHERE bucket_id = 'rag-visuals'
GROUP BY bucket_id;

-- STEP 5 (OPTIONAL): Delete rag-visuals — only if lesson-audio deletion alone
-- is not enough. After deleting lesson-audio (1,045 MB) + DB cleanup (~150 MB),
-- you should be at ~1,130 MB. Deleting rag-visuals gets you to ~650 MB.
-- DELETE FROM storage.objects WHERE bucket_id = 'rag-visuals';

-- STEP 6 (OPTIONAL): Delete sales-collaterals (56 MB, low impact)
-- Safe to delete — these are admin/sales PDF files, not student-facing.
-- DELETE FROM storage.objects WHERE bucket_id = 'sales-collaterals';


-- ─────────────────────────────────────────────────────────────────────────
-- VERIFY AFTER DELETION
-- ─────────────────────────────────────────────────────────────────────────
SELECT bucket_id, count(*) AS files,
       pg_size_pretty(sum((metadata->>'size')::bigint)) AS remaining_size
FROM storage.objects
WHERE (metadata->>'size') IS NOT NULL
GROUP BY bucket_id
ORDER BY sum((metadata->>'size')::bigint) DESC;
