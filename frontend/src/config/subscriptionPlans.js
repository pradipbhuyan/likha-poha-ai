/**
 * subscriptionPlans.js — Canonical plan configuration
 * ─────────────────────────────────────────────────────────────────────────────
 * Single source of truth for all plan definitions, pricing, features, and
 * comparison data used across the entire platform.
 *
 * Four tiers (in display order):
 *   1. free_tier  — Free Tier       (no payment required, limited access)
 *   2. free       — Premium Nano    ₹99  / 8 days  (full access, time-limited)
 *   3. starter    — Premium         ₹299 / month   (full access, monthly)
 *   4. family_premium — Family Premium ₹499 / month (full access, 2 children)
 *
 * Rules enforced here:
 *   • free_tier is NEVER shown as Premium.
 *   • Nano is NEVER shown as limited access — it has FULL access for 8 days.
 *   • Premium and Family Premium are monthly plans.
 *   • All comparison values are consistent with backend access-control logic.
 *
 * COMPARISON_PLAN_ORDER is the canonical column order for the compare table:
 *   Feature | Free Tier | Premium Nano | Premium | Family Premium
 */

// ─────────────────────────────────────────────────────────────────────────────
// Access-level constants — used in comparison cells and access checks
// ─────────────────────────────────────────────────────────────────────────────

export const ACCESS_LEVEL = Object.freeze({
  LIMITED: "LIMITED",
  FULL: "FULL",
});

// ─────────────────────────────────────────────────────────────────────────────
// Plan catalog
// ─────────────────────────────────────────────────────────────────────────────

export const SUBSCRIPTION_PLANS = {
  // ── FREE TIER ─────────────────────────────────────────────────────────────
  // Not a purchasable plan — used for comparison table display only.
  // Users on this tier see the subscription gate.
  free_tier: {
    key: "free_tier",
    label: "Free Tier",
    shortLabel: "Free",
    price: 0,
    billingLabel: "Free",
    audience: "Perfect for getting started.",
    badge: "",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: false,     // Not purchasable — only shown in compare table
    displayOrder: 0,
    accessLevel: ACCESS_LEVEL.LIMITED,
    access_cbse: false,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 0,
    monthly_token_limit: 0,
    included: [
      "Limited daily AI access",
      "Core learning features",
      "Parent Dashboard",
      "Upgrade anytime",
    ],
    notIncluded: [
      "Full AI lessons",
      "Unlimited mock tests",
      "Unlimited doubt solving",
      "Exemplar Research",
      "Exemplar Lessons",
    ],
    comparison: {
      children: "1",
      lessons: "Limited",
      mockTests: "5/day",
      askDoubts: "5/day",
      cbse: "Limited",
      exemplarResearch: "❌ Locked",
      exemplarLessons: "❌ Locked",
      parentDashboard: "Basic",
      fullAccess: "❌ Limited",
      planDuration: "—",
      billingType: "Free",
    },
  },

  // ── PREMIUM NANO ──────────────────────────────────────────────────────────
  // Paid plan: ₹99 / 8 days. Full platform access, time-limited.
  // DB key is "free" for legacy reasons (subscription_plan = "free" in profiles).
  // Distinguished from free_tier by: access_cbse=true + subscription_expires_at set.
  free: {
    key: "free",
    label: "Premium Nano",
    shortLabel: "Premium Nano",
    price: 99,
    billingLabel: "8 days",
    audience:
      "Experience the complete learning platform before committing to a monthly plan.",
    badge: "Start here",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 1,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 100000,
    monthly_token_limit: 1000000,
    included: [
      "All CBSE subjects · All grades",
      "AI Lessons",
      "Ask Doubt",
      "Mock Tests",
      "Parent Dashboard",
      "Progress Insights",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + alerts",
      fullAccess: "✅ Full access",
      planDuration: "8 days",
      billingType: "₹99 one-time",
    },
  },

  // ── PREMIUM ───────────────────────────────────────────────────────────────
  // Paid plan: ₹299 / month. Full platform access, monthly renewal.
  starter: {
    key: "starter",
    label: "Premium",
    shortLabel: "Premium",
    price: 299,
    billingLabel: "month",
    audience:
      "Ideal for students preparing consistently throughout the academic year.",
    badge: "Most Popular",
    recommended: true,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 2,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 100000,
    monthly_token_limit: 3000000,
    included: [
      "Everything in Premium Nano",
      "Continuous monthly access",
      "Unlimited learning within fair usage policy",
      "Priority support",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + alerts",
      fullAccess: "✅ Full access",
      planDuration: "Monthly",
      billingType: "₹299 / month",
    },
  },

  // Hidden alias kept for backwards-compatibility with admin flows
  premium: {
    key: "premium",
    label: "Premium",
    shortLabel: "Premium",
    price: 299,
    billingLabel: "month",
    audience:
      "Best for serious CBSE exam prep — unlimited AI lessons, doubts, and mock tests every month.",
    badge: "",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: false,
    displayOrder: 3,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 100000,
    monthly_token_limit: 3000000,
    included: [
      "All CBSE subjects · All grades",
      "Unlimited doubt solving",
      "Full question bank access",
      "Unlimited mock tests",
      "Parent dashboard + alerts",
      "Exemplar Research & Lessons",
      "Priority support",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + alerts",
      fullAccess: "✅ Full access",
      planDuration: "Monthly",
      billingType: "₹299 / month",
    },
  },

  // ── FAMILY PREMIUM ────────────────────────────────────────────────────────
  // Paid plan: ₹499 / month. Full access for up to 2 children.
  family_premium: {
    key: "family_premium",
    label: "Family Premium",
    shortLabel: "Family Premium",
    price: 499,
    billingLabel: "month",
    audience:
      "One subscription for families with up to two children.",
    badge: "Best value",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 4,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 150000,
    monthly_token_limit: 5000000,
    included: [
      "Everything in Premium",
      "Up to 2 children",
      "Separate child progress",
      "Parent Dashboard",
      "Family learning management",
    ],
    notIncluded: [],
    comparison: {
      children: "2",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + analytics",
      fullAccess: "✅ Full access (2 children)",
      planDuration: "Monthly",
      billingType: "₹499 / month",
    },
  },

  // ── Extended plans (hidden from public plan cards, admin use) ─────────────
  standard_6month: {
    key: "standard_6month",
    label: "Premium — 6 Months",
    shortLabel: "6-Month",
    price: 1495,
    billingLabel: "6 months",
    audience:
      "Pay for 5 months and get 6 — save ₹299 vs monthly. Great for a full semester.",
    badge: "🎁 1 Month Free",
    recommended: false,
    discountPercent: 0,
    discountLabel: "1 month free (save ₹299 vs monthly)",
    isPublic: false,
    displayOrder: 5,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 100000,
    monthly_token_limit: 3000000,
    included: [
      "All CBSE subjects · All grades",
      "Unlimited doubt solving",
      "Full question bank access",
      "Unlimited mock tests",
      "Parent dashboard + alerts",
      "Exemplar Research & Lessons",
      "Priority support",
      "🎁 1 month free vs monthly plan",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + alerts",
      fullAccess: "✅ Full access",
      planDuration: "6 months",
      billingType: "₹1,495 / 6 months",
    },
  },

  standard_annual: {
    key: "standard_annual",
    label: "Premium — Annual",
    shortLabel: "Annual",
    price: 2999,
    billingLabel: "year",
    audience:
      "Best value for one student — pay once a year and get 2 months free vs monthly.",
    badge: "🏆 2 Months Free",
    recommended: false,
    discountPercent: 0,
    discountLabel: "2 months free (save ₹589 vs monthly)",
    isPublic: false,
    displayOrder: 6,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 100000,
    monthly_token_limit: 3000000,
    included: [
      "All CBSE subjects · All grades",
      "Unlimited doubt solving",
      "Full question bank access",
      "Unlimited mock tests",
      "Parent dashboard + alerts",
      "Exemplar Research & Lessons",
      "Priority support",
      "🎉 2 months free vs monthly plan",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + alerts",
      fullAccess: "✅ Full access",
      planDuration: "Annual",
      billingType: "₹2,999 / year",
    },
  },

  family_annual: {
    key: "family_annual",
    label: "Family Premium — Annual",
    shortLabel: "Family Annual",
    price: 4999,
    billingLabel: "year",
    audience:
      "Full family access for a year — 2 months free vs monthly. Ideal for the whole academic year.",
    badge: "🏆 2 Months Free",
    recommended: false,
    discountPercent: 0,
    discountLabel: "2 months free (save ₹989 vs monthly)",
    isPublic: false,
    displayOrder: 7,
    accessLevel: ACCESS_LEVEL.FULL,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 150000,
    monthly_token_limit: 5000000,
    included: [
      "All CBSE subjects · All grades",
      "Unlimited doubt solving",
      "Full question bank access",
      "Unlimited mock tests",
      "Up to 2 children",
      "Parent dashboard + analytics",
      "Exemplar Research & Lessons",
      "Multi-parent access",
      "🎉 2 months free vs monthly plan",
    ],
    notIncluded: [],
    comparison: {
      children: "2",
      lessons: "✅ Unlimited",
      mockTests: "✅ Unlimited",
      askDoubts: "✅ Unlimited",
      cbse: "All subjects",
      exemplarResearch: "✅ Full access",
      exemplarLessons: "✅ Full access",
      parentDashboard: "Full + analytics",
      fullAccess: "✅ Full access (2 children)",
      planDuration: "Annual",
      billingType: "₹4,999 / year",
    },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Plan order constants
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Canonical column order for the plan comparison table.
 * Always shows all four tiers side-by-side:
 *   Feature | Free Tier | Nano | Premium | Family Premium
 */
export const COMPARISON_PLAN_ORDER = [
  "free_tier",
  "free",
  "starter",
  "family_premium",
];

/** Public plan cards shown in the subscription page (purchasable plans only). */
export const SUBSCRIPTION_PLAN_ORDER = [
  "free",
  "starter",
  "standard_6month",
  "standard_annual",
  "family_premium",
  "family_annual",
];

export const PARENT_PLAN_ORDER = [
  "free",
  "starter",
  "standard_6month",
  "standard_annual",
  "family_premium",
  "family_annual",
];

/**
 * Canonical comparison table rows.
 * Format: [rowLabel, comparisonKey]
 * All comparison objects in SUBSCRIPTION_PLANS must contain these keys.
 */
export const COMPARISON_TABLE_ROWS = [
  ["AI Lessons", "lessons"],
  ["Mock Tests", "mockTests"],
  ["Ask Doubts (per day)", "askDoubts"],
  ["CBSE Subjects", "cbse"],
  ["Exemplar Research (Science & Maths)", "exemplarResearch"],
  ["Exemplar Lessons (Grades 8–10)", "exemplarLessons"],
  ["Child Profiles", "children"],
  ["Parent Dashboard", "parentDashboard"],
  ["Full Platform Access", "fullAccess"],
  ["Plan Duration", "planDuration"],
  ["Billing", "billingType"],
];

// ─────────────────────────────────────────────────────────────────────────────
// Utility functions
// ─────────────────────────────────────────────────────────────────────────────

export function getSubscriptionPlan(planKey) {
  /** Return a known plan or fall back to the free_tier for unknown keys. */
  return SUBSCRIPTION_PLANS[planKey] || SUBSCRIPTION_PLANS.free_tier;
}

export function formatPlanPrice(price) {
  /** Format rupee prices for display in parent/admin subscription UIs. */
  return price === 0 ? "Free" : `₹${Number(price || 0).toLocaleString("en-IN")}`;
}

export function getPlanDisplayPrice(plan) {
  /** Calculate the discounted parent-facing display price for a plan. */
  const price = Number(plan?.price || 0);
  const discountPercent = Number(plan?.discountPercent || 0);
  if (discountPercent <= 0) return price;
  return Math.max(0, Math.round(price * (100 - discountPercent) / 100));
}

/**
 * Returns true if the plan grants full platform access (Nano, Premium, Family).
 * Free Tier always returns false regardless of any comparison data.
 */
export function planHasFullAccess(planKey) {
  const plan = SUBSCRIPTION_PLANS[planKey];
  return plan?.accessLevel === ACCESS_LEVEL.FULL;
}

export function normalizeSubscriptionPlan(rawPlan = {}) {
  /**
   * Convert API/database plan shape into the frontend's camelCase display shape.
   *
   * Defaults are merged first so partially persisted Supabase rows still render
   * complete cards and comparison tables.
   */
  const key = rawPlan.key;
  const fallback = SUBSCRIPTION_PLANS[key] || {};

  return {
    ...fallback,
    ...rawPlan,
    shortLabel: rawPlan.shortLabel || rawPlan.short_label || fallback.shortLabel,
    billingLabel: rawPlan.billingLabel || rawPlan.billing_label || fallback.billingLabel,
    discountPercent:
      rawPlan.discountPercent ?? rawPlan.discount_percent ?? fallback.discountPercent ?? 0,
    discountLabel:
      rawPlan.discountLabel ?? rawPlan.discount_label ?? fallback.discountLabel ?? "",
    // Frontend config's isPublic: false always wins — it's an intentional
    // hide decision and should not be overridden by stale DB values.
    isPublic:
      fallback.isPublic === false
        ? false
        : (rawPlan.isPublic ?? rawPlan.is_public ?? fallback.isPublic ?? true),
    displayOrder:
      rawPlan.displayOrder ?? rawPlan.display_order ?? fallback.displayOrder ?? 999,
    accessLevel: rawPlan.accessLevel ?? fallback.accessLevel ?? ACCESS_LEVEL.LIMITED,
    access_cbse: rawPlan.access_cbse ?? fallback.access_cbse ?? false,
    access_sof_science: rawPlan.access_sof_science ?? fallback.access_sof_science ?? false,
    access_sof_maths: rawPlan.access_sof_maths ?? fallback.access_sof_maths ?? false,
    access_sof_english: rawPlan.access_sof_english ?? fallback.access_sof_english ?? false,
    daily_token_limit: rawPlan.daily_token_limit ?? fallback.daily_token_limit ?? 0,
    monthly_token_limit: rawPlan.monthly_token_limit ?? fallback.monthly_token_limit ?? 0,
    included: rawPlan.included || fallback.included || [],
    notIncluded: rawPlan.notIncluded || rawPlan.not_included || fallback.notIncluded || [],
    // Deep-merge: frontend fallback comparison is the base, DB values overlay.
    comparison: { ...(fallback.comparison || {}), ...(rawPlan.comparison || {}) },
  };
}

function keySubscriptionPlans(apiPlans = {}) {
  /** Normalize API plans from either array or keyed-object shape into a map. */
  if (Array.isArray(apiPlans)) {
    return apiPlans.reduce((plans, plan) => {
      if (plan?.key) plans[plan.key] = plan;
      return plans;
    }, {});
  }
  return apiPlans || {};
}

export function mergeSubscriptionPlans(apiPlans = {}) {
  /** Merge backend plan overrides into the built-in plan catalog. */
  const keyedApiPlans = keySubscriptionPlans(apiPlans);
  return Object.keys(SUBSCRIPTION_PLANS).reduce((plans, planKey) => {
    plans[planKey] = normalizeSubscriptionPlan(
      keyedApiPlans[planKey] || SUBSCRIPTION_PLANS[planKey]
    );
    return plans;
  }, {});
}

export function serializeSubscriptionPlan(plan) {
  /** Convert frontend plan state back into the snake_case backend payload shape. */
  return {
    key: plan.key,
    label: plan.label,
    short_label: plan.shortLabel,
    price: Number(plan.price || 0),
    billing_label: plan.billingLabel,
    audience: plan.audience,
    badge: plan.badge || "",
    recommended: !!plan.recommended,
    discount_percent: Number(plan.discountPercent || 0),
    discount_label: plan.discountLabel || "",
    is_public: plan.isPublic !== false,
    display_order: Number(plan.displayOrder || 999),
    access_level: plan.accessLevel || ACCESS_LEVEL.LIMITED,
    access_cbse: !!plan.access_cbse,
    access_sof_science: !!plan.access_sof_science,
    access_sof_maths: !!plan.access_sof_maths,
    access_sof_english: !!plan.access_sof_english,
    daily_token_limit: Number(plan.daily_token_limit || 0),
    monthly_token_limit: Number(plan.monthly_token_limit || 0),
    included: plan.included || [],
    not_included: plan.notIncluded || [],
    comparison: plan.comparison || {},
  };
}
