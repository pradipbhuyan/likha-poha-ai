# Roadmap

_Last updated: 2026-06-28_

## Completed

### Foundation
- Free signup without offer-code requirement
- Canonical subscription resolver + feature authorization
- Plan catalog, parity tests, payment idempotency
- Audit logs, subscription timeline, expiry job
- Admin Console refactor

### Parent Experience (Phase 1–3) ✅
- Full parent dashboard with 9-tab child workspace
- Notifications, analytics, progress report, academic insights
- Add Child flow with credentials panel
- Score normalization (`_normalize_score_pct()`)

### Student Experience ✅
- **Student Dashboard redesign** (Option 1 card-based layout)
- `GET /api/student/dashboard/summary`
- Hero + Quick Stats + Continue Learning + Today's Plan + AI Coach + Subject Progress + Mock Tests + Weak Topics + Achievements + Utility + Motivation
- **Student Exam Schedule** (`student_exam_schedule` table)
  - Student and parent can add exam dates
  - Countdown in days
  - No static placeholder dates
- **Formula Sheet** — full freemium feature
  - Chapter-wise for Grade 5–12 (96+ formulas)
  - `FORMULA_SHEET_PREMIUM` feature key
  - Free: preview 3 formulas per chapter
  - Paid: full expansion + examples + memory tips + MCQ practice
  - KaTeX math rendering
  - Exemplar-style upgrade modal
  - Sidebar item below Mock Test
  - Formula Sheet Quick Actions: Watch Concept Videos, Practice Questions, Study Materials all have real destinations

### Formula Sheet Content ✅
- 96 formulas across Grade 5–12
- Maths: Grade 5-12 (area, algebra, trig, calculus, vectors)
- Science: Grade 9-10 (motion, electricity, optics)
- Physics/Chemistry: Grade 11-12
- Grade 9: 55 formulas across 19 chapters
- Grade 10: 76 formulas across 15 chapters
- Migration v3 pending application (expression_latex, mcqs_json, source_type, status)

### Signup Redesign ✅
- Single-step card-based signup
- Parent + Student roles only (Teacher removed from public signup)
- Grade 5–10 selector for students
- Google Sign In
- Add Child: Grade 5–10 only

### Auth / Session Reliability ✅
- Session recovery on app boot
- **Google OAuth race condition fixed** — session recovery skips when `?code=` in URL
- **isOAuthRedirect check before localStorage** in `onAuthStateChange`
- **Identity age fallback** for post-PKCE URL cleanup
- **authFetch 3-step retry** (800ms) for post-OAuth session window
- Friendly error messages (no Supabase/JWT internals)

### Platform QA Center (Admin) ✅
- **Lesson Quality Audit** — deterministic checks, LLM optional, reports (JSON/MD/CSV)
- **Feature Authorization Audit** — matrix checks Free/Paid/Expired × all features
  - Free Tier Exemplar/Formula/Lesson Download denied
  - Mock Tests limited (not denied) for Free Tier
  - parentId alone never grants paid access
  - Expired plans fall back to FREE_TIER
  - 42/42 checks passing
- Both audits: CLI + Admin UI + download endpoints
- Admin-only (all endpoints have `require_admin`)

## Pending / Near-term

### Formula Sheet v3 Migration (apply via Supabase Studio)
- `expression_latex`, `variables_json`, `mcqs_json`, `use_when`
- `source_type` (seeded/llm_generated/admin_reviewed)
- `status` (draft/published/archived)
- Admin LLM prewarm workflow (post-migration)

### Admin LLM Formula Prewarm
- `POST /api/admin/content/formula-sheets/prewarm`
- LLM-generated draft content per grade/chapter
- Admin review before publish

### Homework & Exam Center
- `homework` and `exam_schedule` tables not yet created
- Currently: `available=false` shown gracefully

### Content Platform
- Admin formula editor UI
- Bulk import/export

### Production Readiness
- E2E browser tests
- Performance/load testing
- Backup/restore procedures
- Sentry integration

## Key Technical Debt

1. `chapter_progress` table never created — always use `student_progress`
2. `test_history.score` column does not exist — always use `percentage`
3. `formula_sheets` v3 migration not yet applied — fallback to base columns
4. Google OAuth session has multiple edge-case fixes — document in onboarding

---

## Completed — July 2026 Sprint

### Audio Pre-warming System (TTS Cache)
- [x] `lesson_audio_cache` DB table + RLS policies
- [x] `audio_cache_service.py` — store/retrieve audio URLs
- [x] Dual Supabase storage routing (Grade 9 → Supabase 1, others → Supabase 2)
- [x] `prewarm_lesson_audio.py` — CLI script with --resume, --limit flags
- [x] `GET /api/tts/cached-url` — frontend checks cache before calling Edge TTS
- [x] `POST /api/cache-management/prewarm/audio/{grade}` — admin trigger
- [x] Admin Cache Management page — Audio progress bar + Build Audio button
- [x] Grade 9 English prewarm completed (~155 lessons, ~240 MB)

### TTS Quality Improvements
- [x] Structured pauses: headings→period, paragraphs→period, bullets→comma
- [x] Hindi voice routing: `hi-IN-SwaraNeural` for Hindi subjects
- [x] Abbreviation expansion: 35 abbreviations (e.g., CBSE, DNA, LHS, cm, etc.)
- [x] Devanagari text preserved (not stripped) for Hindi lessons

### LLM Provider Hardening (NVIDIA)
- [x] NVIDIA client timeout reduced: 120s → 45s (prevents 6-min QB batch stalls)
- [x] Timeout errors excluded from retry loop (fail-fast)
- [x] `_UNAVAILABLE_NVIDIA` model blocklist (google/gemma-* remapped to llama-3.1-8b)
- [x] Admin dropdown shows only 3 confirmed-working models

### Maths LaTeX Quality
- [x] `TUTOR_SYSTEM` MATH RULES rewritten with explicit bad/good examples
- [x] Broken lesson detection script (regex scan lesson_cache)
- [x] Grade 8 (24), Grade 9 (3), Grade 10 (22) broken lessons archived + reprewarm triggered

### LKB Chips Fix
- [x] Chips now appear immediately after lesson generation (not just on re-navigation)

### Sign-up Page Improvements
- [x] Google Sign-Up button added (same OAuth flow as Login page)
- [x] Google data disclosure notice (required by Google OAuth policy)
- [x] Privacy Policy link opens in new tab

### SEO & PWA
- [x] `sitemap.xml` added (homepage, blog, policy pages)
- [x] `robots.txt` added
- [x] Original `favicon.png` restored (was overwritten by generic favicon.ico)

### AI Guide (FirstTimeGuide)
- [x] Restored to top-right corner, always minimised by default
- [x] Student guide: 11 steps (added Formula Sheet + Exemplar Research)
- [x] Parent guide: 5 steps (refreshed for current platform state)
- [x] Panel size reduced ~25%
- [x] Back button added (Skip | Back | Next navigation)

---

## Pending — Audio & TTS

- [ ] Option 3 LaTeX-to-speech conversion (sqrt, frac, powers → natural English)
- [ ] Re-prewarm Grade 9 English audio to Supabase 1 (cleared July 2026)
- [ ] Audio prewarm for Grades 5-8 via Supabase 2
- [ ] Audio prewarm for Grade 10 via Supabase 2

## Pending — Content Quality

- [ ] Scan Grade 10 Science for broken LaTeX (same process as Maths)
- [ ] Scan Grade 8 Science for broken LaTeX
- [ ] After broken lessons repaired: add quality gate to prewarm script
