# Roadmap

_Last updated: 2026-06-28_

## Completed

### August 2026 (added 2026-08-26 — see linked docs for detail, this is a summary only)

- **Exam Prep Center** — new standalone ₹1,999/year plan (JEE/NEET/CUET/SAT/IELTS/TOEFL) replaced the legacy per-exam pack system entirely. See `03_SUBSCRIPTIONS.md`, `FEATURE_MATRIX.md`, `TECH_DEBT.md` (TD-04, resolved).
- **Premium Nano fully discontinued** — confirmed retired at both backend (`is_public: false`, purchase 404s) and frontend layers.
- **Teacher restrictions** — teachers can now only add/invite students into Grade 5–12 (was unrestricted); Exemplar Research blocked for the teacher role entirely, unconditionally, as a student-only paid feature. See `06_TEACHER_PLATFORM.md`.
- **Parent Add Child — Grade 11/12 support** — parents can now create Grade 11/12 child accounts with a mandatory stream selection, matching self-signup. `ParentChildWorkspace` reduced from 9 tabs to 8 (Platform Access tab removed). See `07_PARENT_PLATFORM.md`.
- **Admin signup notification emails** — admin inbox (email, not the in-app Notification Center) now gets a message on every new teacher signup and every new student/parent registration. See `05_ADMIN_PLATFORM.md`.
- **Go-live security hardening pass** — ~10 commits: profile-id ownership hardening, a real username-collision data-leak fix, 3 unauthenticated billable AI routes deleted, mandatory Razorpay webhook verification + production-boot secret requirement, family-scoped child ownership, and a near-miss fix where production-only security gates had been silently inert because `ENVIRONMENT` was never actually set on the host. See `10_SECURITY.md`.
- **Rate limiting shipped** — Redis-backed (in-memory fallback) on login, signup, password reset, username lookup, and payment endpoints. One known gap remains (`complete-signup`) — see `TECH_DEBT.md` TD-13.
- **Mobile** — versionCode reached 50 (from 13); Doubt solving, Analytics, and Google OAuth are all now fully shipped on mobile (previously documented as not-yet-built — that was stale, not the code). Board Papers tab added. See `MOBILE_APP.md`.

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

**The full, actively-maintained register is `TECH_DEBT.md`** — it has status/priority tracking and is re-verified against current code periodically (last re-verified 2026-08-26). The four items below are quick DB/session gotchas worth keeping here for fast reference; don't extend this list further — add new debt to `TECH_DEBT.md` instead.

1. `chapter_progress` table never created — always use `student_progress`
2. `test_history.score` column does not exist — always use `percentage`
3. `formula_sheets` v3 migration not yet applied — fallback to base columns
4. Google OAuth session has multiple edge-case fixes — document in onboarding

---

## Completed — July 2026 Sprint (Week 2 — July 5-7)

### Exam Prep Center — Access & Stream Eligibility Fixes
- [x] `get_access_check_response()` — test users now get all exams eligible (JEE + NEET) regardless of stream
- [x] `akshita.teststudent` profile updated: Grade 11, PCMB, full CBSE subjects
- [x] `exam_eligibility` for test users hardcoded to `jee_main: eligible, neet_ug: eligible`
- [x] Grade 11/12 Access tests (`Grade1112Access.test.jsx`) — all 13 fetch mocks fixed with `vi.stubGlobal`
- [x] `ExamPrepPage.test.jsx` — fetch mocks added for access-check endpoint

### Paste & Import Question Bank (ChatGPT/Custom GPT → Platform)
- [x] `POST /api/admin/exam-prep/questions/import-bulk` — 6-tier validation + MD5 deduplication
- [x] `PasteImportSection` React component — JSON textarea, character/question count preview, import result summary, per-question report
- [x] `adminImportBulk()` API function in `examPrep.js`
- [x] `reviewRefreshKey` state wiring — Review panel auto-refreshes after successful import
- [x] Validation catches: GPT self-invalidation, answer mismatch (correct_option ≠ explanation conclusion)

### Exam Prep UI — Explanation Step Formatting
- [x] `detailed_explanation` rendered as separate lines — split on `Step N:`, `Option X:`, `Therefore` patterns
- [x] Each step in its own `<div>` with 4px margin, line-height 1.9

### Light/Dark Mode Compatibility (ExamPrepPage + AdminCacheManagementPage)
- [x] `QuestionCard` question text + option text: `var(--text,#1e293b)`
- [x] `AIPanel` explanation, question preview: CSS variables
- [x] Follow-up input: `var(--surface,#f8fafc)` light background
- [x] `AdminCacheManagementPage` all form controls: light-mode fallbacks
  - All `select`, `input`, `textarea` use `var(--surface,#f8fafc)` + `var(--text,#1e293b)` + `var(--border,#e2e8f0)`
  - Import result container: `var(--panel,rgba(0,0,0,.06))`

### Custom GPT Prompts for Question Generation
- [x] Designed 3 Custom GPT system prompts: JEE Main, NEET UG, CUET UG
- [x] 72-prompt sequence covering all JEE chapters (Physics×24, Chemistry×24, Mathematics×24)
- [x] Each prompt generates exactly 5 questions in platform JSON format

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

---

## Completed — Lesson Layout & Rendering (July 10, 2026)

### Lesson Page — Workbook Layout + Top Bar
- [x] Option B Workbook layout: all sections expanded inline, colour-coded left border
- [x] Floating ≡ TOC button (position:fixed, right side) — opens/closes section nav panel
- [x] Option A Card Feed layout preserved (flag: `USE_CARD_FEED_LAYOUT`)
- [x] Compact horizontal top bar replaces left sidebar (`USE_TOP_BAR_LAYOUT`)
- [x] Top bar: Grade/Subject/Chapter selectors + Step pill + Generate/Refresh
- [x] DoubtPage: same compact top bar; Mentor Context sidebar hidden; full-width textbox
- [x] Likha Poha AI Guide: moved from `position:fixed` floating to inline header button
- [x] AI Ready status pill removed from header
- [x] `.topbar { z-index: 500 }` — fixes guide panel hidden behind page cards (backdrop-filter stacking context)
- [x] `first-guide-layer { z-index: 1200; top: 80px }` — guide panel above all content

### parseSections() Bug Fix
- [x] 5 heading patterns supported: numbered+hash, numbered+bold, hash-only, bold-only, `Step N: Title`
- [x] Guard: numbered items ending `.` not treated as headings
- [x] `getRenderableContent()` — worked examples (Question: + Step N:) never lose solution
- [x] Parser debug script: `backend/scripts/trace_parser_chapter1.py`

### Rendering Quality
- [x] `fixInlineDisplayMath()` — `$$inline$$` → `$inline$` (applied at render time in LessonSections)
- [x] `normalizeInlineDisplayMath()` — same fix in `normalizeTutorMarkdown()` pipeline (step 0)
- [x] Font consistency: body `1rem`, section titles `1rem`, type badges `0.65rem`, line-height `1.7`
- [x] Dark mode inline question box: full CSS overrides in `body.dark-mode .lesson-inline-question-box`
- [x] Light mode top bar: CSS variables with explicit light-mode fallbacks (`var(--panel, #ffffff)`)
- [x] TOC panel light mode: explicit `#e2e8f0` text (panel always dark background)

### Grade 5 Content Fixes
- [x] Papa's Spectacles (Chapter 1) detected as poem — `POEM_SYSTEM` used
- [x] The Rainbow (Ch3), The Frog (Ch5), Vocation (Ch9) added to `_POEM_KEYWORDS`

### Practice Question Quality
- [x] Pass threshold raised: `score >= 6` → `score >= 7`
- [x] Keyword score floor: `max(1,...)` → `max(0,...)`
- [x] EVALUATOR_SYSTEM: strict textbook-grounded feedback
- [x] Prewarm question count scales with RAG chunks (1 / 2 / 3)
- [x] Textbook exercise Q&A used directly before generating new questions
- [x] MCQ explanation field added (one textbook sentence)

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
- [ ] Regenerate Grade 5 Santoor poem chapters with POEM_SYSTEM (Papa's Spectacles, Rainbow, Frog, Vocation) — archive stale cached lessons and re-prewarm
- [ ] Regenerate all Grade 5 lessons that had format issues (Step N: flat format) → now properly detected by parser, but content is thin — consider refreshing

## Pending — Lesson Page UX

- [ ] Workbook layout responsive: on mobile `< 768px`, hide floating TOC button, show inline section links at top
- [ ] "Next step" preview card at bottom of lesson — smooth navigation
- [ ] Section progress tracking: mark sections as read as student scrolls
- [ ] Grade 5 font size check: `1rem` body may be too large for Grade 1–3 content; consider `0.95rem` floor

## Pending — Practice Question Quality

- [ ] Re-run prewarm question generation for all Grade 5 chapters to pick up the new stricter prompts
- [ ] Add `expected_keywords` extraction step for descriptive questions (derive from model answer)
- [ ] Question bank search for Grade 5 chapters (very few currently in bank)
