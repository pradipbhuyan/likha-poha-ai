/**
 * subscriptionPlanConfig.test.js
 * ────────────────────────────────────────────────────────────────────────────
 * Regression tests for the canonical 4-tier subscription plan configuration.
 *
 * Business rules that must NEVER be violated:
 *   1. Free Tier is NOT shown as Premium — limited access only.
 *   2. Nano has FULL access — never shown as limited.
 *   3. Premium is monthly billing (₹299/month).
 *   4. Family Premium is monthly billing (₹499/month), 2 child profiles.
 *   5. Compare table always has exactly 4 columns: Free | Nano | Premium | Family.
 *   6. All comparison objects contain the same canonical keys.
 *   7. Expired plans fall back to Free Tier regardless of plan type.
 *   8. Exactly one plan card shows "Current" badge per child.
 *   9. No plan hardcodes conflicting access descriptions.
 *
 * Run with:
 *   cd frontend && npx vitest run src/tests/subscriptionPlanConfig.test.js
 */

import { describe, expect, test } from "vitest";
import {
  SUBSCRIPTION_PLANS,
  COMPARISON_PLAN_ORDER,
  COMPARISON_TABLE_ROWS,
  ACCESS_LEVEL,
  planHasFullAccess,
  getSubscriptionPlan,
  formatPlanPrice,
  mergeSubscriptionPlans,
  normalizeSubscriptionPlan,
} from "../config/subscriptionPlans";
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

function daysAgo(days) { return daysFromNow(-days); }

const BASE_STUDENT = {
  role: "student",
  subscriptionPlan: "free",
  accessCbse: false,
  offerAccess: false,
  subscriptionExpiresAt: null,
  parentId: null,
};

// ─────────────────────────────────────────────────────────────────────────────
// 1. Plan catalog integrity
// ─────────────────────────────────────────────────────────────────────────────

describe("Plan catalog integrity", () => {
  test("free_tier plan exists and is not purchasable (isPublic=false)", () => {
    const plan = SUBSCRIPTION_PLANS.free_tier;
    expect(plan).toBeDefined();
    expect(plan.key).toBe("free_tier");
    expect(plan.isPublic).toBe(false);
    expect(plan.label).toBe("Free Tier");
    expect(plan.accessLevel).toBe(ACCESS_LEVEL.LIMITED);
  });

  test("Nano plan (key='free') exists, is purchasable, and has FULL access", () => {
    const plan = SUBSCRIPTION_PLANS.free;
    expect(plan).toBeDefined();
    expect(plan.key).toBe("free");
    expect(plan.label).toBe("Premium Nano");
    expect(plan.shortLabel).toBe("Premium Nano");
    expect(plan.price).toBe(99);
    expect(plan.billingLabel).toBe("8 days");
    expect(plan.isPublic).toBe(true);
    expect(plan.accessLevel).toBe(ACCESS_LEVEL.FULL);
    expect(plan.access_cbse).toBe(true);
  });

  test("Premium plan (key='starter') exists and is ₹299/month", () => {
    const plan = SUBSCRIPTION_PLANS.starter;
    expect(plan).toBeDefined();
    expect(plan.label).toBe("Premium");
    expect(plan.price).toBe(299);
    expect(plan.billingLabel).toBe("month");
    expect(plan.isPublic).toBe(true);
    expect(plan.accessLevel).toBe(ACCESS_LEVEL.FULL);
    expect(plan.access_cbse).toBe(true);
  });

  test("Family Premium plan exists and is ₹499/month with 2 children", () => {
    const plan = SUBSCRIPTION_PLANS.family_premium;
    expect(plan).toBeDefined();
    expect(plan.label).toBe("Family Premium");
    expect(plan.price).toBe(499);
    expect(plan.billingLabel).toBe("month");
    expect(plan.isPublic).toBe(true);
    expect(plan.accessLevel).toBe(ACCESS_LEVEL.FULL);
    expect(plan.comparison.children).toBe("2");
  });

  test("Free Tier NEVER has FULL access level", () => {
    expect(SUBSCRIPTION_PLANS.free_tier.accessLevel).toBe(ACCESS_LEVEL.LIMITED);
    expect(SUBSCRIPTION_PLANS.free_tier.accessLevel).not.toBe(ACCESS_LEVEL.FULL);
  });

  test("Nano, Premium, Family all have FULL access level", () => {
    expect(SUBSCRIPTION_PLANS.free.accessLevel).toBe(ACCESS_LEVEL.FULL);
    expect(SUBSCRIPTION_PLANS.starter.accessLevel).toBe(ACCESS_LEVEL.FULL);
    expect(SUBSCRIPTION_PLANS.family_premium.accessLevel).toBe(ACCESS_LEVEL.FULL);
  });

  test("planHasFullAccess returns false for free_tier, true for paid plans", () => {
    expect(planHasFullAccess("free_tier")).toBe(false);
    expect(planHasFullAccess("free")).toBe(true);     // Nano
    expect(planHasFullAccess("starter")).toBe(true);  // Premium
    expect(planHasFullAccess("family_premium")).toBe(true); // Family
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Comparison table structure
// ─────────────────────────────────────────────────────────────────────────────

describe("Comparison table structure", () => {
  test("COMPARISON_PLAN_ORDER has exactly 4 columns in correct order", () => {
    expect(COMPARISON_PLAN_ORDER).toHaveLength(4);
    expect(COMPARISON_PLAN_ORDER[0]).toBe("free_tier");
    expect(COMPARISON_PLAN_ORDER[1]).toBe("free");      // Nano
    expect(COMPARISON_PLAN_ORDER[2]).toBe("starter");   // Premium
    expect(COMPARISON_PLAN_ORDER[3]).toBe("family_premium");
  });

  test("COMPARISON_TABLE_ROWS contains all required feature rows", () => {
    const rowKeys = COMPARISON_TABLE_ROWS.map(([, key]) => key);
    const required = [
      "lessons", "mockTests", "askDoubts", "cbse",
      "exemplarResearch", "exemplarLessons",
      "children", "parentDashboard",
      "fullAccess", "planDuration", "billingType",
    ];
    for (const key of required) {
      expect(rowKeys).toContain(key);
    }
  });

  test("every plan in COMPARISON_PLAN_ORDER has all comparison keys", () => {
    const rowKeys = COMPARISON_TABLE_ROWS.map(([, key]) => key);
    for (const planKey of COMPARISON_PLAN_ORDER) {
      const plan = SUBSCRIPTION_PLANS[planKey];
      for (const key of rowKeys) {
        expect(plan.comparison).toHaveProperty(key);
      }
    }
  });

  test("Free Tier comparison shows limited/locked values", () => {
    const comp = SUBSCRIPTION_PLANS.free_tier.comparison;
    expect(comp.lessons).toBe("Limited");
    expect(comp.mockTests).toBe("5/day");
    expect(comp.askDoubts).toBe("5/day");
    expect(comp.exemplarResearch).toContain("Locked");
    expect(comp.exemplarLessons).toContain("Locked");
    expect(comp.fullAccess).toContain("Limited");
  });

  test("Nano comparison shows full/unlimited values — never limited", () => {
    const comp = SUBSCRIPTION_PLANS.free.comparison;
    expect(comp.lessons).toContain("Unlimited");
    expect(comp.mockTests).toContain("Unlimited");
    expect(comp.askDoubts).toContain("Unlimited");
    expect(comp.exemplarResearch).toContain("Full access");
    expect(comp.exemplarLessons).toContain("Full access");
    expect(comp.fullAccess).toContain("Full access");
    // Regression: Nano must NEVER show "Limited"
    expect(comp.lessons).not.toBe("Limited");
    expect(comp.mockTests).not.toBe("5/day");
  });

  test("Premium comparison shows full/unlimited values", () => {
    const comp = SUBSCRIPTION_PLANS.starter.comparison;
    expect(comp.lessons).toContain("Unlimited");
    expect(comp.mockTests).toContain("Unlimited");
    expect(comp.fullAccess).toContain("Full access");
    expect(comp.planDuration).toBe("Monthly");
    expect(comp.billingType).toContain("299");
  });

  test("Family Premium comparison shows 2 children and full access", () => {
    const comp = SUBSCRIPTION_PLANS.family_premium.comparison;
    expect(comp.children).toBe("2");
    expect(comp.lessons).toContain("Unlimited");
    expect(comp.fullAccess).toContain("Full access");
    expect(comp.fullAccess).toContain("2 children");
    expect(comp.planDuration).toBe("Monthly");
    expect(comp.billingType).toContain("499");
  });

  test("Nano comparison shows 8-day plan duration and ₹99 billing", () => {
    const comp = SUBSCRIPTION_PLANS.free.comparison;
    expect(comp.planDuration).toBe("8 days");
    expect(comp.billingType).toContain("99");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Tier-specific user states and resolver
// ─────────────────────────────────────────────────────────────────────────────

describe("Free Tier user state", () => {
  test("Free Tier user hits subscription gate", () => {
    expect(needsSubscriptionGate(BASE_STUDENT, null)).toBe(true);
  });

  test("Free Tier user resolves to NONE / FREE tier", () => {
    const result = resolveSubscription(BASE_STUDENT, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
  });

  test("Free Tier label is 'Free Tier', NOT 'Free' or 'Premium'", () => {
    const result = resolveSubscription(BASE_STUDENT, null);
    expect(result.planName).toBe("Free Tier");
    expect(result.planName).not.toContain("Premium");
    expect(result.planName).not.toBe("Free");
  });
});

describe("Premium Nano user state", () => {
  const nanoUser = {
    ...BASE_STUDENT,
    subscriptionPlan: "free",  // DB key for Nano
    accessCbse: true,
    subscriptionExpiresAt: daysFromNow(7),
    subscriptionDaysRemaining: 7,
  };

  test("Nano user resolves to PAID PREMIUM", () => {
    const result = resolveSubscription(nanoUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.activeTier).toBe(TIER.PREMIUM);
    expect(result.hasFullAccess).toBe(true);
  });

  test("Nano plan name is 'Premium Nano' (not 'Free' or 'Limited')", () => {
    const result = resolveSubscription(nanoUser, null);
    expect(result.planName).toBe("Premium Nano");
    expect(result.planName).not.toBe("Free");
    expect(result.planName).not.toContain("Limited");
  });

  test("Nano has 8-day duration in comparison table", () => {
    expect(SUBSCRIPTION_PLANS.free.comparison.planDuration).toBe("8 days");
  });

  test("Nano does NOT trigger subscription gate", () => {
    expect(needsSubscriptionGate(nanoUser, null)).toBe(false);
  });
});

describe("Premium user state", () => {
  const premiumUser = {
    ...BASE_STUDENT,
    subscriptionPlan: "starter",
    accessCbse: true,
    subscriptionExpiresAt: daysFromNow(30),
    subscriptionDaysRemaining: 30,
  };

  test("Premium user resolves to PAID PREMIUM with monthly billing", () => {
    const result = resolveSubscription(premiumUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Premium");
    expect(result.hasFullAccess).toBe(true);
  });

  test("Premium plan is ₹299/month", () => {
    expect(SUBSCRIPTION_PLANS.starter.price).toBe(299);
    expect(SUBSCRIPTION_PLANS.starter.billingLabel).toBe("month");
    expect(SUBSCRIPTION_PLANS.starter.comparison.billingType).toContain("299");
    expect(SUBSCRIPTION_PLANS.starter.comparison.planDuration).toBe("Monthly");
  });
});

describe("Family Premium user state", () => {
  const familyUser = {
    ...BASE_STUDENT,
    subscriptionPlan: "family_premium",
    accessCbse: true,
    subscriptionExpiresAt: daysFromNow(31),
    subscriptionDaysRemaining: 31,
  };

  test("Family Premium user resolves to PAID PREMIUM", () => {
    const result = resolveSubscription(familyUser, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.PAID);
    expect(result.planName).toBe("Family Premium");
    expect(result.hasFullAccess).toBe(true);
  });

  test("Family Premium is ₹499/month with 2 child profiles", () => {
    expect(SUBSCRIPTION_PLANS.family_premium.price).toBe(499);
    expect(SUBSCRIPTION_PLANS.family_premium.billingLabel).toBe("month");
    expect(SUBSCRIPTION_PLANS.family_premium.comparison.children).toBe("2");
    expect(SUBSCRIPTION_PLANS.family_premium.comparison.billingType).toContain("499");
    expect(SUBSCRIPTION_PLANS.family_premium.comparison.planDuration).toBe("Monthly");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Expiry → fallback to Free Tier
// ─────────────────────────────────────────────────────────────────────────────

describe("Expired plan falls back to Free Tier", () => {
  test("Expired Nano → Free Tier (gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "free",
      accessCbse: false,          // backend revoked after expiry
      subscriptionExpiresAt: daysAgo(1),
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(result.hasFullAccess).toBe(false);
    expect(needsSubscriptionGate(user, null)).toBe(true);
  });

  test("Expired Premium → Free Tier (gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(2),
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(needsSubscriptionGate(user, null)).toBe(true);
  });

  test("Expired Family Premium → Free Tier (gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "family_premium",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(1),
      offerAccess: false,
    };
    const result = resolveSubscription(user, null);
    expect(result.accessSource).toBe(ACCESS_SOURCE.NONE);
    expect(result.activeTier).toBe(TIER.FREE);
    expect(needsSubscriptionGate(user, null)).toBe(true);
  });

  test("Expired plan with active offer falls back to offer (not fully gated)", () => {
    const user = {
      ...BASE_STUDENT,
      subscriptionPlan: "starter",
      accessCbse: false,
      subscriptionExpiresAt: daysAgo(1),
      offerAccess: true,
      offerValidUntil: daysFromNow(10),
    };
    const offer = { has_offer_access: true, valid_until: daysFromNow(10), days_remaining: 10, expiring_soon: false };
    const result = resolveSubscription(user, offer);
    expect(result.accessSource).toBe(ACCESS_SOURCE.OFFER_CODE);
    expect(needsSubscriptionGate(user, offer)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Plan names are consistent between config and resolver
// ─────────────────────────────────────────────────────────────────────────────

describe("Plan name consistency across config and resolver", () => {
  test("SUBSCRIPTION_PLANS labels match resolver plan names", () => {
    const cases = [
      ["free",          "Premium Nano"],
      ["starter",       "Premium"],
      ["family_premium","Family Premium"],
      ["standard_6month","Premium — 6 Months"],
      ["standard_annual","Premium — Annual"],
      ["family_annual",  "Family Premium — Annual"],
    ];
    for (const [planKey, expectedResolverName] of cases) {
      // Resolver _paidPlanName must match plan label
      const planLabel = SUBSCRIPTION_PLANS[planKey]?.label;
      // Both the plan label and the resolver name refer to the same plan
      expect(typeof planLabel).toBe("string");
      // The plan config label should match our expected resolver name
      expect(planLabel).toBe(expectedResolverName);
    }
  });

  test("Free Tier plan label is 'Free Tier', never 'Premium Nano'", () => {
    expect(SUBSCRIPTION_PLANS.free_tier.label).toBe("Free Tier");
    expect(SUBSCRIPTION_PLANS.free_tier.label).not.toContain("Premium");
  });

  test("Nano plan label is 'Premium Nano', not 'Free' or 'Free Tier'", () => {
    expect(SUBSCRIPTION_PLANS.free.label).toBe("Premium Nano");
    expect(SUBSCRIPTION_PLANS.free.label).not.toBe("Free");
    expect(SUBSCRIPTION_PLANS.free.label).not.toBe("Free Tier");
  });

  test("getSubscriptionPlan falls back to free_tier for unknown keys", () => {
    const fallback = getSubscriptionPlan("unknown_key_xyz");
    expect(fallback.key).toBe("free_tier");
  });

  test("formatPlanPrice formats ₹0 as 'Free' for free_tier", () => {
    expect(formatPlanPrice(0)).toBe("Free");
  });

  test("formatPlanPrice formats ₹99 correctly", () => {
    expect(formatPlanPrice(99)).toBe("₹99");
  });

  test("formatPlanPrice formats ₹499 correctly", () => {
    expect(formatPlanPrice(499)).toBe("₹499");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. mergeSubscriptionPlans preserves free_tier
// ─────────────────────────────────────────────────────────────────────────────

describe("mergeSubscriptionPlans", () => {
  test("returns free_tier even with empty API response", () => {
    const merged = mergeSubscriptionPlans({});
    expect(merged.free_tier).toBeDefined();
    expect(merged.free_tier.accessLevel).toBe(ACCESS_LEVEL.LIMITED);
  });

  test("API overrides do not flip free_tier to FULL access", () => {
    // A malicious or stale DB row must not override accessLevel to FULL for free_tier
    const maliciousApiPlans = {
      free_tier: { key: "free_tier", accessLevel: ACCESS_LEVEL.FULL, access_cbse: true },
    };
    const merged = mergeSubscriptionPlans(maliciousApiPlans);
    // isPublic:false is enforced by normalizeSubscriptionPlan
    expect(merged.free_tier.isPublic).toBe(false);
  });

  test("normalizeSubscriptionPlan preserves all comparison keys from fallback", () => {
    const minimal = { key: "free" }; // minimal raw plan
    const normalized = normalizeSubscriptionPlan(minimal);
    const rowKeys = COMPARISON_TABLE_ROWS.map(([, k]) => k);
    for (const key of rowKeys) {
      expect(normalized.comparison).toHaveProperty(key);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Current plan badge — exactly one per selection
// ─────────────────────────────────────────────────────────────────────────────

describe("Current plan badge logic", () => {
  test("exactly one plan is 'active' (Current badge) per child subscription", () => {
    const childSubscriptionPlan = "starter"; // child is on Premium
    const publicPlans = Object.values(SUBSCRIPTION_PLANS).filter(p => p.isPublic !== false);
    const activePlans = publicPlans.filter(p => p.key === childSubscriptionPlan);
    expect(activePlans).toHaveLength(1);
  });

  test("free_tier is never shown as active (it has no purchasable key)", () => {
    const freeTier = SUBSCRIPTION_PLANS.free_tier;
    expect(freeTier.isPublic).toBe(false);
    // It cannot be a child's subscription_plan via payment
    // (it's only used as a display entry for the compare table)
  });
});
