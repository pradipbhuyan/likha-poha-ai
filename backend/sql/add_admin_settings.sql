-- admin_settings: key-value store for admin-managed platform configuration.
-- Currently stores the OpenAI API key and master API enabled/disabled switch.
-- Only the backend service_role key (admin_client) can read or write this table.

CREATE TABLE IF NOT EXISTS admin_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Restrict all public/anon access — backend service_role bypasses RLS.
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- Seed the default row so GET /api/admin-control/ai-settings always returns data.
INSERT INTO admin_settings (key, value)
VALUES (
    'ai_settings',
    '{"api_enabled": true, "openai_api_key": ""}'
)
ON CONFLICT (key) DO NOTHING;
