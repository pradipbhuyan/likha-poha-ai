-- Run this on BOTH Supabase projects — shows bucket sizes in one result
SELECT
    bucket_id,
    count(*)                                               AS file_count,
    pg_size_pretty(sum((metadata->>'size')::bigint))       AS total_size,
    round(sum((metadata->>'size')::bigint) / 1024.0 / 1024.0, 1) AS size_mb
FROM storage.objects
WHERE (metadata->>'size') IS NOT NULL
GROUP BY bucket_id
ORDER BY sum((metadata->>'size')::bigint) DESC;
