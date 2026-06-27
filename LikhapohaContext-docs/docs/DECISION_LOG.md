# Decision Log

## Platform Access replaces CBSE Access

Status: Approved

Reason: "CBSE Access" is an implementation term. "Platform Access" is clearer for admins and users.

---

## Offer code no longer required for signup

Status: Implemented

Reason: Users should start on Free Tier with email/password or Google Auth.

---

## Canonical Subscription Resolver

Status: Implemented

File: `backend/app/services/subscription_resolver_service.py`

Reason: Avoid duplicated plan logic and legacy `free` key ambiguity. All access decisions must use the canonical resolver output (`canonicalPlanKey`, `hasFullAccess`, `restrictions`).

---

## Feature Authorization Layer

Status: Implemented (2026-06-27)

File: `backend/app/services/feature_authorization_service.py`

Reason: Prevent Free Tier users from accessing premium features through missed UI/API checks.

Critical bugs that triggered this implementation:
- `hasPaidAccess()` returned True if `user.parentId` was set — children of any parent (including free-plan parents) incorrectly received paid access.
- `isFreeUser` in MockTestPage excluded students with `parentId` — no daily mock test limit applied.
- Backend mock_test.py check was inverted: `not access_cbse and not is_free_tier_user()` always evaluated to False for free users.
- No Exemplar chapter gate existed in the lesson generation endpoint.
- LessonsPage.jsx used `user.parentId` to infer paid access.

Resolution:
- Canonical `authorize_feature(user_id, Feature.X)` must be used for all premium feature decisions.
- `hasPaidAccess(user)` in frontend now uses `accessCbse` and `subscriptionExpiresAt` only.
- `parentId` alone NEVER grants feature access.
- Lesson generation checks Exemplar chapter name prefix and calls `authorize_feature(Feature.EXEMPLAR)`.

---

## Admin Operations Dashboard

Status: Implemented

Reason: Admins need mobile-friendly visibility into payments, webhooks, subscriptions, usage, alerts, and expiry jobs.

---

## Teacher Success Platform — Phase 1 (Classroom Management)

Status: Implemented

Backend: `teacher_classroom.py` — student CRUD, invitations, classrooms, credential management.

---

## Teacher Success Platform — Phase 2 (Actionable Dashboard)

Status: Implemented (2026-06-27)

Backend: `teacher_classroom_p2.py`

New endpoints:
- `GET /api/teacher/students/{id}/timeline` — unified student activity timeline
- `GET /api/teacher/interventions` — prioritized intervention queue (critical/medium/low)
- `GET/POST/PATCH /api/teacher/tasks` + complete/dismiss — teacher task management
- `GET /api/teacher/classrooms/{id}/analytics` — per-classroom metrics
- `GET/POST/PATCH/DELETE /api/teacher/students/{id}/notes` — private notes (never exposed to students/parents)
- `GET /api/teacher/students/{id}/parent-contact` + `POST message-parent` — parent communication

New DB tables: `teacher_tasks`, `teacher_student_notes`, `teacher_parent_messages`

---

## Teacher UX Completion — Phase 3 (Command Center)

Status: Implemented (2026-06-27)

Frontend: `TeacherDashboardPage.jsx` redesigned from tabbed admin screen to single-page productivity command center.

New components:
- `StudentWorkspace.jsx` — 7-section student detail (Overview/Progress/Assessments/Notes/Activity/Parent/Settings)
- `TeacherAssistantCard.jsx` — rule-based summary (no external AI)
- `InterventionQueue.jsx` — grouped critical/medium/low with View + Create Task actions
- `SuggestedTaskModal.jsx` — pre-filled task from intervention data
- `ClassroomAnalyticsCard.jsx` — per-classroom analytics with graceful "Not available yet"

Dashboard now shows: attention queue, today's tasks, pending invitations, student preview — all visible without clicking tabs.

---

## Payments are idempotent

Status: Implemented

Reason: Duplicate verify/webhook calls must not double-activate subscriptions.

---

## /api/subscription/features endpoint

Status: Implemented (2026-06-27)

Reason: Frontend pages need a single source-of-truth feature access endpoint rather than inspecting raw subscription fields. Returns per-feature `{allowed, limited}` for the authenticated user.
