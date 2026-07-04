# Likha Poha AI — Codex Context File

> Feed this single file to any AI agent before starting a new task.
> Last updated: 2026-06-27

---

## What This Product Is

Likha Poha AI is a CBSE tutoring platform for Indian students (Grades 1–12) and their families.

**Personas**: Students, Parents, Teachers, Admins.

**Core features**: AI-powered CBSE lessons, doubt solving, mock tests, NCERT Exemplar access, progress tracking, parent dashboard, teacher classroom management.

**Tech stack**:
- Frontend: React + Vite (single-page app)
- Backend: FastAPI + Python
- Database: Supabase (Postgres + Auth)
- Payments: Razorpay
- AI: OpenAI GPT models

---

## Directory Layout

```
/backend
  app/
    routes/          — FastAPI route modules by domain
    services/        — Reusable domain logic
    data/            — Static data (syllabus, subscription plans)
    models/          — Pydantic schemas
  tests/             — pytest tests
  migrations/        — SQL migration files (idempotent)

/frontend
  src/
    api/             — API client functions (one file per domain)
    components/      — Shared UI components
    components/teacher/ — Teacher portal components
    pages/           — Route-level page components
    utils/           — Shared utilities (resolveSubscription, etc.)
    tests/           — Vitest tests
    config/          — Frontend config (subscriptionPlans.js)
```

---

## Subscription Plans

| Canonical Key | Plan Name | Price | Duration | Access |
|---|---|---|---|---|
| `FREE_TIER` | Free Tier | ₹0 | indefinite | Limited |
| `NANO` | Premium Nano | ₹99 | 8 days | Full |
| `PREMIUM` | Premium | ₹299 | 30 days | Full |
| `FAMILY_PREMIUM` | Family Premium | ₹499 | 30 days | Full (2 children) |
| `ADMIN_GRANT` | Admin Access | admin | perpetual | Full |

**The DB column `subscription_plan` uses raw keys: `free`, `starter`, `premium`, `family_premium`.** The `free` key is shared by both Free Tier AND Nano paid users. NEVER branch on raw plan key without using the canonical resolver.

---

## Canonical Subscription Resolver

**Backend**: `backend/app/services/subscription_resolver_service.py`
- Function: `resolve_user_subscription(user_id: str) -> dict`
- Returns: `canonical_plan_key`, `plan_name`, `has_full_access`, `restrictions`, `access_source`

**Frontend**: `frontend/src/utils/resolveSubscription.js`
- Function: `resolveSubscription(user, offerAccess) -> { activeTier, canonicalPlanKey, hasFullAccess, ... }`
- Helper: `hasPaidAccess(user)` — returns true if user has active paid access

**DO NOT** branch on `user.subscriptionPlan`, `profile.access_cbse`, or `user.parentId` directly. Use the resolver.

---

## CRITICAL: parentId Never Grants Paid Access

A student created by a parent has `parent_id` set. This does NOT mean they have a paid subscription.

**Rule**: Paid access = `access_cbse = true` on the student's OWN profile (set by payment webhook) AND `subscription_expires_at` in the future (if time-limited).

**Wrong** (historical bug — now fixed):
```js
if (user.parentId) return true;  // WRONG — used in old hasPaidAccess()
const isFreeUser = !user.accessCbse && !user.parentId;  // WRONG — used in old MockTestPage
```

**Correct**:
```js
import { hasPaidAccess } from "../utils/resolveSubscription";
const isPaid = hasPaidAccess(user); // checks accessCbse + subscriptionExpiresAt only
const isFreeUser = user?.role === "student" && !hasPaidAccess(user);
```

---

## Canonical Feature Authorization

**Backend**: `backend/app/services/feature_authorization_service.py`

```python
from app.services.feature_authorization_service import authorize_feature, Feature, require_feature

# Use require_feature to auto-raise 403:
require_feature(user_id, Feature.EXEMPLAR)

# Or inspect:
result = authorize_feature(user_id, Feature.MOCK_TEST_UNLIMITED)
if not result["allowed"]:
    raise HTTPException(403, detail=result["restriction_message"])
```

Feature constants: `Feature.LESSONS`, `Feature.EXEMPLAR`, `Feature.EXEMPLAR_RESEARCH`, `Feature.MOCK_TEST`, `Feature.MOCK_TEST_UNLIMITED`, `Feature.ASK_DOUBTS`, `Feature.AI_ASSISTANT`, `Feature.LESSON_DOWNLOAD`

**Frontend**: `GET /api/subscription/features` returns per-feature `{allowed, limited}` for current user.

---

## Feature Access Matrix

| Feature | FREE_TIER | NANO | PREMIUM | FAMILY | ADMIN_GRANT |
|---|---|---|---|---|---|
| LESSONS | Limited (DKB-only) | Full | Full | Full | Full |
| LESSON_DOWNLOAD | No | Yes | Yes | Yes | Yes |
| EXEMPLAR | **No** | Yes | Yes | Yes | Yes |
| EXEMPLAR_RESEARCH | **No** | Yes | Yes | Yes | Yes |
| MOCK_TEST | Limited (5/day) | Full | Full | Full | Full |
| MOCK_TEST_UNLIMITED | **No** | Yes | Yes | Yes | Yes |
| ASK_DOUBTS | Limited (DKB-only) | Full | Full | Full | Full |
| AI_ASSISTANT | Limited | Full | Full | Full | Full |

**Mock test daily limit**: `FREE_MOCK_TEST_DAILY_LIMIT = 5` (backend) = `FREE_DAILY_MOCK_LIMIT = 5` (frontend). Both must stay in sync.

---

## Exemplar Chapter Gating

Exemplar lesson chapters are named with prefix `"Exemplar:"` in the syllabus (e.g., `"Exemplar: Chemical Reactions and Equations"`).

**Backend gate in `lesson.py`** (after free-user bypass):
```python
_chapter_name = (data.chapter or "").strip()
if _chapter_name.lower().startswith("exemplar") or ": exemplar" in _chapter_name.lower():
    from app.services.feature_authorization_service import authorize_feature, Feature
    _fauth = authorize_feature(user.id, Feature.EXEMPLAR)
    if not _fauth["allowed"]:
        raise HTTPException(403, ...)
```

**Frontend gate in `LessonsPage.jsx`**:
```js
import { hasPaidAccess } from "../utils/resolveSubscription";
const hasPaidAccessForLessons = hasPaidAccess(user);  // NOT user.parentId
const isExemplarLocked = chapter?.startsWith("Exemplar:") && !hasPaidAccessForLessons;
```

---

## Backend Route Map

```
/api/auth/           — signup, login, profile, password reset, Google OAuth
/api/syllabus/       — syllabus data, admin chapter overrides
/api/lesson/         — lesson generation, follow-up, textbook visuals
/api/doubt/          — doubt answering (DKB + LLM)
/api/mock-test/      — mock test generation
/api/analytics/      — test history, progress
/api/progress/       — chapter progress save/load
/api/subscription/   — resolve, features endpoint, expiry job, catalog
/api/payments/       — Razorpay order creation/verification, admin test payment
/api/offer/          — offer code redemption
/api/parent-dashboard/ — parent/child data
/api/teacher/        — teacher classroom management (Phase 1 + 2)
/api/teacher-dashboard/ — teacher summary (legacy)
/api/admin/          — admin operations, bulk, views, analytics, support
/api/admin-control/  — platform settings (AI on/off, lesson card style)
/api/chatbot/        — public chatbot widget (no auth)
/api/rag/            — RAG document management (admin-only)
```

---

## Frontend API Client Map

```
src/api/
  auth.js            — login, signup, profile
  lesson.js          — generateLesson, askLessonFollowUp, textbook visuals
  doubt.js           — answerDoubt, getDoubtHistory
  mockTest.js        — generateMockTest
  analytics.js       — saveTestHistory, saveWrongAnswers
  progress.js        — getChapterProgress, saveChapterProgress
  syllabus.js        — getSyllabus
  teacherDashboard.js — all teacher APIs (Phase 1 + 2)
  platformSettings.js — getLessonCardPublicSettings
  adminControl.js    — admin control APIs
```

---

## Teacher Portal Structure

```
TeacherDashboardPage.jsx       — command center (single-page, tabs for deep-dive)
  ├── Dashboard tab            — KPIs + attention queue + tasks + invitations + student preview
  ├── Students tab             — full roster → opens StudentWorkspace
  ├── Classrooms tab           — manage + ClassroomAnalyticsCard
  ├── Invitations tab          — CRUD with status filter
  └── Tasks tab                — open/completed/dismissed + create form

components/teacher/
  StudentWorkspace.jsx         — 7-section slide-over: Overview/Progress/Assessments/Notes/Activity/Parent/Settings
  TeacherAssistantCard.jsx     — rule-based summary (no AI)
  InterventionQueue.jsx        — critical/medium/low groups with actions
  SuggestedTaskModal.jsx       — pre-filled task from intervention
  ClassroomAnalyticsCard.jsx   — per-classroom metrics (graceful "Not available yet")
```

Teacher Phase 2 API endpoints at `/api/teacher/`:
- `GET /students/{id}/timeline`, `GET /interventions`
- `GET/POST/PATCH /tasks`, `/tasks/{id}/complete`, `/tasks/{id}/dismiss`
- `GET /classrooms/{id}/analytics`
- `GET/POST/PATCH/DELETE /students/{id}/notes`
- `GET /students/{id}/parent-contact`, `POST /students/{id}/message-parent`

**Security rules for teacher notes**:
- Notes are `visibility=teacher_private`
- Note CONTENT must never appear in audit log metadata
- Notes are never exposed to students or parents via any API

---

## Subscription Resolver Logic (Precedence Order)

1. Active paid subscription (`subscription_expires_at` in future) → PREMIUM
2. Perpetual paid plan (non-`free` key + `access_cbse=True` + no expiry) → PREMIUM
3. Legacy Nano (`free` key + `access_cbse=True` + no expiry + role≠parent) → NANO
4. Valid offer/free-trial redemption (`offer_redemptions` table) → FREE_TIER with limited access
5. Admin grant (`access_cbse=True`, no expiry, no offer) → ADMIN_GRANT
6. Default → FREE_TIER

**Expiry job** (`expiry_job_service.py`): sets `access_cbse=False`, `subscription_expires_at=None` for expired plans. Must never revoke admin grants. Idempotent.

---

## Payment Flow

1. `POST /api/payments/create-order` — creates Razorpay order
2. Frontend: user pays
3. `POST /api/payments/verify` — verifies signature, idempotency guard, activates plan
4. `POST /api/payments/webhook` — Razorpay webhook backup (also idempotent)
5. Plan activation: sets `access_cbse=True`, `subscription_expires_at`, `subscription_plan` on profile
6. Child profiles inherit access only if payment explicitly covers them (Family plan)

---

## Offer Codes

Two types:
- `free_trial` — sets `access_cbse=False` (DKB-only access, limited)
- `discount` — sets `access_cbse=True` (paid access at discount)

Offer check: `is_free_tier_user(user_id)` from `offer_access_service.py` — returns True for all free/expired users.

---

## Key Safety Rules for Agents

1. **Backend owns authorization** — frontend gating is UX only, never security.
2. **Use `authorize_feature()` for all premium features** — never roll custom access checks.
3. **Use `hasPaidAccess(user)` in frontend** — never check `user.parentId` or `user.subscriptionPlan === "free"` for access decisions.
4. **`parentId` ≠ paid access** — a child of a free parent has `parentId` but no paid features.
5. **Exemplar chapters start with `"Exemplar:"` in syllabus data** — gate them in both backend and frontend.
6. **Never expose**: Supabase service-role key, JWTs, API keys, Razorpay secrets, temporary passwords in audit logs.
7. **Never break**: existing test suite (102 backend + 376 frontend passing), subscription resolver, payment idempotency.
8. **Add regression tests** for every behavior change, especially authorization changes.
9. **Teacher notes content** must never appear in audit log `metadata` field.
10. **`subscription_plan = "free"` is ambiguous** — it means both Free Tier AND Nano paid. Always use `canonical_plan_key`.

---

## Test Suite Summary

Backend tests (pytest):
```
tests/test_feature_authorization.py   — 69 tests, feature matrix, bug regressions
tests/test_subscription_resolver_regression.py — resolver correctness
tests/test_subscription_states.py     — subscription state transitions
tests/test_mock_test.py               — mock test access
tests/test_security.py                — endpoint security
tests/test_admin_access.py            — admin-only enforcement
tests/test_payments.py                — payment flows
tests/test_teacher_classroom_platform.py — Phase 1 teacher
tests/test_teacher_p2.py              — Phase 2 teacher (23 tests)
```

Frontend tests (Vitest):
```
src/tests/TeacherDashboard.test.jsx   — teacher command center
src/tests/TeacherDashboardPage.test.jsx — teacher tabs
src/tests/TeacherUXPhase3.test.jsx    — student workspace, interventions, tasks (25 tests)
src/tests/AdminAnalyticsCorrectness.test.jsx
src/tests/AdminOperationsPage.test.jsx
```

Run backend: `cd backend && .venv/bin/python -m pytest`
Run frontend: `cd frontend && npm run test`

---

## CI Rules

- `npm run lint -- --max-warnings 50` must pass (0 errors, ≤50 warnings)
- All backend and frontend tests must pass before pushing
- Error messages in backend endpoints must match what existing tests assert

---

## What NOT to Do

- Do not add `if (user.parentId) return true` to any access check
- Do not check `user.subscriptionPlan === "free"` for access decisions (ambiguous)
- Do not bypass `enforce_learning_access` without checking Exemplar chapter names
- Do not store note content in audit log metadata
- Do not call `resolve_user_subscription` or `is_free_tier_user` inside tight loops — cache if needed
- Do not expose parent email from `/api/teacher/students/{id}/parent-contact` — only `has_email: bool`
- Do not create new subscription tiers without updating: resolver, feature matrix, FEATURE_MATRIX.md, subscription plans config, and tests
- Do not rename `subscription_plan` DB column
- Do not add new raw plan keys — normalize to canonical keys

---

## Audio Cache System (Added 2026-07-03)

### New Files
```
backend/app/services/audio_cache_service.py   — store_audio(), get_cached_audio_url(), routing logic
backend/app/routes/tts.py                     — GET /tts/cached-url, GET /tts/audio-cache/overview
backend/scripts/prewarm_lesson_audio.py       — CLI prewarm script (--grade, --subject, --resume, --limit)
backend/migrations/20260703_lesson_audio_cache.sql
```

### New API Routes (prefix: /api/tts)
- `GET  /api/tts/cached-url?grade=&subject=&chapter=&step_title=` → `{cached: bool, url?: str}`
- `GET  /api/tts/audio-cache/overview?grade=` → admin summary

### New API Routes (prefix: /api/cache-management)
- `GET  /api/cache-management/audio/overview/{grade_slug}` → `{audio_cached, audio_expected, total_mb}`
- `POST /api/cache-management/prewarm/audio/{grade_slug}` → triggers background TTS prewarm

### Storage Routing Rule (CRITICAL)
- Grade 9 audio → Supabase 1 `lesson-audio` bucket
- All other grades → Supabase 2 `lesson-audio` bucket
- `lesson_audio_cache` DB table → always Supabase 1
- Do NOT change this routing without updating `audio_cache_service.py`

### TTS Voice Routing Rule
- Subject contains "hindi" → `hi-IN-SwaraNeural`
- All other subjects → `en-IN-NeerjaNeural`
- Source: `frontend/src/pages/LessonsPage.jsx` `getVoiceForSubject()`

### TUTOR_SYSTEM MATH RULES (Critical — DO NOT WEAKEN)
Every math expression MUST be in `$...$`. NEVER write math in plain `()`. NEVER use `$$` inside `()`. NEVER repeat a variable like `x^2 x 2`. See `backend/app/services/tutor_service.py` MATH RULES section.

### Broken Lesson Repair Pattern
```bash
# 1. Scan for broken LaTeX
# 2. Archive broken rows in lesson_cache (status='archived')
# 3. Regenerate:
echo "yes" | python3 scripts/prewarm_lessons.py --grade "Grade N" --subject "Maths"
```

### New Frontend Constants (LessonsPage.jsx)
- `HINDI_VOICE = "hi-IN-SwaraNeural"`
- `getVoiceForSubject(subject)` — auto-detects Hindi

### Admin Guide — NVIDIA Models (Confirmed Working July 2026)
Only 3 models work on free-tier nvapi-* accounts:
- `meta/llama-3.1-8b-instruct` (fastest, recommended for batch)
- `meta/llama-3.1-70b-instruct` (best quality)
- `meta/llama-3.2-3b-instruct` (ultra-fast)
