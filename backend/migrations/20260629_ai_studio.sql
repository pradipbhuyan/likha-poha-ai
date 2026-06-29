-- ─────────────────────────────────────────────────────────────────────────────
-- Admin AI Studio — Database Migration
-- Run in Supabase SQL Editor (admin / service_role access required)
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. AI Provider Configs ────────────────────────────────────────────────────
-- Stores per-provider configuration.  API keys are NEVER stored here —
-- they remain in admin_settings.ai_settings.  This table stores the
-- provider metadata, connection params, and feature flags only.

CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    provider_key  TEXT NOT NULL UNIQUE,  -- openai | groq | gemini | cerebras | sambanova | venice | ollama_cloud | ollama_local | anthropic
    display_name  TEXT NOT NULL,
    is_enabled    BOOLEAN NOT NULL DEFAULT true,
    is_primary    BOOLEAN NOT NULL DEFAULT false,
    is_fallback   BOOLEAN NOT NULL DEFAULT false,
    base_url      TEXT,                  -- for Ollama/custom endpoints
    default_model TEXT,
    temperature   NUMERIC(3,2) DEFAULT 0.4,
    max_tokens    INTEGER DEFAULT 4096,
    timeout_s     INTEGER DEFAULT 60,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 2. AI Model Profiles ───────────────────────────────────────────────────────
-- Feature → provider/model mapping.  Allows each platform feature to use
-- a different provider/model without touching application code.

CREATE TABLE IF NOT EXISTS ai_model_profiles (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    feature_key       TEXT NOT NULL UNIQUE,
    -- Feature keys: lesson_repair | lesson_prewarm | formula_generation |
    --               formula_review | mcq_generation | lesson_quality_review |
    --               ask_doubt | ai_tutor | summary_generation | common_mistakes
    display_name      TEXT NOT NULL,
    provider_key      TEXT NOT NULL DEFAULT 'openai',
    model             TEXT NOT NULL DEFAULT 'gpt-4.1-nano',
    temperature       NUMERIC(3,2) DEFAULT 0.4,
    max_tokens        INTEGER DEFAULT 4096,
    fallback_provider TEXT,
    fallback_model    TEXT,
    is_enabled        BOOLEAN NOT NULL DEFAULT true,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default feature profiles
INSERT INTO ai_model_profiles (feature_key, display_name, provider_key, model) VALUES
    ('lesson_repair',          'Lesson Repair',           'openai', 'gpt-4.1-nano'),
    ('lesson_prewarm',         'Lesson Prewarming',        'openai', 'gpt-4.1-nano'),
    ('formula_generation',     'Formula Generation',      'openai', 'gpt-4.1-nano'),
    ('formula_review',         'Formula Review',          'openai', 'gpt-4.1-nano'),
    ('mcq_generation',         'MCQ Generation',          'openai', 'gpt-4.1-nano'),
    ('lesson_quality_review',  'Lesson Quality Review',   'openai', 'gpt-4.1-nano'),
    ('ask_doubt',              'Ask Doubt',               'openai', 'gpt-4.1-nano'),
    ('ai_tutor',               'AI Tutor',                'openai', 'gpt-4.1-nano'),
    ('summary_generation',     'Summary Generation',      'openai', 'gpt-4.1-nano'),
    ('common_mistakes',        'Common Mistakes',         'openai', 'gpt-4.1-nano')
ON CONFLICT (feature_key) DO NOTHING;

-- ── 3. AI Prompt Templates ────────────────────────────────────────────────────
-- Master prompt template rows (one per feature).

CREATE TABLE IF NOT EXISTS ai_prompt_templates (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    feature_key     TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    description     TEXT,
    active_version  INTEGER NOT NULL DEFAULT 1,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 4. AI Prompt Template Versions ───────────────────────────────────────────
-- Each edit creates a new version row. Active version determined by
-- ai_prompt_templates.active_version.

CREATE TABLE IF NOT EXISTS ai_prompt_template_versions (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    template_id       TEXT NOT NULL REFERENCES ai_prompt_templates(id) ON DELETE CASCADE,
    version_number    INTEGER NOT NULL,
    system_prompt     TEXT NOT NULL DEFAULT '',
    user_prompt       TEXT NOT NULL DEFAULT '',
    change_summary    TEXT,
    created_by        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (template_id, version_number)
);

-- ── 5. AI Generation Jobs ─────────────────────────────────────────────────────
-- Tracks all AI-triggered generation jobs for the Jobs tab.

CREATE TABLE IF NOT EXISTS ai_generation_jobs (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    job_type        TEXT NOT NULL,
    -- job_type: lesson_repair | lesson_prewarm | formula_prewarm | mcq_generation | quality_review
    status          TEXT NOT NULL DEFAULT 'queued',
    -- status: queued | running | completed | failed | cancelled
    provider_key    TEXT,
    model_used      TEXT,
    total_items     INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    failed_items    INTEGER DEFAULT 0,
    validation_score NUMERIC(5,2),
    published_count INTEGER DEFAULT 0,
    draft_count     INTEGER DEFAULT 0,
    error_summary   TEXT,
    metadata        JSONB,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 6. AI Usage Events ────────────────────────────────────────────────────────
-- Optional finer-grained usage tracking.
-- Note: ai_usage_logs already exists in the platform; this table adds
-- provider-level aggregation and cost tracking by feature.
-- If ai_usage_logs already covers your needs, you may skip this table.

CREATE TABLE IF NOT EXISTS ai_usage_events (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    feature_key       TEXT,
    provider_key      TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    estimated_cost    NUMERIC(10,8) DEFAULT 0,
    latency_ms        INTEGER,
    success           BOOLEAN DEFAULT true,
    error_code        TEXT,
    username          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast usage aggregation
CREATE INDEX IF NOT EXISTS idx_ai_usage_events_created ON ai_usage_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_events_provider ON ai_usage_events(provider_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_events_feature ON ai_usage_events(feature_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_generation_jobs_status ON ai_generation_jobs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_generation_jobs_type ON ai_generation_jobs(job_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_prompt_versions_template ON ai_prompt_template_versions(template_id, version_number);

-- ── updated_at triggers ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_ai_studio_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DO $$ BEGIN
    CREATE TRIGGER trg_ai_provider_configs_updated
        BEFORE UPDATE ON ai_provider_configs
        FOR EACH ROW EXECUTE FUNCTION update_ai_studio_timestamp();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_ai_model_profiles_updated
        BEFORE UPDATE ON ai_model_profiles
        FOR EACH ROW EXECUTE FUNCTION update_ai_studio_timestamp();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_ai_prompt_templates_updated
        BEFORE UPDATE ON ai_prompt_templates
        FOR EACH ROW EXECUTE FUNCTION update_ai_studio_timestamp();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_ai_generation_jobs_updated
        BEFORE UPDATE ON ai_generation_jobs
        FOR EACH ROW EXECUTE FUNCTION update_ai_studio_timestamp();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- RLS: Admin-only access (apply after table creation)
-- ALTER TABLE ai_provider_configs    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_model_profiles      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_prompt_templates    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_prompt_template_versions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_generation_jobs     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_usage_events        ENABLE ROW LEVEL SECURITY;
-- (All access via service_role / admin_client — no anon-key access needed)
