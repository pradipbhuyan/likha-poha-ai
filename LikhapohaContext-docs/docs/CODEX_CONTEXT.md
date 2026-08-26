# Likhapoha AI — Codex Context

_Last updated: 2026-07-13 (mobile Phase 3 — formula rendering, MCQ, lesson structured cards, mock test fixes; examprep crash fix; Google Auth; Grade 11/12 + stream signup; admin JWT fix)_
_2026-08-26: this file was merged from a duplicate root-level copy (`LikhapohaContext-docs/CODEX_CONTEXT.md`, now a redirect stub) that had silently drifted one day further than this one. This is now the only copy — read this location, not the root. The body below is otherwise still dated 2026-07-13 and has NOT been fully re-verified; test counts, plan names, and Exam Prep rules especially are known stale — see the delta list right below and the numbered docs (`01_PRODUCT_CONTEXT.md` onward), `TECH_DEBT.md`, and `DECISION_LOG.md`, which WERE re-verified against current code on 2026-08-26._

## ⚠️ Known-stale as of 2026-08-26 — read these corrections before trusting the body below

- **"Premium Nano" is retired**, not an active plan — don't offer it. A new standalone **Exam Prep Center** plan (₹1,999/yr) exists and isn't mentioned anywhere below. See `03_SUBSCRIPTIONS.md`.
- **Exam Prep access model changed**: the legacy per-exam pack system this file may reference elsewhere was deleted; access is now one flag (`subscription_plan_settings.access_exam_prep`). See `03_SUBSCRIPTIONS.md`'s 2026-08-26 section and `TECH_DEBT.md` TD-04 (Resolved).
- **Teachers are now restricted to Grade 5–12** when adding/inviting students, and are **blocked from Exemplar Research entirely**, regardless of plan. Not mentioned below at all. See `06_TEACHER_PLATFORM.md`.
- **Parents can now add Grade 11/12 children** (with a mandatory stream). Not mentioned below. See `07_PARENT_PLATFORM.md`.
- **Rate limiting shipped** (Redis-backed, login/signup/password-reset/lookup-email/payments) and a **~10-commit security hardening pass** landed — neither mentioned below. See `10_SECURITY.md`.
- **Test counts, mobile version/build number, and file-size figures below are all several weeks stale** — don't quote them; check the source files directly.

## What is Likhapoha AI

Likhapoha AI is a CBSE learning platform (Grade 5–10 primary, Grade 11-12 available) with AI-powered lessons, mock tests, doubt solving, exemplar practice, formula sheets, and progress analytics.

## Platform Roles

| Role | Dashboard | Notes |
|---|---|---|
| `student` | StudentDashboardPage | Redesigned (2026-06-28) — card-based layout |
| `parent` | ParentDashboardPage | Phase 1–3 complete |
| `teacher` | TeacherDashboardPage | Phase 1–3 complete |
| `admin` | AdminControlPage | Full operations + Platform QA Center |
| `sales` | SalesLeadPage | — |

## Current Test State

- **Backend:** 2201 tests passing, 37 skipped (full suite confirmed 2026-07-12)
- **Frontend:** 719 tests passing (52 test files, vitest) — +28 MockTestPage tests + 3 new MCQWidget/lesson tests
- **Lint:** 0 errors, 50 warnings (AT CI maximum — do NOT add any new warnings)

## ⚠️ MANDATORY Pre-Push Checklist

**Always run these before `git push` to prevent CI failures:**

```bash
# From the project root
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```

If either command fails, fix before pushing. These take ~15 seconds total.

### Why CI fails but local doesn't — 3 known failure modes

1. **Test assertions for old broken behavior** — If you fix a bug, tests written for the broken state will now fail in CI. Always run `npx vitest run` locally after every fix.

2. **ESLint warning count exceeds 50** — CI runs `eslint src/ --max-warnings 50` on the ENTIRE directory. Running ESLint on a single file locally misses the aggregate count. Always run on all of `src/`.

3. **Async timing race in tests** — Never use `getAllBy*` (synchronous) after `findBy*` (async) when the element you're looking for appears after a data fetch. Use `findAllBy*` (async retry) instead.

### ESLint `react-hooks/exhaustive-deps` rules in App.jsx

- The warning is reported on the `useEffect(() => {` opening line (line number), not the closing `}, [deps])` line.
- `// eslint-disable-line` goes on the closing `}, []);` line for mount-only effects.
- Never put `// eslint-disable-line` on the `[darkMode]` reactive effect — that effect IS correct and needs no suppression.
- `_finishOAuthLogin` inside the OAuth `useEffect` is intentionally excluded from deps to prevent infinite re-subscription.

## Platform Chat (User-to-User Messaging) — Added 2026-07-12

### Overview
Real-time user-to-user chat between teachers↔students, parents↔teachers, admin↔anyone.  
Backed by Supabase Realtime (WebSocket) + PostgreSQL + Supabase Storage.

### Access Rules
- Admin + Teacher: always enabled
- Paid subscription plan: auto-enabled
- Free users: admin-grant only (stored in `admin_settings.chat_access_users`)
- Global kill-switch: `admin_settings.platform_chat_settings.global_enabled`

### DB Tables (migration: `20260712_platform_chat.sql`)
- `chat_rooms` — participant_a_id, participant_b_id, room_type, is_active, last_message_at. RLS: participants only.
- `chat_messages` — room_id, sender_id, content, message_type (text|image|voice|file), attachment_url/name/size/mime, read_at, deleted_at, expires_at. RLS: room participants only.

### Storage
- Bucket: `chat-attachments` (private, 10 MB limit)
- Policies: `20260712_chat_storage_policies.sql` — INSERT/SELECT/DELETE for `authenticated` role
- Files served via `createSignedUrl()` (1-hour expiry) — never publicly accessible
- Images >2 MB auto-compressed client-side (JPEG 80%, max 1920px) before upload

### API Routes (Chat)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/chat/settings` | Check if current user can use chat |
| GET | `/api/chat/contacts` | Role-scoped contact list |
| GET | `/api/chat/rooms` | My rooms with last message + unread count |
| POST | `/api/chat/rooms` | Get-or-create room with another user |
| GET | `/api/chat/rooms/{id}/messages` | Paginated history |
| POST | `/api/chat/rooms/{id}/messages` | Send text/image/voice/file |
| POST | `/api/chat/rooms/{id}/read` | Mark unread as read |
| POST | `/api/chat/upload` | Get signed Supabase Storage upload URL |
| DELETE | `/api/chat/messages/{id}` | Soft-delete own message |
| GET | `/api/admin/chat/settings` | Admin: global chat settings |
| PUT | `/api/admin/chat/settings` | Admin: update settings |
| GET | `/api/admin/chat/users` | Admin: list explicit grants |
| PATCH | `/api/admin/chat/users/{id}` | Admin: grant/revoke per user |
| GET | `/api/admin/chat/rooms` | Admin: moderation view |
| DELETE | `/api/admin/chat/rooms/{id}` | Admin: deactivate room |

### Frontend Components

| File | Purpose |
|---|---|
| `frontend/src/components/PlatformChat.jsx` | Floating 💬 widget — rooms, contacts, messages, Realtime |
| `frontend/src/api/platformChat.js` | API client + `subscribeToRoom()` + `uploadChatFile()` |
| `frontend/src/pages/AdminChatPage.jsx` | Admin: settings, per-user grants, room moderation |

### Realtime
- Subscribe: `supabase.channel('chat:{roomId}').on('postgres_changes', {event:'INSERT', table:'chat_messages', filter:'room_id=eq.{id}'}, ...)`
- Enable: Supabase Dashboard → Database → Replication → add `chat_messages` table (or run `ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;`)

### Contact Routing
- Student → assigned teacher(s) + parent
- Teacher → all assigned students
- Parent → teachers assigned to their children
- Admin → all active users

## Product Bugs Page — Updated 2026-07-11

### New Features
- **Hide Closed toggle** (default ON) — filters `fixed`/`wont_fix` issues from view
- **Per-row Close button** — marks issue fixed and removes from list instantly
- **IssueDrawer "✓ Close Issue" button** — in drawer header for open issues
- **Row checkboxes** + Select All / Deselect All
- **Bulk action toolbar** (appears when ≥1 row selected):
  - ✓ Close Selected (fixed) — calls `POST /api/admin/issues/bulk-close`
  - ✗ Won't Fix — bulk-close with wont_fix status
  - 📋 Copy All for Codex (N) — builds consolidated markdown prompt for all selected issues

### API Routes (Issues — Updated)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/admin/issues/bulk-close` | Close up to 200 issues at once (fixed\|wont_fix) |

### Security Fix
`_sanitize_browser_info()` STRING_FIELDS truncation changed from 300→200 chars to match `test_browser_info_truncates_long_values` security test contract.

## API Routes (Student)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/student/dashboard/summary` | All student dashboard data |
| GET | `/api/student/exams` | Student exam schedule |
| POST | `/api/student/exams` | Add exam date |
| PATCH | `/api/student/exams/{id}` | Update exam |
| DELETE | `/api/student/exams/{id}` | Cancel exam |
| GET | `/api/student/formula-sheets` | Formula sheets (chapter-wise, freemium, Grade 5-12) |

## API Routes (Admin — Formula Import)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/admin/formula-sheets/import` | Bulk-upsert GPT-generated formula JSON into `formula_sheets` table. Admin only. |

**Formula Import body:**
```json
{
  "grade": "Grade 9",
  "subject": "Mathematics",
  "formulas": [
    {
      "formula_name": "Remainder Theorem",
      "expression": "p(a) = remainder when p(x) divided by (x - a)",
      "chapter": "Polynomials",
      "difficulty": "medium",
      "explanation": "...",
      "variables": "...",
      "example": "...",
      "solution_steps": "...",
      "memory_tip": "...",
      "tags": ["polynomial"],
      "active": true
    }
  ]
}
```
**Upsert key:** `formula_name (ilike) + grade + subject + chapter` — existing rows are updated, new rows inserted.  
**Returns:** `{ success, inserted, updated, skipped, errors[], message }`

## API Routes (Parent)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/parent/dashboard/summary` | Canonical parent dashboard |
| GET | `/api/parent/children/{id}/detail` | Child detail |
| GET | `/api/parent/children/{id}/analytics` | Child analytics |
| GET | `/api/parent/children/{id}/academic-insights` | Insights |
| GET | `/api/parent/children/{id}/progress-report` | Report |
| GET | `/api/parent/notifications` | Notification center |
| POST | `/api/parent/notifications/{id}/read` | Mark read |
| POST | `/api/parent/notifications/read-all` | Mark all read |
| POST | `/api/parent-dashboard/create-student` | Add child |
| GET | `/api/parent/children/{id}/exams` | Child exam schedule |
| POST | `/api/parent/children/{id}/exams` | Add exam for child |

## API Routes (Admin QA Center)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/admin/qa/lesson-quality/latest` | Latest lesson quality report |
| GET | `/api/admin/qa/lesson-quality/history` | Run history |
| POST | `/api/admin/qa/lesson-quality/run` | Start audit job |
| GET | `/api/admin/qa/lesson-quality/status/{id}` | Poll job |
| GET | `/api/admin/qa/lesson-quality/report` | Download report |
| GET | `/api/admin/qa/feature-authorization/latest` | Latest auth audit report |
| GET | `/api/admin/qa/feature-authorization/history` | Run history |
| POST | `/api/admin/qa/feature-authorization/run` | Start auth audit |
| GET | `/api/admin/qa/feature-authorization/status/{id}` | Poll job |
| GET | `/api/admin/qa/feature-authorization/report` | Download report |

## API Routes (Admin Lesson Repair)

Admin-only (require_admin on all). Backed by in-memory store with graceful DB fallback.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/admin/qa/lesson-repair/llm-info` | Currently configured provider, model, cost estimates (no key exposed) |
| GET | `/api/admin/qa/lesson-repair/latest` | Latest repair job + audit report metadata |
| GET | `/api/admin/qa/lesson-repair/history` | Recent job history |
| POST | `/api/admin/qa/lesson-repair/run` | Start repair job (mode, grade/subject/chapter filter, use_llm, override_api_key) |
| GET | `/api/admin/qa/lesson-repair/status/{job_id}` | Poll job status |
| GET | `/api/admin/qa/lesson-repair/tasks/{job_id}` | List tasks for a job |
| GET | `/api/admin/qa/lesson-repair/task/{task_id}` | Full task detail (issues, before, after, validation) |
| POST | `/api/admin/qa/lesson-repair/task/{task_id}/approve` | Approve draft (requires ready_for_review) |
| POST | `/api/admin/qa/lesson-repair/task/{task_id}/publish` | Publish to lesson_cache (requires approved) |
| POST | `/api/admin/qa/lesson-repair/task/{task_id}/rerun` | Re-run LLM repair for failed/validation_failed tasks |
| POST | `/api/admin/qa/lesson-repair/job/{job_id}/cancel` | Cancel queued/running job |
| GET | `/api/admin/qa/lesson-repair/report` | Download report (JSON/CSV/MD) |

## Critical Database Rules

1. **Use `student_progress`** — not `chapter_progress` (does not exist)
2. **Use `test_history.percentage`** — not `score` or `total_questions` (don't exist)
3. **Use `ai_usage_logs`** — not `ai_conversation_logs` (does not exist)
4. **Missing tables return graceful empty** via `_safe_query()` — never crash
5. **`formula_sheets` v2 columns** — check for 42703 error, fall back to base columns if missing

## Critical Code Rules

1. **`_normalize_score_pct(percentage, raw_score, max_score)`** — use for ALL score display
   - Never multiply `percentage` by 100
   - Returns None for invalid/missing data
   - Lives in `parent_dashboard_v2.py`

2. **`get_feature_summary(user_id)`** — canonical feature access
   - Never use raw `subscription_plan` for feature gating
   - Never infer paid access from `parentId`

3. **`_verify_child_ownership(parent_id, child_id)`** — all parent child endpoints
4. **`require_student`** — all student endpoints
5. **`require_parent`** — all parent endpoints
6. **`require_admin`** — all admin QA endpoints

## Google OAuth Rules (CRITICAL — Updated 2026-06-29)

### Architecture

OAuth onboarding now uses a deterministic backend state machine. The `oauth_profile_complete` DB column is the authoritative signal — NOT identity age heuristics.

| State | Condition | Frontend action |
|-------|-----------|-----------------|
| A | `profile_complete=true` | Route to dashboard immediately |
| B | `needs_role_selection=true` (new user) | Show one-time role picker |
| C | `needs_role_selection=true` (no profile) | Show one-time role picker |
| D | `409 role_conflict` from complete-profile | Show friendly error, block |

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/auth/me` | Canonical OAuth state check — returns `profile_complete`, `needs_role_selection` |
| POST | `/api/auth/oauth/complete-profile` | Secure role assignment — idempotent, blocks role switching |

### DB Migration Required

`backend/migrations/20260629_oauth_profile_complete.sql` — adds `oauth_profile_complete BOOLEAN DEFAULT TRUE`. **Run in Supabase SQL Editor before deploying.**

- Existing profiles: `DEFAULT TRUE` → no forced re-onboarding
- New OAuth profiles: trigger sets `FALSE` → role picker shown once
- After role selected: `/oauth/complete-profile` sets `TRUE`

### Business Rules

1. One role per Google account — enforced by backend (`409` if role differs)
2. `oauth_profile_complete=FALSE` placeholder has `daily_token_limit=0` — AI endpoints blocked even if frontend bypassed
3. **Role cannot be changed via direct Supabase client call** — all role changes go through `/oauth/complete-profile`
4. All new OAuth profiles start FREE_TIER: `access_cbse=False`, `subscription_plan='free'`
5. Legacy rows (pre-migration, `oauth_profile_complete=NULL`) are treated as `True` — no forced re-onboarding

### authClient.js Error Mapping (Fixed 2026-06-29)

| HTTP Status | User-facing message |
|-------------|---------------------|
| 401 | "Your session has expired. Please sign in again." |
| 403 (parent) | "This account is not registered as a Parent." |
| 403 (student) | "This account is not registered as a Student." |
| 403 (teacher) | "This account is not registered as a Teacher." |
| 403 (generic) | "This account does not have access to this page." |
| 409 | Show the `detail` message (safe — role conflict text) |

**NEVER map 403 to "session expired"** — 403 = role mismatch, 401 = token expired.

### Frontend (App.jsx) OAuth Flow

1. `onAuthStateChange` fires with `event=SIGNED_IN` for non-email providers
2. Clear stale `localStorage` before processing
3. Call `GET /api/auth/me` (retry up to 4×, 800ms gap, for trigger async delay)
4. If `needs_role_selection=true` → show role picker (`pendingOauthUser`)
5. Role picker calls `POST /api/auth/oauth/complete-profile` (backend-validated)
6. `_finishOAuthLogin(meData, session)` builds normalized user + calls `handleLogin`

### OAuth Cross-Device Reliability Layer (Updated 2026-06-29)

**Root cause of cross-device silent failure:**  
Supabase PKCE auto-exchanges `code=` and clears the URL before `onAuthStateChange` fires. Old heuristics (URL params + identity age < 5 min) both fail on a second device login → silent failure with no error, no dashboard.

**Fix:** Single reliable rule in App.jsx:
```javascript
const hasAppProfile = !!localStorage.getItem("tutor_user");
// SIGNED_IN + no app profile → fresh login on any device
if (!hasAppProfile) { /* always process as fresh login */ }
```

**New file: `frontend/src/api/oauthDiagnostics.js`**
- `getOrCreateCorrelationId()` — generates/restores from sessionStorage
- `storeCorrelationIdBeforeRedirect()` — call before `signInWithOAuth()`
- `recordStage(stage, status, message, errorCode)` — 14 named stages, **NEVER records tokens**
- `inspectCallbackUrl(url)` — detects `code=`/`error=`/`access_token=` safely (boolean only)
- `getErrorMessage(errorCode)` — user-friendly messages, never raw codes
- `clearOAuthSession()` — removes only `oauth_*` sessionStorage keys, never `sb-*`

**App.jsx reliability improvements:**
1. Explicit PKCE exchange on mount: `supabase.auth.exchangeCodeForSession(window.location.href)`
2. Bounded session retry: 8-attempt backoff (100ms → 1500ms) + 1.5s event listener fallback
3. Correlation ID sent as `X-OAuth-Correlation-ID` header to `/auth/me`
4. Provider error (`error=` in URL) → immediate visible error, not silent spinner
5. Double-invocation guard keyed to `window.location.href`
6. Only `tutor_user` + `tutor_active_page` cleared — never `sb-*` Supabase auth keys

**Legacy rules (now superseded — do not use):**
- ~~Identity age fallback~~ — removed, was unreliable
- ~~URL param detection~~ — removed, Supabase clears URL before handler runs

## Signup Rules

- Teacher role NOT in public signup (admin-created only)
- Student signup: Grade 5–10 selector required
- Parent signup: no grade needed
- All new signups: `access_cbse=false`, `subscription_plan="free"`
- No payment/offer code in signup flow
- Add Child grade dropdown: Grade 5–10 only

## Score Display Rules

Never show scores > 100%. Always use `_normalize_score_pct()` or `safePct()`.

## Feature Matrix

| Feature | Free Tier | Paid |
|---|---|---|
| AI Lessons | Limited | Full |
| Mock Tests | 5/day | Unlimited |
| Ask Doubts | Limited | Full |
| Exemplar | Locked | Full |
| Exemplar Research | Locked | Full |
| Formula Sheet page | Open | Open |
| Formula Sheet expansion | Locked | Full |

## Formula Sheet Rules

- `FORMULA_SHEET_PREMIUM` feature key controls expansion/details
- Free users: see formula name + expression + description (first 3 per chapter)
- Paid users: full expansion — examples, solution steps, memory tips, MCQ practice
- Upgrade modal: same pattern as Exemplar Research (not inline text)
- Upgrade routes to `subscriptionPlans` (NOT `subscription`)
- `formula_sheets` table — use v2 columns if available, fall back to base if 42703 error

## Platform QA Center

### Lesson Quality Audit
- CLI: `python scripts/audit_lesson_quality.py --sample|--all|--fail-critical|--use-llm`
- Reports: `reports/lesson_quality/` (JSON + MD + CSV)
- DB table: `lesson_quality_audit_runs`

### Feature Authorization Audit
- CLI: `python scripts/audit_feature_authorization.py --sample|--all|--fail-critical|--json`
- Reports: `reports/feature_authorization/` (JSON + MD + CSV)
- Patches `feature_authorization_service.resolve_user_subscription` (NOT resolver module)
- 42+ checks: Free/Paid/Expired plans × all features + scenario checks

### Lesson Sections Audit → Repair Pipeline

**Step 1: Audit** — finds lessons missing/failing the 8 canonical sections:
```
introduction | what_you_will_learn | simple_explanation | step_by_step_breakdown
worked_example | common_mistake | quick_check_question | summary
```
Report saved to `reports/lesson_sections/lesson_sections_report.json`.

**Step 2: Repair (Admin UI — Lesson Repair page)**
- Mode: `sample` (10 lessons) | `filtered` (grade/subject/chapter) | `all`
- LLM repair: opt-in only — `use_llm=True` required
- AI Provider panel shows current provider, model, cost estimates per lesson
- Session API key override: takes precedence over Admin Settings, never logged/stored
- Draft-first safety: LLM generates → validation (score ≥90, depth ≥85, 0 critical) → admin reviews → approve → publish
- Publish only writes to `lesson_cache` after explicit admin approval

**Step 2: Repair (CLI)**
```bash
cd backend
.venv/bin/python scripts/repair_lesson_sections.py --sample          # 10 failures
.venv/bin/python scripts/repair_lesson_sections.py --grade 9 --use-llm  # LLM repair
.venv/bin/python scripts/repair_lesson_sections.py --list-failures    # show failures only
.venv/bin/python scripts/repair_lesson_sections.py --validate-only    # validate a draft JSON
```

**Repair task statuses:**
`queued` → `running` → `ready_for_review` (no LLM) or `validation_failed` / `ready_for_review` (LLM)
→ `approved` → `published`  |  `failed` → rerun

**DB tables** (migration: `20260629_lesson_repair_jobs.sql`):
- `lesson_repair_jobs` — job metadata, counters
- `lesson_repair_tasks` — per-lesson tasks with before/after content, validation results

**Safety rules (never violate):**
- `original_content_json` preserved forever — never deleted
- `publish_repaired_task()` only works when `status == 'approved'`
- LLM never runs automatically — `use_llm=True` required in request
- `override_api_key` never logged, never stored, in-memory only
- `requested_by_admin_id` stripped from all API responses

## Child Limits by Plan

| Plan | Child Limit |
|---|---|
| FREE_TIER | 1 |
| NANO | 1 |
| PREMIUM | 1 |
| FAMILY_PREMIUM | 2 |
| ADMIN_GRANT | None (unlimited) |

## CI Configuration

- **Max warnings:** 50 (ESLint) — project currently AT 50 (the maximum)
- **Test runner:** vitest (frontend), pytest (backend)
- **Lint runner:** `eslint src/ --max-warnings 50` on entire `src/` directory
- **Test isolation:** All API calls mocked. No live backend/Supabase in tests.
- **Key constraint:** `findAllByTestId` (async) must be used for elements that appear after data fetches — never `getAllByTestId` (sync) after an initial `findBy*`

## Lesson Rendering Pipeline — normalizeTutorMarkdown (Updated 2026-07-12)

`normalizeTutorMarkdown()` in `frontend/src/utils/markdownCleanup.js` runs 12 passes in this order:

| Step | Function | Purpose |
|---|---|---|
| 0 | `normalizeNestedDollarSignsInDisplay` | Strip `$...$` nested inside `$$...$$` display blocks |
| 1 | `normalizeSpacedDollarMath` | `$ expr $` → `$expr$` (remark-math ignores dollar+space) |
| 2 | `normalizeInlineDisplayMath` | `$$` inline → `$`; trailing `$$` at end-of-line stripped |
| 3 | `normalizeOrphanedDollarSigns` | Odd `$` count on a line → strip trailing orphan `$` |
| 4 | `normalizeBulletPoints` | `•` bullets → `- ` markdown lists |
| 5 | `normalizeMermaidBlocks` | Wrap loose `graph TD` in code fences |
| 6 | `normalizeLatexParentheses` | `(\frac{}{})` → `$...$` |
| 7 | `normalizePlainAlgebra` | `(a+b)^2` → `$...$` |
| 8 | `normalizeSquareBracketMath` | `[\LaTeX]` and `\[...\]` → `$$...$$` |
| 9 | `normalizePlainExponents` | `10^7` → `$10^{7}$` (outside existing math) |
| 10 | `normalizeDollarMath` | Fix `$10...$` currency-lookalike spacing |
| 11 | `removeUnsupportedQuestionClosers` | Rewrite "Would you like..." prompts |

**Critical:** `normalizeTutorMarkdown` only runs on LESSON MARKDOWN — not inside code fences and not on visual-json items. `StructuredVisualBlock.VisualItemText` separately applies `normalizePlainExponents` + `normalizePlainAlgebra` so visual items get math rendering even without `$` delimiters.

## Lesson Rendering Rules (Updated 2026-07-12)

### Tables (Mobile)
All ReactMarkdown section body renders use `LessonMarkdownTable` as the custom `table` component — wraps every `<table>` in `<div style={{ overflowX: "auto" }}>` so tables scroll horizontally on mobile instead of clipping.

### Font Uniformity
- `.lesson-section-body code`: `font-family: inherit` — inline code uses prose typeface
- `.lesson-section-body h1-h4`: normalized to `1rem / 700` — no heading size jumps
- `.lesson-unwrapped-block p`: explicit `16px` to match `.lesson-section-body p`

### Scroll Behaviour
- **Scroll to feedback:** `WorkbookSection` and `CardFeedSection` auto-scroll to the AI feedback div via `scrollIntoView({ behavior: "smooth", block: "nearest" })` when feedback appears
- **Scroll to top:** `LessonsPage.jsx` has a `useEffect([currentStepIndex])` that calls `window.scrollTo({ top: 0, behavior: "smooth" })` on every step change (skips initial mount via `isFirstStepRender` ref)

### Visual Aid Math
`StructuredVisualBlock.VisualItemText` applies `normalizePlainExponents(normalizePlainAlgebra(text))` before rendering — plain-text items like `v^2 = v0^2 + 2ax` render with KaTeX superscripts even without `$` delimiters in the DB content.

## Web MockTestPage — Mobile Fixes (2026-07-13)

### Problems Fixed
1. **Format selector 3-column grid broken on mobile** — inline `gridTemplateColumns: "repeat(3, 1fr)"` was never overridden. Now uses CSS class `mock-format-grid` → stacks to 1 column on ≤ 600px.
2. **MCQ empty options guard** — If `question.options` is `{}` (empty dict from LLM), was silently rendering zero radio buttons. Now shows "⚠ Answer options unavailable" warning.
3. **Question navigator touch targets 36px** (below 44px recommended). Now `.mock-nav-btn` CSS class with 44×44px on mobile.
4. **Option font 20px + question header 28px** — reduced to 16px / 18px at ≤ 760px breakpoint.

### CSS additions (App.css)
- `.mock-format-grid` — `repeat(3,1fr)` on desktop, `1fr` on ≤ 600px
- `.mock-nav-btn` — 36×36px desktop, 44×44px on ≤ 760px
- `@media (max-width: 760px)`: `.premium-option-row` font 16px, `.premium-question-header h4` font 18px, `.premium-question-card` padding 16px

### Tests Added
`frontend/src/tests/MockTestPage.test.jsx` — **28 tests** covering:
- Setup phase: 3 format cards, free/paid lock badges, daily limit counter, Generate button states
- Exam phase: phase transition, navigator buttons, 12 radio inputs, answer selection, answered count
- Empty options guard: warning shown, zero radios, valid options work normally
- Written question: textarea rendered, AI Feedback button shown
- Result phase: score, Answer Review section, Take Another Test navigation

---

## Mobile App — Exam Prep Crash Fix (2026-07-13)

### Root Cause
`mobile/app/(tabs)/examprep-data.ts` was a pure data module (no default React export) placed inside the expo-router `app/` directory. Its `Tabs.Screen` entry in `_layout.tsx` set **both** `href: null` and `tabBarButton: () => null` simultaneously — expo-router v6 forbids this combination and throws:

> Render Error: Cannot use `href` and `tabBarButton` together.

### Fix Applied
1. **`mobile/app/(tabs)/_layout.tsx`** — removed `tabBarButton: () => null` and `tabBarItemStyle: { display: "none" }` from the `examprep-data` Tabs.Screen entry, keeping only `href: null`. This is the canonical expo-router pattern for fully excluding a screen from tab navigation.
2. **`examprep-data.ts` relocated** — moved from `mobile/app/(tabs)/examprep-data.ts` → `mobile/lib/examprep-data.ts`. Data-only modules (no default React export) must not live in the expo-router `app/` directory.
3. **`mobile/app/(tabs)/examprep.tsx`** — import updated from `"./examprep-data"` → `"../../lib/examprep-data"`.
4. **`examprep-data` Tabs.Screen entry removed** from `_layout.tsx` entirely (file no longer in `app/`).

### Rule (add to mobile development guidelines)
- **Never place data-only `.ts` files in `mobile/app/`** — expo-router treats every file there as a potential route.
- **Never combine `href: null` with `tabBarButton`** in a `Tabs.Screen options` — use `href: null` alone to suppress a screen from the tab bar.

---

## Mobile App — Google Auth (2026-07-13)

### Files Changed
| File | Change |
|---|---|
| `mobile/lib/auth.ts` | `signInWithGoogle()` updated: added `skipBrowserRedirect: true`, now returns `{ url, redirectUri, error }` — caller controls browser open |
| `mobile/app/_layout.tsx` | Added `processSession()` — calls `GET /api/auth/me` after every session change; routes to `/auth/role-select` if `needs_role_selection`, `/(tabs)` if ready, `/auth/login` if unauthenticated |
| `mobile/app/auth/login.tsx` | Added Google Sign-In button above email form. Uses `WebBrowser.openAuthSessionAsync` + `supabase.auth.exchangeCodeForSession` |
| `mobile/app/auth/role-select.tsx` | **New** — one-time role picker for Google OAuth new users. POST `/api/auth/oauth/complete-profile` → `supabase.auth.refreshSession()` → `_layout.tsx` routes to `/(tabs)` |
| `mobile/.env.example` | Added Google OAuth setup instructions (Supabase Dashboard + Google Cloud Console redirect URIs) |

### Auth State Machine (`_layout.tsx`)

```
loading → check session → call /api/auth/me
  ├─ needs_role_selection=true → /auth/role-select (Google new user)
  ├─ profile_complete=true     → /(tabs)           (returning user)
  ├─ /api/auth/me unreachable  → /(tabs)           (graceful fallback)
  └─ no session                → /auth/login
```

### Google OAuth Flow (end-to-end)

1. User taps **"Continue with Google"** on `/auth/login`
2. `signInWithGoogle()` calls `supabase.auth.signInWithOAuth({ provider: 'google', skipBrowserRedirect: true })` → returns OAuth URL
3. `WebBrowser.openAuthSessionAsync(url, redirectUri)` opens in-app browser
4. User authenticates with Google; browser redirects to `likhapoha://...?code=...`
5. `supabase.auth.exchangeCodeForSession(result.url)` exchanges PKCE code for Supabase session
6. `_layout.tsx` `onAuthStateChange` fires → `processSession()` → `GET /api/auth/me`
7. **New user** (`needs_role_selection=true`) → `/auth/role-select` → pick role + grade → `POST /api/auth/oauth/complete-profile` → `refreshSession()` → `/(tabs)`
8. **Returning user** (`profile_complete=true`) → `/(tabs)` directly

### Metro / Expo Startup on Zscaler Network
When Zscaler intercepts network traffic, `npx expo start --clear` fails with `TypeError: fetch failed` (Expo CLI's dependency version check is blocked). Always use:
```bash
npx expo start --clear --offline
```
`--offline` skips the dependency network check and Metro starts normally.

### Setup Required (one-time, in Supabase Dashboard)

1. **Authentication → Providers → Google** — enable, add Google Client ID + Secret
2. **Authentication → URL Configuration → Redirect URLs** — add:
   - `likhapoha://` (production)
   - `exp://127.0.0.1:8081` (Expo Go Android)
   - `exp://localhost:8081` (Expo Go iOS)
3. **Google Cloud Console → OAuth 2.0 Credentials → Authorized redirect URIs** — add:
   - `https://dpivlbbyzlbpwnwgajso.supabase.co/auth/v1/callback`

### Business Rules Enforced
- Teacher role not available via Google OAuth (not shown in role picker)
- Student grade selector: 5–10 only
- 409 role conflict → friendly error, user blocked (same as web)
- HTTP 401 = session expired; HTTP 403 = role mismatch (never conflated)
- `oauth_profile_complete` DB column is authoritative — not heuristics

---

## Mobile App — Grade 11/12 + Stream Selection (2026-07-13)

### Files Changed
| File | Change |
|---|---|
| `mobile/lib/auth.ts` | `signUpWithEmail()` and `completeOAuthProfile()` both accept optional `stream` param (sent to backend) |
| `mobile/app/auth/signup.tsx` | Grades extended 5–10 → **5–12**; stream picker shown for Grade 11/12 |
| `mobile/app/auth/role-select.tsx` | Same Grade 5–12 chips + stream picker (Google OAuth new users) |

### Stream Options (Grade 11/12 only)
| Key | Label | Subjects |
|---|---|---|
| `PCM` | Science — PCM | Physics · Chemistry · Maths · English |
| `PCB` | Science — PCB | Physics · Chemistry · Biology · English |
| `PCMB` | Science — PCMB | Physics · Chemistry · Maths · Biology · English |
| `Commerce` | Commerce | Accountancy · Business · Economics · English |
| `Humanities` | Humanities | History · Polsci · Geography · Economics · English |

### Rules
- Selecting Grade 11 or 12 reveals the stream picker (required field)
- Changing grade resets stream selection
- Selecting Grade 5–10 hides stream picker
- Stream passed to backend as `stream` field (backend stores in `profiles.stream` + populates `cbse_subjects`)
- Mirrors web `SignupPage.jsx` logic exactly

---

## Admin Control Page — JWT Fix (2026-07-13)

### Root Cause
`AdminControlPage.jsx` had 5 raw `fetch()` calls using `user?.accessToken`. The `user` object does not have an `accessToken` field → token was `undefined` → `Authorization: Bearer undefined` → backend JWT library throws "token contains an invalid number of segments".

Affected endpoints (all 401 in logs):
- `GET /api/admin-control/blog-collaborators`
- `POST /api/admin-control/blog-collaborators`
- `DELETE /api/admin-control/blog-collaborators/:ghUsername`
- `GET /api/admin-control/logging-settings`
- `POST /api/admin-control/logging-settings`

### Fix
- Added `import { authFetch } from "../api/authClient"` to `AdminControlPage.jsx`
- Replaced all 5 raw `fetch()` calls with `authFetch()` — gets live Supabase session token with 3-retry backoff
- `useEffect` guard changed from `if (user?.accessToken)` → `if (user)`

### Rule
Never use raw `fetch()` with `user?.accessToken` in the web frontend. Always use `authFetch()` from `../api/authClient` for protected backend calls.

---

## Mobile App — Mock Test Fixes (2026-07-13)

### File: `mobile/app/(tabs)/mocktest.tsx`

#### Bug 1 — Answer options never shown (CRITICAL)
Backend returns `options` as dict `{A:"...", B:"...", C:"...", D:"..."}`. Old code used `Array.isArray(q.options)` → always `false` → `options = []` → no answer choices rendered.

**Fix:** `typeof q.options === "object" && !Array.isArray(q.options)` → `Object.entries(q.options)` to render `A. ...`, `B. ...` etc.

#### Bug 2 — Wrong answer field name
Used `q.correct_answer` (undefined) instead of `q.answer` (the actual backend field). Fixed in data normalization and score calculation.

#### Bug 3 — Score always 0
Compared option text values to the wrong field. Now compares selected KEY (`"A"`) to `q.answer` KEY (`"A"`).

#### Bug 4 — Question bank cache miss (slow generation)
Sent `difficulty: "medium"` (lowercase) but `question_bank.difficulty` stores `"Medium"` (capitalized, matching web app). Bank lookup uses `eq("difficulty", value)` — case-sensitive exact match → 0 rows → LLM fallback → 5–15s wait every time.

**Fix:** `DIFFICULTIES = ["Easy", "Medium", "Hard"]` + `useState("Medium")` — difficulty now matches the DB column exactly. Bank hits → <1s response.

---

## Mobile App — Lessons Phase 3 (2026-07-13)

### File: `mobile/app/(tabs)/lessons.tsx`

#### Structured Section Cards
`parseSections()` + `getSectionType()` ported from web `LessonSections.jsx`. Each section auto-detected and rendered as a color-coded card:
- 🎯 Introduction (blue) — keywords: introduction, overview, context
- 📘 Concept (amber) — keywords: explanation, concept, breakdown
- 🧪 Examples (green) — keywords: worked example, step-by-step
- ⚠️ Watch Out (orange) — keywords: common mistake, warning, avoid
- ✅ Quick Check (red) — keywords: quick check, practice, self check
- 📌 Summary (purple) — keywords: summary, recap, revision, key points

#### Likha Poha AI GIF Loading Screen
`getLoadingMessage(stepIndex, subject)` — exact port from `LessonsPage.jsx` — 6 steps × 6 subjects (Maths/Science/Hindi/Social/English/default). Shows `likhapohaai.gif` + animated bouncing dots + subject/step/chapter info while lesson generates.
- Android: GIF animates natively via `Image` component
- iOS: static first frame + `ActivityIndicator` overlay (no expo-image needed)

#### Quick Check Interactive MCQ
`parseMCQ(content)` extracts question/options (A/B/C/D)/answer/explanation from Quick Check section markdown. `MCQWidget` renders:
- Tappable A/B/C/D option buttons
- Instant validation: green ✓ correct / red ✗ wrong + dimmed others
- Explanation shown after answer
- "🔄 Try Again" button for wrong answers
- Falls back to plain markdown if no MCQ detected

#### Math Formula Rendering — LaTeX → Unicode
`react-native-markdown-display` has no KaTeX support. `$$...$$ ` and `$...$` were showing as raw LaTeX text.

**Fix: `mathToUnicode(latex)`** — 60+ regex transformations:
- `\sqrt{x}` → `√(x)`, `^2` → `²`, `_1` → `₁`
- `\frac{a}{b}` → `(a)/(b)`, `\text{Word}` → `Word`
- `\times → ×`, `\pm → ±`, `\leq → ≤`, `\pi → π`, `\infty → ∞`

**Fix: `MathAwareMarkdown` component** — splits content by `$$...$$` blocks:
- Display math: rendered as styled 📐 formula card (accent-color left border)
- Inline `$...$`: converted to Unicode inline within `<Markdown>`
- Regular markdown: passes through unchanged

**IMPORTANT for future mobile lesson work:**
- Do NOT pass raw lesson markdown directly to `<Markdown>` — always use `<MathAwareMarkdown>`
- `SectionCard` uses `MathAwareMarkdown` for all non-MCQ sections
- MCQ widget `parseMCQ()` strips `**` bold before parsing — handles both bold and plain formats

#### Quick Check MCQ Format (Backend Enforced — 2026-07-13)
`TUTOR_SYSTEM` in `tutor_service.py` now requires ALL Quick Check questions to use MCQ (4 options A/B/C/D) or True/False format with an explicit `Answer: X` line. Open-ended descriptive questions are banned from this section.

**Required format in generated lessons:**
```
Which of the following is an irrational number?

A) 0.5
B) √2
C) 22/7
D) 1.25

Answer: B

Explanation: √2 is irrational because it cannot be expressed as p/q.
```

**Why this matters:**
- `parseMCQ()` in `mobile/app/(tabs)/lessons.tsx` detects `A) B) C) D)` options + `Answer:` line to render the interactive MCQ widget
- Without this format, Quick Check falls back to plain markdown (no interactivity)
- Old **cached** lessons still have open-ended questions — use the "Refresh lesson" button (admin) or wait for cache expiry to get MCQ format on existing chapters

**Do NOT invalidate the lesson cache globally** — refresh on a per-chapter basis as needed.

#### Step Navigation
- Prev ◀ / Next ▶ bar with step counter "2/5" and step name
- Progress dots (gray=upcoming, brand=current, green=completed) — tappable to jump
- Footer nav after lesson loads: Previous / Next Step / ✅ Complete

---

## File Locations

| Purpose | File |
|---|---|
| **OAuth state machine** | `frontend/src/App.jsx` (onAuthStateChange handler) |
| **OAuth diagnostics utility** | `frontend/src/api/oauthDiagnostics.js` (correlation IDs, stages, URL inspection) |
| **OAuth endpoints** | `backend/app/routes/auth.py` (GET /me, POST /oauth/complete-profile) |
| **OAuth DB migration** | `backend/migrations/20260629_oauth_profile_complete.sql` |
| **OAuth backend tests** | `backend/tests/test_oauth_flow.py` (21 tests) |
| **OAuth reliability tests** | `frontend/src/tests/OAuthReliability.test.jsx` (22 tests) |
| **Auth error mapping** | `frontend/src/api/authClient.js` |
| **Auth error mapping tests** | `frontend/src/tests/OAuthErrorMapping.test.jsx` |
| **Auth reliability tests** | `frontend/src/tests/AuthSessionReliability.test.jsx` |
| **Lesson Repair page** | `frontend/src/pages/AdminLessonRepairPage.jsx` |
| **Lesson Repair API client** | `frontend/src/api/lessonRepair.js` |
| **Lesson Repair API routes** | `backend/app/routes/lesson_repair.py` (11 admin endpoints) |
| **Lesson Repair service** | `backend/app/services/lesson_repair_service.py` |
| **Lesson Repair CLI** | `backend/scripts/repair_lesson_sections.py` |
| **Lesson Repair DB migration** | `backend/migrations/20260629_lesson_repair_jobs.sql` |
| **Lesson Repair backend tests** | `backend/tests/test_lesson_repair.py` (28 tests) |
| **Lesson Repair frontend tests** | `frontend/src/tests/AdminLessonRepairPage.test.jsx` (23 tests) |
| Student dashboard | `frontend/src/pages/StudentDashboardPage.jsx` |
| Student dashboard CSS | `frontend/src/pages/StudentDashboardPage.css` |
| Student dashboard API | `backend/app/routes/student_dashboard.py` |
| Formula Sheet page | `frontend/src/pages/FormulaSheetPage.jsx` |
| Formula Sheet API | `backend/app/routes/formula_sheets.py` |
| Formula Sheet seed | `backend/scripts/seed_formula_sheets.py` |
| Exam schedule API | `backend/app/routes/exam_schedule.py` |
| Parent dashboard | `frontend/src/pages/ParentDashboardPage.jsx` |
| Parent components | `frontend/src/components/parent/` |
| Admin QA Center | `frontend/src/pages/AdminQACenterPage.jsx` |
| Feature Auth Audit | `frontend/src/pages/FeatureAuthAuditPage.jsx` |
| QA Center APIs | `backend/app/routes/admin_qa.py` |
| Lesson Quality Audit | `backend/scripts/audit_lesson_quality.py` |
| Feature Auth Audit | `backend/scripts/audit_feature_authorization.py` |
| Lesson Sections Audit | `backend/scripts/audit_lesson_sections.py` |
| Score normalization | `_normalize_score_pct()` in `parent_dashboard_v2.py` |
| Subscription resolver | `backend/app/services/subscription_resolver_service.py` |
| Feature authorization | `backend/app/services/feature_authorization_service.py` |
| Auth client (friendly errors) | `frontend/src/api/authClient.js` |
| Signup page | `frontend/src/pages/SignupPage.jsx` |
| Content management docs | `LikhapohaContext-docs/docs/CONTENT_MANAGEMENT.md` |
| **Platform Chat widget** | `frontend/src/components/PlatformChat.jsx` |
| **Platform Chat API client** | `frontend/src/api/platformChat.js` |
| **Platform Chat backend routes** | `backend/app/routes/platform_chat.py` |
| **Platform Chat DB migration** | `backend/migrations/20260712_platform_chat.sql` |
| **Chat Storage policies** | `backend/migrations/20260712_chat_storage_policies.sql` |
| **Admin Chat settings page** | `frontend/src/pages/AdminChatPage.jsx` |
| **Product Bugs page** | `frontend/src/pages/AdminIssuesPage.jsx` |
| **Product Bugs backend** | `backend/app/routes/issues.py` (includes bulk-close) |
| **Markdown normalization pipeline** | `frontend/src/utils/markdownCleanup.js` |
| **Lesson sections renderer** | `frontend/src/components/LessonSections.jsx` |
| **Structured visual block** | `frontend/src/components/StructuredVisualBlock.jsx` |
| **Lesson page (scroll-to-top, step nav)** | `frontend/src/pages/LessonsPage.jsx` |
| **Lesson + section CSS** | `frontend/src/App.css` |
| **Mock Test page (web)** | `frontend/src/pages/MockTestPage.jsx` |
| **Mock Test page tests** | `frontend/src/tests/MockTestPage.test.jsx` (28 tests) |
| **Mobile app root** | `mobile/` (React Native / Expo SDK 54, react-native 0.81.5, expo-router 6.x) |
| **Mobile Supabase client** | `mobile/lib/supabase.ts` (expo-secure-store adapter) |
| **Mobile auth helpers** | `mobile/lib/auth.ts` (signInWithEmail, signInWithGoogle, checkAuthState) |
| **Mobile authFetch** | `mobile/lib/authFetch.ts` (JWT fetch with same 401/403 mapping as web) |
| **Mobile screens** | `mobile/app/(tabs)/` — index (Dashboard), lessons, mocktest, account, examprep |
| **Exam Prep screen** | `mobile/app/(tabs)/examprep.tsx` |
| **Exam Prep data** | `mobile/lib/examprep-data.ts` — static reference data (EXAMS, SC, QR) — NOT a route |
| **Mobile auth screens** | `mobile/app/auth/` — login.tsx, signup.tsx, role-select.tsx |
| **Mobile Google OAuth role picker** | `mobile/app/auth/role-select.tsx` — shown once for new Google OAuth users |
| **Shared JS package** | `shared/@likhapoha/shared` — API clients + utils used by both web and mobile |
| **Shared API clients** | `shared/api/` — auth, lesson, doubt, mockTest, analytics, progress, syllabus, tts |
| **Shared utils** | `shared/utils/` — markdownCleanup, resolveSubscription, subjectAccess, syllabusDefaults |
| **Mobile env template** | `mobile/.env.example` |
| **EAS Build config** | `mobile/eas.json` |
| **Mobile theme** | `mobile/lib/theme.ts` — dark/light mode palette via `useTheme()` |
| **Mobile dark mode** | All auth screens (login, signup, role-select) use `useTheme()` |
| **Mobile app icon** | `mobile/assets/icon-1024.png` — 1024×1024 Likha Poha AI logo (purple bg) |
| **Local APK build script** | `mobile/build_apk.sh` v5.0 — auto git pull + 14-point verification + rm -rf android |
| **Analytics screen** | `mobile/app/(tabs)/analytics.tsx` |
| **Doubt screen** | `mobile/app/(tabs)/doubt.tsx` |
| **Exemplar screen** | `mobile/app/(tabs)/exemplar.tsx` |
| **Formula screen** | `mobile/app/(tabs)/formula.tsx` |
| **Learn screen** | `mobile/app/(tabs)/learn.tsx` |

---

## Session Changes — 2026-07-13 to 2026-07-14

### Mobile Auth
- **`login.tsx`**: Google OAuth via WebView (Zscaler-safe using `react-native-webview`); username login via `GET /api/auth/lookup-email/{username}`; dark mode via `useTheme()`
- **`signup.tsx`**: Grades 5–12 selector; stream picker for Grade 11/12 (PCM/PCB/PCMB/Commerce/Humanities); dark mode
- **`role-select.tsx`** (NEW): Shown once after Google OAuth for new users to pick grade + stream
- **`auth.ts`**: `signInWithGoogle()` WebView flow; stream passed to `completeOAuthProfile`

### Mobile Screens
- **`lessons.tsx`**: Grade selector locked for free tier (`isGradeLocked = studentGrade !== null && !hasFullAccess`); Exemplar chapters locked for free tier (`isExemplarLocked`); feature access from `GET /api/subscription/features`; LaTeX → Unicode via `mathToUnicode()`; interactive MCQ widget in Quick Check sections; animated loading dots + Likha Poha AI GIF
- **`examprep.tsx`** (NEW): 3 tabs — Quick Reference | Practice | Simulated Test. Simulated Test = NTA-style timed exam with countdown timer, question palette (grey/green/purple/brand), Mark & Next / Clear / Save & Next, submit with snake_case body (`question_id`, `selected_option`, `time_spent_seconds`), score screen (correct/wrong/skipped). API: `POST /api/exam-prep/simulated-tests/start` → fetch questions per subject → `POST /api/exam-prep/simulated-tests/{id}/submit`
- **`index.tsx`**: "Exam Prep" button added to both welcome state and loaded Quick Actions grid
- **`app/_layout.tsx`**: SafeAreaProvider at root; auth state machine

### Mobile Libs
- **`lib/theme.ts`** (NEW): dark/light mode palette, `useTheme()` hook
- **`lib/authFetch.ts`**: Fixed `detail.toLowerCase()` crash when detail is not a string

### Mobile Build
- **`build_apk.sh`** v5.0: auto `git pull` + 14-point feature verification (aborts if any check fails) + `rm -rf android` before prebuild + version header printed at start
- **`index.ts`**: Fixed to `import "expo-router/entry"` (was using old `registerRootComponent(MinimalApp)`)
- **`MinimalApp.tsx`**: Deleted (was showing purple test screen)
- **`app.json`**: icon updated to `./assets/icon-1024.png`
- **`assets/icon-1024.png`**: 1024×1024 Likha Poha AI logo, adaptive icon with purple background

### Frontend Web
- **`App.css`**: Mobile responsiveness fixes; lesson card font sizes unified to 16px
- **`AdminControlPage.jsx`**: authFetch compatibility fix
- **`LessonsPage.jsx`**: Font size consistency fixes
- **`MockTestPage.jsx`**: CSS fixes
- **`vite.config.js`**: Added stub env vars (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) in test section → fixes `AdminControlPage.test.jsx` CI failure

### Key API Patterns (mobile)
- Username → email: `GET /api/auth/lookup-email/{username}` → `{email}` → `supabase.auth.signInWithPassword`
- Feature gating: `GET /api/subscription/features` → `{has_full_access, features: {EXEMPLAR: {allowed}, ...}}`
- Simulated test start: `POST /api/exam-prep/simulated-tests/start` body `{exam: "jee_main"}` → `{test_id, question_ids, duration_minutes}`
- Questions per subject: `GET /api/exam-prep/questions?exam={}&subject={}&limit={}` → `{questions}`
- Simulated test submit: `POST /api/exam-prep/simulated-tests/{id}/submit` body `{answers: [{question_id, selected_option}], time_spent_seconds}`
