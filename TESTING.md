# Testing Guide

![Tests](https://github.com/pradipbhuyan/cbse-tutor-platform/actions/workflows/tests.yml/badge.svg)

This project has three layers of tests:

1. Backend API tests using pytest
2. Frontend component tests using Vitest
3. End-to-end tests using Playwright

It also includes a longer monthly student journey simulation for realistic platform usage testing.

---

## Backend tests

Run these from the `backend` folder:

```bash
cd backend
./venv/bin/python -m pytest -v
```

---

## Backend coverage

Run this from the `backend` folder:

```bash
cd backend
./venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

This shows backend test coverage and highlights missing lines that still need tests.

---

## Frontend component tests

Run these from the `frontend` folder:

```bash
cd frontend
npm test
```

Vitest runs in watch mode.

Press `q` to quit after tests pass.

Current frontend tests cover (578 tests, 46 test files):

- LessonsPage loading saved lesson progress
- Practice question generation
- Practice mode disabling Ask AI follow-up
- OAuth reliability: correlation IDs, stage tracking, URL inspection, error mapping
- OAuth error mapping: all HTTP codes → user-friendly messages (no raw codes exposed)
- Auth session reliability: retry logic, token refresh, friendly error messages
- Admin QA Center: lesson quality audit UI, feature authorization audit
- Admin Lesson Repair: LLM info panel, cost estimates, task workflow, drawer actions
- Admin Productivity: operations panel, cache management
- Admin Control Page: family management, teacher assignment
- Subscription Plans: plan cards, promo codes, upgrade flow
- Parent Dashboard (Phase 1–3): child workspace, notifications, analytics
- Teacher Dashboard: tab navigation, student list, invitation management
- Signup Page: free tier, offer code, Supabase error sanitization
- Formula Sheet: freemium gating, expansion, upgrade modal
- Report Issue Modal: submission, field validation
- Sales Demo, Collateral, Incentive pages

---

## Playwright E2E tests

Playwright tests require the frontend app to be running.

### Terminal 1: start frontend

```bash
cd frontend
npm run dev
```

Keep this terminal running.

### Terminal 2: run Playwright

Open another terminal:

```bash
cd frontend
npx playwright test
```

Current E2E tests cover (26 tests, 5 spec files):

- App loads / renders non-empty content (`lesson-practice.spec.js`)
- Public navigation: landing → login → signup → back, direct URLs for
  `/signup`, `/teacher-signup`, legal pages, and confirmation that a
  signed-out visitor never sees authenticated dashboard content
  (`navigation.spec.js`)
- Email/password login: role-based routing to the correct dashboard for
  student/parent/teacher/admin, invalid-credentials and unconfirmed-email
  error messages, forgot-password (`login.spec.js`)
- Free signup: happy path, client-side validation (short password, Grade
  11/12 stream required), duplicate-email and rate-limit API errors,
  unconfirmed-email-after-signup (`signup.spec.js`)
- Free-tier access restriction: a free student sees the upgrade prompt and
  can follow it through to the Subscription page (`access-control.spec.js`)

These tests mock the Supabase and backend network calls (see
`e2e/support/mockAuth.js`) rather than hitting a live Supabase project, so
they're deterministic and don't require real credentials or a running
backend — only `npm run dev` for the frontend.

Not yet automated at the E2E layer (still only covered by backend pytest
and/or frontend Vitest tests, or not covered at all): parent adds child,
teacher adds student, paid upgrade payment flow, subscription
expiry/fallback, admin payment test, admin operations checks.

---

## Monthly student journey simulation

This project also has a longer scenario simulation that behaves like a student using the platform over a month.

The script is:

```text
backend/simulations/monthly_student_journey.py
```

This simulation calls the real backend APIs and covers:

- Lesson generation
- Progress saving
- Profile activity and XP updates
- Doubt answering
- Answer evaluation
- Practice question generation
- CBSE mock test generation
- SOF Olympiad mock test generation
- Test history saving
- Recommendations
- Usage tracking

This is not a normal unit test. It may call real AI services and write data to Supabase.

### Terminal 1: start backend

```bash
cd backend
./venv/bin/python -m uvicorn app.main:app --reload
```

Keep this terminal running.

### Terminal 2: run the simulation

Open another terminal:

```bash
cd backend
./venv/bin/python simulations/monthly_student_journey.py
```

Expected result:

- API calls should return `200`
- Profile counters should increase
- XP should increase
- Usage summary should show requests and tokens
- Recommendations should be based on saved test history

---

## ⚠️ MANDATORY Pre-Push Checklist

**Run these before every `git push` to prevent CI failures:**

```bash
# Frontend: tests + lint (takes ~15 seconds)
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```

Both commands must pass. If either fails, fix before pushing.

---

## Why CI fails but local doesn't — 3 known failure modes

### 1. Tests written for old broken behavior
If you fix a bug, pre-existing tests asserting the broken behavior will now fail in CI.

**Example:** `AuthSessionReliability.test.jsx` had `expect(caught).toMatch(/session has expired/)` for a 403 response. After fixing authClient to correctly map 403 → "does not have access", the test needed updating.

**Prevention:** Always run `npx vitest run` after every fix.

### 2. ESLint warning count exceeds 50
CI runs `eslint src/ --max-warnings 50` on the **entire `src/`** directory. Running ESLint on a single file misses the aggregate count.

**Prevention:** Always run `npx eslint src/ --max-warnings 50` — not per-file.

### 3. Async timing race in tests
Using `getAllByTestId` (synchronous) after `findByText` (async) causes failures because `findByText` resolves before data fetches complete.

**Rule:** Always use `findAllBy*` (async, retries) for elements that appear after mock API responses — never `getAllBy*` (sync).

```javascript
// ✗ WRONG — sync query after async findBy
await screen.findByText("Total Users");
const badges = screen.getAllByTestId("badge-not-enabled"); // fails — data not loaded yet

// ✓ CORRECT — async query waits for data
await screen.findByText("Total Users");
const badges = await screen.findAllByTestId("badge-not-enabled"); // retries until found
```

### 4. ESLint disable directives on wrong lines

`react-hooks/exhaustive-deps` reports on the `useEffect(() => {` opening line, not the closing `}, [deps])` line.

```javascript
// ✗ WRONG — disable on closing line (warning is on opening line)
useEffect(() => { ... }, []); // eslint-disable-line react-hooks/exhaustive-deps

// ✓ CORRECT — disable on closing line of mount-only [] effects
// (The rule actually fires here in this project's ESLint config)
}, []); // eslint-disable-line react-hooks/exhaustive-deps

// ✓ Also correct — disable-next-line before the effect
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => { ... }, []);
```

Never add an eslint-disable on a line that has no warning — that produces an "unused eslint-disable directive" warning.

---

## Recommended full test checklist

Before pushing important changes, run all three test layers.

### 1. Backend

```bash
cd backend
./venv/bin/python -m pytest -v
```

### 2. Frontend (REQUIRED before push)

```bash
cd frontend
npx vitest run && npx eslint src/ --max-warnings 50
```

Both must pass. This catches the 3 CI failure modes above.

For watch mode during development:

```bash
cd frontend
npm test
```

### 3. E2E

Make sure the frontend dev server is running first:

```bash
cd frontend
npm run dev
```

Then in another terminal:

```bash
cd frontend
npx playwright test
```

### 4. Optional monthly simulation

Run this only when you want a realistic longer scenario test:

```bash
cd backend
./venv/bin/python simulations/monthly_student_journey.py
```

Make sure the backend server is already running before starting the simulation.

---

## Notes

- Backend tests use pytest and FastAPI `TestClient`.
- Frontend component tests use Vitest and React Testing Library.
- E2E tests use Playwright.
- The monthly student journey simulation calls real backend APIs and may write data to Supabase.
- The simulation may call real AI services, so avoid running it repeatedly unless needed.
- Vitest should not run Playwright tests. The `e2e` folder is excluded in `vite.config.js`.
- Some backend tests use mocks to avoid calling Supabase, OpenAI, or other external services.
- Generated files like `.coverage` should not be committed.
- **CI max warning limit: 50.** Adding new files or patterns can push warnings over the limit — always check aggregate count before pushing.
- **`findAllBy*` not `getAllBy*`** for elements rendered after async data loads.
- **`authClient.js` 401 vs 403:** 401 = session expired message, 403 = role-specific access-denied message. Never map 403 to session expired.
- **OAuth diagnostics:** `oauthDiagnostics.js` records stages safely. Never pass tokens/codes to `recordStage()`. Use correlation IDs for cross-device tracing.
- **Lesson Repair tests:** mock `getRepairLlmInfo` in `beforeEach` — all repair tests need it to avoid network calls.
- **Backend Lesson Repair tests:** use valid UUIDs for user IDs — Supabase rejects non-UUID strings with `22P02`.

---

## Recent Changes (2026-06-29)

### OAuth Cross-Device Fix
- **Root cause:** Supabase PKCE clears URL before our handler runs; identity age heuristic only works on first login
- **Fix:** `hasAppProfile = !!localStorage.getItem("tutor_user")` — no tutor_user + SIGNED_IN = fresh login on any device
- **New:** `oauthDiagnostics.js` — correlation IDs, 14 stage names, URL inspection, error mapping (no tokens recorded)
- **New:** `OAuthReliability.test.jsx` — 22 tests covering diagnostics utility
- **Backend:** `/auth/me` accepts `X-OAuth-Correlation-ID` header, emits structured log events

### Admin Lesson Repair Workflow
- **New:** Full repair pipeline: sample/filtered/all mode, LLM toggle, progress bar, task table, detail drawer
- **New:** `GET /api/admin/qa/lesson-repair/llm-info` — provider/model/cost info (never exposes key)
- **New:** Session-only API key override — takes precedence over Admin Settings, never logged/stored
- **Backend tests:** `test_lesson_repair.py` — 28 tests
- **Frontend tests:** `AdminLessonRepairPage.test.jsx` — 23 tests

### DB Migrations (run in Supabase SQL Editor)
- `20260629_oauth_profile_complete.sql` — `oauth_profile_complete` column
- `20260629_lesson_repair_jobs.sql` — `lesson_repair_jobs` + `lesson_repair_tasks` tables
