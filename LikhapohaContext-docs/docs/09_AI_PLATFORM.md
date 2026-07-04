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

---

## TTS (Text-to-Speech) System — Updated July 2026

### Architecture
1. **Frontend** (`LessonsPage.jsx`): Calls `GET /api/tts/cached-url` first
   - If `cached=true` → plays URL directly from Supabase CDN (instant)
   - If `cached=false` → calls `POST /api/tts/generate` → Edge TTS (~15-20s)
2. **Backend** (`tts_service.py`): `clean_text_for_tts()` transforms lesson markdown before synthesis

### Voice Selection
| Subject | Voice |
|---------|-------|
| Hindi / Hindi Olympiad | `hi-IN-SwaraNeural` |
| All other subjects | `en-IN-NeerjaNeural` |

### Text Cleaning Pipeline (`clean_text_for_tts()`)
1. Section headings → text + period (pause)
2. Bold/italic markers → stripped (text kept)
3. Bullet items → comma-separated
4. Code blocks → stripped
5. **Abbreviation expansion** (35 terms): e.g.→"for example", CBSE→"C B S E", DNA→"D N A", cm→"centimetres"
6. LaTeX (`$...$`, `$$...$$`) → stripped (pending: convert to spoken English)
7. Blank lines → period (sentence pause)
8. Single newlines → comma (breath pause)
9. Cleanup: consecutive commas, double periods, empty list artefacts

### Pre-warmed Audio Cache
- **DB table:** `lesson_audio_cache` (Supabase 1)
- **Storage:** Grade 9 → Supabase 1; all others → Supabase 2
- **Prewarm script:** `backend/scripts/prewarm_lesson_audio.py`
- **Admin UI:** Cache & Question Bank page → Audio progress bar + Build Audio button

### Known Limitation — LaTeX Expressions
Inline LaTeX expressions like `$\sqrt{3} = \frac{a}{b}$` are currently stripped to silence. Option 3 (regex-based spoken conversion) is planned:
- `\sqrt{x}` → "square root of x"
- `\frac{a}{b}` → "a over b"
- `^2` → "squared"
