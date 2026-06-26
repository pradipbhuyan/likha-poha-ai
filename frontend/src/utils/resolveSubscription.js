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
  if (user.subscriptionExpiresAt) {
    const expiresMs = new Date(user.subscriptionExpiresAt).getTime();
    if (!isNaN(expiresMs) && expiresMs > now) {
      return {
        activeTier: TIER.PREMIUM,
        planName: _paidPlanName(user.subscriptionPlan),
        accessSource: ACCESS_SOURCE.PAID,
        hasFullAccess: true,
        validUntil: user.subscriptionExpiresAt,
        daysRemaining: user.subscriptionDaysRemaining ?? null,
        expiringSoon: !!user.subscriptionExpiringSoon,
      };
    }
    // Past expiry — fall through (backend should have revoked access_cbse already)
  }

  // ── 2. Perpetual paid plan (monthly/annual that has been granted without expiry) ─
  // Indicator: paid plan key (not "free") + any access flag + no expiry set.
  // This handles the transition period before subscription_expires_at was added
  // and any admin-activated monthly plans.
  const planKey = user.subscriptionPlan || "free";
  const hasAccessFlag = !!(
    user.accessCbse ||
    user.accessSofScience ||
    user.accessSofMaths ||
    user.accessSofEnglish
  );
  // Only treat as paid if plan key is NOT "free" — the "free" key is used by
  // both the free tier AND the Nano paid plan (₹99/8 days), so we rely on
  // subscriptionExpiresAt (step 1) to distinguish paid Nano from free.
  if (hasAccessFlag && planKey !== "free" && !user.subscriptionExpiresAt) {
    return {
      activeTier: TIER.PREMIUM,
      planName: _paidPlanName(planKey),
      accessSource: ACCESS_SOURCE.PAID,
      hasFullAccess: true,
      validUntil: null,
      daysRemaining: null,
      expiringSoon: false,
    };
  }

  // ── 3. Valid offer / free-trial access ────────────────────────────────────
  // Offer-code users have accessCbse=false in their profile (set by signup-with-offer-code).
  // Their access is determined by the offer_redemptions table, not profile flags.
  if (offerAccess?.has_offer_access && offerAccess?.valid_until) {
    return {
      activeTier: TIER.FREE,
      planName: "Offer / Free Access",
      accessSource: ACCESS_SOURCE.OFFER_CODE,
      hasFullAccess: false, // DKB-only gate applies to offer users
      validUntil: offerAccess.valid_until,
      daysRemaining: offerAccess.days_remaining ?? null,
      expiringSoon: !!offerAccess.expiring_soon,
    };
  }

  // ── 4. Admin-granted CBSE/SOF access (accessCbse set directly by admin) ──
  // Catches the case where an admin toggled access_cbse=true without creating a
  // formal subscription record.
  if (hasAccessFlag) {
    return {
      activeTier: TIER.PREMIUM,
      planName: "Admin Access",
      accessSource: ACCESS_SOURCE.ADMIN_GRANT,
      hasFullAccess: true,
      validUntil: null,
      daysRemaining: null,
      expiringSoon: false,
    };
  }

  // ── 5. Default free — no access ───────────────────────────────────────────
  return {
    activeTier: TIER.FREE,
    planName: "Free",
    accessSource: ACCESS_SOURCE.NONE,
    hasFullAccess: false,
    validUntil: null,
    daysRemaining: null,
    expiringSoon: false,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

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
 * Returns true when the subscription gate should be shown to a student.
 * Mirrors the `needsSubscription` condition in App.jsx exactly.
 *
 * @param {object} user
 * @param {object|null} offerAccess
 */
export function needsSubscriptionGate(user = {}, offerAccess = null) {
  if (user.role !== "student") return false;
  if (user.parentId) return false; // parent-linked children don't self-subscribe

  const resolved = resolveSubscription(user, offerAccess);
  // Gate fires only when there is no active access at all
  return resolved.accessSource === ACCESS_SOURCE.NONE;
}
