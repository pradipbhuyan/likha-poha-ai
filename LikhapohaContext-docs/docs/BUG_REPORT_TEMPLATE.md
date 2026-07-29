# Bug Report Template — Likha Poha AI

> **How to use:** Copy this file. Fill in sections 1–4. The rest is auto-context for the AI agent.
> The filled report is what you paste to Codex / Axet / any AI agent instead of the raw auto-generated report.

---

## SECTION 1 — Defect Identity

| Field | Value |
|---|---|
| **Defect ID** | `<!-- paste UUID from bug tracker -->` |
| **Type** | `content issue` / `rendering bug` / `access bug` / `crash` / `data bug` / `UI issue` |
| **Severity** | `critical` / `high` / `medium` / `low` |
| **Status** | `open` |
| **Reported** | `<!-- date/time -->` |

---

## SECTION 2 — What the User Sees (Exact Description)

```
<!-- Paste the exact raw description from the bug tracker here.
     Include screenshots, copied text, error messages verbatim.
     Do not paraphrase — verbatim reproduction is the diagnostic baseline. -->
```

### Context

| Field | Value |
|---|---|
| **Route** | `<!-- e.g. /lessons, /doubt, /quiz, /dashboard -->` |
| **Grade** | `<!-- e.g. Grade 11 -->` |
| **Subject** | `<!-- e.g. Physics -->` |
| **Chapter** | `<!-- e.g. Units and Measurements -->` |
| **Step / Section** | `<!-- e.g. Core explanation -->` |
| **User role** | `<!-- student / teacher / parent / admin -->` |
| **Platform** | `<!-- e.g. MacIntel, Windows, Android -->` |
| **Viewport** | `<!-- e.g. 1374×645 -->` |
| **Admin Notes** | `<!-- any triage notes -->` |

---

## SECTION 3 — Suspected Root Cause (optional, fill if known)

```
<!-- If you already have a hypothesis, write it here.
     Otherwise leave blank — the AI will investigate. -->
```

---

## SECTION 4 — Definition of Done for This Fix

<!-- Check all that apply. The AI must satisfy every checked item. -->

- [ ] The visual bug / incorrect output is no longer reproducible
- [ ] Regression test added covering the exact input that caused the bug
- [ ] No existing tests were broken
- [ ] `cd frontend && npx vitest run` — all tests pass
- [ ] `cd frontend && npx eslint src/ --max-warnings 50` — 0 errors, ≤ 49 warnings
- [ ] `cd backend && .venv/bin/python -m pytest` — all tests pass (if backend touched)
- [ ] Cached/stored content regenerated if the bug was in stored data (not just rendering)

---

---
---

# CODEX SESSION BOOTSTRAP — Auto-Context (Do Not Remove)

> The sections below are auto-injected platform context. The AI agent must read these before touching any code.

## Platform Overview

**Likha Poha AI** — production CBSE tutoring platform (Grades 5–12), used by students, parents, teachers, and admins.

**Stack:** React + Vite (frontend) · FastAPI + Python (backend) · Supabase (Postgres + Auth) · Razorpay (payments) · OpenAI GPT (AI features)

**Repository root:** `/Users/a0247716/Pradips_Project/cbse-tutor-platform/`  
All relative paths are relative to this root.

```
cbse-tutor-platform/
├── frontend/                 ← React + Vite SPA
├── backend/                  ← FastAPI + Python
├── LikhapohaContext-docs/    ← Product/engineering documentation
│   └── docs/                 ← Full handbook (01–14 + FEATURE_MATRIX, DECISION_LOG, API_GUIDELINES)
└── TESTING.md
```

---

## Mandatory Pre-Task Reading

Before touching any code, read these in order:

1. `LikhapohaContext-docs/docs/CODEX_BOOTSTRAP.md`
2. `LikhapohaContext-docs/docs/CODEX_CONTEXT.md`
3. `LikhapohaContext-docs/CODEX_CONTEXT.md` (latest snapshot)
4. `LikhapohaContext-docs/docs/01_PRODUCT_CONTEXT.md`
5. `LikhapohaContext-docs/docs/02_ARCHITECTURE.md`

**Route-specific reading:**

| Route / Area | Read Also |
|---|---|
| Lessons, AI content, LLM | `docs/09_AI_PLATFORM.md` |
| Subscriptions, payments, access | `docs/03_SUBSCRIPTIONS.md` + `FEATURE_MATRIX.md` |
| Admin features | `docs/05_ADMIN_PLATFORM.md` |
| Teacher features | `docs/06_TEACHER_PLATFORM.md` |
| Parent features | `docs/07_PARENT_PLATFORM.md` |
| Student dashboard | `docs/08_STUDENT_PLATFORM.md` |
| Tests | `docs/12_TESTING.md` |
| Dev standards | `docs/13_DEVELOPMENT_GUIDE.md` |

---

## Test Counts (Do Not Regress)

| Suite | Count |
|---|---|
| Backend (pytest) | 535+ |
| Frontend (vitest, 46 files) | 578 |

**CI thresholds:** ESLint 0 errors / ≤ 49 warnings. All tests must pass before `git push`.

**Mandatory pre-push:**
```bash
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```

---

## Architecture Contract (Never Violate)

| Rule | Detail |
|---|---|
| Backend owns authorization | Frontend gating is UX only — never security |
| Canonical subscription resolver | `backend/app/services/subscription_resolver_service.py` → `resolve_user_subscription()` |
| Canonical feature authorization | `backend/app/services/feature_authorization_service.py` → `authorize_feature()` |
| Frontend resolver | `frontend/src/utils/resolveSubscription.js` → `hasPaidAccess(user)` |
| Feature summary endpoint | `GET /api/subscription/features` — use in frontend, never inspect raw fields |

---

## Hard Rules

### Subscription & Access
- **NEVER** use `user.parentId` to infer paid access
- **NEVER** branch on `user.subscriptionPlan === "free"` (ambiguous — maps to both Free Tier AND Nano)
- **ALWAYS** use `hasPaidAccess(user)` in frontend
- **ALWAYS** use `authorize_feature(user_id, Feature.X)` in backend

### Database
- Table: `student_progress` — NOT `chapter_progress`
- Column: `test_history.percentage` — NOT `score` or `total_questions`
- Score normalization: `_normalize_score_pct()` — **never** multiply `percentage × 100`

### Exemplar Gating
- Frontend: `chapter?.includes("Exemplar:")` — never `startsWith`
- Backend: `"exemplar:" in chapter.lower()` — same reason

### Google OAuth (App.jsx)
- Auth state source of truth: `oauth_profile_complete` DB column — not age heuristics
- `onAuthStateChange`: check `isOAuthRedirect` BEFORE `localStorage.getItem("tutor_user")`
- HTTP 401 = session expired; HTTP 403 = role mismatch — **never** map 403 to "session expired"

### Lesson Rendering
- `parseSections()` handles 5 heading patterns — never reduce
- `getRenderableContent()`: `Question:` + `Step N:` = worked example — **never** strip the solution
- Inline `$$expr$$` → fix with `fixInlineDisplayMath()` before ReactMarkdown
- `normalizeTutorMarkdown()` in `frontend/src/utils/markdownCleanup.js` — runs at render time on raw LLM output; the Supabase cache stores raw content untouched

### CSS
- Inline fallbacks must be light-mode: `var(--text, #111827)` not `var(--text, #f8fafc)`

---

## Key File Map

| What | Where |
|---|---|
| App routing + OAuth state machine | `frontend/src/App.jsx` |
| Lesson content rendering + parseSections | `frontend/src/components/LessonSections.jsx` |
| Math/markdown normalization pipeline | `frontend/src/utils/markdownCleanup.js` |
| Lessons page | `frontend/src/pages/LessonsPage.jsx` |
| Tutor AI service (LLM + cache) | `backend/app/services/tutor_service.py` |
| Lesson cache service | `backend/app/services/lesson_cache_service.py` |
| Lesson repair | `frontend/src/pages/AdminLessonRepairPage.jsx`, `backend/app/services/lesson_repair_service.py` |
| Subscription resolver (backend) | `backend/app/services/subscription_resolver_service.py` |
| Feature authorization (backend) | `backend/app/services/feature_authorization_service.py` |
| Frontend resolver | `frontend/src/utils/resolveSubscription.js` |
| Student dashboard | `frontend/src/pages/StudentDashboardPage.jsx` |
| Parent dashboard | `frontend/src/pages/ParentDashboardPage.jsx` |
| Teacher dashboard | `frontend/src/pages/TeacherDashboardPage.jsx` |
| Admin QA Center | `frontend/src/pages/AdminQACenterPage.jsx` |
| Theme CSS variables | `frontend/src/App.css` |
| OAuth diagnostics | `frontend/src/api/oauthDiagnostics.js` |
| TTS + audio cache | `backend/app/services/audio_cache_service.py`, `tts_service.py` |
| Exam Prep | `frontend/src/pages/ExamPrepPage.jsx`, `backend/app/services/exam_prep_service.py` |

---

## Child Limits by Plan

| Plan | Child Limit |
|---|---|
| FREE_TIER | 1 |
| NANO | 1 |
| PREMIUM | 1 |
| FAMILY_PREMIUM | 2 |
| ADMIN_GRANT | Unlimited |

---

## Anti-Patterns (Never Do These)

| Anti-Pattern | Reason |
|---|---|
| `if (user.parentId) return true` | parentId ≠ paid access |
| `subscriptionPlan === "free"` for access checks | ambiguous |
| `percentage * 100` | already 0–100 |
| `startsWith("Exemplar:")` | Part prefix breaks it |
| Hardcoded dark text in inline styles | use light fallbacks |
| Adding `_finishOAuthLogin` to OAuth `useEffect` deps | infinite re-subscription |
| Rolling custom feature access checks | use `authorize_feature()` |
| `chapter_progress` table | does not exist |
| `test_history.score` or `.total_questions` | do not exist |
| `$$expr$$` inline without `fixInlineDisplayMath()` | breaks KaTeX rendering |
| Calling `normalizeTutorMarkdown()` server-side | it is a client-only render-time function |

---

## ESLint Rule
`react-hooks/exhaustive-deps` warning → `// eslint-disable-line` goes on the **closing** `}, []);` line, not the opening line.
