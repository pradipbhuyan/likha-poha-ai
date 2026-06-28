# Roadmap

_Last updated: 2026-06-28_

## Completed

### Foundation
- Free signup without offer-code requirement
- Canonical subscription resolver (`resolveSubscription`, `_normalize_score_pct`)
- Plan catalog and parity tests
- Payment idempotency and webhook deduplication
- Audit logs
- Subscription timeline
- Expiry job
- Admin Console refactor (quick actions, search, favorites, notifications, recent activity)
- Teacher Platform Phase 1–3

### Parent Experience (Phase 1–3) ✅
- `GET /api/parent/dashboard/summary` — canonical dashboard with feature badges
- `GET /api/parent/children/{id}/detail` — enriched child detail
- `GET /api/parent/children/{id}/analytics` — progress, mock tests, activity
- `GET /api/parent/children/{id}/academic-insights` — homework/exam insights
- `GET /api/parent/children/{id}/progress-report` — print-friendly report
- `GET /api/parent/notifications` — notification center (DB + rule-based fallback)
- `parent_notifications` table
- UX redesign: ParentHeroSummary, ParentChildStatusCard, ParentActionPlan, ParentNotificationGroups, ParentAccessExplanation, ParentProgressStory, ParentChildWorkspace (9-tab)
- Add Child: credentials panel + "What to do next" instructions
- Child limit enforced from subscription resolver (not hardcoded)
- All scores use `_normalize_score_pct()` — no 1200%/1600% bugs
- `student_progress` table (not `chapter_progress`) + `percentage` column (not `score/total_questions`)

### Student Experience ✅
- Student Dashboard redesign (Option 1 card-based layout)
- `GET /api/student/dashboard/summary` — all dashboard data in one call
- Hero + Quick Stats + Continue Learning + Today's Plan + AI Coach + Subject Progress + Mock Tests + Weak Topics + Achievements + Utility + Motivation
- Responsive: 4-col → 2-col (tablet) → 1-col (mobile)
- CSS variables for light/dark mode
- Score normalization canonical helper shared across endpoints
- 439 tests passing

### Signup Redesign ✅
- Single-step card-based signup (Option 1)
- Parent + Student roles only (Teacher removed from public signup)
- Grade selector for students (Grade 5–10)
- Google Sign In button
- All new accounts start on Free Tier
- No payment/offer code in signup flow

### Auth / Session Reliability ✅
- Session recovery on app boot: verifies Supabase session, refreshes, fetches fresh profile
- Google OAuth hang fixed: full OAuth only on actual redirect URLs, not page reload
- `handleLogin` fetches fresh profile for ALL roles
- Friendly error messages: no Supabase/JWT internals shown to users
- `handleRefreshUser()` utility for post-mutation refresh

### Child Login Flow ✅
- `create_student` returns `login_id` + `login_email`
- Silent profile insert failure detected → auth user rollback → 500 error
- Credentials panel shown to parent after child creation
- Signup `access_cbse=false` enforced (no paid access on signup)

## In Progress / Near-term

### Content Platform
- Lesson management admin UI
- Question bank improvements
- Exemplar management
- AI prompt management
- Bulk import/export

### Teacher Platform Enhancements
- Teacher-student chat
- Assignment tracking
- Parent-teacher communication summaries

## Pending

### Homework & Exam Center
- `homework` and `exam_schedule` tables to be created
- Until then: `homework.available=false`, `exams.available=false` shown gracefully

### Advanced Student Features
- Adaptive learning path
- Topic mastery tracking
- Mock test improvement charts with trend analysis
- Achievements/badges system (beyond current rule-based)

### Production Readiness
- E2E browser tests
- Performance/load testing (stress test existing endpoints)
- Backup/restore procedures
- Monitoring and alerting refinements
- Sentry/error tracking integration
- Operational dashboard enhancements

## Key Technical Debt

1. `chapter_progress` table was never created — always use `student_progress`
2. `test_history.score` column does not exist — always use `percentage`
3. Free Tier child limit defaults to 1 (None from resolver) — handled explicitly in v2 endpoint
4. Google OAuth returning user hang — fixed with URL gate check
