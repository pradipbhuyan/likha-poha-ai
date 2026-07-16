# Tech Debt Register

_Last updated: 2026-07-16_

This file tracks known architecture, security, and operational debt across the platform (web, backend, mobile). It exists so debt is planned against deliberately instead of rediscovered by whoever hits it next.

Origin: a full-platform assessment (architecture / design / security / usability) conducted 2026-07-16, cross-checked against `10_SECURITY.md`, `14_ROADMAP.md`'s existing "Key Technical Debt" section, and direct code inspection (file sizes, middleware, auth guard coverage, dependency tree).

## How to use this doc

- **Status:** `Open` → `In Progress` → `Done` (move done items to the Resolved section with the date and what changed).
- **Priority:** `P0` (do next) · `P1` · `P2` — set at intake, re-rank anytime; this doc doesn't dictate order, planning conversations do.
- Add new items as they're found. Don't delete — move to Resolved so the history of what's been paid down is visible.

---

## Priority queue (P0)

These five were flagged as the highest-impact items in the 2026-07-16 assessment. Order below is a recommendation, not a commitment — pick the starting point in planning.

| ID | Item | Category | Status |
|---|---|---|---|
| ~~TD-01~~ | ~~OAuth docs contradict actual behavior~~ | Security / Docs | ✅ Done — see [Resolved](#resolved) |
| [TD-02](#td-02-no-production-observability) | No production observability (errors, uptime) | Operational | Open |
| [TD-03](#td-03-monolithic-files-at-the-eslint-ceiling) | Monolithic files driving CI lint ceiling | Architecture | Open |
| [TD-04](#td-04-exam-prep-subscription-model-is-ambiguous) | Exam Prep subscription model is ambiguous | Architecture / Billing | Open |
| [TD-05](#td-05-mobile-release-process-is-a-single-fragile-local-script) | Mobile release process is a single fragile local script | Operational | Open |

---

## Architecture

### TD-03: Monolithic files at the ESLint ceiling
**Status:** Open · **Priority:** P0

Several files have grown past the point of safe single-author maintenance:

| File | Lines |
|---|---|
| `frontend/src/pages/AdminControlPage.jsx` | 3,932 |
| `frontend/src/pages/RagUploadPage.jsx` | 3,428 |
| `frontend/src/pages/LessonsPage.jsx` | 2,969 |
| `frontend/src/pages/ExamPrepPage.jsx` | 2,918 |
| `backend/app/routes/admin_control.py` | 2,610 |
| `backend/app/routes/rag.py` | 2,423 |
| `backend/app/services/exam_prep_service.py` | 2,393 (mixes access control, 6 exams' hardcoded syllabus data, and DB queries in one file) |
| `frontend/src/App.jsx` | 1,869 (routing + entire OAuth state machine) |

**Impact:** ESLint is already at CI's max-warnings ceiling (50/50 per `CODEX_CONTEXT.md`) — these files are why it's hard to bring down rather than easy. Every change to them carries more blast radius than it should, and they're the files most likely to develop merge conflicts or regressions.

**Suggested first cut:** split `exam_prep_service.py`'s static syllabus data (JEE/NEET/CUET/SAT/IELTS/TOEFL subject/topic dictionaries) out of the access-control functions — pure data, easy to extract, immediately shrinks the highest-churn backend file by more than half.

---

### TD-04: Exam Prep subscription model is ambiguous
**Status:** Open · **Priority:** P0

Two coexisting, contradictory gating mechanisms for Exam Prep content access:

1. **Legacy:** `exam_prep_subscriptions` table (migration `20260709_exam_prep_subscriptions.sql`) — per-exam pack purchases, independent of the main CBSE subscription. Its `CHECK` constraint only allows `exam_type IN ('jee_main','neet_ug','cuet_ug')` — it **cannot represent SAT, IELTS, or TOEFL**, despite all three being fully built out in `exam_prep_service.py`.
2. **Current:** `exam_prep_service.py`'s `check_exam_prep_content_access()` gates via the canonical `Feature.EXAM_PREP_CONTENT`, tied to the main CBSE Premium/Family Premium plan via `subscription_plan_settings.access_exam_prep`.

It's unclear from the code alone which one is authoritative, or whether the legacy table is dead. This is exactly the kind of silent fork that turns into a billing bug — a user could plausibly hold a row in one system's "unlocked" state and not the other's.

**Resolution needed:** explicit decision (retire the legacy table, or formally revive it for the standalone Exam Prep Pass work — see the Exam Prep Center planning thread) + a `DECISION_LOG.md` entry once settled.

---

### TD-06: Mobile duplicates web's subscription/access logic instead of importing it
**Status:** Open · **Priority:** P2

`shared/utils/resolveSubscription.js` exists precisely so web and mobile share one implementation of subscription/access logic. Mobile doesn't use it — e.g. `isGradeLocked` in `mobile/app/(tabs)/formula.tsx` is a separate hand-rolled implementation that currently happens to match the web logic. Nothing enforces that it keeps matching.

**Impact:** low today, compounding — every future access-rule change now has to be remembered in two places.

---

## Security

### TD-07: No rate limiting on any endpoint
**Status:** Open · **Priority:** P1

`backend/requirements.txt` has no rate-limiting library (no `slowapi` or equivalent). Login, signup, and the username→email lookup endpoint (`/api/auth/lookup-email/{username}`) are all open to brute-force or enumeration at unlimited request rates.

---

### TD-08: No HTML sanitizer despite `dangerouslySetInnerHTML` usage
**Status:** Open · **Priority:** P2

`dompurify` (or equivalent) isn't in `frontend/package.json`. Two call sites inject raw HTML: `BlogPostPage.jsx` (`post.html`) and `ExamPrepPage.jsx`'s `MathText` component. Both are currently fed admin/build-authored content, so today's risk is low — but the content pipeline is trending toward more LLM-generated content with less per-item human review (bulk question import, formula prewarm). "Trust the source" doesn't scale with that trend.

---

## Operational

### TD-02: No production observability
**Status:** Open · **Priority:** P0

No error tracking (Sentry or equivalent), no uptime monitoring, no load testing — all listed as still-pending under `14_ROADMAP.md`'s "Production Readiness" section. The platform is a live paid product; right now, outages and errors are discovered via support tickets, not alerts.

---

### TD-05: Mobile release process is a single fragile local script
**Status:** Open · **Priority:** P0

`mobile/build_apk.sh` depends on: git credentials cached on one specific machine, a Zscaler corporate cert only present on that machine, and (until 2026-07-16) a `versionCode` bump that lived only in an uncommitted local file. That last gap caused two real incidents — build 17 and build 34 both had their version counter silently reset when local `app.json` changes were discarded before a `git pull`. The auto-commit-and-push fix landed 2026-07-16, but the underlying single-machine dependency (git auth, Zscaler cert, Android Studio/Java toolchain) remains.

**Resolution needed:** move the build onto EAS Build or a CI runner so release capability isn't tied to one laptop.

---

### TD-09: Deferred migrations have become permanent application logic
**Status:** Open · **Priority:** P2

`formula_sheets` v3 migration was never applied (per `14_ROADMAP.md`), so the code permanently carries a "catch Postgres error 42703, fall back to base columns" branch rather than a clean schema. This is a pattern worth watching — deferred migrations that the code has to permanently accommodate add up to real complexity over time.

---

## Design / Usability

### TD-10: Admin surfaces have outgrown "internal tool" usability
**Status:** Open · **Priority:** P2

`AdminControlPage.jsx` (3,932 lines) and `RagUploadPage.jsx` (3,428 lines) are hard for anyone but their original author to safely operate or extend. Same root cause as TD-03, but called out separately because the impact here is on the team's own operating experience, not just code maintainability.

---

### TD-11: Dark mode rolled out inconsistently rather than as a platform-wide system
**Status:** Open · **Priority:** P2

`14_ROADMAP.md` lists "Light/Dark Mode Compatibility (ExamPrepPage + AdminCacheManagementPage)" as a discrete recent fix, implying other surfaces got dark-mode support later and separately rather than via one token system applied platform-wide from the start.

---

## Resolved

_(move items here as they're closed, with date + what changed)_

### TD-01: OAuth documentation contradicts actual behavior
**Resolved:** 2026-07-16

`10_SECURITY.md` claimed PKCE flow as default and documented a specifically-retired workaround ("identity age fallback") as if still current, while `CODEX_CONTEXT.md` and mobile docs correctly described implicit flow on mobile and listed that same workaround as removed. This contradiction was traced to real recurring incidents in git history (`f6206fd`, `82a435f`, `bbcc86d` — repeated fixes for the same PKCE-vs-implicit mistake).

**What changed:** Rewrote `10_SECURITY.md`'s OAuth section (replacing "Google OAuth — Critical Rules") with a single platform-specific section: a Web-vs-Mobile flow table with the *why*, the web state machine (states A–D, cross-checked against the live `GET /me` / `POST /oauth/complete-profile` handlers in `backend/app/routes/auth.py`), the mobile `handleOAuthSuccess()` flow-detection logic (cross-checked against `mobile/app/auth/login.tsx`) with its five known fragile points and their fixes in priority-check order, and an explicit "Retired — do not reimplement" list for the two techniques that were tried and removed.
