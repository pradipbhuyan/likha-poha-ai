# AI and Content Platform

## AI Principles

AI features should support learning, not replace structured pedagogy. AI usage should be logged where possible and should respect plan restrictions.

## AI Areas

- Ask Doubts
- AI explanations
- AI solutions
- AI recommendations
- Teacher Assistant summaries (currently rule-based)
- Prompt management

## Content Areas

- Lessons
- Question bank
- Mock tests
- Exemplar content
- Previous/sample papers
- Solutions

## Content Management Roadmap

- Lesson management
- Question bank CRUD
- Difficulty/tagging
- Exemplar management
- Prompt templates/versioning
- AI prompt sandbox
- Usage metrics

## Access

Premium-only content must be protected by backend feature authorization.

---

## AI Studio (Admin) — 2026-06-30

The AI Studio at `/api/admin/ai-studio/` allows admins to configure all AI behaviour without code changes.

### Providers
All 9 providers supported: OpenAI, Groq, Cerebras, Gemini, SambaNova, Venice AI, Ollama Cloud, Local Ollama, Anthropic.

**Fallback provider:** Set via AI Studio → Providers → "Set Fallback". When the primary provider fails (timeout, 429, etc.), `ask_llm()` automatically retries with the fallback. Configure in `admin_settings.ai_settings.fallback_provider`.

**Recommended model for Ollama Cloud:** `gpt-oss:20b` (fastest free-tier model, ~3s latency). Avoid `gemma3:4b` — times out on long prompts (90s+).

### Model Routing
Per-feature provider/model assignment. Edit via AI Studio → Model Routing. Each feature (lesson_repair, mcq_generation, etc.) can use a different provider.

**UI:** Provider dropdown lists all 9 providers. Model dropdown cascades from selected provider's suggested models. "✎ Enter custom…" option for unlisted models.

### Prompt Templates
10 default CBSE prompt templates seeded (2026-06-30):
- Lesson Repair, Lesson Prewarming, Formula Generation, Formula Review
- MCQ Generation, Lesson Quality Review, Ask Doubt, AI Tutor
- Summary Generation, Common Mistakes

Each template supports versioning. Save creates new version; activate any previous version via the admin UI.

**Seed script:** `python3 scripts/seed_prompt_templates.py`

### Provider Catalog Endpoint
`GET /api/admin/ai-studio/providers/catalog` — returns lightweight `{provider_key, display_name, suggested_models}` list for UI dropdowns. No API keys or sensitive data returned.

### Ollama Cloud Notes
- Free-tier models (confirmed working): `gemma3:4b`, `gemma3:12b`, `gpt-oss:20b`
- `gpt-oss:20b` is fastest (1-3s latency on short prompts, ~3s on full lesson prompts)
- `gemma3:4b` times out on long prompts despite fast short-prompt response
- Premium models (`glm-5.2`, `kimi-k2.6`) require subscription (403)
- API format: native `/api/chat` (NOT OpenAI `/v1/chat/completions`)
