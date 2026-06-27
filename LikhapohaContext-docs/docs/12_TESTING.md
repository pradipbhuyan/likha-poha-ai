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

- signup/free onboarding
- parent adds child
- free access restrictions
- paid upgrade flows
- expiry/fallback
- teacher adds student
- admin payment test
- admin operations checks
