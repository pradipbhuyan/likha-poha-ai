# Testing and Regression Guidelines

## Testing Philosophy

Every behavior change requires regression tests. Critical business rules must be tested at both backend and frontend layers where applicable.

## Required Test Categories

- Subscription resolver tests
- Feature authorization matrix tests
- Payment verification and webhook idempotency tests
- Admin-only endpoint tests
- Teacher ownership tests
- Parent-child ownership tests
- Frontend rendering/access tests
- Mobile responsiveness tests where practical
- E2E tests for critical flows

## Critical Authorization Regression

For each premium feature, test:

- Free user denied
- Paid user allowed
- Expired paid user denied/fallback
- Offer-code behavior as specified
- Admin/admin grant allowed where specified
- Direct API access denied when unauthorized

## Payment Tests

Cover:

- Nano 8 days
- Premium 30 days
- Family 30 days
- Failed/pending payment no access
- Duplicate verify no duplicate activation
- Duplicate webhook no duplicate activation
- Admin ₹1 test uses intended plan

## Teacher Tests

Cover:

- Free limit 10
- Paid limit 30
- ownership enforcement
- credential email paid-only
- invitations
- classrooms
- tasks
- notes privacy
- parent messaging

## Frontend Tests

Verify:

- loading/empty/error states
- disabled/upgrade UI
- tab/mobile navigation
- no raw backend errors
- no secrets in rendered payloads

## E2E Roadmap

Automate:

- [x] signup/free onboarding — `frontend/e2e/signup.spec.js`
- [ ] parent adds child
- [x] free access restrictions — `frontend/e2e/access-control.spec.js`
- [ ] paid upgrade flows (entry point into the Subscription page is covered
      by `access-control.spec.js`; the actual payment/checkout flow is not)
- [ ] expiry/fallback
- [ ] teacher adds student
- [ ] admin payment test
- [ ] admin operations checks

Also now covered, not on the original list:

- [x] login role-routing (student/parent/teacher/admin) and error handling —
      `frontend/e2e/login.spec.js`
- [x] public navigation and unauthenticated access guarding —
      `frontend/e2e/navigation.spec.js`

## Mobile Test Coverage — Gap Found 2026-08-26

**`mobile/` currently has zero automated test files** (`find mobile -iname "*.test.*"` → 0 results). Everything above is backend (pytest) or web frontend (vitest/Playwright) — the mobile app, which now has real Google OAuth, Doubt solving, Analytics, and Board Papers per `MOBILE_APP.md`, ships with no regression coverage at all. Not tracked in `TECH_DEBT.md` as its own item currently; flagging here since this doc is the canonical place regression gaps get planned against — add a tracked item if/when this becomes a priority.

## Test Suite Health Note (2026-08-26 spot-check)

A backend/frontend skip sweep (file-level `describe.skip`/`xdescribe`/`pytest.mark.skip`) found: **0** in `frontend/src/tests/` (68 files), **2** in `backend/tests/` (104 files) — both legitimate and neither security/payment-related (`test_doubt_kb_ai_off.py`, gated on a real API key being present locally; one parametrized case in `test_grade_5_to_10_mock_tests_ai_off.py`, gated on a question bank not yet built for Grades 5-8). `frontend/src/tests/LessonsPage.test.jsx`, previously quarantined (11 broken tests, commit `2ae1f99f`), was fully rewritten against the current Chapter Journey architecture (`5ecc3140`, 2026-08-16) and is in good standing at 30 tests. No wholesale-skipped security or payment test files found anywhere.

All of the above mock Supabase/backend network calls (`frontend/e2e/support/mockAuth.js`)
rather than running against a live Supabase project, so they run deterministically
off just the frontend dev server. The remaining unchecked items involve
multi-step backend mutations (creating child/student records, payment
webhooks, admin grants) that are better suited to real backend state and
haven't been tackled yet.
