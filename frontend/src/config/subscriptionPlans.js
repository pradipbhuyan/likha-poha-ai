export const SUBSCRIPTION_PLANS = {
  free: {
    key: "free",
    label: "Try It Out",
    shortLabel: "Trial",
    price: 100,
    billingLabel: "14 days",
    audience:
      "Explore the platform before committing — access CBSE lessons, doubts, and basic mock tests.",
    badge: "Start here",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 1,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 50000,
    monthly_token_limit: 1000000,
    included: [
      "1 child profile",
      "CBSE lessons — 3 subjects",
      "5 doubt questions per day",
      "Basic mock tests",
      "Parent dashboard",
    ],
    notIncluded: [
      "All CBSE subjects",
      "Unlimited doubt solving",
      "Full question bank",
      "Advanced analytics",
    ],
    comparison: {
      children: "1",
      aiUsage: "Limited",
      cbse: "3 subjects",
      parentDashboard: "Basic",
    },
  },
  starter: {
    key: "starter",
    label: "Standard",
    shortLabel: "Standard",
    price: 299,
    billingLabel: "month",
    audience:
      "Best for serious CBSE exam prep with unlimited AI access and full parent tracking.",
    badge: "Most Popular",
    recommended: true,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 2,
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
      "Parent dashboard + alerts",
      "Priority support",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      aiUsage: "Unlimited",
      cbse: "All subjects",
      parentDashboard: "Full + alerts",
    },
  },
  premium: {
    key: "premium",
    label: "Standard",
    shortLabel: "Standard",
    price: 299,
    billingLabel: "month",
    audience:
      "Best for serious CBSE exam prep with unlimited AI access and full parent tracking.",
    badge: "",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: false,
    displayOrder: 3,
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
      "Parent dashboard + alerts",
      "Priority support",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      aiUsage: "Unlimited",
      cbse: "All subjects",
      parentDashboard: "Full + alerts",
    },
  },
  family_premium: {
    key: "family_premium",
    label: "Family",
    shortLabel: "Family",
    price: 499,
    billingLabel: "month",
    audience:
      "Best value plan for families with two children — full CBSE access for both.",
    badge: "Best value",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 3,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 150000,
    monthly_token_limit: 5000000,
    included: [
      "Everything in Standard",
      "Up to 2 children",
      "Multi-parent access",
      "Separate progress tracking",
      "Teacher dashboard access",
    ],
    notIncluded: [],
    comparison: {
      children: "2",
      aiUsage: "Family limit",
      cbse: "All subjects",
      parentDashboard: "Full + analytics",
    },
  },
};

export const SUBSCRIPTION_PLAN_ORDER = [
  "free",
  "starter",
  "family_premium",
];

export const PARENT_PLAN_ORDER = [
  "free",
  "starter",
  "family_premium",
];

export function getSubscriptionPlan(planKey) {
  /** Return a known plan or fall back to Free Trial for unknown keys. */
  return SUBSCRIPTION_PLANS[planKey] || SUBSCRIPTION_PLANS.free;
}

export function formatPlanPrice(price) {
  /** Format rupee prices for display in parent/admin subscription UIs. */
  return `₹${Number(price || 0).toLocaleString("en-IN")}`;
}

export function getPlanDisplayPrice(plan) {
  /** Calculate the discounted parent-facing display price for a plan. */
  const price = Number(plan?.price || 0);
  const discountPercent = Number(plan?.discountPercent || 0);

  if (discountPercent <= 0) return price;

  return Math.max(0, Math.round(price * (100 - discountPercent) / 100));
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
    isPublic: rawPlan.isPublic ?? rawPlan.is_public ?? fallback.isPublic ?? true,
    displayOrder:
      rawPlan.displayOrder ?? rawPlan.display_order ?? fallback.displayOrder ?? 999,
    access_cbse: rawPlan.access_cbse ?? fallback.access_cbse ?? true,
    access_sof_science:
      rawPlan.access_sof_science ?? fallback.access_sof_science ?? false,
    access_sof_maths:
      rawPlan.access_sof_maths ?? fallback.access_sof_maths ?? false,
    access_sof_english:
      rawPlan.access_sof_english ?? fallback.access_sof_english ?? false,
    daily_token_limit:
      rawPlan.daily_token_limit ?? fallback.daily_token_limit ?? 0,
    monthly_token_limit:
      rawPlan.monthly_token_limit ?? fallback.monthly_token_limit ?? 0,
    included: rawPlan.included || fallback.included || [],
    notIncluded:
      rawPlan.notIncluded || rawPlan.not_included || fallback.notIncluded || [],
    comparison: rawPlan.comparison || fallback.comparison || {},
  };
}

function keySubscriptionPlans(apiPlans = {}) {
  /** Normalize API plans from either array or keyed-object shape into a map. */
  if (Array.isArray(apiPlans)) {
    return apiPlans.reduce((plans, plan) => {
      if (plan?.key) {
        plans[plan.key] = plan;
      }

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
