/**
 * resolveSubscription.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Single canonical subscription resolver for the frontend.
 *
 * This is the ONLY place that decides what subscription state a user is in.
 * Both App.jsx and SubscriptionPlansPage.jsx must use this function so they
 * can never show conflicting plans for the same user.
 *
 * Four tiers (highest → lowest precedence):
 *   1. PAID (active)   — subscriptionExpiresAt in future OR perpetual paid plan key
 *   2. OFFER_CODE      — offerAccess.has_offer_access=true (free trial via offer code)
 *   3. ADMIN_GRANT     — accessCbse=true set directly by admin (no expiry, no offer)
 *   4. NONE (FREE)     — no access at all → subscription gate shows
 *
 * Maps to the four display tiers in SUBSCRIPTION_PLANS:
 *   free_tier → NONE / OFFER_CODE (limited access)
 *   free      → PAID (Premium Nano ₹99/8 days, full access)
 *   starter   → PAID (Premium ₹299/month, full access)
 *   family_premium → PAID (Family Premium ₹499/month, full access, 2 children)
 *
 * Invariant: planName is NEVER "Premium Nano" for offer-code users.
 */

export const ACCESS_SOURCE = Object.freeze({
  PAID: "PAID",
  OFFER_CODE: "OFFER_CODE",
  ADMIN_GRANT: "ADMIN_GRANT",
  NONE: "NONE",
});

export const TIER = Object.freeze({
  FREE: "FREE",
  PREMIUM: "PREMIUM",
});

/**
 * Resolve a user's canonical subscription state.
 *
 * @param {object} user        The user object from App.jsx / localStorage.
 *   Expected fields (all optional, missing treated as falsy):
 *     subscriptionExpiresAt  — ISO string from /api/auth/profile
 *     subscriptionDaysRemaining — int
 *     subscriptionExpiringSoon  — bool
 *     subscriptionPlan       — plan key string ("free", "starter", …)
 *     accessCbse             — bool
 *     accessSofScience       — bool
 *     accessSofMaths         — bool
 *     accessSofEnglish       — bool
 *     offerAccess            — bool (stored on user object from login)
 *
 * @param {object|null} offerAccess  Live response from /api/offer/my-access.
 *   Expected fields (all optional):
 *     has_offer_access  — bool
 *     valid_until       — ISO string
 *     days_remaining    — int
 *     expiring_soon     — bool
 *
 * @returns {{
 *   activeTier: "FREE"|"PREMIUM",
 *   planName: string,
 *   accessSource: "PAID"|"OFFER_CODE"|"ADMIN_GRANT"|"NONE",
 *   hasFullAccess: boolean,
 *   validUntil: string|null,
 *   daysRemaining: number|null,
 *   expiringSoon: boolean,
 * }}
 */
export function resolveSubscription(user = {}, offerAccess = null) {
  const now = Date.now();

  // ── 1. Active paid subscription (time-limited: Nano 8-day, monthly, annual) ─
  // subscriptionExpiresAt is ONLY set by profile_access_from_plan() after a real
  // Razorpay payment. It is never set by offer-code redemption.
  let hadExpiredSubscription = false;
  if (user.subscriptionExpiresAt) {
    const expiresMs = new Date(user.subscriptionExpiresAt).getTime();
    if (!isNaN(expiresMs) && expiresMs > now) {
      return {
        activeTier: TIER.PREMIUM,
        planName: _paidPlanName(user.subscriptionPlan),
        canonicalPlanKey: _canonicalPlanKey(user.subscriptionPlan),
        accessSource: ACCESS_SOURCE.PAID,
        hasFullAccess: true,
        validUntil: user.subscriptionExpiresAt,
        daysRemaining: user.subscriptionDaysRemaining ?? null,
        expiringSoon: !!user.subscriptionExpiringSoon,
      };
    }
    // Paid subscription expired — mark flag and continue.
    // Do NOT return yet: an active offer redemption should still provide access.
    // The hadExpiredSubscription flag prevents ADMIN_GRANT from firing (step 4).
    hadExpiredSubscription = true;
  }

  // ── 2. Perpetual paid plan (monthly/annual granted without expiry) ─────────
  const planKey = user.subscriptionPlan || "free";
  const hasAccessFlag = !!(
    user.accessCbse ||
    user.accessSofScience ||
    user.accessSofMaths ||
    user.accessSofEnglish
  );
  // Only treat as paid if plan key is NOT "free" — the "free" key is shared by
  // Free Tier AND Nano paid (₹99/8 days). subscriptionExpiresAt (step 1)
  // distinguishes them for active paid Nano. Perpetual (no expiry) non-"free"
  // plan keys are caught here.
  if (hasAccessFlag && planKey !== "free" && !user.subscriptionExpiresAt) {
    return {
      activeTier: TIER.PREMIUM,
      planName: _paidPlanName(planKey),
      canonicalPlanKey: _canonicalPlanKey(planKey),
      accessSource: ACCESS_SOURCE.PAID,
      hasFullAccess: true,
      validUntil: null,
      daysRemaining: null,
      expiringSoon: false,
    };
  }

  // ── 2b. Legacy Nano (plan_key="free" + accessCbse + no expiry) ────────────
  // Users who paid for Nano before subscription_expires_at was introduced.
  // Without this check they would incorrectly show "Admin Access" (step 4).
  if (hasAccessFlag && planKey === "free" && !user.subscriptionExpiresAt) {
    return {
      activeTier: TIER.PREMIUM,
      planName: "Premium Nano",
      canonicalPlanKey: "NANO",
      accessSource: ACCESS_SOURCE.PAID,
      hasFullAccess: true,
      validUntil: null,
      daysRemaining: null,
      expiringSoon: false,
    };
  }

  // ── 3. Valid offer / free-trial access ────────────────────────────────────
  if (offerAccess?.has_offer_access && offerAccess?.valid_until) {
    return {
      activeTier: TIER.FREE,
      planName: "Offer / Free Access",
      canonicalPlanKey: "FREE_TIER",
      accessSource: ACCESS_SOURCE.OFFER_CODE,
      hasFullAccess: false,
      validUntil: offerAccess.valid_until,
      daysRemaining: offerAccess.days_remaining ?? null,
      expiringSoon: !!offerAccess.expiring_soon,
    };
  }

  // ── 4. Admin-granted CBSE/SOF access ──────────────────────────────────────
  // Skip if subscription_expires_at was set (even if expired) — access_cbse may
  // still be True pending backend revocation; must not show "Admin Access".
  if (hasAccessFlag && !hadExpiredSubscription) {
    return {
      activeTier: TIER.PREMIUM,
      planName: "Admin Access",
      canonicalPlanKey: "ADMIN_GRANT",
      accessSource: ACCESS_SOURCE.ADMIN_GRANT,
      hasFullAccess: true,
      validUntil: null,
      daysRemaining: null,
      expiringSoon: false,
    };
  }

  // ── 5. Default free tier ──────────────────────────────────────────────────
  return _freeTierResult();
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function _freeTierResult() {
  return {
    activeTier: TIER.FREE,
    planName: "Free Tier",
    canonicalPlanKey: "FREE_TIER",
    accessSource: ACCESS_SOURCE.NONE,
    hasFullAccess: false,
    validUntil: null,
    daysRemaining: null,
    expiringSoon: false,
  };
}

function _paidPlanName(planKey) {
  switch (planKey) {
    case "free":            return "Premium Nano";
    case "family_premium":  return "Family Premium";
    case "family_annual":   return "Family Premium — Annual";
    case "standard_6month": return "Premium — 6 Months";
    case "standard_annual": return "Premium — Annual";
    default:                return "Premium";
  }
}

/**
 * Map raw DB plan key to canonical unambiguous key.
 * Callers of this function have already determined the user IS on a paid plan,
 * so "free" here means Nano (not Free Tier).
 */
function _canonicalPlanKey(planKey) {
  const mapping = {
    "free":           "NANO",
    "starter":        "PREMIUM",
    "premium":        "PREMIUM",
    "family_premium": "FAMILY_PREMIUM",
    "family_annual":  "FAMILY_ANNUAL",
    "standard_6month":"PREMIUM_6MONTH",
    "standard_annual":"PREMIUM_ANNUAL",
  };
  return mapping[planKey] ?? "PREMIUM";
}

/**
 * Returns true when the user has paid access (any active paid tier).
 *
 * Use this instead of raw `subscriptionPlan !== "free"` comparisons.
 * The "free" DB key is shared by both Free Tier and the Nano paid plan, so
 * `subscriptionPlan === "free"` is ambiguous — `accessCbse` is the
 * authoritative signal for "has paid plan access".
 *
 * SECURITY NOTE: `parentId` alone does NOT grant paid access.
 * A child added by a free-plan parent has parentId set but no accessCbse.
 * Only `accessCbse=true` (set by payment webhook or admin) grants access.
 *
 * Hierarchy:
 *   1. Admin → always has access
 *   2. accessCbse=true → paid, admin-granted, or active legacy Nano
 *      (this covers parent-managed children IF their parent paid — the
 *       payment webhook sets access_cbse=true on the child's profile)
 *   3. subscriptionExpiresAt in the future → active paid plan
 *   4. Otherwise → no paid access (Free Tier)
 *
 * @param {object} user
 */
export function hasPaidAccess(user = {}) {
  if (!user) return false;
  if (user.role === "admin") return true;

  // Active paid subscription (time-limited)
  if (user.subscriptionExpiresAt) {
    const expiresMs = new Date(user.subscriptionExpiresAt).getTime();
    if (!isNaN(expiresMs) && expiresMs > Date.now()) return true;
  }

  // access_cbse=true is set by payment webhook only — reliable paid indicator
  // NOTE: parentId alone is NOT sufficient — a free-plan parent's child has
  // parentId but no accessCbse and must be treated as Free Tier.
  if (user.accessCbse) return true;

  return false;
}

/**
 * Returns true when the subscription gate should be shown to a student.
 * Mirrors the `needsSubscription` condition in App.jsx exactly.
 *
 * @param {object} user
 * @param {object|null} offerAccess
 */
export function needsSubscriptionGate(user = {}, offerAccess = null) {
  if (user.role !== "student") return false;
  // NOTE: Do NOT gate parent-linked children from the subscription page.
  // They don't self-subscribe, but they still need proper authorization checks.
  // Removed: `if (user.parentId) return false;` — this was bypassing the gate
  // for ALL children regardless of whether the parent actually paid.
  // Children of free-plan parents should see the upgrade path.
  if (user.parentId) return false; // children subscribe via parent — no self-gate

  const resolved = resolveSubscription(user, offerAccess);
  // Gate fires only when there is no active access at all
  return resolved.accessSource === ACCESS_SOURCE.NONE;
}
