# Product Context

## Product Vision

The CBSE Tutor Platform is an AI-powered learning platform for CBSE students. It supports students, parents, teachers, and administrators through structured learning, mock tests, AI-assisted doubt resolution, exemplar practice, progress tracking, and classroom management.

The product must be reliable, safe, mobile-friendly, and understandable to non-technical users.

## Core User Roles

### Student

Students learn, practice, take mock tests, ask doubts, review exemplar material where allowed, and track progress.

### Parent

Parents create and manage child profiles, view progress, understand strengths and weaknesses, manage subscriptions, and receive notifications.

### Teacher

Teachers manage assigned students, classrooms, invitations, tasks, interventions, private notes, progress monitoring, and parent communication.

### Admin

Admins manage accounts, access, subscriptions, offers, parent-child associations, teacher-student associations, AI settings, operations, analytics, support, and platform health.

## Subscription Philosophy

Every new user can sign up with email/password or Google Auth without an offer code. New users start on Free Tier.

Paid plans unlock full platform access:

- **Premium**: ₹299/month, full platform access, one child profile
- **Family Premium**: ₹499/month, full platform access, two child profiles
- **Premium 6-Month**: ₹1,495 / 6 months (offer-code / admin only)
- **Premium Annual**: ₹2,999 / year (offer-code / admin only)
- **Family Annual**: ₹4,999 / year (offer-code / admin only)

> **Note:** The legacy "Premium Nano" plan (₹99/8 days) has been retired and is no longer sold (`isPublic: false`). Existing users on this plan retain their access until expiry. Do not create new Nano subscriptions through the UI.

Free Tier has restricted access. It must never accidentally receive full premium capability.

## Platform Access Terminology

Use “Platform Access” in user-facing UI. Do not show “CBSE Access” to admins, parents, teachers, or students unless referencing legacy implementation.

“Platform Access (Admin Override)” means an admin manually grants access outside normal payment flow.

## Canonical Access Philosophy

The platform must distinguish:

- Free Tier
- Offer-code access
- Active paid access
- Expired paid access
- Admin override
- Admin role

No feature should independently inspect raw fields such as `subscription_plan` or `access_cbse`. Use canonical subscription resolution and feature authorization.

## Teacher Product Philosophy

The Teacher Portal should feel like a classroom productivity workspace, not only a roster screen. Teachers should immediately understand:

- Who needs attention
- What tasks are pending
- Which invitations need action
- Which classrooms are struggling
- Which parents may need communication

Teacher features include student roster, invitations, classrooms, intervention queue, tasks, notes, timeline, classroom analytics, parent communication, and Teacher Assistant summaries.

## Parent Product Philosophy

The Parent Dashboard should help parents understand a child’s progress without interpreting raw data. Parents should see clear summaries, weak areas, homework/exam insights, subscription status, and notifications.

## Student Product Philosophy

The Student Dashboard should encourage progress and motivation through continue-learning flows, recommendations, mock test history, streaks, achievements, and clear access/upgrade messaging.

## Admin Product Philosophy

The Admin Console should be a mobile-friendly operations and support workspace. It includes structured tabs, quick actions, global search, favorites, recent activity, notification center, operations dashboard, analytics, support tools, bulk tools, and access management.

## Legal Pages Maintenance

The following legal pages must be kept in sync with the actual product state. **Update them whenever the product changes:**

| Page | File | Update when… |
|------|------|--------------|
| Refund Policy | `frontend/src/pages/RefundPolicyPage.jsx` | Plans, prices, or refund window change |
| Privacy Policy | `frontend/src/pages/PrivacyPolicyPage.jsx` | New data collected, new AI providers, new integrations |
| Terms of Service | `frontend/src/pages/TermsOfServicePage.jsx` | New features, grade range, plans, or operator details change |

**Checklist for each policy update:**
- [ ] Update the "Last updated: Month YYYY" date at the top
- [ ] Update the grade range if it changes from Grades 5–12
- [ ] Update the feature list in Terms of Service Section 2
- [ ] Update subscription plan names/prices in Refund Policy and Terms of Service
- [ ] Update the third-party service list in Privacy Policy if new AI providers or infrastructure is added
- [ ] Check that the contact email is still accurate (fetched dynamically from `/api/payments/contact` but the fallback is `likhapohaai@gmail.com`)

Each policy JSX file contains a `── Maintenance reminder ──` comment block at the top of the component to guide future edits.

## Business Rules

1. Offer codes are not required for new signup.
2. New users start in Free Tier.
3. Free Tier has restricted access.
4. Premium, Family Premium, and extended plans have full platform access while active.
5. Premium and Family Premium are valid for exactly 30 days.
6. Extended 6-month and annual plans use their configured `duration_days`.
7. Expired paid plans fall back to Free Tier or valid offer-code access.
8. Paid active plans override free/offer access.
9. Failed or pending payments must not unlock premium access.
10. Admin ₹1 payment tests must remain admin-only and must use intended plan, not charged amount.
11. The retired Nano plan (key: "free") must not appear in public plan cards or the comparison table (`isPublic: false`). Existing holders retain access until expiry.
11. Teacher Free plan allows up to 10 students.
12. Teacher paid plans allow up to 30 students.
13. Teacher credential email is paid-only.
14. Parent-child association is admin-controlled.
15. Admin grants must not be revoked by paid-plan expiry jobs.

## Product Guardrails

- Do not expose internal field names in the UI.
- Do not expose raw errors from Supabase/PostgREST to users.
- Do not invent analytics where data is unavailable.
- Show “Not available yet”, “No activity during selected period”, or “Unable to load” as appropriate.
- Prefer clear business language over implementation language.

## Definition of Done

A feature is complete only when:

- Backend authorization is enforced.
- Frontend renders correct state.
- Mobile UX is usable.
- Sensitive actions are audited.
- Tests cover success, failure, and access denial.
- Expired/legacy/subscription edge cases are covered where relevant.
- Documentation is updated if business rules change.
- **Legal pages (Refund Policy, Privacy Policy, Terms of Service) are reviewed and updated if the feature changes plans, grades, data collection, or features described therein.**
