# Access Control & Onboarding Architecture Blueprint

**Purpose.** This document maps how authentication, role/profile setup, and free-vs-paid
feature gating actually work today — web, mobile, and the backend policy both are supposed
to obey. It started from two mobile bugs found in manual testing and, while tracing them,
went through two rounds of factual correction before landing on the state below. That
history is kept in §0 because it's instructive: two of the earlier "findings" turned out to
be misreadings of stale docs and out-of-date code — worth knowing so nobody re-derives them.

Audited 2026-08-25 against `main` (post commit `32a161d5`, 2026-08-24). File:line
references will drift as code changes — treat them as pointers to re-verify.

---

## 0. Headline findings

**Confirmed product policy** (stated directly by the product owner, and matching
`shared/config/subscriptionPlans.js` — explicitly "canonical plan configuration...
single source of truth"): Exemplar Research is a **paid, student-only** feature.
Free students: locked. Paid students: full access. Teachers: no access, no
marketing, no code path acknowledging them — confirmed fully implemented as of
commit `32a161d5` ("Block teachers from Exemplar Research entirely," 2026-08-24,
same day this audit started).

| # | Where | What's wrong | Status |
|---|---|---|---|
| ~~1~~ | ~~Mobile~~ — `exemplar.tsx` | ~~Any student, free or paid, gets full functional access~~ — **fixed indirectly**, 2026-08-25: fixing #2 at the backend made this screen's existing `features.EXEMPLAR_RESEARCH.allowed` read correct with zero mobile code changes. That flag is computed once, centrally, by `get_feature_summary()` — once it reflects reality, every consumer of it does too. No separate client-side plan check was added (would have reintroduced the "ad hoc per-screen entitlement logic" §1 warns against); mobile's existing `if (!hasAccess) return` guards were already correctly structured, they just trusted a broken input. | **Resolved 2026-08-25** |
| ~~2~~ | ~~Backend~~ — no route enforced student-tier gating | ~~Neither route checked student plan~~ — **fixed**, 2026-08-25: `Feature.EXEMPLAR_RESEARCH`'s matrix entry now uses the same paid-plan set as `Feature.EXEMPLAR` (`allowed_plans`, was `None`), and `require_feature(user.id, Feature.EXEMPLAR_RESEARCH)` was added after the existing teacher-role check in both `teacher.py` routes and `doubt.py`'s chapter gate. Backend-tested: 6 new tests (free/paid × student, on both routes), all passing; 5 pre-existing tests updated to match the corrected policy (they encoded the old "free for everyone" behavior). Full suite green. | **Resolved 2026-08-25** |
| ~~3~~ | ~~Mobile~~ — `authFetch.ts:31` | ~~Wrong hardcoded message on exemplar 403s~~ — **fixed**, 2026-08-25, and the bug was one layer deeper than first described: structured `detail` objects (which is what `require_feature()` and the Exemplar routes' 403s actually send) were being coerced with `String(rawDetail)`, producing the literal text `"[object Object]"` — the keyword match on that string could never have worked as written. Now the function detects a structured `detail` object and uses its `.message` directly. | **Resolved 2026-08-25** |
| ~~4~~ | ~~Mobile~~ — OAuth new-user flow | Unrelated to Exemplar Research. Role-select screen existed and was wired correctly in principle, but two `catch` blocks silently treated a failed `/api/auth/me` check as "authenticated as-is" — **fixed 2026-08-25**: `checkAuthState` now retries with backoff (`checkAuthStateWithRetry`, 2 retries, exponential backoff), and `_layout.tsx` fails closed to a new blocking "error" auth state with a retry button on repeated failure, instead of defaulting to "ready." Also removed a second, independent copy of the same check-then-route logic in `login.tsx`'s OAuth handler, which raced `_layout.tsx`'s routing decision and had the identical silent-default bug — it now defers entirely to `_layout.tsx`, the single place that already listens for the session change. | **Resolved 2026-08-25** |
| ~~5~~ | ~~Client architecture, both~~ | No shared "what can this user do" resolver on mobile — **fixed on mobile, 2026-08-25**: new `UserProfileContext`/`useUserProfile()` hook fetches `/api/auth/me` + `/api/subscription/features` exactly once per session (mounted at the tabs layout), replacing 7 independent per-screen fetches (the tabs layout itself, `doubt.tsx`, `exemplar.tsx`, `formula.tsx`, `lessons.tsx`, `learn.tsx`, `mocktest.tsx`) with one typed shape. Every screen's existing fallback/default logic was preserved exactly, verified field-by-field before migrating. Web still has no equivalent (prop-drilling from `App.jsx`, §7) — lower priority, no field-reported bug traced to it the way finding 1 traced to mobile's version of this gap. | **Resolved (mobile) 2026-08-25** |
| ~~6~~ | ~~Web — teacher pricing/access~~ | ~~Teachers advertised/served Exemplar Research~~ — **already fixed**, commit `32a161d5`: pricing copy removed, `App.jsx`'s page case returns null for teachers, both backend routes 403 every teacher unconditionally, tests updated (101/101 backend, 104/104 frontend passing). No action needed. | **Resolved 2026-08-24** |

**Remaining open work:** none of the original 6 findings are open. The only carried-forward
item is extending finding 5's fix to web (§7) — a lower-priority parity improvement, not a
bug fix, since nothing traced a live problem to web's prop-drilling pattern the way finding 1
traced one to mobile's per-screen fetch duplication.

### How the first two drafts of this document got it wrong

Worth recording plainly, since both errors are easy to repeat:

1. **First draft** read `feature_authorization_service.py`'s `EXEMPLAR_RESEARCH` entry
   (`allowed_plans: None`) and its old comment ("never sold to students as a paid
   feature") at face value, concluding the feature was free for all students and that
   web's paywall was a bug. Backwards — it's a paid *student* feature; the entry's real
   meaning is "role, not plan, is what used to matter here," not "free for everyone."
2. **Second draft**, correcting the first, over-corrected by trusting
   `docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md`'s prose summary ("Auth via
   require_teacher_or_admin") instead of reading the route body directly. The actual
   route explicitly warns against that exact mistake in its own docstring: *"this route
   must accept any authenticated user, not require_teacher_or_admin... Getting this
   wrong once already broke the page for real students."* Web's `Sidebar.jsx`
   `roles:["student"]` and its `hasPaidAccess()` gate were both correct all along.

Lesson embedded in the process, not just the finding: **when backend prose (docstrings,
status docs, comment tables) and backend route bodies disagree, the route body is the
only one that's actually running.** Every claim in this revision is sourced from a route
body, a matrix dict, or a canonical config file re-read on 2026-08-25 — not from a comment
describing what the code is *supposed* to do.

---

## 1. Design principle this blueprint asks both clients to follow

> **The backend is the only place that decides what a user can access. Each client gets
> exactly one function/resolver that asks the backend and every gated screen calls that
> one thing — never a bespoke per-screen check.**

Web states this intent in writing for the *subscription-tier* dimension —
`resolveSubscription.js`'s docblock calls itself "the ONLY place that decides what
subscription state a user is in." That held up under scrutiny for Exemplar Research once
the actual policy was understood correctly (§0). What's still genuinely missing is the
backend half of the principle: `feature_authorization_service.py`'s matrix has no way to
express "this role is blocked outright; this other role is gated by plan" in one entry
(§2) — so the student-plan half of Exemplar Research's policy was pushed entirely onto
the client, with no backend enforcement at all. That's a real structural gap, independent
of who's currently getting it right.

---

## 2. Backend: the canonical policy layer

**File:** `backend/app/services/feature_authorization_service.py`

`authorize_feature()`/`require_feature()` re-resolve from the DB on every call —
"Backend NEVER trusts frontend claims about subscription," per the module docstring.
Now true for every feature in the matrix, including this one — as of 2026-08-25 it no
longer needs the caveat this section used to carry:

```python
Feature.EXEMPLAR_RESEARCH: {
    # Two independent gates, both real:
    #   1. ROLE — every teacher 403'd unconditionally at the route layer.
    #      Not expressed here; this matrix has no role axis, only plan.
    #   2. PLAN — students/parents/admin gated by subscription plan, same
    #      paid-plan set as Feature.EXEMPLAR.
    "allowed_plans": {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                      "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT",
                      "EXAM_PREP_CENTER"},
    "limited_on": set(),
    "upgrade_message": "Exemplar Research is available with a paid subscription.",
},
```

**Before 2026-08-25**, this entry was `"allowed_plans": None` — which does not mean
"free for everyone," it means "this matrix has no plan-based restriction to express for
this feature." That was true of the *role* axis (real, correctly enforced at the route
layer since 2026-08-24) but was silently also true of the *plan* axis, which nothing
was expressing at all — unlike every other paid feature (`EXEMPLAR`,
`FORMULA_SHEET_PREMIUM`, `EXAM_PREP_CONTENT`), Exemplar Research's free/paid split for
students lived only in web's client-side `hasPaidAccess()` check, with nothing backend
-side to fall back on. Mobile never replicated that check (§5), so free-tier mobile
students got full functional access — the actual live bug this whole document was
tracking down.

**Current enforcement, both axes real, both backend-side:**

| Route | Role check | Plan check |
|---|---|---|
| `POST /api/teacher/exemplar-research/explain` (`teacher.py:327-365`) | 403s every teacher unconditionally | `require_feature()` 403s free-tier students/parents |
| `POST /api/teacher/exemplar-research/availability` (`teacher.py:285-318`) | Same | Same |
| `POST /api/doubt/answer`, chapter starts `"Exemplar:"` (`doubt.py:174-195`) | Same | Same |

All three routes now follow the same two-step pattern: the pre-existing unconditional
teacher block, then `require_feature(user.id, Feature.EXEMPLAR_RESEARCH)` for everyone
else. Verified with 6 new tests (free-tier and paid-tier students, on both the
availability and doubt-answer routes) plus 5 pre-existing tests updated to match the
corrected policy — they'd been written against the old "free for everyone" behavior and
failed immediately once the matrix changed, exactly as intended. Full backend suite
green.

---

## 3. Auth & new-user provisioning

### 3.1 Shared backend contract

- `POST /api/auth/signup-free` (`auth.py:1265`) — email/password signup; teacher role
  is rejected here and redirected to `POST /api/auth/teacher-signup`.
- **Google OAuth, new user:** a Postgres trigger
  (`migrations/20260624_google_oauth_profile_trigger.sql` +
  `20260629_oauth_profile_complete.sql`) auto-inserts a placeholder `profiles` row —
  `role='student'`, `grade='Grade 9'`, `oauth_profile_complete=false`. Deliberate and
  shared, not a client-side default.
- `GET /api/auth/me` (`auth.py:363-437`) reports `needs_role_selection = not
  oauth_profile_complete`. Both clients are supposed to treat `true` as "show the
  picker before letting the user into the app."
- `POST /api/auth/oauth/complete-profile` (`auth.py:453`) — where the picker's answer
  gets written, flipping the flag.

### 3.2 Web implementation

No dedicated onboarding page — the wizard is inlined in `App.jsx` (a 2133-line
monolith with no router; see §6). Triggered when `pendingOauthUser` is set
(`App.jsx:426`): step "role" (1322) → step "school" for teachers (1427, sets
`pending_verification`) or step "grade" + stream for students (1521-1650). Each step
POSTs to `complete-profile` directly.

### 3.3 Mobile implementation

Mobile **does** have the equivalent screen — `mobile/app/auth/role-select.tsx`, a full
student/parent + grade (5-12) + stream picker, POSTing through
`completeOAuthProfile()` (`mobile/lib/auth.ts:86-105`). The root navigator
(`mobile/app/_layout.tsx:22-94`) re-derives `needs_role_selection` on every auth-state
change and force-routes to it. The intent is correct.

**The bug (finding #4, fixed 2026-08-25) was a silently-swallowed failure path, not a
missing screen:**

```
mobile/app/_layout.tsx:42-48        catch { setAuthState("ready") }
                                       // "Backend unreachable... treat as authenticated"
mobile/app/auth/login.tsx:271-274   catch (e2) { ... router.replace("/(tabs)") }
```

Both sites treated a failed `/api/auth/me` fetch as "let them in anyway." On a brand-new
Google sign-in, the DB placeholder (`Grade 9`, `student`, `oauth_profile_complete=false`)
is already sitting there, so the user would land on the dashboard *as if* onboarding
already happened. More likely on mobile than web precisely because of the network
conditions mobile already builds custom handling for elsewhere — the in-app
`GoogleOAuthWebView` (`login.tsx:36-114`) exists specifically to survive
corporate/Zscaler TLS interception.

**Fix, implemented:**
- `mobile/lib/auth.ts` gained `checkAuthStateWithRetry()` — 2 retries with exponential
  backoff (600ms, 1200ms) before giving up.
- `mobile/app/_layout.tsx` uses it, and on total failure sets a new `"error"` auth state
  (added to the state union) instead of `"ready"` — renders a blocking
  `AuthCheckErrorScreen` with a "Try again" button that re-runs the check against the
  last known session, rather than requiring a fresh sign-in.
- `mobile/app/auth/login.tsx`'s OAuth handler had its own independent copy of this same
  check-then-route logic, racing `_layout.tsx`'s routing decision — removed entirely.
  Establishing the session already fires Supabase's `onAuthStateChange`, which
  `_layout.tsx`'s root listener is subscribed to; it's now the single place that decides
  routing for every sign-in path (email, Google, and both native/Expo-Go OAuth flows),
  not two places that could disagree.

---

## 4. User roles & profile model

**Web** has no single canonical type, but the shape is consistent because it's
assembled once, in `_finishOAuthLogin()` (`App.jsx:462-486`), and prop-drilled
unchanged: `role`, `grade`, `board`, `parentId`, `accessCbse`, `subscriptionPlan`, etc.

**Mobile — fixed 2026-08-25.** Previously had no canonical shape at all — 7 independent
call sites (the tabs layout, `doubt.tsx`, `exemplar.tsx`, `formula.tsx`, `lessons.tsx`,
`learn.tsx`, `mocktest.tsx`) each defined their own partial interface and independently
fetched `/api/auth/me` and/or `/api/subscription/features`. Finding #1's exact mechanism
lived here: `exemplar.tsx`'s own ad hoc read, `features?.EXEMPLAR_RESEARCH?.allowed ??
has_full_access ?? false`, trusted a value nothing else validated.

Now: `mobile/lib/UserProfileContext.tsx` exports one typed `UserProfile` interface
(`grade`, `stream`, `cbseSubjects`, `username`, `email`, `canReportIssues`) plus
`features`/`hasFullAccess`, fetched once via a `UserProfileProvider` mounted at
`(tabs)/_layout.tsx` and read via `useUserProfile()`. Every one of the 7 original call
sites was migrated; each screen's exact existing fallback/default logic was preserved
(verified field-by-field before migrating — e.g. `formula.tsx`/`learn.tsx` default to
`"Grade 9"` even when the fetch fails, `doubt.tsx`/`mocktest.tsx` leave grade unset
instead — both patterns kept exactly as they were, just sourced from the shared fetch
instead of a local one). `lessons.tsx` is the one consumer that needs the raw `features`
map (it reads `Feature.EXEMPLAR` specifically, not just a pre-computed boolean), so the
context exposes the full map rather than only derived flags.

**Web** still has no canonical type, but the shape is consistent because it's assembled
once, in `_finishOAuthLogin()` (`App.jsx:462-486`), and prop-drilled unchanged: `role`,
`grade`, `board`, `parentId`, `accessCbse`, `subscriptionPlan`, etc. No `board`, `mode`,
or `offerAccess` field exists in mobile's shape — none of the 7 migrated screens ever
read them, so the new context doesn't carry them either; add on demand if a future
screen needs them, rather than speculatively.

**Requirement, now met on mobile:** one typed `Profile` shape, fetched once, passed
down — not re-fetched and re-shaped per screen. Extending the same pattern to web
(replacing `App.jsx`'s prop-drilling with a context) would bring full parity but wasn't
done here — nothing traced a live bug to web's version of this gap the way finding #1
traced one to mobile's.

---

## 5. Free vs paid access gating

### 5.1 Web

Canonical resolver: `hasPaidAccess(user)` in `resolveSubscription.js` (lines 216-232):
admin → true; active `subscriptionExpiresAt` → true; `accessCbse` truthy → true; else
false. `ExemplarResearchPage.jsx:336` uses it to gate `explainTopic()`, `handleSearch()`,
and topic activation — all three, correctly, matching the canonical student plan config
(`shared/config/subscriptionPlans.js`: `exemplarResearch: "❌ Locked"` on `free_tier`,
`"✅ Full access"` on every paid tier). Confirmed correct end-to-end on this audit.

### 5.2 Mobile — fixed 2026-08-25

No equivalent of `hasPaidAccess()` exists, and none was added. `exemplar.tsx`'s
`hasAccess` still reads `features.EXEMPLAR_RESEARCH.allowed` — unchanged client code —
but that flag is now correct, because §2's backend fix changed what it *means*.
Previously `allowed_plans: None` made it `true` for any non-teacher regardless of plan;
now it's computed the same way as every other paid feature's flag
(`cpk in allowed_plans`), so it correctly resolves `false` for free-tier
students/parents and `true` for paid ones. Mobile's actual data calls (explain, search,
generate-practice) still go through `/api/doubt/answer`, which now independently
enforces the same plan check server-side (§2) — so even if the client flag were ever
stale, the request itself would still be denied.

### 5.3 What "correct" looks like — implemented 2026-08-25

The fix had two parts, both backend-only:

1. `feature_authorization_service.py`: `Feature.EXEMPLAR_RESEARCH`'s `allowed_plans`
   changed from `None` to the same paid-plan set as `Feature.EXEMPLAR`, so
   `get_feature_summary()` (which powers `/api/subscription/features`, which both
   `ExemplarResearchPage.jsx` — indirectly, via the config — and `exemplar.tsx` —
   directly — depend on) now reports the real entitlement.
2. `teacher.py` (both routes) and `doubt.py`'s chapter gate: added
   `require_feature(user.id, Feature.EXEMPLAR_RESEARCH)` immediately after the existing
   unconditional teacher-role block, so a free-tier student/parent is denied at the
   actual data-serving layer, not just hidden by a client that happened to agree.

Deliberately **not** done: adding a parallel, mobile-only re-derivation of
`hasPaidAccess()`-style logic. That would have reintroduced exactly the "ad hoc
per-screen entitlement check" pattern §1 warns against, in a case where the single
backend-computed signal was fixable at the source instead. Verified via 6 new backend
tests (free/paid × student, across both routes) plus the 5 pre-existing tests that
encoded the old policy, updated to match the corrected one — full suite green.

---

## 6. Navigation & route guarding

**Web:** No router library. `App.jsx` holds an `activePage` string and a ~45-case
switch. No `ProtectedRoute` wrapper; role gating is soft — `Sidebar.jsx` nav items carry
a `roles: [...]` array that hides links (confirmed correct for Exemplar Research:
`roles: ["student"]`, `Sidebar.jsx:412-419`), and `App.jsx`'s `exemplarResearch` case now
has a defensive `if (user?.role === "teacher") return null;` guard added in the
2026-08-24 fix. The switch otherwise never re-checks role per case — any other page is
reachable if something sets `activePage` to it, regardless of role. Worth a hardening
pass independent of this feature.

**Mobile:** `mobile/app/_layout.tsx` (root Stack) is the only real guard, now
distinguishing four states: unauthenticated / needs-role-selection / ready / error (the
last added 2026-08-25, see §3.3). Past "ready," the tab navigator applies no further
restriction — all feature-level gating is pushed into each screen independently. This
was the architectural root of finding #1 (N screens, N independent chances to misread a
backend flag's meaning) — §4/§5's shared `UserProfileContext` fix reduces that to one
place reading the flag, though it doesn't add a route-level guard itself. A real
per-page role guard on either platform is still the one open item (§8's last checklist
row).

---

## 7. State management

**Web:** No `AuthContext`. Current user is a `useState` in `App.jsx:362`, hydrated from
`localStorage` as a full JSON blob, prop-drilled into every page.

**Mobile — fixed 2026-08-25.** Previously no Context/Zustand/Redux anywhere; current
user lived nowhere centrally. Now `UserProfileContext` (React Context, `createContext`/
`useContext` — the first of its kind anywhere in `mobile/`, confirmed via a full-repo
grep before adding it) holds `profile`/`features`/`hasFullAccess`/`loading`, mounted
once at `(tabs)/_layout.tsx`, read via `useUserProfile()` from any screen under the tabs
group. Fetch-once-on-mount, matching every one of the 7 original call sites' behavior
(none of them re-fetched on focus or dependency change either); a `refresh()` is exposed
for future use but nothing currently calls it, same as before.

**Requirement, met on mobile, not yet on web:** mobile doesn't need web's prop-drilling
pattern (arguably shouldn't adopt it), but needed *one* place holding current
user/entitlement state that every screen reads — now has it. Web's own prop-drilling
still works and wasn't touched; unifying the two platforms' *patterns* (not just their
data) would be a further step, not required by anything this audit traced to a bug.

---

## 8. Mobile parity checklist

- [x] **(High, backend) — fixed 2026-08-25.** Added a real student-plan check to
      `teacher.py`'s explain and availability routes and `doubt.py`'s "Exemplar:" gate
      (`require_feature(user.id, Feature.EXEMPLAR_RESEARCH)`, right after the existing
      teacher-role block). Matrix entry's `allowed_plans` changed from `None` to the
      same paid-plan set as `Feature.EXEMPLAR`.
- [x] **(High, mobile) — resolved as a side effect of the backend fix, 2026-08-25.**
      No change made to `exemplar.tsx`. Its existing `hasAccess` read of
      `features.EXEMPLAR_RESEARCH.allowed` is now correct because the backend fix
      above changed what that flag means — deliberately did not add a redundant
      client-side re-derivation of the same signal.
- [x] **(High, mobile) — fixed 2026-08-25.** `_layout.tsx` and `login.tsx` no longer
      treat a failed `/api/auth/me` fetch as "proceed as authenticated." Added
      `checkAuthStateWithRetry()` (2 retries, exponential backoff); on total failure
      `_layout.tsx` fails closed to a new blocking `"error"` state with a retry button
      instead of defaulting to `"ready"`. Also removed `login.tsx`'s own independent
      copy of the check-then-route logic (it raced `_layout.tsx`'s decision and had the
      same silent-default bug) — routing now happens from exactly one place.
- [x] **(Medium, mobile) — fixed 2026-08-25.** `authFetch.ts`'s blanket "exemplar" →
      hardcoded-message override removed. Root cause was one layer deeper than
      originally described: a structured `detail` object was being coerced with
      `String(rawDetail)` into the literal text `"[object Object]"` before any keyword
      match could work — the function now detects a structured `detail` and uses its
      `.message` field directly.
- [x] **(Structural, mobile) — fixed 2026-08-25.** One typed `UserProfile` shape
      (`mobile/lib/UserProfileContext.tsx`), one place (`(tabs)/_layout.tsx`) that
      fetches `/api/auth/me` + `/api/subscription/features` once per session —
      replaced all 7 independent per-screen fetches (tabs layout, `doubt.tsx`,
      `exemplar.tsx`, `formula.tsx`, `lessons.tsx`, `learn.tsx`, `mocktest.tsx`), each
      migrated with its exact existing fallback logic preserved. Verified with a
      full-project TypeScript check (0 errors) after every file.
- [ ] **(Structural, both)** Neither client has a real per-page role guard beyond
      Exemplar Research's now-fixed special case — pages are reachable if navigation
      state points at them. Worth a follow-up hardening pass on both platforms. The
      only item from this checklist still open.

**No longer needed** (resolved 2026-08-24, commit `32a161d5`): removing Exemplar
Research from teacher pricing/marketing, blocking teacher access on both backend
routes, and the `App.jsx` teacher-role page guard. Verified via direct re-read of
current `main`, not just the commit message.

---

## 9. File reference index

**Backend**
- `backend/app/services/feature_authorization_service.py` — canonical matrix;
  `EXEMPLAR_RESEARCH` plan-gated same as `EXEMPLAR` as of 2026-08-25 — see §2
- `backend/app/routes/teacher.py:285-365` — explain/availability routes, both role- and
  plan-gated
- `backend/app/routes/doubt.py:173-195` — same pattern, chapter-name-triggered
- `backend/app/routes/auth.py` — signup, login, `/me`, OAuth complete-profile
- `backend/migrations/20260624_google_oauth_profile_trigger.sql`,
  `20260629_oauth_profile_complete.sql` — `Grade 9`/`student` placeholder trigger
- `docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md` — history of the 2026-08-15 pivot to the
  pre-authored-bank route (its "Auth via require_teacher_or_admin" line is stale prose;
  the route body never used that dependency — see §0)

**Web**
- `shared/utils/resolveSubscription.js` (`frontend/src/utils/resolveSubscription.js`) —
  `hasPaidAccess()`, confirmed correct for Exemplar Research
- `frontend/src/App.jsx` — global user state, OAuth wizard, page switch, teacher guard
  on `exemplarResearch` case (added 2026-08-24)
- `frontend/src/pages/ExemplarResearchPage.jsx` — teacher-specific logic removed
  2026-08-24
- `frontend/src/pages/SubscriptionPlansPage.jsx` — teacher pricing table, cleaned
  2026-08-24
- `frontend/src/components/Sidebar.jsx:412-419` — `roles:["student"]`, correct
- `shared/config/subscriptionPlans.js` — canonical student plan/comparison config,
  confirms paid-student-only policy

**Mobile**
- `mobile/lib/UserProfileContext.tsx` — new, 2026-08-25; shared profile/features
  fetch — see §4/§5/§7
- `mobile/app/_layout.tsx` — root auth-state guard; finding #4 fixed 2026-08-25 (new
  `"error"` state + retry, replaces silent `"ready"` fallback)
- `mobile/app/auth/login.tsx` — sign-in; its own duplicate OAuth routing check removed
  2026-08-25 (finding #4)
- `mobile/app/auth/role-select.tsx` — onboarding, unchanged
- `mobile/lib/auth.ts` — `checkAuthStateWithRetry()` added 2026-08-25
- `mobile/lib/authFetch.ts` — finding #3, fixed 2026-08-25
- `mobile/app/(tabs)/_layout.tsx` — mounts `UserProfileProvider`; finding #1 resolved
  2026-08-25 (as a side effect of the backend fix, §5.2) plus migrated to the shared
  context (§5)
- `mobile/app/(tabs)/exemplar.tsx`, `doubt.tsx`, `formula.tsx`, `lessons.tsx`,
  `learn.tsx`, `mocktest.tsx` — all 6 migrated to `useUserProfile()`, finding #5,
  2026-08-25
- `mobile/app/(tabs)/account.tsx`, `index.tsx` — NOT migrated; these hit different
  endpoints (`/api/auth/profile`, `/api/student/dashboard/summary`) with their own
  broader payloads, out of scope for this specific duplication
