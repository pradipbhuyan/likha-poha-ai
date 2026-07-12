# Ideal Codex Prompt — Likha Poha AI Platform

> Copy everything between the horizontal rules below and paste it as your opening message to Codex before describing any task.

---

---

## CODEX SESSION BOOTSTRAP — Read This Before Any Task

You are working on **Likha Poha AI** — a production CBSE tutoring platform (Grades 5–12) used by students, parents, teachers, and admins. The platform is built with **React + Vite (frontend)**, **FastAPI + Python (backend)**, **Supabase (Postgres + Auth)**, **Razorpay (payments)**, and **OpenAI GPT (AI features)**.

**Repository root:** `/Users/a0247716/Pradips_Project/cbse-tutor-platform/`  
All relative paths below are relative to this root. All `cd` commands should be run from this root unless stated otherwise.

```
cbse-tutor-platform/          ← REPO ROOT (your working directory)
├── frontend/                 ← React + Vite SPA
├── backend/                  ← FastAPI + Python
├── LikhapohaContext-docs/    ← All product/engineering documentation
│   ├── AGENTS.md
│   ├── CODEX_CONTEXT.md      ← latest snapshot
│   └── docs/                 ← full handbook
│       ├── CODEX_BOOTSTRAP.md
│       ├── CODEX_CONTEXT.md
│       ├── 01_PRODUCT_CONTEXT.md … 14_ROADMAP.md
│       ├── FEATURE_MATRIX.md
│       ├── DECISION_LOG.md
│       └── API_GUIDELINES.md
├── docs/                     ← legacy/infra docs (not product rules)
└── TESTING.md
```

---

### STEP 1 — Read These Docs First (Non-Negotiable)

Before touching any code, read the following files in order. All paths are relative to the repo root above:

1. `LikhapohaContext-docs/docs/CODEX_BOOTSTRAP.md` ← start here
2. `LikhapohaContext-docs/docs/CODEX_CONTEXT.md` ← single-file critical context
3. `LikhapohaContext-docs/CODEX_CONTEXT.md` ← latest snapshot (may have newer entries)
4. `LikhapohaContext-docs/docs/01_PRODUCT_CONTEXT.md`
5. `LikhapohaContext-docs/docs/02_ARCHITECTURE.md`

If the task touches subscriptions, payments, or feature access, also read:
- `LikhapohaContext-docs/docs/03_SUBSCRIPTIONS.md`
- `LikhapohaContext-docs/docs/FEATURE_MATRIX.md`

If the task touches a specific role, read the matching doc:
- Admin → `LikhapohaContext-docs/docs/05_ADMIN_PLATFORM.md`
- Teacher → `LikhapohaContext-docs/docs/06_TEACHER_PLATFORM.md`
- Parent → `LikhapohaContext-docs/docs/07_PARENT_PLATFORM.md`
- Student → `LikhapohaContext-docs/docs/08_STUDENT_PLATFORM.md`
- AI/Lessons/Content → `LikhapohaContext-docs/docs/09_AI_PLATFORM.md`

For tests: `LikhapohaContext-docs/docs/12_TESTING.md`.  
For development standards: `LikhapohaContext-docs/docs/13_DEVELOPMENT_GUIDE.md`.

---

### STEP 2 — Current Platform State

**Test counts (passing — do not regress):**
- Backend: 535+ tests (pytest)
- Frontend: 578 tests (vitest, 46 test files)

**CI thresholds:**
- ESLint: 0 errors, ≤ 49 warnings (CI max is 50)
- All backend and frontend tests must pass before `git push`

**Mandatory pre-push commands (always run both):**
```bash
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```
These take ~15 seconds. Never skip them.

---

### STEP 3 — Architecture Contract (Never Violate)

| Rule | Detail |
|---|---|
| Backend owns authorization | Frontend gating is UX only — never security |
| Canonical subscription resolver | `backend/app/services/subscription_resolver_service.py` → `resolve_user_subscription()` |
| Canonical feature authorization | `backend/app/services/feature_authorization_service.py` → `authorize_feature()` / `require_feature()` |
| Frontend resolver | `frontend/src/utils/resolveSubscription.js` → `hasPaidAccess(user)` |
| Feature summary endpoint | `GET /api/subscription/features` — use this in frontend, never inspect raw fields |

---

### STEP 4 — HARD RULES (Violations Will Break Production)

#### Subscription & Access

- **NEVER** use `user.parentId` to infer paid access — a child with a parent is NOT necessarily paid
- **NEVER** branch on `user.subscriptionPlan === "free"` — `"free"` key maps to BOTH Free Tier AND Nano paid (ambiguous)
- **NEVER** use raw `profile.access_cbse` or `profile.subscription_plan` for feature decisions — always use the canonical resolver
- **ALWAYS** use `hasPaidAccess(user)` in frontend (checks `accessCbse` + `subscriptionExpiresAt` together)
- **ALWAYS** use `authorize_feature(user_id, Feature.X)` or `require_feature()` in backend for any premium feature

#### Database Field Names

- Table: `student_progress` — NOT `chapter_progress` (does not exist)
- Column: `test_history.percentage` — NOT `score` or `total_questions` (do not exist)
- Table: `ai_usage_logs` — NOT `ai_conversation_logs` (does not exist)
- Score normalization: use `_normalize_score_pct(percentage, raw_score, max_score)` — **never multiply `percentage` × 100**

#### Exemplar Chapter Gating

- Frontend: `chapter?.includes("Exemplar:")` — **never** `startsWith("Exemplar:")` (Part prefix breaks startsWith)
- Backend: `"exemplar:" in _chapter_name.lower()` — same reason
- Gate: `require_feature(user_id, Feature.EXEMPLAR)` in backend `lesson.py`

#### Secrets — Never Expose

- Supabase service-role key
- JWTs / Bearer tokens
- Razorpay secrets or raw webhook payloads
- OpenAI API keys
- Temporary child passwords
- Teacher note content in audit log metadata

#### Google OAuth (App.jsx)

- **Auth state machine source of truth:** `oauth_profile_complete` DB column — NOT identity age heuristics
- `onAuthStateChange`: check `isOAuthRedirect` BEFORE `localStorage.getItem("tutor_user")`
- Session recovery `useEffect` MUST be skipped when `?code=` or `#access_token=` is in URL
- Never clear `sb-*` Supabase auth keys from localStorage — only clear `tutor_user` + `tutor_active_page`
- HTTP 401 = session expired; HTTP 403 = role mismatch — **never map 403 to "session expired"**

#### CSS / Light + Dark Mode

- Inline style fallbacks MUST be light-mode defaults: `var(--text, #111827)` not `var(--text, #f8fafc)`
- `.topbar` MUST have `position: relative; z-index: 500` (backdrop-filter creates stacking context)

#### Lesson Rendering

- `parseSections()` in `LessonSections.jsx` handles 5 heading patterns — never reduce to fewer
- `getRenderableContent()`: if section has `Question:` + `Step N:`, it is a worked example — **never strip the solution**
- `$$` inline → fix with `fixInlineDisplayMath()` before passing to ReactMarkdown

#### ESLint / React Hooks

- `react-hooks/exhaustive-deps` warning reported on `useEffect(() => {` line — `// eslint-disable-line` goes on the **closing** `}, []);` line
- `_finishOAuthLogin` inside OAuth `useEffect` is intentionally excluded from deps — do not add it

---

### STEP 5 — Child Limits by Plan

| Plan | Child Limit |
|---|---|
| FREE_TIER | 1 |
| NANO | 1 |
| PREMIUM | 1 |
| FAMILY_PREMIUM | 2 |
| ADMIN_GRANT | Unlimited |

---

### STEP 6 — Key File Map

| What | Where |
|---|---|
| App routing + OAuth state machine | `frontend/src/App.jsx` |
| Auth error mapping | `frontend/src/api/authClient.js` |
| Subscription resolver (backend) | `backend/app/services/subscription_resolver_service.py` |
| Feature authorization (backend) | `backend/app/services/feature_authorization_service.py` |
| Subscription resolver (frontend) | `frontend/src/utils/resolveSubscription.js` |
| Score normalization | `_normalize_score_pct()` in `backend/app/routes/parent_dashboard_v2.py` |
| Lesson content + parseSections | `frontend/src/components/LessonSections.jsx` |
| Lessons page (top bar layout) | `frontend/src/pages/LessonsPage.jsx` |
| Student dashboard | `frontend/src/pages/StudentDashboardPage.jsx` |
| Parent dashboard | `frontend/src/pages/ParentDashboardPage.jsx` |
| Teacher dashboard | `frontend/src/pages/TeacherDashboardPage.jsx` |
| Admin QA Center | `frontend/src/pages/AdminQACenterPage.jsx` |
| Admin Lesson Repair | `frontend/src/pages/AdminLessonRepairPage.jsx` |
| OAuth diagnostics | `frontend/src/api/oauthDiagnostics.js` |
| TTS + audio cache | `backend/app/services/audio_cache_service.py`, `tts_service.py` |
| Tutor AI service | `backend/app/services/tutor_service.py` |
| Exam Prep | `frontend/src/pages/ExamPrepPage.jsx`, `backend/app/services/exam_prep_service.py` |
| Theme CSS variables | `frontend/src/App.css` |

---

### STEP 7 — Definition of Done

A task is **complete only when all of the following are true:**

- [ ] Backend authorization is enforced (not just frontend-gated)
- [ ] Frontend renders the correct state on both **desktop and mobile**
- [ ] Regression tests added for every behavior change
- [ ] `cd frontend && npx vitest run` — all tests pass
- [ ] `cd frontend && npx eslint src/ --max-warnings 50` — 0 errors, ≤ 49 warnings
- [ ] `cd backend && .venv/bin/python -m pytest` — all tests pass
- [ ] No secrets, tokens, or PII exposed in API responses, audit logs, or console
- [ ] Documentation updated if any business rule, API contract, or permission changed
- [ ] Migrations are idempotent and additive (never destructive unless explicitly instructed)

---

### STEP 8 — What NOT to Do

| Anti-Pattern | Reason |
|---|---|
| `if (user.parentId) return true` | parentId ≠ paid access |
| `user.subscriptionPlan === "free"` for access | ambiguous — means both Free Tier and Nano |
| `getAllByTestId` after `findBy*` | use `findAllByTestId` (async retry) after async fetch |
| `percentage * 100` | percentage is already 0–100 |
| `startsWith("Exemplar:")` | Part N prefix breaks it — use `includes("Exemplar:")` |
| Hardcoded dark text in inline styles | light mode fallbacks must be light values |
| Adding `_finishOAuthLogin` to OAuth useEffect deps | causes infinite re-subscription |
| Rolling custom feature access checks | always use `authorize_feature()` |
| Calling `resolve_user_subscription` in a loop | cache the result |
| Inventing data for analytics when unavailable | show "Not available yet" |
| `chapter_progress` table | does not exist — use `student_progress` |
| `test_history.score` or `.total_questions` | do not exist — use `.percentage` |
| Storing note content in audit log metadata | teacher notes are private — metadata only |
| `$$expr$$` inline LaTeX | use `$expr$` for inline — run `fixInlineDisplayMath()` |

---

### NOW — Describe Your Task

After confirming you have read the documents listed in Step 1, implement the following:

> **[REPLACE THIS LINE WITH YOUR SPECIFIC TASK DESCRIPTION]**

Constraints:
- Do not violate any product rules listed above
- Add regression tests for any behavior you change
- Update documentation in `LikhapohaContext-docs/` if any business rule, permission, or API contract changes
- Keep changes additive and backward-compatible unless explicitly told otherwise
- If the task requires changing subscription logic, payment flows, or the database schema, ask one targeted clarifying question before proceeding

---
