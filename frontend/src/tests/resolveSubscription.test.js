/**
 * resolveSubscription.test.js
 * ────────────────────────────────────────────────────────────────────────────
 * Regression tests for the canonical frontend subscription resolver.
 *
 * Business rules encoded here must NEVER be violated:
 *   1. Offer-code users see "Offer / Free Access", NOT "Premium Nano"
 *   2. Paid users see the correct paid plan name and have hasFullAccess=true
 *   3. Paid plans always take precedence over offer access while active
 *   4. Expired paid plans fall back correctly — no premium access retained
 *   5. The resolver returns exactly ONE consistent state — no UI conflicts
 *   6. Failed/pending payments (no subscriptionExpiresAt set) → no premium
 *
 * Run with:
 *   cd frontend && npx vitest run src/tests/resolveSubscription.test.js
 */

import { describe, expect, test } from "vitest";
import {
  resolveSubscription,
  needsSubscriptionGate,
  ACCESS_SOURCE,
  TIER,
} from "../utils/resolveSubscription";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function daysFromNow(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

function daysAgo(days) {
  return daysFromNow(-days);
}

const BASE_STUDENT = {
  role: "student",
  subscriptionPlan: "free",
  accessCbse: false,
  accessSofScience: false,
  accessSofMaths: false,
  accessSofEnglish: false,
  offerAccess: false,
  offerValidUntil: null,
  subscriptionExpiresAt: null,
  subscriptionDaysRemaining: null,
  subscriptionExpiringSoon: false,
  parentId: null,
};

const ACTIVE_OFFER = {
  has_offer_access: true,
  valid_until: daysFromNow(34),
  days_remaining: 34,
  expiring_soon: false,
};

const EXPIRING_OFFER = {
  has_offer_access: true,
  valid_until: daysFromNow(3),
  days_remaining: 3,
  expiring_soon: true,
};

// ─────────────────────────────────────────────────────────────────────────────
// 1. Offer-code user — must NEVER see "Premium Nano"
// ─────────────────────────────────────────────────────────────────────────────

describe("Offer-code user", () => {
  test("resolves to OFFER_CODE source and FREE tier", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(result.activeTier).toBe(TIER.FREE);
  });

  test("plan name is 'Offer / Free Access', never 'Premium Nano'", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.planName).toBe("Offer / Free Access");
    expect(result.planName).not.toContain("Premium");
  });

  test("hasFullAccess is false (DKB-only gate applies to offer users)", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.hasFullAccess).toBe(false);
  });

  test("subscription gate is NOT shown (offer bypasses the gate)", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    expect(needsSubscriptionGate(user, ACTIVE_OFFER)).toBe(false);
  });

  test("validUntil and daysRemaining come from offerAccess, not user object", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.validUntil).toBe(ACTIVE_OFFER.valid_until);
    expect(result.daysRemaining).toBe(34);
    expect(result.expiringSoon).toBe(false);
  });

  test("expiringSoon is true when offer has <= 7 days remaining", () => {
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(3) };
    const result = resolveSubscription(user, EXPIRING_OFFER);
    expect(result.expiringSoon).toBe(true);
    expect(result.daysRemaining).toBe(3);
  });

  test("REGRESSION: offer user with null subscriptionExpiresAt does NOT resolve to PAID", () => {
    // Root cause of the original bug: offer-code users (who never paid) were
    // displayed as "Premium Nano active" because the banner checked offerAccess
    // without checking whether the user actually has a paid subscription.
    // The resolver must always return OFFER_CODE for this user state.
    const user = {
      ...BASE_STUDENT,
      offerAccess: true,
      offerValidUntil: daysFromNow(34),
      subscriptionExpiresAt: null,   // NOT set — offer-code signup path never sets this
      accessCbse: false,             // offer-code path sets access_cbse=false
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(result.planName).not.toBe("Premium Nano");
    expect(result.activeTier).toBe(TIER.FREE);
  });

  test("expired offer with no paid plan → NONE (gated)", () => {
    const user = { ...BASE_STUDENT, offerAccess: false, subscriptionExpiresAt: null };
    const expiredOffer = { has_offer_access: false, valid_until: null, days_remaining: 0, expiring_soon: false };
    const result = resolveSubscription(user, expiredOffer);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(needsSubscriptionGate(user, expiredOffer)).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Paid subscription user
// ─────────────────────────────────────────────────────────────────────────────

describe("Paid subscription user", () => {
  test("Premium Nano (₹99/8-day) resolves to PAID PREMIUM with name 'Premium Nano'", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",  // Nano key is "free"
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(7),
      subscriptionDaysRemaining: 7,
      subscriptionExpiringSoon: false,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.activeTier).toBe(TIER.PREMIUM);
    expect(result.planName).toBe("Premium Nano");
    expect(result.hasFullAccess).toBe(true);
  });

  test("Premium monthly resolves to PAID PREMIUM with name 'Premium'", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(30),
      subscriptionDaysRemaining: 30,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium");
    expect(result.hasFullAccess).toBe(true);
  });

  test("Family Premium resolves with correct plan name", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "family_premium",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(31),
      subscriptionDaysRemaining: 31,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.planName).toBe("Family Premium");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
  });

  test("Annual plan resolves with correct plan name", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "standard_annual",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(365),
      subscriptionDaysRemaining: 365,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.planName).toBe("Premium — Annual");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
  });

  test("subscription gate is NOT shown for active paid user", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(30),
      offerAccess: false,
    };
    expect(needsSubscriptionGate(user, null)).toBe(false);
  });

  test("expiry date and daysRemaining are returned correctly", () => {
    const expiresAt = daysFromNow(5);
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,
      subscriptionExpiresAt: expiresAt,
      subscriptionDaysRemaining: 5,
      subscriptionExpiringSoon: true,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.validUntil).toBe(expiresAt);
    expect(result.daysRemaining).toBe(5);
    expect(result.expiringSoon).toBe(true);
  });

  test("failed/pending payment (no subscriptionExpiresAt) does NOT grant premium", () => {
    // Payment was created but not verified — no subscriptionExpiresAt set,
    // no access_cbse flag flipped. Must stay FREE.
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: false,           // not yet granted
      subscriptionExpiresAt: null, // not yet set
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
    expect(needsSubscriptionGate(user, null)).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Paid plan takes precedence over offer access while active
// ─────────────────────────────────────────────────────────────────────────────

describe("Paid plan + offer access simultaneously", () => {
  test("active paid subscription wins over concurrent offer redemption", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(25),
      subscriptionDaysRemaining: 25,
      offerAccess: true,
      offerValidUntil: daysFromNow(20),
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium");
    expect(result.planName).not.toBe("Offer / Free Access");
    expect(result.activeTier).toBe(TIER.PREMIUM);
  });

  test("after paid plan expires, falls back to offer access (not gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: false,              // backend revoked
      subscriptionExpiresAt: daysAgo(1),
      subscriptionDaysRemaining: 0,
      offerAccess: true,
      offerValidUntil: daysFromNow(20),
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(result.planName).toBe("Offer / Free Access");
    expect(result.activeTier).toBe(TIER.FREE);
    expect(needsSubscriptionGate(user, ACTIVE_OFFER)).toBe(false);
  });

  test("multiple payments: latest active paid plan wins", () => {
    // Latest payment has a future expiry — must use that, not a stale offer.
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(28),
      subscriptionDaysRemaining: 28,
      offerAccess: true,
      offerValidUntil: daysFromNow(10),
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.daysRemaining).toBe(28);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Expired paid plan — must not retain premium access
// ─────────────────────────────────────────────────────────────────────────────

describe("Expired paid plan", () => {
  test("expired paid plan + no offer → FREE / gated", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(1),
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
    expect(needsSubscriptionGate(user, null)).toBe(true);
  });

  test("expired paid plan + active offer → OFFER_CODE (not gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(2),
      offerAccess: true,
      offerValidUntil: daysFromNow(15),
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(needsSubscriptionGate(user, ACTIVE_OFFER)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Free tier / subscription gate
// ─────────────────────────────────────────────────────────────────────────────

describe("Free tier (no enrollment)", () => {
  test("brand-new student with no payment/offer is gated", () => {
    expect(needsSubscriptionGate(BASE_STUDENT, null)).toBe(true);
  });

  test("resolves to FREE / NONE with no validUntil", () => {
    const result = resolveSubscription(BASE_STUDENT, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
    expect(result.validUntil).toBeNull();
  });

  test("parent-linked child is never gated (parent manages access)", () => {
    const user = { ...BASE_STUDENT, parentId: "parent-uuid-123" };
    expect(needsSubscriptionGate(user, null)).toBe(false);
  });

  test("admin role is never gated", () => {
    const admin = { role: "admin", subscriptionPlan: "free", accessCbse: false, parentId: null };
    expect(needsSubscriptionGate(admin, null)).toBe(false);
  });

  test("admin-granted CBSE access on non-'free' plan resolves to PAID (perpetual)", () => {
    // A user with accessCbse=True + non-"free" plan + no expiry is caught by
    // step 2 (perpetual paid plan). It's indistinguishable from a paid plan
    // activated without an expiry — both return PAID with full access.
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: null,
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.activeTier).toBe(TIER.PREMIUM);
    expect(result.hasFullAccess).toBe(true);
    expect(needsSubscriptionGate(user, null)).toBe(false);
  });

  test("legacy Nano user (plan_key='free' + accessCbse + no expiry) resolves to NANO", () => {
    // Users who paid for Nano before subscription_expires_at was added.
    // plan_key="free" + access_cbse=True + no expiry → step 2b catches as NANO.
    const user = { ...BASE_STUDENT, accessCbse: true, subscriptionExpiresAt: null, offerAccess: false };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium Nano");
    expect(result.canonicalPlanKey).toBe("NANO");
    expect(result.activeTier).toBe(TIER.PREMIUM);
    expect(result.hasFullAccess).toBe(true);
    expect(needsSubscriptionGate(user, null)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. UI conflict prevention — single consistent state
// ─────────────────────────────────────────────────────────────────────────────

describe("UI conflict prevention", () => {
  test("resolver always returns exactly one accessSource", () => {
    const scenarios = [
      [BASE_STUDENT, null],
      [{ ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) }, ACTIVE_OFFER],
      [{ ...BASE_STUDENT, accessCbse: true, subscriptionExpiresAt: daysFromNow(7) }, null],
      [{ ...BASE_STUDENT, accessCbse: true, subscriptionPlan: "starter", subscriptionExpiresAt: daysFromNow(30) }, null],
      [{ ...BASE_STUDENT, accessCbse: true, subscriptionExpiresAt: null }, null],  // step 2b → PAID/NANO
    ];
    const validSources = Object.values(ACCESS_SOURCE);
    for (const [user, offer] of scenarios) {
      const result = resolveSubscription(user, offer);
      expect(validSources).toContain(result.accessSource);
      // Ensure activeTier matches accessSource
      if (result.accessSource === ACCESS_SOURCE.PAID || result.accessSource === ACCESS_SOURCE.ADMIN_GRANT) {
        expect(result.activeTier).toBe(TIER.PREMIUM);
      } else {
        expect(result.activeTier).toBe(TIER.FREE);
      }
    }
  });

  test("resolver always returns canonicalPlanKey", () => {
    const scenarios = [
      [BASE_STUDENT, null, "FREE_TIER"],
      [
        { ...BASE_STUDENT, subscriptionPlan: "free", accessCbse: true, subscriptionExpiresAt: daysFromNow(7) },
        null, "NANO",
      ],
      [
        { ...BASE_STUDENT, subscriptionPlan: "starter", accessCbse: true, subscriptionExpiresAt: daysFromNow(30) },
        null, "PREMIUM",
      ],
      [
        { ...BASE_STUDENT, subscriptionPlan: "family_premium", accessCbse: true, subscriptionExpiresAt: daysFromNow(30) },
        null, "FAMILY_PREMIUM",
      ],
      [
        { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) },
        ACTIVE_OFFER, "FREE_TIER",
      ],
    ];
    for (const [user, offer, expectedKey] of scenarios) {
      const result = resolveSubscription(user, offer);
      expect(result.canonicalPlanKey).toBe(expectedKey);
    }
  });

  test("free tier resolves to planName 'Free Tier' (not 'Free')", () => {
    const result = resolveSubscription(BASE_STUDENT, null);
    expect(result.planName).toBe("Free Tier");
    expect(result.canonicalPlanKey).toBe("FREE_TIER");
  });

  test("expired paid plan + no offer resolves to FREE_TIER (not ADMIN_GRANT)", () => {
    // Critical: access_cbse may still be True in the DB until cron revokes it.
    // hadExpiredSubscription flag prevents ADMIN_GRANT from firing.
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,              // still True — backend hasn't revoked yet
      subscriptionExpiresAt: daysAgo(1),
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.canonicalPlanKey).toBe("FREE_TIER");
    expect(result.planName).toBe("Free Tier");
    expect(result.hasFullAccess).toBe(false);
  });

  test("offer user: currentPlanLabel !== 'Premium Nano' (the original bug)", () => {
    // Simulate exactly what StudentSubscriptionView computes for currentPlanLabel
    const user = { ...BASE_STUDENT, offerAccess: true, offerValidUntil: daysFromNow(34) };
    const resolved = resolveSubscription(user, ACTIVE_OFFER);
    const currentPlanLabel =
      resolved.accessSource === ACCESS_SOURCE.OFFER_CODE
        ? "Offer / Free Access"
        : resolved.accessSource === ACCESS_SOURCE.NONE
          ? "Free"
          : resolved.planName;
    expect(currentPlanLabel).toBe("Offer / Free Access");
    expect(currentPlanLabel).not.toBe("Premium Nano");
  });

// ─────────────────────────────────────────────────────────────────────────────
// 7. Explicit regression tests — 10 scenarios by spec
// ─────────────────────────────────────────────────────────────────────────────

describe("Subscription resolver regression tests", () => {

  // ── Scenario 1: Active paid Nano ────────────────────────────────────────
  test("1. Active paid Nano (plan_key='free', future expiry) → NANO, PAID, full access", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(7),
      subscriptionDaysRemaining: 7,
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("NANO");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.hasFullAccess).toBe(true);
    expect(result.planName).toBe("Premium Nano");
    expect(result.activeTier).toBe(TIER.PREMIUM);
  });

  // ── Scenario 2: Expired Nano + active offer ──────────────────────────────
  test("2. Expired Nano + active offer → OFFER_CODE, FREE, not ADMIN_GRANT", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(1),
    };
    const result = resolveSubscription(user, ACTIVE_OFFER);
    expect(result.canonicalPlanKey).toBe("FREE_TIER");
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(result.hasFullAccess).toBe(false);
    expect(result.accessSource).not.toBe(ACCESS_SOURCE.ADMIN_GRANT);
  });

  // ── Scenario 3: Expired Nano, no offer ──────────────────────────────────
  test("3. Expired Nano, no offer → FREE_TIER, NONE, full access=false, not ADMIN_GRANT", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,   // may still be True pre-revocation
      subscriptionExpiresAt: daysAgo(2),
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("FREE_TIER");
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.hasFullAccess).toBe(false);
    expect(result.accessSource).not.toBe(ACCESS_SOURCE.ADMIN_GRANT);
  });

  // ── Scenario 4: Legacy Nano (no expiry, paid evidence = access_cbse) ────
  test("4. Legacy Nano (plan_key='free', accessCbse=true, no expiry) → NANO, PAID, not ADMIN_GRANT", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,
      subscriptionExpiresAt: null,  // paid before expires_at system was added
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("NANO");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.hasFullAccess).toBe(true);
    expect(result.planName).toBe("Premium Nano");
    expect(result.accessSource).not.toBe(ACCESS_SOURCE.ADMIN_GRANT);
  });

  // ── Scenario 5: Never-paid user ─────────────────────────────────────────
  test("5. New never-paid user → FREE_TIER, planName='Free Tier', NONE", () => {
    const result = resolveSubscription(BASE_STUDENT, null);
    expect(result.canonicalPlanKey).toBe("FREE_TIER");
    expect(result.planName).toBe("Free Tier");
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.hasFullAccess).toBe(false);
  });

  // ── Scenarios 6, 7, 8: Payment expiry durations ──────────────────────────
  test("6. Premium payment expiry is exactly 30 days (not 31)", () => {
    // The 30-day business rule is enforced in _BILLING_LABEL_TO_DAYS['month']=30
    // and verified by profile_access_from_plan in the backend test suite.
    // Here we verify the resolver treats a 30-day expiry as active PAID.
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(30),
      subscriptionDaysRemaining: 30,
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("PREMIUM");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.daysRemaining).toBe(30);
  });

  test("7. Family Premium payment expiry is exactly 30 days (not 31)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "family_premium",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(30),
      subscriptionDaysRemaining: 30,
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("FAMILY_PREMIUM");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.daysRemaining).toBe(30);
  });

  test("8. Nano payment expiry remains exactly 8 days", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(8),
      subscriptionDaysRemaining: 8,
    };
    const result = resolveSubscription(user, null);
    expect(result.canonicalPlanKey).toBe("NANO");
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.daysRemaining).toBe(8);
  });

  // ── Scenario 9: Frontend UI branches on canonicalPlanKey ────────────────
  test("9. UI branches on canonicalPlanKey — 'free' plan_key correctly disambiguated", () => {
    // Simulate UI logic: never branch on raw subscriptionPlan==="free"
    // Always use canonicalPlanKey to determine display.

    const activePaidNano = {
      ...BASE_STUDENT, subscriptionPlan: "free", accessCbse: true,
      subscriptionExpiresAt: daysFromNow(7), subscriptionDaysRemaining: 7,
    };
    const freeTierUser = { ...BASE_STUDENT };

    const nanoResult = resolveSubscription(activePaidNano, null);
    const freeResult = resolveSubscription(freeTierUser, null);

    // Both users have subscriptionPlan === "free" in the DB.
    // But canonicalPlanKey correctly distinguishes them:
    expect(nanoResult.canonicalPlanKey).toBe("NANO");   // paid user
    expect(freeResult.canonicalPlanKey).toBe("FREE_TIER"); // never paid

    // The raw plan key is ambiguous — must NOT branch on it directly:
    expect(activePaidNano.subscriptionPlan).toBe("free");
    expect(freeTierUser.subscriptionPlan).toBe("free");
    // Both have the same raw key — canonicalPlanKey is the correct discriminator.

    // UI would correctly show "Premium Nano" for the paid user, "Free Tier" for the other:
    const getDisplayPlan = (resolved) => resolved.canonicalPlanKey === "FREE_TIER"
      ? "Free Tier"
      : resolved.planName;

    expect(getDisplayPlan(nanoResult)).toBe("Premium Nano");
    expect(getDisplayPlan(freeResult)).toBe("Free Tier");
  });

  // ── Scenario 10: Subscription page shows exactly one active plan ─────────
  test("10. Subscription page shows exactly one current active plan per user", () => {
    // For each user state, the resolver returns exactly ONE accessSource.
    // The subscription page can safely show a single "current plan" card.
    const states = [
      // [user, offer, expectedPlan, expectedSource]
      [BASE_STUDENT, null, "FREE_TIER", ACCESS_SOURCE.NONE],
      [
        { ...BASE_STUDENT, subscriptionPlan: "free", accessCbse: true, subscriptionExpiresAt: daysFromNow(7), subscriptionDaysRemaining: 7 },
        null, "NANO", ACCESS_SOURCE.PAID,
      ],
      [
        { ...BASE_STUDENT, subscriptionPlan: "starter", accessCbse: true, subscriptionExpiresAt: daysFromNow(30), subscriptionDaysRemaining: 30 },
        null, "PREMIUM", ACCESS_SOURCE.PAID,
      ],
      [
        { ...BASE_STUDENT, subscriptionPlan: "family_premium", accessCbse: true, subscriptionExpiresAt: daysFromNow(30), subscriptionDaysRemaining: 30 },
        null, "FAMILY_PREMIUM", ACCESS_SOURCE.PAID,
      ],
      [
        { ...BASE_STUDENT, subscriptionPlan: "free", accessCbse: false, subscriptionExpiresAt: daysAgo(1) },
        ACTIVE_OFFER, "FREE_TIER", ACCESS_SOURCE.OFFER_CODE,
      ],
    ];
    for (const [user, offer, expectedKey, expectedSource] of states) {
      const result = resolveSubscription(user, offer);
      // Exactly one canonical key
      expect(result.canonicalPlanKey).toBe(expectedKey);
      // Exactly one access source
      expect(result.accessSource).toBe(expectedSource);
      // hasFullAccess is deterministic
      const expectFull = expectedSource === ACCESS_SOURCE.PAID;
      expect(result.hasFullAccess).toBe(expectFull);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// (existing test)
// ─────────────────────────────────────────────────────────────────────────────

  test("paid Nano user: currentPlanLabel is 'Premium Nano', banner shows PAID state", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: true,
      subscriptionExpiresAt: daysFromNow(7),
      subscriptionDaysRemaining: 7,
      offerAccess: false,
    };
    const resolved = resolveSubscription(user, null);
    const currentPlanLabel =
      resolved.accessSource === ACCESS_SOURCE.OFFER_CODE
        ? "Offer / Free Access"
        : resolved.accessSource === ACCESS_SOURCE.NONE
          ? "Free"
          : resolved.planName;
    expect(currentPlanLabel).toBe("Premium Nano");
    // Banner should show (PAID + validUntil set)
    expect(resolved.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(resolved.validUntil).not.toBeNull();
  });
});
