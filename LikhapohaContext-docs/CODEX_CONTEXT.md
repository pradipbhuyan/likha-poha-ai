# Likhapoha AI — Codex Context

_Last updated: 2026-06-28_

## What is Likhapoha AI

Likhapoha AI is a CBSE learning platform (Grade 5–10) with AI-powered lessons, mock tests, doubt solving, exemplar practice, and progress analytics.

## Platform Roles

| Role | Dashboard | Notes |
|---|---|---|
| `student` | StudentDashboardPage | Redesigned (2026-06-28) — card-based layout |
| `parent` | ParentDashboardPage | Phase 1–3 complete |
| `teacher` | TeacherDashboardPage | Phase 1–3 complete |
| `admin` | AdminControlPage | Full operations |
| `sales` | SalesLeadPage | — |

## Current Test State

- **Backend:** 439 tests passing (all pytest suites)
- **Frontend:** 439 tests passing (38 test files, vitest)
- **Lint:** 0 errors, 50 warnings (at limit)

## API Routes (Student)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/student/dashboard/summary` | All student dashboard data in one call |
| GET | `/api/auth/profile` | Canonical profile + subscription refresh |
| GET | `/api/auth/lookup-email/{username}` | Username → email for login |
| GET | `/api/analytics/history` | Mock test history |

## API Routes (Parent)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/parent/dashboard/summary` | Canonical parent dashboard |
| GET | `/api/parent/children/{id}/detail` | Child detail with mock tests, progress |
| GET | `/api/parent/children/{id}/analytics` | Richer analytics (90d) |
| GET | `/api/parent/children/{id}/academic-insights` | Homework/exam insights |
| GET | `/api/parent/children/{id}/progress-report` | Print-friendly report |
| GET | `/api/parent/notifications` | Notification center |
| POST | `/api/parent/notifications/{id}/read` | Mark one read |
| POST | `/api/parent/notifications/read-all` | Mark all read |
| POST | `/api/parent-dashboard/create-student` | Add child account |

## Critical Database Rules

1. **Use `student_progress`** — not `chapter_progress` (does not exist)
2. **Use `test_history.percentage`** — not `score` or `total_questions` (don't exist)
3. **Use `ai_usage_logs`** — not `ai_conversation_logs` or `student_activity` (don't exist)
4. **Missing tables return graceful empty** via `_safe_query()` — never crash

## Critical Code Rules

1. **`_normalize_score_pct(percentage, raw_score, max_score)`** — use for ALL score display
   - Never multiply `percentage` by 100
   - Returns None for invalid/missing data
   - Lives in `parent_dashboard_v2.py`, imported by `parent_dashboard_p2.py` and `student_dashboard.py`

2. **`get_feature_summary(user_id)`** — canonical feature access
   - Never use raw `subscription_plan` for feature gating
   - Never infer paid access from `parentId`

3. **`_verify_child_ownership(parent_id, child_id)`** — all parent child endpoints
4. **`require_student`** — all student endpoints
5. **`require_parent`** — all parent endpoints

## Signup Rules

- Teacher role NOT in public signup (admin-created only)
- Student signup: Grade 5–10 selector required
- Parent signup: no grade needed
- All new signups: `access_cbse=false`, `subscription_plan="free"`
- No payment/offer code in signup flow

## Auth Rules

- Google OAuth: full processing only on actual redirect URLs (`#access_token=` or `?code=`)
- Session recovery on boot: verify session → refresh → fetch fresh profile
- Expired session: clear localStorage → redirect to login
- Error messages: friendly to user, technical details console-only

## Score Display Rules

Never show scores > 100%. Always use `_normalize_score_pct()` or `safePct()` in frontend.

## Feature Matrix

| Feature | Free Tier | Paid |
|---|---|---|
| AI Lessons | Limited | Full |
| Mock Tests | 5/day | Unlimited |
| Ask Doubts | Limited | Full |
| Exemplar | Locked | Full |
| Exemplar Research | Locked | Full |

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
| Student dashboard page | `frontend/src/pages/StudentDashboardPage.jsx` |
| Student dashboard CSS | `frontend/src/pages/StudentDashboardPage.css` |
| Student dashboard API | `backend/app/routes/student_dashboard.py` |
| Parent dashboard page | `frontend/src/pages/ParentDashboardPage.jsx` |
| Parent components | `frontend/src/components/parent/` |
| Parent APIs | `backend/app/routes/parent_dashboard_v2.py` + `parent_dashboard_p2.py` |
| Score normalization | `_normalize_score_pct()` in `parent_dashboard_v2.py` |
| Canonical subscription resolver | `backend/app/services/subscription_resolver_service.py` |
| Canonical feature authorization | `backend/app/services/feature_authorization_service.py` |
| Auth client (friendly errors) | `frontend/src/api/authClient.js` |
| Signup page | `frontend/src/pages/SignupPage.jsx` |
