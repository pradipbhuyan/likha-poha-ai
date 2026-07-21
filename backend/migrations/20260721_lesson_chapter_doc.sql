-- Chapter Journey documents (Phase 1)
-- One row per chapter: the validated typed-block document served by
-- GET /api/lesson/chapter-doc. Run in BOTH Supabase projects (primary and
-- the Grade 11/12 project) — grade_db_router picks the right one.

CREATE TABLE IF NOT EXISTS lesson_chapter_doc (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board       TEXT NOT NULL,
    grade       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    chapter     TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'CBSE',
    version     INT  NOT NULL DEFAULT 1,
    source      TEXT NOT NULL DEFAULT 'converted',  -- converted | prewarm_v2
    doc         JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',     -- active | stale | archived
    access_count INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chapter_doc_lookup
    ON lesson_chapter_doc (grade, subject, chapter, mode, status);
