# Parent Platform

_Last updated: 2026-06-28_

## Vision

The Parent Dashboard helps parents understand their child's progress clearly and take immediate action — in under 10 seconds.

## Implemented Features (Phase 1–3)

### Phase 1 — Canonical Parent Dashboard
- `GET /api/parent/dashboard/summary` — children with subscription, feature badges, activity, recommendations, notifications
- `GET /api/parent/children/{id}/detail` — enriched child detail with progress, mock tests, weak topics
- Parent-child ownership enforced on all endpoints
- `parentId` alone never grants paid access
- Feature badges from canonical `get_feature_summary()` — never from raw `access_cbse`
- Child limit enforced from canonical subscription resolver (FREE/NANO/PREMIUM=1, FAMILY=2, ADMIN=None)

### Phase 2 — Analytics, Notifications, Insights, Report
- `GET /api/parent/children/{id}/analytics` — progress, mock tests (with `percentage` column fix), activity (90d), strengths/weaknesses
- `GET /api/parent/children/{id}/academic-insights` — homework unavailable gracefully, mock test suggestions
- `GET /api/parent/children/{id}/progress-report` — print-friendly report, teacher-private notes never included
- `GET /api/parent/notifications` — persistent DB + rule-based fallback (feature_locked, child_inactive, low_score, expiry)
- `POST /api/parent/notifications/{id}/read` and `/read-all`
- `parent_notifications` table with indexes (idempotent migration)
- `_normalize_score_pct()` canonical helper — scores always 0-100, never multiplied from wrong columns

### Phase 3 — UX Completion
New extracted components:
- `ParentHeroSummary` — greeting, child count, plan chip, urgent banner, CTAs
- `ParentChildStatusCard` — status (Doing Well/Restricted/Inactive/Expiring), stats, progress bar, top recommendation
- `ParentActionPlan` — "Things to Do Tonight" from recommendations + notifications
- `ParentNotificationGroups` — grouped (Needs Attention / Good News / Upcoming / Platform Access), mark-read
- `ParentAccessExplanation` — "Platform Access" terminology (NOT "CBSE Access"), feature list with badges
- `ParentProgressStory` — visual progress: subject bars, score trend, strengths, needs practice
- `ParentChildWorkspace` — **8-tab** story-driven drawer: Overview, Today's Plan, Progress, Strengths & Needs, Mock Tests, Homework & Exams, Notifications, Report. (The "Platform Access" tab was removed 2026-08 as redundant; `ParentAccessExplanation.jsx` was deleted entirely — was 9 tabs before this.)

### Add Child Flow
- Creates Supabase auth user + profile in one atomic operation
- Silent profile insert failure detected → rollback auth user → return 500
- Response includes `login_id` and `login_email` for parent to share with child
- Credentials panel with copy buttons shown once after creation
- "What to do next" instructions shown after successful child creation
- Child limit message only shown when parent is truly at their plan's limit (not on first open)
- **Grade dropdown: Grade 5–12** (updated 2026-08 — Grade 11/12 was briefly removed then re-added). Grade 11/12 requires a mandatory stream selection (PCM / PCB / PCMB / Commerce / Humanities), mirroring self-signup; `cbse_subjects` are derived server-side from the chosen stream. Enforced both in `ParentDashboardPage.jsx`'s `AddChildModal` and server-side in `POST /api/parent-dashboard/create-student`.

## Data Sources
- `student_progress` table (not `chapter_progress` which does not exist)
- `test_history.percentage` column (not `score/total_questions` which don't exist)
- `weak_area_alerts` table
- `ai_usage_logs` (90d window)

## Parent Rules
- New parent starts on Free Tier.
- Newly added child starts on Free Tier with `access_cbse=false`.
- `parentId` alone never implies paid access.
- Teacher-private notes never exposed.
- Admin audit metadata never exposed.
- Canonical feature authorization used everywhere.

## Signup
- Single-step card-based signup (Option 1).
- Parent and Student roles only (Teacher removed from public signup).
- Student signup includes Grade selector (Grade 5–10).
- Google Sign In supported.
- All new accounts start on Free Tier.

---

## Add Child Modal — 2026-06-30 Fix

**Issue:** "Child limit reached" upgrade card was shown to new parents (0 children) immediately on opening the modal.

**Fix:** Upgrade card now only shows when `!canAdd && childCount > 0`. New parents (0 children) always see the Add Child form.

**Files:** `frontend/src/pages/ParentDashboardPage.jsx` — `AddChildModal` receives `childCount={children.length}` prop.
