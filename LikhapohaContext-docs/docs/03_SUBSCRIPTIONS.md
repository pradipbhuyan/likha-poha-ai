# Subscriptions and Feature Authorization

## Plans

| Plan | Price | Duration | Access | Child Limit |
|---|---:|---:|---|---:|
| Free Tier | ₹0 | none | Limited | 1 by default unless configured otherwise |
| Premium Nano | ₹99 | 8 days | Full | 1 |
| Premium | ₹299 | 30 days | Full | 1 |
| Family Premium | ₹499 | 30 days | Full | 2 |

## Core Rules

1. All new signups start in Free Tier.
2. Offer code is not required for signup.
3. Nano, Premium, and Family Premium are full-access plans only while active.
4. Expired paid plans fall back to Free Tier or valid offer-code access.
5. Paid active plan takes precedence over free/offer access.
6. Pending/failed payments do not grant access.
7. Admin override must be separate from paid access and must not be revoked by expiry jobs.
8. Do not branch on raw `subscription_plan` in UI or feature endpoints.

## Canonical Plan Keys

Use stable canonical keys:

- `FREE_TIER`
- `NANO`
- `PREMIUM`
- `FAMILY_PREMIUM`
- `ADMIN_GRANT`

Legacy values such as raw `free` must be normalized by the resolver.

## Subscription Resolver Output

Resolver output should include:

- `canonicalPlanKey`
- `planName`
- `source`
- `accessLevel`
- `hasFullAccess`
- `expiresAt`
- `childLimit`
- `studentLimit`
- `restrictions`

## Feature Authorization

Feature access must be determined by one canonical feature authorization service/matrix, not by UI conditionals or raw DB fields.

Expected authorization response:

```json
{
  "allowed": false,
  "feature": "EXEMPLAR",
  "canonicalPlanKey": "FREE_TIER",
  "reason": "premium_required",
  "upgradeMessage": "This feature is available with Premium."
}
```

## Protected Features

Feature authorization should cover at minimum:

- Lessons
- Exemplar lessons
- Exemplar research
- Mock tests
- Unlimited mock tests
- Ask Doubts
- AI chat/solutions
- Question bank
- Progress analytics
- Parent dashboard
- Teacher dashboard
- Admin panel

## Critical Regression Rule

A Free Tier child/student must not receive full access to:

- Exemplar lessons
- Exemplar section
- unrestricted mock tests
- premium AI features

Access must be blocked both in frontend navigation and backend endpoints.

## Expiry Behavior

- Nano expires after exactly 8 days.
- Premium expires after exactly 30 days.
- Family Premium expires after exactly 30 days.
- Expired paid plan no longer grants premium access.
- Expiry fallback should be handled by resolver and by idempotent expiry job.

## Admin Test Payments

Admin ₹1 payment tests are allowed only in admin test/payment tools. They must:

- be admin-only
- charge ₹1 in test flow
- activate by intended plan ID, not charged amount
- preserve normal checkout pricing
- be audited

## Teacher Plan Limits

- Free teacher: 10 students
- Paid teacher: 30 students
- Expired paid teacher: falls back to 10
- Credential email: paid-only

## Do Not

- Do not rename DB fields casually.
- Do not store new ambiguous plan keys.
- Do not let frontend-only gating serve as access control.
- Do not use raw `access_cbse` as product terminology.
