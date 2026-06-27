-- ─────────────────────────────────────────────────────────────────────────────
-- 20260627_parent_notifications.sql
-- Parent Notifications table for Parent Experience Phase 2
-- Idempotent: all objects use IF NOT EXISTS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS parent_notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    child_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    type            TEXT NOT NULL CHECK (type IN (
                        'plan_expiring','plan_expired','child_inactive',
                        'mock_test_completed','low_mock_score','strong_improvement',
                        'recommendation','feature_locked','payment_failed',
                        'upgrade_suggestion','general'
                    )),
    title           TEXT NOT NULL,
    message         TEXT NOT NULL DEFAULT '',
    severity        TEXT NOT NULL DEFAULT 'info'
                        CHECK (severity IN ('critical','warning','info','success')),
    status          TEXT NOT NULL DEFAULT 'unread'
                        CHECK (status IN ('unread','read')),
    -- sanitized metadata: never contains secrets, tokens, raw audit data
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_parent_notif_parent_id  ON parent_notifications (parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_notif_child_id   ON parent_notifications (child_id);
CREATE INDEX IF NOT EXISTS idx_parent_notif_status     ON parent_notifications (status);
CREATE INDEX IF NOT EXISTS idx_parent_notif_created_at ON parent_notifications (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_parent_notif_type       ON parent_notifications (type);
