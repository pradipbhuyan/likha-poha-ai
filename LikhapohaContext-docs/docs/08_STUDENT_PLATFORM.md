# Student Platform

_Last updated: 2026-06-28_

## Vision

The Student Dashboard motivates learning and makes the next best action immediately obvious — students should know what to do in under 5 seconds.

## Implemented Features

### Student Dashboard Redesign (Option 1 — Card-Based Layout)

**Backend:** `GET /api/student/dashboard/summary`
- Profile (safe fields: username, grade, streak, lessons_completed)
- Subscription + feature access (canonical resolver — never from raw `access_cbse`)
- Mock tests: total, avg, best, subject averages, recent, score trend
  - All scores via `_normalize_score_pct()` — never >100%
- Progress from `student_progress` table (last chapter for Continue Learning)
- Weak topics from `weak_area_alerts`
- Activity from `ai_usage_logs` (90d window)
- Rule-based achievements: streak, lessons, first test, high score
- Rule-based recommendations: inactive/practice/mock/upgrade
- Today's plan: 4 prioritized tasks
- Safety: student ownership enforced, no teacher/admin data exposed

**Frontend layout:**
1. **Hero** — "Good morning, Name!" + Day Streak card + Overall Progress card
2. **Quick Stats Row** — Today's Goal · Lessons Left · Next Exam · XP Points
3. **Main Row (3 cols)** — Continue Learning / Today's Plan / AI Learning Coach
4. **Middle Row (4 cols)** — Subject Progress / Recent Mock Tests / Weak Topics / Achievements
5. **Utility Row (4 cols)** — Revision Center / AI Doubt Solver / Upcoming Exams / Quick Actions
6. **Motivation Card** — rotating motivational quote

**CSS** — Responsive: 4-col → 2-col (tablet) → 1-col (mobile), CSS variables for light/dark mode.

**Fallback:** Every card handles missing data gracefully — no blank panels.

### Student Signup
- Single-step card-based signup (SignupPage.jsx)
- Parent + Student roles only (Teacher not in public signup)
- Student signup includes Grade selector (Grade 5–10)
- Grade saved to profile and used to show relevant lessons on dashboard
- Google Sign In supported
- All new accounts start on Free Tier

## Access Rules

Student features must follow the canonical feature authorization matrix:

| Feature | Free Tier | Paid |
|---|---|---|
| AI Lessons | Limited | Full |
| Mock Tests | 5/day | Unlimited |
| Ask Doubts | Limited | Full |
| Exemplar | Locked | Full |
| Exemplar Research | Locked | Full |

- `parentId` alone never implies paid access.
- Feature access comes from `get_feature_summary(user_id)` — never from raw `subscription_plan`.

## Data Sources

| Data | Table | Key Column |
|---|---|---|
| Mock test history | `test_history` | `percentage` (0-100), `raw_score`, `max_score` |
| Lesson progress | `student_progress` | `completed`, `current_step_index` |
| Weak areas | `weak_area_alerts` | `best_score`, `subject`, `chapter` |
| AI activity | `ai_usage_logs` | `feature`, `created_at` |

**Important:** `chapter_progress` table does NOT exist. Use `student_progress`.
**Important:** `test_history.score` and `test_history.total_questions` columns do NOT exist. Use `percentage`.

## Score Normalization

All score display must use `_normalize_score_pct(percentage, raw_score, max_score)`:
- `percentage` in [0,100] → use directly
- `percentage` > 100 → invalid, fallback to `raw_score / max_score * 100`
- No valid data → return `None` → show "Score not available"
- Never multiply an already-percent value by 100
- Never divide by zero

## Auth / Session

- Session recovery on app boot: verifies Supabase session, refreshes token, fetches fresh profile
- Google OAuth hang fix: full OAuth processing only runs on actual OAuth redirect URLs (`#access_token=` or `?code=`), not on normal page reload with existing session
- `handleLogin` fetches fresh `/api/auth/profile` for ALL roles (not just students)
- `handleRefreshUser()` available to refresh after data mutations

## Student Profile Fields

| Field | Description |
|---|---|
| `study_streak_days` | Current learning streak |
| `lessons_completed` | Total lessons generated |
| `grade` | Grade 5–10 (set at signup) |
| `board` | CBSE (default) |
| `access_cbse` | Canonical paid access flag |
| `subscription_expires_at` | Expiry date if applicable |
