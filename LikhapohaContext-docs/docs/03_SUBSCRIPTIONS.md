# Subscriptions and Feature Authorization

## Plans

_Refreshed 2026-08-26 against `backend/app/data/subscription_plans.py` + `shared/config/subscriptionPlans.js` (frontend visibility always wins over backend `is_public` — see note below)._

| Plan | Price | Duration | Access | Child Limit | Status |
|---|---:|---:|---|---:|---|
| Free Tier | ₹0 | none | Limited | 1 by default unless configured otherwise | Public |
| Premium Nano | ₹99 | 8 days | Full | 1 | **Retired — not sold.** `isPublic: false` both layers; purchase 404s server-side. Existing holders keep access until expiry. |
| Premium | ₹299 | 30 days | Full | 1 | Public |
| Family Premium | ₹499 | 30 days | Full | 2 | Public |
| Premium — 6 Months | ₹1,495 | 184 days | Full | 1 | Hidden (offer-code / admin grant) |
| Premium — Annual | ₹2,999 | 366 days | Full | 1 | Hidden (offer-code / admin grant) |
| Family Premium — Annual | ₹4,999 | 366 days | Full | 2 | Hidden (offer-code / admin grant) |
| Exam Prep Center | ₹1,999 | 366 days | JEE/NEET/CUET/SAT/IELTS/TOEFL content only — **not** CBSE core access | — | Public, standalone add-on (added 2026-07, see the 2026-08-26 section below) |

> **Internal-only key found in code, not a real product plan:** `subscription_plans.py` also defines a `premium` key (`is_public: false`, same ₹299/30-day terms as `starter`/"Premium"). Purpose unconfirmed — looks like a vestigial duplicate. See `TECH_DEBT.md`.

## Core Rules

1. All new signups start in Free Tier.
2. Offer code is not required for signup.
3. Premium, Family Premium, Premium 6-Month, Premium Annual, and Family Annual are full-access plans while active. **Nano is retired** — no new subscriptions; existing holders keep access until expiry (do not treat it as a currently-sellable full-access plan).
4. Expired paid plans fall back to Free Tier or valid offer-code access.
5. Paid active plan takes precedence over free/offer access.
6. Pending/failed payments do not grant access.
7. Admin override must be separate from paid access and must not be revoked by expiry jobs.
8. Do not branch on raw `subscription_plan` in UI or feature endpoints.

## Canonical Plan Keys

Use stable canonical keys:

- `FREE_TIER`
- `NANO` (retired — legacy holders only, never assign to a new subscription)
- `PREMIUM`
- `FAMILY_PREMIUM`
- `PREMIUM_6MONTH`
- `PREMIUM_ANNUAL`
- `FAMILY_ANNUAL`
- `EXAM_PREP_CENTER` (standalone — does not grant CBSE core access)
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

---

## 2026-06-30: Plan Structure Update

### Correct Plan Order (parent subscription page)

| Order | DB Key | Label | Price | is_public |
|-------|--------|-------|-------|-----------|
| 1 | `free_tier` | Free Tier | ₹0 / free forever | ✅ |
| 2 | `free` | Premium Nano | ₹99 / 8 days | ✅ |
| 3 | `starter` | Premium | ₹299 / month | ✅ |
| 4 | `family_premium` | Family Premium | ₹499 / month | ✅ |

**Critical:** `profiles.subscription_plan = "free"` means Premium Nano (time-limited), NOT the free tier. Distinguished by `access_cbse=True + subscription_expires_at set`.

### subscription_plan_settings DB
All plans now stored in `subscription_plan_settings` table. `free_tier` added 2026-06-30. `free` plan corrected to show Premium Nano features and price.

### Frontend Plan Keys
- `free_tier` → label "Free Tier", shown as current for unsubscribed users
- `free` → label "Premium Nano", ₹99/8 days purchasable plan
- `starter` → label "Premium", ₹299/month
- `family_premium` → label "Family Premium", ₹499/month

**Source:** `frontend/src/config/subscriptionPlans.js`

---

## 2026-07-08: Centralized Subscription Management

### What is now DB-driven (no code deploy needed)

| Field | Where configured | Effect |
|---|---|---|
| `price` | `subscription_plan_settings` | Razorpay charges this amount (minus discount) |
| `discount_percent` | `subscription_plan_settings` | Applied to price before Razorpay charge |
| `duration_days` | `subscription_plan_settings` | Exact subscription expiry in days |
| `access_exam_prep` | `subscription_plan_settings` | Whether plan includes Exam Prep Center |
| `access_exemplar` | `subscription_plan_settings` | Whether plan includes Exemplar Research & Lessons |
| `access_cbse` | `subscription_plan_settings` | Core platform access after payment |
| `daily_token_limit` | `subscription_plan_settings` | AI token quota per day |
| `monthly_token_limit` | `subscription_plan_settings` | AI token quota per month |
| `included` / `not_included` | `subscription_plan_settings` | Feature list shown on subscription page |
| Contact details | `subscription_contact_settings` | Support email/phone/WhatsApp on parent page |

### Migration required

Run `backend/migrations/20260708_subscription_plan_feature_flags.sql` on **main Supabase** (`dpivlbbyzlbpwnwgajso`) to add:
- `duration_days integer` — overrides `billing_label→days` lookup
- `access_exam_prep boolean DEFAULT false`
- `access_exemplar boolean DEFAULT true`

### Expiry resolution (updated)

`plan_expires_at(plan)` now uses:
1. `plan.duration_days` (DB-explicit) → most precise, admin-configurable
2. `_BILLING_LABEL_TO_DAYS` lookup → legacy fallback
3. `None` → perpetual / admin-grant

**File:** `backend/app/routes/payments.py`

### Feature authorization — DB override

`feature_authorization_service.py` checks `_DB_DRIVEN_FEATURES` for:
- `EXAM_PREP_CONTENT` → reads `access_exam_prep` from `subscription_plan_settings`
- `EXEMPLAR` → reads `access_exemplar` from `subscription_plan_settings`
- `EXEMPLAR_RESEARCH` → reads `access_exemplar` from `subscription_plan_settings`

Admin can enable/disable these per-plan from Admin → Subscription Settings without code deployment.

### Admin UI fields (AdminSubscriptionSettingsPage)

Each plan card now shows:
- **Duration (days)** — number input, overrides billing label
- **🎓 Exam Prep (JEE/NEET/CUET)** — checkbox
- **📖 Exemplar Access** — checkbox

### Bulk Import grade sanitization

`POST /api/admin/exam-prep/questions/import-bulk` now sanitizes:
- `grade`: "Grade 11-12", "Grade 11/12", "12" → normalized to "Grade 11" or "Grade 12"
- `source_type`: unknown values → "llm_generated"
- `marks`, `negative_marks`: type-safe float conversion with fallback

### Extended plan keys (hidden, admin use)

| DB Key | Label | Price | Duration |
|---|---|---|---|
| `standard_6month` | Premium — 6 Months | ₹1,495 | 184 days |
| `standard_annual` | Premium — Annual | ₹2,999 | 366 days |
| `family_annual` | Family Premium — Annual | ₹4,999 | 366 days |

These are `is_public: false` and do not appear in the public subscription page unless admin enables them.

---

## 2026-08-26: Exam Prep Center Replaces Legacy Per-Exam Packs (TD-04 resolved)

**Background:** `TECH_DEBT.md`'s TD-04 flagged two coexisting, contradictory Exam Prep gating mechanisms — a legacy `exam_prep_subscriptions` table / `exam_prep_packs.py` route (per-exam pack purchases, only `jee_main`/`neet_ug`/`cuet_ug`) vs. the canonical `Feature.EXAM_PREP_CONTENT` check.

**Resolution:** The legacy pack system was deleted outright rather than revived — per its own removal comment in `subscription_plans.py`, no customer ever held a pack. Removed: `backend/app/routes/exam_prep_packs.py`, `backend/tests/test_exam_prep_packs.py`, `frontend/src/api/examPrepPacks.js`, and the pack-aware helpers `get_active_packs()` / `check_exam_content_access_with_packs()` from `exam_prep_service.py`. The `exam_prep_subscriptions` table itself is left in place as a historic migration only — no application code reads or writes it anymore.

**Current model — exactly one gate:** `exam_prep_service.check_exam_prep_content_access()` = grade/role eligibility (`check_exam_prep_access()`) + `authorize_feature(user_id, Feature.EXAM_PREP_CONTENT)`, which resolves via `subscription_plan_settings.access_exam_prep`. Satisfied by holding the `exam_prep_center` plan (₹1,999/year — see Plans table above) or an admin/test-user override. Free/Nano now uniformly get `has_access: false, preview_only: true` — no more partial "owned this one pack" access.

**Status note:** committed 2026-08-26.
