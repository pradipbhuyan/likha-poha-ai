# Likhapoha AI — Codex Context

_Last updated: 2026-06-28_

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

- **Backend:** 486+ tests passing
- **Frontend:** 486 tests passing (41 test files, vitest)
- **Lint:** 0 errors, 50 warnings (at limit)

## API Routes (Student)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/student/dashboard/summary` | All student dashboard data |
| GET | `/api/student/exams` | Student exam schedule |
| POST | `/api/student/exams` | Add exam date |
| PATCH | `/api/student/exams/{id}` | Update exam |
| DELETE | `/api/student/exams/{id}` | Cancel exam |
| GET | `/api/student/formula-sheets` | Formula sheets (chapter-wise, freemium) |

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

## Google OAuth Rules (CRITICAL)

1. **Session recovery must skip when `?code=` is in URL** — otherwise races with OAuth handler
2. **`isOAuthRedirect` check must be FIRST** in `onAuthStateChange` — before localStorage check
3. **Identity age fallback** — if `session.user.identities[0].created_at < 5 min`, treat as fresh OAuth
4. **`authFetch` retries** — 3 steps: `getSession()` → `refreshSession()` → wait 800ms + retry
5. **Never show `localStorage.getItem("tutor_user")` shortcut on fresh OAuth redirect**

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

## Child Limits by Plan

| Plan | Child Limit |
|---|---|
| FREE_TIER | 1 |
| NANO | 1 |
| PREMIUM | 1 |
| FAMILY_PREMIUM | 2 |
| ADMIN_GRANT | None (unlimited) |

## File Locations

| Purpose | File |
|---|---|
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
| Score normalization | `_normalize_score_pct()` in `parent_dashboard_v2.py` |
| Subscription resolver | `backend/app/services/subscription_resolver_service.py` |
| Feature authorization | `backend/app/services/feature_authorization_service.py` |
| Auth client (friendly errors) | `frontend/src/api/authClient.js` |
| Signup page | `frontend/src/pages/SignupPage.jsx` |
| Content management docs | `LikhapohaContext-docs/docs/CONTENT_MANAGEMENT.md` |
