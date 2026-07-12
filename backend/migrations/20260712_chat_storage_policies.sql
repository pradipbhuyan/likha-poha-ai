-- ============================================================
-- 20260712_chat_storage_policies.sql
-- Storage RLS policies for the chat-attachments bucket.
-- Run AFTER creating the bucket in Supabase Dashboard → Storage.
-- Idempotent — safe to run multiple times.
-- ============================================================

-- Allow any authenticated user to upload files to the chat-attachments bucket
DROP POLICY IF EXISTS "chat_attachments_insert" ON storage.objects;
CREATE POLICY "chat_attachments_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'chat-attachments');

-- Allow any authenticated user to read/download files from the chat-attachments bucket
DROP POLICY IF EXISTS "chat_attachments_select" ON storage.objects;
CREATE POLICY "chat_attachments_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (bucket_id = 'chat-attachments');

-- Allow users to delete their own uploaded files (optional, for future use)
DROP POLICY IF EXISTS "chat_attachments_delete" ON storage.objects;
CREATE POLICY "chat_attachments_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'chat-attachments'
        AND auth.uid()::text = split_part(name, '_', 1)
    );

-- Verify
SELECT policyname, cmd, roles
FROM pg_policies
WHERE tablename = 'objects'
  AND policyname LIKE 'chat_attachments%';
