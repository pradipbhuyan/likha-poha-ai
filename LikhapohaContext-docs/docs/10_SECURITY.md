# Security and Authorization

## Core Security Rules

- Backend owns authorization.
- Frontend restrictions are not security boundaries.
- Admin-only endpoints must enforce admin role server-side.
- Teacher endpoints must enforce teacher ownership.
- Parent endpoints must enforce parent-child ownership.
- Student endpoints must enforce student identity/assignment.

## Secrets

Never expose:

- Supabase service role key
- JWTs
- API keys
- Razorpay secrets
- webhook secrets
- passwords
- temporary passwords
- raw payment payloads

## Passwords

Passwords must be handled through Supabase Auth/admin flows. Temporary passwords may be shown once only if necessary and must never be stored, logged, or audited in plaintext.

## Payments

- Verify Razorpay signatures.
- Use idempotency guards.
- Duplicate callbacks/webhooks must not double-activate or double-extend subscriptions.
- Admin ₹1 tests must be admin-only.

## Audit Logs

Audit sensitive actions. Sanitize metadata. Audit failure must not break main business flow.

## Rate Limiting

Rate limit sensitive endpoints such as login, signup, password reset, payment creation/verification, admin test payment, and AI/doubt endpoints.

## View as User

Use read-only frontend simulation. Do not exchange JWTs. Audit start/end/denied events.

---

## Critical Authorization Rules (Updated 2026-06-27)

### parentId Never Grants Feature Access

A child profile has `parent_id` set when created by a parent. This alone NEVER means the child has a paid subscription.

**Rule**: Feature access is determined exclusively by:
1. `access_cbse = true` on the child's own profile (set by payment webhook or admin)
2. An active `subscription_expires_at` in the future on the child's profile

**What this means in code**:
- Backend: `resolve_user_subscription(user_id)` reads from child's OWN profile
- Frontend: `hasPaidAccess(user)` checks `accessCbse` and `subscriptionExpiresAt` only. `user.parentId` is NEVER used as a paid access signal.

### Canonical Feature Authorization

All premium feature decisions must use `feature_authorization_service.py` on the backend:

```python
from app.services.feature_authorization_service import authorize_feature, Feature, require_feature

# Raises HTTP 403 if denied:
require_feature(user_id, Feature.EXEMPLAR)

# Or check manually:
result = authorize_feature(user_id, Feature.EXEMPLAR_RESEARCH)
if not result["allowed"]:
    raise HTTPException(403, detail=result["restriction_message"])
```

Frontend canonical check:
```js
import { hasPaidAccess } from "../utils/resolveSubscription";
const isPaid = hasPaidAccess(user); // uses accessCbse + subscriptionExpiresAt
```

### Exemplar Chapters Must Be Gated Backend-Side

Exemplar chapter names begin with `"Exemplar:"`. The lesson generation endpoint checks:
```python
if chapter.lower().startswith("exemplar") or ": exemplar" in chapter.lower():
    require_feature(user_id, Feature.EXEMPLAR)  # raises 403 for FREE_TIER
```

This check is placed AFTER the `is_free_tier_user` bypass so it catches free users even if they bypass the CBSE access check.

### Free Tier Mock Test Daily Limit

The 5/day limit is frontend-enforced via localStorage. The backend allows free users through mock test generation (they have limited but real access). The canonical daily limit constant is:
- Backend: `FREE_MOCK_TEST_DAILY_LIMIT = 5` in `feature_authorization_service.py`
- Frontend: `FREE_DAILY_MOCK_LIMIT = 5` in `MockTestPage.jsx`

Both must stay in sync.

### Feature Authorization Regression Tests

`backend/tests/test_feature_authorization.py` contains 69 regression tests covering:
- FREE_TIER denied for Exemplar/Exemplar Research/Unlimited Mock Tests
- All paid plans (NANO/PREMIUM/FAMILY/ADMIN_GRANT) get full access
- `hasPaidAccess(parentId only)` returns False
- `isFreeUser(child of free parent)` returns True
- Exemplar chapter detection
- Full scenario: "new free parent + Grade 10 child = denied Exemplar + limited mock tests"
