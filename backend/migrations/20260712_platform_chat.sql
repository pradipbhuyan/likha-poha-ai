-- ============================================================
-- 20260712_platform_chat.sql
-- Platform user-to-user chat (teacher↔student, parent↔teacher)
-- Idempotent — safe to run multiple times.
-- ============================================================

-- ── 1. Chat rooms ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_rooms (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_type        TEXT NOT NULL DEFAULT 'teacher_student'
                         CHECK (room_type IN ('teacher_student','parent_teacher','admin_user')),
    participant_a_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    participant_b_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active        BOOL NOT NULL DEFAULT TRUE,
    UNIQUE (participant_a_id, participant_b_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_rooms_participant_a ON chat_rooms (participant_a_id);
CREATE INDEX IF NOT EXISTS idx_chat_rooms_participant_b ON chat_rooms (participant_b_id);
CREATE INDEX IF NOT EXISTS idx_chat_rooms_last_msg ON chat_rooms (last_message_at DESC);

-- ── 2. Chat messages ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id          UUID NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    sender_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content          TEXT,                          -- nullable for attachment-only messages
    message_type     TEXT NOT NULL DEFAULT 'text'
                         CHECK (message_type IN ('text','image','voice','file')),
    attachment_url   TEXT,                          -- Supabase Storage signed URL
    attachment_name  TEXT,
    attachment_size  INTEGER,                       -- bytes
    attachment_mime  TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at          TIMESTAMPTZ,                   -- NULL = unread by recipient
    deleted_at       TIMESTAMPTZ,                   -- soft delete
    expires_at       TIMESTAMPTZ                    -- set by retention policy
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_room   ON chat_messages (room_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sender ON chat_messages (sender_id);

-- ── 3. Row Level Security ─────────────────────────────────────────────────────
ALTER TABLE chat_rooms    ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Participants can see their own rooms
DROP POLICY IF EXISTS chat_rooms_participants ON chat_rooms;
CREATE POLICY chat_rooms_participants ON chat_rooms
    FOR SELECT USING (
        auth.uid() = participant_a_id OR auth.uid() = participant_b_id
    );

-- Participants can see messages in their rooms
DROP POLICY IF EXISTS chat_messages_participants ON chat_messages;
CREATE POLICY chat_messages_participants ON chat_messages
    FOR SELECT USING (
        deleted_at IS NULL AND
        room_id IN (
            SELECT id FROM chat_rooms
            WHERE participant_a_id = auth.uid() OR participant_b_id = auth.uid()
        )
    );

-- Participants can insert messages into their rooms
DROP POLICY IF EXISTS chat_messages_insert ON chat_messages;
CREATE POLICY chat_messages_insert ON chat_messages
    FOR INSERT WITH CHECK (
        sender_id = auth.uid() AND
        room_id IN (
            SELECT id FROM chat_rooms
            WHERE (participant_a_id = auth.uid() OR participant_b_id = auth.uid())
            AND is_active = TRUE
        )
    );

-- Participants can update read_at on messages they received
DROP POLICY IF EXISTS chat_messages_mark_read ON chat_messages;
CREATE POLICY chat_messages_mark_read ON chat_messages
    FOR UPDATE USING (
        sender_id != auth.uid() AND
        room_id IN (
            SELECT id FROM chat_rooms
            WHERE participant_a_id = auth.uid() OR participant_b_id = auth.uid()
        )
    );

-- ── 4. Enable Realtime on chat_messages ───────────────────────────────────────
-- Run in Supabase SQL Editor (requires superuser):
-- ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
--
-- If you prefer: enable via Supabase Dashboard → Database → Replication
-- → select chat_messages table → enable INSERT events.

-- ── 5. Storage bucket note ────────────────────────────────────────────────────
-- Create bucket 'chat-attachments' via Supabase Dashboard → Storage → New Bucket
-- Settings: Private (NOT public), max file size 10 MB
-- RLS policy: authenticated users can upload to chat-attachments/{their_user_id}/
-- Admin service_role can read/write all.
-- The backend creates signed upload/download URLs — files are never publicly accessible.

-- ── 6. Verify ────────────────────────────────────────────────────────────────
SELECT 'chat_rooms'    AS tbl, COUNT(*) AS rows FROM chat_rooms
UNION ALL
SELECT 'chat_messages' AS tbl, COUNT(*) AS rows FROM chat_messages;
