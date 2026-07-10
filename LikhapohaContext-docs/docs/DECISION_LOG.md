# Decision Log

_Last updated: 2026-06-28_

This file records key technical decisions made during development, including the reasoning and any constraints that must not be violated.

---

## 2026-06-28: Google OAuth Race Condition — Session Recovery Skipped on OAuth Return

**Decision:** Session recovery `useEffect` must NOT run when `?code=` or `#access_token=` is present in the URL.

**Root cause:** When user returns from Google OAuth (`?code=` in URL), two concurrent code paths ran:
1. Session recovery called `getSession()` → exchanged `?code=` → then `refreshSession()`
2. `onAuthStateChange` OAuth handler also fired and called `refreshSession()`

The second `refreshSession()` invalidated the first session, causing "Your session has expired" error.

**Fix:** Added `_isOAuthReturn` guard in session recovery:
```js
if (savedUser && !_isOAuthReturn) { /* session recovery */ }
```

---

## 2026-06-28: Google OAuth — isOAuthRedirect Check Before localStorage

**Decision:** The `isOAuthRedirect` URL check must happen BEFORE the `localStorage.getItem("tutor_user")` check in `onAuthStateChange`.

**Root cause:** When user with existing session clicked Google Sign In, the handler found `tutor_user` in localStorage and returned early with a token refresh — never processing the new Google login.

**Fix:** Check `isOAuthRedirect` first. If it's a fresh OAuth redirect, skip the localStorage shortcut entirely.

---

## 2026-06-28: Google OAuth — Identity Age Fallback

**Decision:** Use `session.user.identities[0].created_at < 5 minutes` as fallback OAuth detection when URL markers are already cleaned up.

**Root cause:** Supabase PKCE automatically exchanges `?code=` during `getSession()` (session recovery) and cleans the URL. By the time `onAuthStateChange` fires, `window.location.search` no longer contains `code=`.

**Fix:** `_recentOAuth` check: if identity was created < 5 minutes ago, treat as fresh OAuth regardless of URL state.

---

## 2026-06-28: authFetch Session Retry for Post-OAuth Window

**Decision:** `authFetch` must retry with 800ms delay if `getSession()` returns no token.

**Root cause:** After Google OAuth, there's a brief window (< 1s) where Supabase session isn't yet accessible in `getSession()`. Pages that load immediately after `handleLogin()` fail with "session expired".

**Fix:** 3-step token retrieval: `getSession()` → `refreshSession()` → wait 800ms + retry.

---

## 2026-06-28: Platform QA Center — Feature Authorization Audit

**Decision:** Feature Authorization Audit uses `_FEATURE_MATRIX` and `authorize_feature()` from the canonical service directly — no business logic duplication.

**Key:** Patches `resolve_user_subscription` inside `feature_authorization_service` module (not the resolver module) so mocks work correctly.

**Identity age fallback:** For expired plan testing, passes `"FREE_TIER"` effective plan to mock resolver (expired plans → `FREE_TIER`).

---

## 2026-06-28: Platform QA Center — Lesson Quality Audit

**Decision:** Lesson Quality Audit is admin-only. Background thread (`daemon=True`) to avoid blocking web requests for full audits. In-memory job registry + DB persistence (graceful fallback if `lesson_quality_audit_runs` table not applied).

**LLM mode:** Disabled by default. When enabled, patches `feature_authorization_service.resolve_user_subscription` and caches by SHA256 of content. LLM exceptions never crash deterministic audit.

---

## 2026-06-28: Formula Sheet Freemium Model

**Decision:** Formula Sheet page is open to all users. Premium content (solved examples, memory tips, MCQ expansion) gated by `FORMULA_SHEET_PREMIUM` feature key. Free users see first 3 formulas per chapter as preview.

**Upgrade modal:** Uses Exemplar Research pattern — click expand on locked formula → modal with "🔐 This feature is for paid subscribers" → "🚀 See Plans & Upgrade" → routes to `subscriptionPlans` page.

---

## 2026-06-28: Formula Sheet v2 Fallback Query

**Decision:** `formula_sheets.py` endpoint tries v2 columns first (topic, variables, solution_steps, memory_tip, etc.). If `42703` (column does not exist) error → falls back to base columns. Automatically upgrades when v2 migration is applied.

**Why:** v3 migration columns were not applied to live DB initially. Graceful fallback ensures page works without disruption.

---

## 2026-06-28: Student Dashboard Redesign

**Decision:** `StudentDashboardPage.jsx` replaces `DashboardPage.jsx` as the student dashboard (Option 1 card-based layout).

**Backend:** `GET /api/student/dashboard/summary` returns all data in one call.

**Score safety:** `safePct()` frontend helper + `_normalize_score_pct()` backend helper — scores always 0-100.

**Formula Sheet Quick Action:** Routes to `"formulaSheet"` page (not `"subscription"` or `"learnMore"`).

---

## Earlier Decisions (carried forward)

### parentId Alone Never Grants Access
`access_cbse` must be explicitly `true`. Enforced at both API layer (subscription resolver) and frontend (`resolveSubscription.js`).

### Canonical Feature Authorization
Feature access comes from `get_feature_summary(user_id)`. Never branch on raw `subscription_plan`. Never infer access from `parentId`.

### test_history.percentage
Always use `percentage` column (0-100). `score` and `total_questions` columns do NOT exist. Never multiply `percentage` by 100.

---

## 2026-07-07: Exam Prep — Test User Gets All Exams Eligible

**Decision:** `EXAM_PREP_TEST_USERS` (e.g. `akshita.teststudent`) receive hardcoded full exam eligibility regardless of stream.

**Before:** `build_exam_eligibility(None)` was called → JEE/NEET returned as ineligible (stream=None).

**After (in `get_access_check_response`):**
```python
if username in EXAM_PREP_TEST_USERS:
    return {
        "exam_eligibility": {
            "jee_main": {"eligible": True, "reason": ""},
            "neet_ug":  {"eligible": True, "reason": ""},
            "cuet_ug":  {"eligible": True, "coming_soon": True, ...},
        },
        ...
    }
```

**Profile also updated:** `akshita.teststudent` set to Grade 11, Stream PCMB so the sidebar shows Grade 11/12 features.

**File:** `backend/app/services/exam_prep_service.py`

---

## 2026-07-07: Paste & Import — 6-Tier Validation for ChatGPT Questions

**Decision:** Bulk import endpoint validates each question before inserting. Catches common ChatGPT generation errors automatically.

**Validation tiers (in order):**
1. Required fields (exam_type, grade, subject, chapter, topic, question_text, options, correct_option, detailed_explanation, difficulty)
2. Field values (exam_type ∈ {jee_main,neet_ug,cuet_ug}, difficulty ∈ {easy,medium,hard}, correct_option ∈ {A,B,C,D}, options has exactly A/B/C/D)
3. Self-invalidation: if "invalid" AND "should be replaced" in explanation → skip
4. Answer mismatch: if explanation says "Therefore answer is X" but correct_option is Y → `imported_with_warning` (still saved, needs review before publish)
5. Deduplication: MD5 of question_text vs existing questions
6. All valid → saved as `draft`

**Why answer mismatch = warning not error:** GPT sometimes sets the correct_option field incorrectly while the explanation is actually correct. Admin can verify and fix before publishing.

**File:** `backend/app/routes/exam_prep.py`

---

## 2026-07-07: CSS Variable Convention — Light/Dark Mode Fallbacks

**Decision:** All inline styles in React components use CSS variable fallbacks that work in BOTH light and dark mode.

**Convention:**
```
background: "var(--surface,#f8fafc)"    ← #f8fafc shows in light mode if --surface not set
color: "var(--text,#1e293b)"            ← dark text fallback for light mode  
border: "1px solid var(--border,#e2e8f0)" ← subtle border in light mode
```

**Previous pattern (WRONG — dark only):**
```
background: "var(--surface,#0f172a)"   ← shows dark even in light mode
color: "#f1f5f9"                        ← hardcoded light (invisible on white)
```

**How theme switching works:** The app's CSS theme sets `--surface`, `--text`, `--border` etc. for dark mode. In light mode, if these vars are not set, the fallback value controls the appearance. So the fallback must be the LIGHT mode value.

**Applied to:** `ExamPrepPage.jsx` (QuestionCard, AIPanel), `AdminCacheManagementPage.jsx` (all selects, inputs, textareas in QuestionReviewPanel, ExamPrepQBSection, PasteImportSection)

---

### student_progress not chapter_progress
`chapter_progress` table does NOT exist. All progress data is in `student_progress`.

---

## 2026-06-30: Exemplar Chapter Locking — Use `includes()` Not `startsWith()`

**Decision:** Frontend exemplar lock check must use `includes("Exemplar:")` not `startsWith("Exemplar:")`.

**Root cause:** The syllabus route adds "Part N - " display prefix when a subject has multiple book parts (e.g. Grade 8 Maths has Part 1 and Part 2). This turned "Exemplar: Rational Numbers" into "Part 1 - Exemplar: Rational Numbers", breaking `startsWith("Exemplar:")`.

**Fix (two-layer):**
1. `LessonsPage.jsx`: `chapter?.includes("Exemplar:")` — works regardless of prefix
2. `syllabus.py` `create_part_display_label()`: skip "Part N - " prefix for chapters containing "Exemplar:"
3. `lesson.py`: `"exemplar:" in _chapter_name.lower()` — backend also handles any prefix

**Rule:** Never use `startsWith("Exemplar:")` — always use `includes("Exemplar:")` in frontend, `"exemplar:" in` in backend.

---

## 2026-06-30: Subscription Plans — free_tier vs free (Nano)

**Decision:** The DB key `"free"` in `profiles.subscription_plan` maps to Premium Nano (₹99/8 days), NOT the free tier.

**Context:**
- Frontend `subscriptionPlans.js`: `free_tier` = actual free plan (no price); `free` = Premium Nano (₹99)
- Backend `subscription_plans.py`: now has `free_tier` (order=1), `free`=Nano (order=2), `starter`=Premium (order=3)
- DB `subscription_plan_settings` updated to match

**Distinguished by:** `access_cbse=True + subscription_expires_at set` = Nano active; `access_cbse=False` = free tier.

---

## 2026-06-30: Add Child Modal — Show Upgrade Card Only When childCount > 0

**Decision:** The "Child limit reached" upgrade card in `AddChildModal` must NOT show for new parents (0 existing children).

**Rule:** Show upgrade card only when `!canAdd && childCount > 0`. Always show the form when `childCount === 0`.

---

## 2026-06-30: Ollama Cloud Fallback Provider

**Decision:** `ask_llm()` now supports automatic fallback to a configured secondary provider when primary fails.

**Implementation:** `openai_service.py` reads `fallback_provider` from `admin_settings.ai_settings`. Configure via AI Studio → Providers → Set Fallback.

---

## 2026-06-30: Grade 11/12 NCERT Exemplar RAG

**Decision:** NCERT only publishes exemplar PDFs for Grade 11 Maths/Biology and Grade 12 Maths/Physics/Biology. Grade 11 Physics/Chemistry and Grade 12 Chemistry return 404 on all URL patterns — confirmed June 2026.

**Storage:** Grade 11/12 exemplar chunks stored in secondary Supabase (`grade_1112_client`), tagged `chapter = "Exemplar: {name}"`.

---

## 2026-07-01: Content Order in AI-Generated Lessons

**Issue:** AI occasionally generates lists in reverse/non-sequential order (e.g., "Example 1.3, 1.2, 1.1" instead of "1.1, 1.2, 1.3").

**Classification:** Content quality issue (not a rendering/frontend bug). The frontend displays exactly what's stored in the DB.

**Fix path:** Admin Lesson Repair → select the affected step → repair with AI.

**Prevention:** When this pattern is detected in future prompt improvements, add explicit ordering instruction: "Always list examples, steps, and numbered items in ascending order (1, 2, 3 — never 3, 2, 1)."

**Do NOT:** Auto-sort list items in the frontend rendering pipeline — this would incorrectly reorder intentionally unordered content.

---

## 2026-07-03: LKB Chips Not Appearing on First Lesson Generation

**Issue:** Lesson Knowledge Base (LKB) chips didn't appear after `handleGenerateLesson()` completed — only appeared after navigating away and back.

**Root cause:** `ensureLessonKbChips()` was only called in two places: `loadProgress()` (runs on chapter change, before lesson exists) and `useEffect` on `currentStepIndex` (only fires when step index changes). Neither fires after lesson generation on the same step.

**Fix:** Added explicit `ensureLessonKbChips()` call inside `handleGenerateLesson()` immediately after `setLesson(result.lesson)`.

**File:** `frontend/src/pages/LessonsPage.jsx`

---

## 2026-07-03: NVIDIA QB Batch Timeout — 6 Minutes Per Failed Batch

**Issue:** Question bank build batches for Grade 11 Mathematics were taking 6 minutes to fail (361s).

**Root cause:** NVIDIA client had `timeout=120s`. With 3 retry attempts × 120s = 361s per failed batch. NVIDIA server sends streaming keepalives that prevent the timeout from firing at 120s.

**Fix:**
1. Reduced NVIDIA client timeout: `120s → 45s`
2. Added `is_timeout` flag to explicitly exclude timeout errors from retry loop — timeouts now fail fast after 1 attempt

**File:** `backend/app/services/openai_service.py`

---

## 2026-07-03: NVIDIA google/gemma-3-* Models Return 404

**Issue:** Admin settings had `nvidia_model = "google/gemma-3-4b-it"` which returns `404 Function not found for account` on free-tier accounts.

**Fix:** Added `_UNAVAILABLE_NVIDIA` set in `get_effective_settings()` — any model in this set is remapped to `DEFAULT_NVIDIA_MODEL` (meta/llama-3.1-8b-instruct).

**Tested models on nvapi-V-ccDZ... account:**
- ✅ meta/llama-3.1-8b-instruct, meta/llama-3.1-70b-instruct, meta/llama-3.2-3b-instruct
- ❌ meta/llama-4-scout-17b-16e-instruct (404), deepseek-ai/deepseek-v4-flash (timeout), all google/gemma-* (404)

**File:** `backend/app/services/openai_service.py`

---

## 2026-07-03: TTS — Pause Strategy for Natural Narration

**Decision:** `clean_text_for_tts()` now introduces natural pauses using punctuation (Edge TTS respects sentence-ending punctuation):
- Section headings → period (long pause before content)
- Blank lines between paragraphs → period
- Single newlines → comma (brief breath)
- Bullet items → comma
- LaTeX inline `$...$` and display `$$...$$` → stripped to blank space

**File:** `backend/app/services/tts_service.py`

---

## 2026-07-03: TTS — Hindi Lessons Use Different Voice

**Issue:** Hindi lessons (Devanagari script) were being passed to `en-IN-NeerjaNeural` which cannot speak Hindi, producing silence.

**Fix:** Added `getVoiceForSubject(subject)` in `LessonsPage.jsx`:
- Hindi/Hindi Olympiad → `hi-IN-SwaraNeural`
- All other subjects → `en-IN-NeerjaNeural`

**File:** `frontend/src/pages/LessonsPage.jsx`

---

## 2026-07-03: TTS — Abbreviation Expansion

**Decision:** `clean_text_for_tts()` expands abbreviations before speech generation so the narrator says "for example" instead of "e.g.", "C B S E" instead of "CBSE", etc.

35 abbreviations added: Latin (e.g., i.e., etc.), Academic (CBSE, NCERT, HOTS, LHS, RHS), Science (DNA, RNA, pH, m/s), Maths (LCM, HCF, AP, GP), Units (cm, mm, km, kg, ml).

**File:** `backend/app/services/tts_service.py`

---

## 2026-07-03: Audio Cache — Dual Supabase Storage Routing

**Decision:** To avoid hitting the 1 GB free tier storage limit on Supabase 1, audio files are routed by grade:
- Grade 9 → Supabase 1 (`dpivlbbyzlbpwnwgajso`) `lesson-audio` bucket
- All other grades → Supabase 2 (`sjfjyzaaypfzyfhhggqw`) `lesson-audio` bucket

**Implementation:**
- `_get_storage_client(grade)` returns the correct Supabase client
- `lesson_audio_cache` DB table stays on Supabase 1 (all grades — URLs in the row point to the correct CDN)
- No frontend changes — browser fetches audio from whatever URL is stored in DB

**File:** `backend/app/services/audio_cache_service.py`

---

## 2026-07-03: Maths LaTeX Rendering — MATH RULES Strengthened

**Issue:** LLM was generating malformed LaTeX in maths lessons:
- `(x^2 + 4x + 4)` — math inside plain parentheses
- `x^2 x 2` — variable repeated
- `(x - 2$$x + 2)` — `$$` inside parentheses

**Fix:** `TUTOR_SYSTEM` MATH RULES section rewritten with explicit BAD examples for every failure pattern. Key additions:
- "NEVER write any math expression inside normal parentheses ()"
- "NEVER use $$ inside () like (x - 2$$x + 2)"
- "NEVER repeat a variable twice like 'x^2 x 2'"
- Factored expressions: always `$(x-2)(x+3)$` not plain text

**File:** `backend/app/services/tutor_service.py`

---

## 2026-07-08: Math/Chemistry Formula Rendering in Exam Prep

**Problem:** Exam Prep questions displayed `H2O`, `10^23`, `mol^-1` as plain text. Chemistry and physics formulas from the question bank appeared unformatted.

**Solution:** Added `formatMathText()` + `MathText` component to `ExamPrepPage.jsx`:
- `H2O` → H₂O (auto-subscript for chemical formulas)
- `10^23` → 10²³ (superscript notation)
- `mol^-1` → mol⁻¹
- LaTeX symbols: `\times` → ×, `\alpha` → α, `\rightarrow` → →, `\sqrt{x}` → √(x), `\frac{a}{b}` → (a)/(b)
- Applied to question text AND option text in both Quick Practice and Simulated Test modes
- Uses `dangerouslySetInnerHTML` with memoized formatting — no library dependency

**File:** `frontend/src/pages/ExamPrepPage.jsx`

---

## 2026-07-08: CUET UG — All Three Exams Now Active

**Decision:** JEE Main, NEET UG, and CUET UG are all active in the Exam Prep Center. CUET is no longer "Coming Soon".

**CUET implementation:**
- Student picks subject combination before simulation (preset or custom)
- Presets: PCM, PCB, PCMB, Commerce, Humanities, Custom
- Marking: +5/-1 (different from JEE/NEET's +4/-1)
- Duration varies by section count (45 min/domain subject + 60 min for General Test)
- 16 supported subjects including domain subjects
- Questions fetched per-subject from `exam_prep_questions` with `exam_type=cuet_ug`

**CUET subject naming:** Subjects use "(Domain)" suffix in DB and frontend (e.g. "Physics (Domain)") to distinguish from JEE Physics. Questions for domain subjects need to be generated separately.

**Files:** `frontend/src/pages/ExamPrepPage.jsx`, `backend/app/services/exam_prep_service.py`

---

## 2026-07-08: Centralized Subscription Management

**Problem:** Admin panel could change plan display (prices, badges, feature text) but could not change:
1. Actual Razorpay charge amounts without code deploy
2. Subscription expiry days without code deploy
3. Feature access (Exam Prep, Exemplar) without code deploy

**Analysis revealed:** Razorpay amounts WERE already DB-driven via `plan_display_amount(plan)` → reads from `subscription_plan_settings`. But expiry and feature flags were hardcoded.

**Solution:**
1. **`duration_days` column** → `plan_expires_at()` checks this first, then falls back to `_BILLING_LABEL_TO_DAYS` lookup
2. **`access_exam_prep` + `access_exemplar` columns** → `feature_authorization_service.py` checks `_DB_DRIVEN_FEATURES` dict; admin can override per-plan from UI
3. **Admin UI** → Duration days input + Exam Prep / Exemplar checkboxes on each plan card
4. **Backward compat** → If migration not run, save gracefully skips new columns; existing saves work

**Migration:** `backend/migrations/20260708_subscription_plan_feature_flags.sql` on Supabase 1 (`dpivlbbyzlbpwnwgajso`)

**Tests:** `backend/tests/test_subscription_centralized.py` — 84 tests covering all cases

---

## 2026-07-08: Bulk Import — Grade/Source Type Sanitization

**Problem:** Custom GPT generated questions with `"grade": "Grade 11-12"` which violated DB check constraint `grade IN ('Grade 11','Grade 12')`. All 10 imports failed.

**Fix:** `POST /api/admin/exam-prep/questions/import-bulk` now sanitizes:
- `grade`: any value → "Grade 11" or "Grade 12" (defaults to Grade 12)
- `source_type`: unknown values → "llm_generated"
- `marks`/`negative_marks`: type-safe float conversion

**Rule:** Always use `Grade 12` (not "Grade 11-12") in Custom GPT batch prompts.

**File:** `backend/app/routes/exam_prep.py`

---

## 2026-07-08: Admin API Error Display Fix

**Problem:** FastAPI 422 validation errors returned as `detail: [{loc, msg, type}, ...]` array. `new Error(array)` coerced to `"[object Object],[object Object],..."`. Admin saw unreadable errors.

**Fix:** `parseError()` in `adminControl.js` now detects array detail and formats as: `body.plans.0.billing_label: Field required | body.plans.1.included: Input should be a valid list`

**Also fixed:** `subscription_plan_settings.included` stored as JSON string in Supabase. Backend `_to_list()` + frontend `_toArray()` helpers normalize JSON strings, plain strings, and native arrays → always send proper `list[str]` to Pydantic.

**Files:** `frontend/src/api/adminControl.js`, `frontend/src/config/subscriptionPlans.js`, `backend/app/routes/admin_control.py`

---

## 2026-07-10: Lesson Layout — Option B Workbook + Full-Width Top Bar

**Decision:** Replace the left sidebar "Learning Path" panel on the Lessons page with a compact horizontal top bar. Lesson content takes the full page width. Introduced Option B "Workbook" layout with floating TOC.

**Layout flags in `LessonSections.jsx`:**
- `USE_WORKBOOK_LAYOUT = true` — Option B: all sections inline, floating ≡ TOC button (right side, `position:fixed`)
- `USE_CARD_FEED_LAYOUT = false` — Option A: colour-coded card feed
- Both false → legacy accordion

**Layout flag in `LessonsPage.jsx`:**
- `USE_TOP_BAR_LAYOUT = true` — moves Grade/Subject/Chapter/Step selectors to compact top bar; sidebar hidden

**Floating TOC:** `position: fixed; right: 16px; top: 50%`. Opens to the left of the button. Panel uses explicit dark background (`rgba(15,23,42,.96)`) with explicit light text (`#e2e8f0`) to work in both light and dark modes.

**topbar z-index fix:** `.topbar` had `backdrop-filter: blur(18px)` which creates a stacking context. Guide panel was hidden behind page cards. Fixed by adding `position: relative; z-index: 500` to `.topbar` CSS.

**Files changed:**
- `frontend/src/components/LessonSections.jsx` — workbook layout, parseSections, floating TOC
- `frontend/src/pages/LessonsPage.jsx` — compact top bar, USE_TOP_BAR_LAYOUT flag
- `frontend/src/pages/DoubtPage.jsx` — same compact top bar pattern
- `frontend/src/App.css` — topbar z-index, dark mode question box, first-guide-layer z-index

---

## 2026-07-10: parseSections() Bug — Content Silently Discarded

**Bug:** `parseSections()` in `LessonSections.jsx` only recognised headings with a leading number (`1. Title`). Lessons using `## Heading`, `**Bold**`, or `Step N: Title` formats collapsed entirely into ONE card labelled "Introduction".

**Impact discovered:** Grade 5 Physics "Worked Examples" step had **272 out of 299 words discarded** (91% loss). `getRenderableContent()` was also stripping everything after "Question:" including the full worked solution.

**Fixes:**
1. `parseSections()` now handles 5 heading patterns:
   - `## 1. Title`, `**1. Title**` (numbered + hash/bold)
   - `## Title` (hash without number)
   - `**Title**` (bold standalone)
   - `Step N: Title` (plain text without terminal `.`)
2. `getRenderableContent()` detects worked examples (Question: + Step N: solution) and returns full body — never discards solution content.

**Verification script:** `backend/scripts/trace_parser_chapter1.py` — shows rendered vs discarded words per section.

---

## 2026-07-10: Grade 5 Santoor Poem Chapter Detection

**Bug:** `detect_chapter_type("English", "1. Papa's Spectacles")` returned `"prose"`. The RAG confirms it's a poem (chunk starts with "THE POEM Today our papa..."). Lesson was generated with `PROSE_LITERATURE_SYSTEM` instead of `POEM_SYSTEM`.

**Fix:** Added Grade 5 Santoor poem chapter keywords to `_POEM_KEYWORDS` in `tutor_service.py`:
```python
"papa's spectacles", "spectacles",  # Chapter 1
"the rainbow",                       # Chapter 3
"the frog",                          # Chapter 5
"vocation",                          # Chapter 9
```

**File:** `backend/app/services/tutor_service.py`

---

## 2026-07-10: Inline $$ LaTeX Fix

**Bug:** LLM sometimes writes display-math delimiter `$$` inline within a sentence (e.g. `x = v0t + 1/2 $$at^2.`). KaTeX treats `$$` as a block delimiter — invalid inline — causing red broken text.

**Fix:** `fixInlineDisplayMath()` function in `LessonSections.jsx`, called directly on `renderableContent` before passing to ReactMarkdown. Also added `normalizeInlineDisplayMath()` as step 0 in `normalizeTutorMarkdown()` pipeline in `markdownCleanup.js`.

**Rules:**
- `text $$expr$$ more` → `text $expr$ more`
- `text $$expr` (unclosed) → `text $expr$`
- Standalone `$$\nformula\n$$` block → unchanged

**Files:** `frontend/src/components/LessonSections.jsx`, `frontend/src/utils/markdownCleanup.js`

---

## 2026-07-10: Stricter Practice Question Quality

**Decisions:**
1. **Scoring:** Pass threshold raised from `score >= 6` to `score >= 7` (70% keyword coverage required). Keyword score now `max(0,...)` not `max(1,...)` — no free marks for attempt alone.
2. **EVALUATOR_SYSTEM:** Now explicitly strict — flags vague/general answers. "Your answer is too general — use specific facts from the chapter."
3. **Question count scaled by RAG chunks:** ≤2 chunks → 1 question; 3–5 chunks → 2 questions; 6+ chunks → 3 questions. Small chapters never over-tested.
4. **Textbook questions first:** Prewarm generator is instructed to look for existing exercise Q&A in the RAG content and use them directly before generating new ones. Zero general knowledge allowed.
5. **MCQ explanation field:** Now generated from the textbook sentence explaining the correct answer.

**Files:** `backend/app/services/evaluation_service.py`, `backend/app/routes/lesson.py` (prewarm/generate-questions endpoint)

---

## 2026-07-10: Dark Mode Inline Question Box Fix

**Bug:** `.lesson-inline-question-box` used hardcoded white gradient background with hardcoded dark text. In dark mode, `body.dark-mode` sets `color: #f8fafc` globally — child `<p>` elements rendered by ReactMarkdown inherited white text, invisible on white background.

**Fix:** Added `body.dark-mode` overrides in `App.css` for the entire inline question box component — background, text, buttons, feedback, textarea.

**File:** `frontend/src/App.css`

---

## 2026-07-03: Broken Maths Lesson Detection and Repair

**Process established:**
1. Regex scan `lesson_cache` for broken LaTeX patterns
2. Archive broken rows (`status='archived'`) — hidden from students, regenerated on next prewarm
3. Run prewarm script with `echo "yes" | python3 scripts/prewarm_lessons.py --grade "Grade N" --subject "Maths"`

**Results (July 2026):**
- Grade 9: 3 broken (Ch1 Coordinates, Ch4 Algebraic Identities) — repaired
- Grade 10: 22 broken (Ch2, 3, 8, 9, 12, 13, 14, Exemplar chapters) — archived + prewarm running
- Grade 8: 24 broken (all Exemplar chapters) — archived + prewarm running
- Grade 6, 7: clean

**Note:** Pre-warmed lessons in `lesson_cache` are NOT auto-updated by prompt changes. Must archive + regenerate manually.
