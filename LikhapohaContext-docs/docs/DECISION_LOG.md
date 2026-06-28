# Decision Log

_Last updated: 2026-06-28_

This file records key technical decisions made during development, including the reasoning and any constraints that must not be violated.

---

## 2026-06-28: Student Dashboard Redesign

**Decision:** Build `StudentDashboardPage.jsx` as the new student dashboard (Option 1 card-based layout), replacing `DashboardPage.jsx`.

**New endpoint:** `GET /api/student/dashboard/summary` returning all dashboard data in one call.

**Why:** Old dashboard was a single-page component with scattered API calls, no responsive layout, and no clear "what to do next" guidance. New design matches Option 1 mockup with Hero, Quick Stats, Continue Learning, Today's Plan, AI Coach, Subject Progress, Mock Tests, Weak Topics, Achievements, Utility, Motivation.

**Safety:** `require_student` enforced. All scores via `_normalize_score_pct()`. Missing tables return graceful empty. No teacher/admin data exposed.

---

## 2026-06-28: Signup Redesign — Single-Step Card-Based

**Decision:** Replace multi-step SignupPage (1027 lines with pay/offer tabs) with single-step card-based form (295 lines).

**Changes:**
- Teacher role removed from public signup (Parent + Student only)
- Grade selector for students (Grade 5–10)
- Google Sign In button
- No payment, offer code, or step labels
- All new accounts start on Free Tier (`access_cbse=false`)

**Why:** Simpler, faster onboarding. Payment/upgrade happens inside the platform, not during signup.

---

## 2026-06-28: Google OAuth Hang on Return Visit — Fixed

**Decision:** Gate full OAuth processing to only actual OAuth redirects (URL has `#access_token=` or `?code=`).

**Root cause:** On normal page reload with existing Google session, `refreshSession()` fired `onAuthStateChange` with `SIGNED_IN`. `localStorage.getItem("tutor_user")` was null (async recovery not done), causing 6-attempt profile polling to start → `oauthLoading=true` → UI hangs.

**Fix:** Check URL for OAuth params before entering full OAuth processing. Returning users are handled by session recovery instead.

---

## 2026-06-28: Auth Error Message Sanitization

**Decision:** All user-facing auth error messages must be friendly. Supabase/JWT internals logged to console only.

**Changes in `authClient.js`:**
- No Supabase access token → "Your session has expired. Please sign in again."
- 401/403 → "Your session has expired. Please sign in again."
- 500 → "We're having trouble right now. Please try again in a moment."
- Business errors (400) without auth keywords → shown as-is

---

## 2026-06-28: Session Recovery on App Boot

**Decision:** On app load with saved `tutor_user` in localStorage, verify Supabase session and fetch fresh profile.

**Why:** Prevents stale subscription/access/role data after returning to the site without logging out.

**Behavior:**
- Expired session → clear localStorage → setUser(null)
- Valid session → refresh token → fetch `/api/auth/profile` → update state
- Network failure → keep stale data (non-critical, user still sees dashboard)
- `handleLogin` now fetches fresh profile for ALL roles (was students-only)

---

## 2026-06-28: Child Login Credential Display

**Decision:** After `create_student`, return `login_id` + `login_email` in response. Show one-time credentials panel to parent.

**Root cause of login failure:** UI never showed credentials. Parent didn't know what username/ID the child should use.

**Login flow:** Child types username → `/api/auth/lookup-email/{username}` → returns profile.email → `signInWithPassword(email, password)`.

**Safety:** Password shown once in credentials panel, never stored in profile, never in audit logs.

---

## 2026-06-28: Score Column Fix — test_history.percentage

**Decision:** All score extraction must use `percentage` column, not `score` or `total_questions`.

**Root cause:** `test_history` table stores:
- `percentage` — already 0-100 (e.g., 60.0, 80.0) ← **USE THIS**
- `raw_score` — marks obtained (e.g., 3.0, 4.0)
- `max_score` — total marks (e.g., 5.0, 20.0)
- `score` column — **does NOT exist**
- `total_questions` column — **does NOT exist**

**Fix:** `_normalize_score_pct(percentage, raw_score, max_score)` — never multiplies percentage by 100.

---

## 2026-06-28: student_progress not chapter_progress

**Decision:** Use `student_progress` table for all lesson/chapter progress queries.

**Root cause:** `chapter_progress` table was never created. All progress data is in `student_progress`.

---

## 2026-06-27: Parent Notification Center

**Decision:** `parent_notifications` table for persistent notifications + rule-based fallback when table is empty.

**Rule-based types:** `feature_locked`, `child_inactive`, `plan_expiring`, `low_mock_score`, `strong_improvement`.

**Metadata sanitization:** On read, strip `token`, `secret`, `key`, `password`, `audit_detail` keys.

---

## 2026-06-27: Child Limit from Subscription Resolver

**Decision:** `create_student` enforces child limit from canonical subscription resolver, not hardcoded `>= 2`.

| Plan | Child Limit |
|---|---|
| FREE_TIER | 1 |
| NANO | 1 |
| PREMIUM | 1 |
| FAMILY_PREMIUM | 2 |
| ADMIN_GRANT | None (unlimited) |

**Fix:** `child_limit = None or 1` bug — `None or 1 = 1` incorrectly capped admin at 1. Fixed with explicit conditional.

---

## 2026-06-26: _normalize_score_pct Canonical Helper

**Decision:** All score display uses a single canonical helper in `parent_dashboard_v2.py`.

**Rules:**
1. `percentage` in [0,100] → use directly
2. `percentage` > 100 → invalid, try `raw / max * 100`
3. `max_score = 0` → return None
4. No data → return None

**Reason:** Previous code multiplied `percentage` by `(score/total_questions)*100` causing 1200%, 1600% display bugs.

---

## Earlier Decisions

### parentId Alone Never Grants Access
`access_cbse` must be explicitly `true`. A child with only `parent_id` set but `access_cbse=false` is Free Tier. This is enforced at both API layer (subscription resolver) and frontend (`resolveSubscription.js`).

### Canonical Feature Authorization
Feature access comes from `get_feature_summary(user_id)` in `feature_authorization_service.py`. Never branch on raw `subscription_plan` string. Never infer access from `parentId`.

### Offer Code Not Required for Signup
All new users sign up free. Offer codes are redeemable separately. Signup UI has no offer code field.

### Expiry Revocation
When `subscription_expires_at` is in the past, `access_cbse` is set to `false` by the expiry job. This is the canonical way to revoke access — not by deleting the subscription record.
