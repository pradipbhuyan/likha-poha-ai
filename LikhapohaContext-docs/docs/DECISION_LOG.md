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
