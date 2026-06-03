export const SUBSCRIPTION_PLANS = {
  free: {
    key: "free",
    label: "Free Trial",
    shortLabel: "Free",
    price: 0,
    billingLabel: "14 days",
    audience:
      "Best for exploring lessons, doubts, and basic progress before choosing a paid plan.",
    badge: "Current starter",
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
      "Limited AI lessons and doubt solving",
      "Basic CBSE practice and progress view",
    ],
    notIncluded: [
      "SOF mock tests",
      "Advanced analytics",
    ],
    comparison: {
      children: "1",
      aiUsage: "Limited",
      cbse: "Limited",
      sof: "Locked",
      ragSof: "Locked",
      parentDashboard: "Basic",
    },
  },
  starter: {
    key: "starter",
    label: "Standard",
    shortLabel: "Standard",
    price: 499,
    billingLabel: "month",
    audience:
      "Best for regular CBSE learning with higher AI limits and parent tracking.",
    badge: "",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 2,
    access_cbse: true,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    daily_token_limit: 75000,
    monthly_token_limit: 1500000,
    included: [
      "Everything in Free Trial",
      "Higher AI lessons, doubts, and explanations",
      "CBSE mock tests and chapter revision",
      "Full parent dashboard",
    ],
    notIncluded: [
      "SOF RAG mock tests",
    ],
    comparison: {
      children: "1",
      aiUsage: "Higher limit",
      cbse: "Included",
      sof: "Locked",
      ragSof: "Locked",
      parentDashboard: "Full",
    },
  },
  premium: {
    key: "premium",
    label: "Premium SOF",
    shortLabel: "Premium",
    price: 999,
    billingLabel: "month",
    audience:
      "Best for CBSE plus Science, Maths, and English Olympiad preparation.",
    badge: "Recommended",
    recommended: true,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 3,
    access_cbse: true,
    access_sof_science: true,
    access_sof_maths: true,
    access_sof_english: true,
    daily_token_limit: 100000,
    monthly_token_limit: 3000000,
    included: [
      "Everything in Standard",
      "SOF Science, Maths, and English access",
      "RAG-based SOF mock tests from uploaded workbook content",
      "Highest AI usage limit",
      "Advanced analytics and weak-area recommendations",
    ],
    notIncluded: [],
    comparison: {
      children: "1",
      aiUsage: "Highest limit",
      cbse: "Included",
      sof: "Included",
      ragSof: "Included",
      parentDashboard: "Full + analytics",
    },
  },
  family_premium: {
    key: "family_premium",
    label: "Family Premium",
    shortLabel: "Family Premium",
    price: 1499,
    billingLabel: "month",
    audience:
      "Best discounted plan for two children who both need every CBSE and SOF feature.",
    badge: "Best value",
    recommended: false,
    discountPercent: 0,
    discountLabel: "",
    isPublic: true,
    displayOrder: 4,
    access_cbse: true,
    access_sof_science: true,
    access_sof_maths: true,
    access_sof_english: true,
    daily_token_limit: 150000,
    monthly_token_limit: 5000000,
    included: [
      "Everything in Premium SOF for two children",
      "Discounted two-child family pricing",
      "SOF Science, Maths, and English for both children",
      "Expanded monthly AI usage",
      "Family progress and usage view",
    ],
    notIncluded: [],
    comparison: {
      children: "2",
      aiUsage: "Family limit",
      cbse: "Included",
      sof: "Included",
      ragSof: "Included",
      parentDashboard: "Full + analytics",
    },
  },
};

export const SUBSCRIPTION_PLAN_ORDER = [
  "free",
  "starter",
  "premium",
  "family_premium",
];

export const PARENT_PLAN_ORDER = [
  "free",
  "starter",
  "premium",
  "family_premium",
];

export function getSubscriptionPlan(planKey) {
  return SUBSCRIPTION_PLANS[planKey] || SUBSCRIPTION_PLANS.free;
}

export function formatPlanPrice(price) {
  return `₹${Number(price || 0).toLocaleString("en-IN")}`;
}

export function getPlanDisplayPrice(plan) {
  const price = Number(plan?.price || 0);
  const discountPercent = Number(plan?.discountPercent || 0);

  if (discountPercent <= 0) return price;

  return Math.max(0, Math.round(price * (100 - discountPercent) / 100));
}

export function normalizeSubscriptionPlan(rawPlan = {}) {
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
  const keyedApiPlans = keySubscriptionPlans(apiPlans);

  return Object.keys(SUBSCRIPTION_PLANS).reduce((plans, planKey) => {
    plans[planKey] = normalizeSubscriptionPlan(
      keyedApiPlans[planKey] || SUBSCRIPTION_PLANS[planKey]
    );

    return plans;
  }, {});
}

export function serializeSubscriptionPlan(plan) {
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
