DEFAULT_SUBSCRIPTION_PLANS = {
    # ── Free Tier — no subscription, limited access ───────────────────────────
    # This is what a parent sees as their "current" plan before purchasing.
    # Not a purchasable plan — just the baseline state.
    "free_tier": {
        "key": "free_tier",
        "label": "Free Tier",
        "short_label": "Free",
        "price": 0,
        "billing_label": "free forever",
        "audience": (
            "Explore the platform before committing — access CBSE lessons, "
            "doubts, and basic mock tests."
        ),
        "badge": "",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 1,
        "access_cbse": False,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 10000,
        "monthly_token_limit": 200000,
        "included": [
            "3 CBSE subjects",
            "5 doubt questions per day",
            "Basic mock tests (5/day)",
            "Parent dashboard",
        ],
        "not_included": [
            "All CBSE subjects",
            "Unlimited doubt solving",
            "Full question bank",
            "Exemplar lessons",
            "Advanced analytics",
        ],
        "comparison": {
            "children": "1",
            "aiUsage": "Limited",
            "cbse": "3 subjects",
            "parentDashboard": "Basic",
        },
    },
    # ── Premium Nano — ₹99 / 8 days, full access ─────────────────────────────
    # DB key is "free" for legacy reasons (subscription_plan = "free" in profiles).
    # Distinguished from free_tier by: access_cbse=True + subscription_expires_at set.
    "free": {
        "key": "free",
        "label": "Premium Nano",
        "short_label": "Nano",
        "price": 99,
        "billing_label": "8 days",
        "audience": (
            "Full platform access for 8 days — all CBSE subjects, unlimited doubts, "
            "mock tests. No restrictions."
        ),
        "badge": "Start here",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 2,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 100000,
        "monthly_token_limit": 1000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited doubt solving",
            "Full question bank access",
            "Unlimited mock tests",
            "Parent dashboard + alerts",
            "Exemplar Research & Lessons",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited",
            "cbse": "All subjects",
            "parentDashboard": "Full + alerts",
        },
    },
    "starter": {
        "key": "starter",
        "label": "Premium",
        "short_label": "Premium",
        "price": 299,
        "billing_label": "month",
        "audience": (
            "Best for serious CBSE exam prep with unlimited AI access and "
            "full parent tracking."
        ),
        "badge": "Most Popular",
        "recommended": True,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 3,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited doubt solving",
            "Full question bank access",
            "Parent dashboard + alerts",
            "Priority support",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited",
            "cbse": "All subjects",
            "parentDashboard": "Full + alerts",
        },
    },
    "premium": {
        "key": "premium",
        "label": "Standard",
        "short_label": "Standard",
        "price": 299,
        "billing_label": "month",
        "audience": (
            "Best for serious CBSE exam prep with unlimited AI access and "
            "full parent tracking."
        ),
        "badge": "",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": False,
        "display_order": 3,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited doubt solving",
            "Full question bank access",
            "Parent dashboard + alerts",
            "Priority support",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited",
            "cbse": "All subjects",
            "parentDashboard": "Full + alerts",
        },
    },
    "family_premium": {
        "key": "family_premium",
        "label": "Family",
        "short_label": "Family",
        "price": 499,
        "billing_label": "month",
        "audience": (
            "Best value plan for families with two children — full CBSE "
            "access for both."
        ),
        "badge": "Best value",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 4,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 150000,
        "monthly_token_limit": 5000000,
        "included": [
            "Everything in Standard",
            "Up to 2 children",
            "Multi-parent access",
            "Separate progress tracking",
            "Teacher dashboard access",
        ],
        "not_included": [],
        "comparison": {
            "children": "2",
            "aiUsage": "Family limit",
            "cbse": "All subjects",
            "parentDashboard": "Full + analytics",
        },
    },
    "standard_6month": {
        "key": "standard_6month",
        "label": "Standard — 6 Months",
        "short_label": "6-Month",
        "price": 1495,
        "billing_label": "6 months",
        "audience": (
            "Pay for 5 months and get 6 — save ₹299 vs monthly. "
            "Great for a full semester."
        ),
        "badge": "🎁 1 Month Free",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "1 month free (save ₹299 vs monthly)",
        "is_public": True,
        "display_order": 3,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited doubt solving",
            "Full question bank access",
            "Parent dashboard + alerts",
            "Priority support",
            "🎁 1 month free vs monthly plan",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited",
            "cbse": "All subjects",
            "parentDashboard": "Full + alerts",
        },
    },
    "standard_annual": {
        "key": "standard_annual",
        "label": "Standard — Annual",
        "short_label": "Annual",
        "price": 2999,
        "billing_label": "year",
        "audience": (
            "Best value for one student — pay once a year and get "
            "2 months free vs monthly."
        ),
        "badge": "🏆 2 Months Free",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "2 months free (save ₹589 vs monthly)",
        "is_public": True,
        "display_order": 4,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited doubt solving",
            "Full question bank access",
            "Parent dashboard + alerts",
            "Priority support",
            "🎉 2 months free vs monthly plan",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited",
            "cbse": "All subjects",
            "parentDashboard": "Full + alerts",
        },
    },
    "family_annual": {
        "key": "family_annual",
        "label": "Family — Annual",
        "short_label": "Family Annual",
        "price": 4999,
        "billing_label": "year",
        "audience": (
            "Full family access for a year — 2 months free vs monthly. "
            "Ideal for the whole academic year."
        ),
        "badge": "🏆 2 Months Free",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "2 months free (save ₹989 vs monthly)",
        "is_public": True,
        "display_order": 5,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 150000,
        "monthly_token_limit": 5000000,
        "included": [
            "Everything in Family Monthly",
            "Up to 2 children",
            "Multi-parent access",
            "Separate progress tracking",
            "Teacher dashboard access",
            "🎉 2 months free vs monthly plan",
        ],
        "not_included": [],
        "comparison": {
            "children": "2",
            "aiUsage": "Family limit",
            "cbse": "All subjects",
            "parentDashboard": "Full + analytics",
        },
    },
}


def get_default_subscription_plans():
    """
    Return a deep-enough copy of built-in plan settings.

    Copies prevent route/admin code from mutating the module-level defaults while
    preparing API responses or merging database overrides.
    """
    return {
        key: {
            **plan,
            "included": list(plan["included"]),
            "not_included": list(plan["not_included"]),
            "comparison": dict(plan["comparison"]),
        }
        for key, plan in DEFAULT_SUBSCRIPTION_PLANS.items()
    }


def subscription_plan_order(plans):
    """Return plan keys sorted by their configured display order."""
    return [
        key
        for key, _plan in sorted(
            plans.items(),
            key=lambda item: item[1].get("display_order", 999),
        )
    ]
