-- ─────────────────────────────────────────────────────────────────────────────
-- lesson_audio_cache — pre-warmed TTS audio URLs
--
-- Stores Supabase Storage public URLs for Edge TTS audio generated from
-- pre-warmed lesson content. Cache key mirrors lesson_cache: grade + subject +
-- chapter + step_title + voice + rate.
--
-- POC scope: Grade 9 English (155 lessons, ~240 MB, ~48 min generation)
-- Bucket:    lesson-audio (public, Supabase Storage)
-- TTS:       Microsoft Edge TTS (edge-tts), voice en-IN-NeerjaNeural, free
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lesson_audio_cache (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key       text UNIQUE NOT NULL,        -- hash of grade|subject|chapter|step_title|voice|rate
    grade           text NOT NULL,
    subject         text NOT NULL,
    chapter         text NOT NULL,
    step_title      text NOT NULL,
    voice           text NOT NULL DEFAULT 'en-IN-NeerjaNeural',
    rate            text NOT NULL DEFAULT '+0%',
    audio_url       text NOT NULL,               -- Supabase Storage public URL
    file_path       text NOT NULL,               -- path inside bucket e.g. grade-9/english/ch1/step1.mp3
    file_size_bytes integer,
    duration_seconds real,
    status          text NOT NULL DEFAULT 'active',  -- active | archived
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_accessed_at timestamptz
);

-- Fast lookup by lesson context
CREATE INDEX IF NOT EXISTS lesson_audio_cache_lookup_idx
    ON lesson_audio_cache (grade, subject, chapter, step_title, voice, rate);

-- RLS: admins read/write; authenticated users read
ALTER TABLE lesson_audio_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin full access on lesson_audio_cache"
    ON lesson_audio_cache
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
              AND profiles.role = 'admin'
        )
    );

CREATE POLICY "authenticated users can read lesson_audio_cache"
    ON lesson_audio_cache
    FOR SELECT
    TO authenticated
    USING (status = 'active');
