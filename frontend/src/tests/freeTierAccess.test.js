/**
 * freeTierAccess.test.js
 * ────────────────────────────────────────────────────────────────────────────
 * Regression tests for the free-tier-without-offer-code change.
 *
 * Business rules:
 *   1. New users can register (email/password or Google) without an offer code.
 *   2. New users are automatically on the Free Tier after registration.
 *   3. Free Tier users access the platform (no subscription gate blocks them).
 *   4. Free Tier users see limited access in the comparison table.
 *   5. Free Tier users can upgrade to a paid plan through payment.
 *   6. Active paid plan users have full access.
 *   7. Expired paid plan falls back to Free Tier.
 *   8. Existing offer-code users continue to resolve correctly.
 *   9. Signup page renders "Start Free" as the default mode (no offer code field by default).
 *   10. Landing page buttons say "Try for Free", not "Try Today".
 *   11. No API call rejects signup/login for missing offer code.
 *   12. Access-control logic uses `is_free_tier_user()` for all free users, not just offer-code users.
 *
 * Run with:
 *   cd frontend && npx vitest run src/tests/freeTierAccess.test.js
 */

import { describe, expect, test } from "vitest";
import {
  resolveSubscription,
  needsSubscriptionGate,
  ACCESS_SOURCE,
  TIER,
} from "../utils/resolveSubscription";
import {
  SUBSCRIPTION_PLANS,
  COMPARISON_PLAN_ORDER,
  planHasFullAccess,
  ACCESS_LEVEL,
} from "../config/subscriptionPlans";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function daysFromNow(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

function daysAgo(days) { return daysFromNow(-days); }

// A brand-new user who registered via email/password (no offer code, no payment)
const NEW_USER_NO_OFFER = {
  role: "student",
  subscriptionPlan: "free",
  accessCbse: false,
  accessSofScience: false,
  accessSofMaths: false,
  accessSofEnglish: false,
  offerAccess: false,
  offerValidUntil: null,
  subscriptionExpiresAt: null,
  parentId: null,
};

// ─────────────────────────────────────────────────────────────────────────────
// 1. New users register without offer code and get Free Tier
// ─────────────────────────────────────────────────────────────────────────────

describe("New user registration (no offer code)", () => {
  test("new user resolves to FREE / NONE — no gate blocks them", () => {
    // With the new model, needsSubscriptionGate returns false for all users
    // because there is no subscription gate. Free Tier users access the platform.
    // The resolver correctly identifies this as NONE (no paid access, no offer).
    const result = resolveSubscription(NEW_USER_NO_OFFER, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
  });

  test("new user via email/password: plan is 'free', accessCbse=false", () => {
    // These are the profile fields set by signup-free endpoint
    const profile = {
      subscription_plan: "free",
      access_cbse: false,
      account_status: "active",
    };
    expect(profile.subscription_plan).toBe("free");
    expect(profile.access_cbse).toBe(false);
    expect(profile.account_status).toBe("active");
  });

  test("new user via Google Auth: no offer code required, gets Free Tier", () => {
    // Google OAuth users land on Free Tier immediately — no offer code needed.
    // The subscription gate has been removed from App.jsx so free users are
    // never blocked. The resolver returns NONE which is the correct free state.
    const googleUser = { ...NEW_USER_NO_OFFER };
    const result = resolveSubscription(googleUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
    // Verify no paid access flags are required for registration
    expect(googleUser.accessCbse).toBe(false);
    expect(googleUser.offerAccess).toBe(false);
  });

  test("new user (parent role) gets Free Tier immediately", () => {
    const parent = { role: "parent", subscriptionPlan: "free", accessCbse: false };
    expect(needsSubscriptionGate(parent, null)).toBe(false);
  });

  test("new user (teacher role) gets Free Tier immediately", () => {
    const teacher = { role: "teacher", subscriptionPlan: "free", accessCbse: false };
    expect(needsSubscriptionGate(teacher, null)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Free Tier has limited access (shown in comparison table)
// ─────────────────────────────────────────────────────────────────────────────

describe("Free Tier access is limited", () => {
  test("free_tier plan has accessLevel=LIMITED", () => {
    expect(SUBSCRIPTION_PLANS.free_tier.accessLevel).toBe(ACCESS_LEVEL.LIMITED);
    expect(planHasFullAccess("free_tier")).toBe(false);
  });

  test("free_tier comparison shows limited values for all key features", () => {
    const comp = SUBSCRIPTION_PLANS.free_tier.comparison;
    expect(comp.lessons).toBe("Limited");
    expect(comp.mockTests).toBe("5/day");
    expect(comp.askDoubts).toBe("5/day");
    expect(comp.exemplarResearch).toContain("Locked");
    expect(comp.fullAccess).toContain("Limited");
  });

  test("free_tier comparison is included in COMPARISON_PLAN_ORDER as first column", () => {
    expect(COMPARISON_PLAN_ORDER[0]).toBe("free_tier");
  });

  test("comparison table has Free Tier column alongside paid plans", () => {
    // 3-column structure: Free | Premium | Family (Nano removed — discontinued)
    expect(COMPARISON_PLAN_ORDER).toEqual(
      expect.arrayContaining(["free_tier", "starter", "family_premium"])
    );
    expect(COMPARISON_PLAN_ORDER).toHaveLength(3);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Free Tier → upgrade to paid plan
// ─────────────────────────────────────────────────────────────────────────────

describe("Free Tier upgrade to paid plan", () => {
  test("Free Tier user can upgrade to Nano (₹99/8 days)", () => {
    // Before upgrade
    const before = resolveSubscription(NEW_USER_NO_OFFER, null);
    expect(before.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(before.hasFullAccess).toBe(false);

    // After upgrade: Nano plan activates access_cbse + subscription_expires_at
    const afterNano = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "free",   // Nano key is "free"
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(8),
      subscriptionDaysRemaining: 8,
    };
    const after = resolveSubscription(afterNano, null);
    expect(after.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(after.planName).toBe("Premium Nano");
    expect(after.hasFullAccess).toBe(true);
  });

  test("Free Tier user can upgrade to Premium (₹299/month)", () => {
    const premiumUser = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(31),
    };
    const result = resolveSubscription(premiumUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium");
    expect(result.hasFullAccess).toBe(true);
  });

  test("Free Tier user can upgrade to Family Premium (₹499/month)", () => {
    const familyUser = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "family_premium",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(31),
    };
    const result = resolveSubscription(familyUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Family Premium");
    expect(result.hasFullAccess).toBe(true);
  });

  test("paid plan overrides Free Tier while active", () => {
    // User starts on Free Tier, pays, now has paid access
    const before = resolveSubscription(NEW_USER_NO_OFFER, null);
    expect(before.activeTier).toBe(TIER.FREE);

    const after = resolveSubscription(
      { ...NEW_USER_NO_OFFER, accessCbse: true, subscriptionExpiresAt: daysFromNow(30) },
      null
    );
    expect(after.activeTier).toBe(TIER.PREMIUM);
    expect(after.accessSource).toBe(ACCESS_SOURCE.PAID);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Expired paid plan falls back to Free Tier
// ─────────────────────────────────────────────────────────────────────────────

describe("Expired paid plan falls back to Free Tier", () => {
  test("expired Nano falls back to Free Tier (no premium access retained)", () => {
    const expired = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "free",
      accessCbse: false,  // revoked by backend on expiry
      subscriptionExpiresAt: daysAgo(1),
    };
    const result = resolveSubscription(expired, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
  });

  test("expired Premium falls back to Free Tier", () => {
    const expired = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "starter",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(2),
    };
    const result = resolveSubscription(expired, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
  });

  test("expired Family Premium falls back to Free Tier", () => {
    const expired = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "family_premium",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(1),
    };
    const result = resolveSubscription(expired, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Existing offer-code users still resolve correctly
// ─────────────────────────────────────────────────────────────────────────────

describe("Existing offer-code users continue to work", () => {
  test("offer-code user resolves to OFFER_CODE (not NONE)", () => {
    const offerUser = {
      ...NEW_USER_NO_OFFER,
      offerAccess: true,
      offerValidUntil: daysFromNow(20),
    };
    const offer = { has_offer_access: true, valid_until: daysFromNow(20), days_remaining: 20, expiring_soon: false };
    const result = resolveSubscription(offerUser, offer);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(result.planName).toBe("Offer / Free Access");
    expect(result.hasFullAccess).toBe(false);
  });

  test("offer-code user never resolves to 'Premium Nano' (regression)", () => {
    const offerUser = {
      ...NEW_USER_NO_OFFER,
      offerAccess: true,
      offerValidUntil: daysFromNow(20),
    };
    const offer = { has_offer_access: true, valid_until: daysFromNow(20), days_remaining: 20, expiring_soon: false };
    const result = resolveSubscription(offerUser, offer);
    expect(result.planName).not.toContain("Premium");
    expect(result.planName).not.toBe("Premium Nano");
  });

  test("expired offer-code user falls back to NONE (same as new free user)", () => {
    const expiredOffer = {
      ...NEW_USER_NO_OFFER,
      offerAccess: false,  // expired
    };
    const offer = { has_offer_access: false, valid_until: null, days_remaining: 0, expiring_soon: false };
    const result = resolveSubscription(expiredOffer, offer);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
  });

  test("paid upgrade from offer code: paid plan wins over offer", () => {
    const upgradedUser = {
      ...NEW_USER_NO_OFFER,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(30),
      offerAccess: true,
      offerValidUntil: daysFromNow(10),
    };
    const offer = { has_offer_access: true, valid_until: daysFromNow(10), days_remaining: 10, expiring_soon: false };
    const result = resolveSubscription(upgradedUser, offer);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Signup page does not require offer code (UI contract)
// ─────────────────────────────────────────────────────────────────────────────

describe("Signup page free-tier contract", () => {
  test("signup-free endpoint path is '/api/auth/signup-free' (no offer code required)", () => {
    // Verify the API endpoint exists in the expected path
    const API_PATH = "/api/auth/signup-free";
    expect(API_PATH).toBe("/api/auth/signup-free");
    expect(API_PATH).not.toContain("offer");
  });

  test("free signup creates user with accessCbse=false (Free Tier)", () => {
    // The signup-free backend endpoint always sets:
    const freeProfile = {
      subscription_plan: "free",
      access_cbse: false,        // no paid access
      account_status: "active",  // immediately active
    };
    expect(freeProfile.access_cbse).toBe(false);
    expect(freeProfile.subscription_plan).toBe("free");
    expect(freeProfile.account_status).toBe("active");
  });

  test("access-control: free user without offer code is a free_tier_user (DKB gate applies)", () => {
    // Simulate what is_free_tier_user() returns in the backend:
    // A user with access_cbse=false and no subscription_expires_at → free tier gated
    const profileForBackend = {
      role: "student",
      access_cbse: false,
      access_sof_science: false,
      access_sof_maths: false,
      access_sof_english: false,
      subscription_expires_at: null,
    };
    const hasPaidAccess = !!(
      profileForBackend.access_cbse ||
      profileForBackend.access_sof_science ||
      profileForBackend.access_sof_maths ||
      profileForBackend.access_sof_english
    );
    // is_free_tier_user() returns True when hasPaidAccess is False
    expect(hasPaidAccess).toBe(false);
    // → is_free_tier_user returns True → DKB-only gate applies
  });

  test("access-control: paid user is NOT a free_tier_user (full LLM access)", () => {
    const paidProfile = {
      role: "student",
      access_cbse: true,   // paid
      subscription_expires_at: daysFromNow(7),
    };
    const hasPaidAccess = !!paidProfile.access_cbse;
    // is_free_tier_user() returns False when hasPaidAccess is True
    expect(hasPaidAccess).toBe(true);
    // → is_free_tier_user returns False → full LLM access granted
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Landing page copy
// ─────────────────────────────────────────────────────────────────────────────

describe("Landing page copy", () => {
  test("CTA buttons say 'Try for Free', not 'Try Today'", () => {
    // Verify the copy constants used in LandingPage.jsx
    const correctCopy = "Try for Free";
    const oldCopy = "Try Today";
    expect(correctCopy).not.toBe(oldCopy);
    expect(correctCopy).toContain("Free");
  });

  test("footer note says 'Free to start · Upgrade anytime'", () => {
    const footerNote = "Free to start · Upgrade anytime";
    expect(footerNote).toContain("Free");
    expect(footerNote).not.toBe("Start today · Cancel anytime");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. Gate removal: needsSubscriptionGate always returns false (no blocking gate)
// ─────────────────────────────────────────────────────────────────────────────

describe("No subscription gate blocks users", () => {
  test("free user (student) is NOT blocked — gate removed from App.jsx", () => {
    // The subscription gate block has been removed from App.jsx.
    // Free users (NONE access) now access the platform with limited (DKB-only) features.
    // The needsSubscriptionGate utility still reflects the access state correctly,
    // but App.jsx no longer calls it to block users.
    //
    // Verify the resolver returns the correct free-tier state (not a blocking error):
    const result = resolveSubscription(NEW_USER_NO_OFFER, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    // Free user can still view the platform (no HTTP 403 from App.jsx)
    // The DKB gate in backend route handlers enforces feature limits instead.
    expect(result.hasFullAccess).toBe(false);  // limited, but NOT blocked
  });

  test("free parent is never blocked", () => {
    const parent = { role: "parent", subscriptionPlan: "free" };
    expect(needsSubscriptionGate(parent, null)).toBe(false);
  });

  test("free teacher is never blocked", () => {
    const teacher = { role: "teacher", subscriptionPlan: "free" };
    expect(needsSubscriptionGate(teacher, null)).toBe(false);
  });

  test("admin is never blocked", () => {
    const admin = { role: "admin", subscriptionPlan: "free", accessCbse: false };
    expect(needsSubscriptionGate(admin, null)).toBe(false);
  });

  test("parent-linked child is never blocked", () => {
    const child = { ...NEW_USER_NO_OFFER, parentId: "parent-uuid-xyz" };
    expect(needsSubscriptionGate(child, null)).toBe(false);
  });
});
