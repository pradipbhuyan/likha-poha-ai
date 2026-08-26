DEFAULT_SUBSCRIPTION_PLANS = {
    # ── Free Tier — no subscription, limited access ───────────────────────────
    # This is what a parent sees as their "current" plan before purchasing.
    # Not a purchasable plan — just the baseline state.
    "free_tier": {
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": None,
        "access_exam_prep": False,
        "access_exemplar": False,
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
    # Discontinued from public sale — is_public=False hides it from the landing
    # page / SubscriptionPlansPage and blocks new purchases in payments.py
    # (get_public_plan). Existing Nano subscribers are unaffected: the
    # subscription resolver identifies them independently of this config
    # (subscription_resolver_service.py's Legacy Nano branch is hardcoded and
    # does not read is_public), so their access continues unchanged.
    "free": {
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 8,
        "access_exam_prep": True,
        "access_exemplar": True,
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
        "is_public": False,
        "display_order": 2,
        "access_cbse": True,
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
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 30,
        "access_exam_prep": False,
        "access_exemplar": True,
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
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "All CBSE subjects · All grades",
            "Unlimited AI lessons, doubts & mock tests",
            "Exemplar Research & Lessons",
            "Formula & Concepts library",

            "10 Years of Board Papers with answers",
            "Learn More curated video library",
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
    # "premium" — NOT a duplicate of "starter" to clean up; both are real,
    # separate raw DB values for the *same* product tier, and this entry is
    # intentional (confirmed 2026-08-26, was previously logged as "purpose
    # unconfirmed" in TECH_DEBT.md TD-15). "starter" is the current key new
    # subscriptions are created with; "premium" is recognized by
    # subscription_resolver_service._canonical_plan_key() (and its mirror,
    # shared/utils/resolveSubscription.js) as a legacy raw value that maps to
    # the same canonical PREMIUM tier — the same pattern already used for
    # "free" meaning legacy Nano (see that function's own docstring). Keep
    # this entry's price/duration/features in sync with "starter" above;
    # do not delete it without confirming no profile row still carries
    # subscription_plan="premium" (not verifiable from this repo alone).
    "premium": {
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 30,
        "access_exam_prep": False,
        "access_exemplar": True,
        "key": "premium",
        "label": "Premium",
        "short_label": "Premium",
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
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 30,
        "access_exam_prep": False,
        "access_exemplar": True,
        "key": "family_premium",
        "label": "Family Premium",
        "short_label": "Family Premium",
        "price": 499,
        "billing_label": "month",
        "audience": (
            "One subscription for families with up to two children."
        ),
        "badge": "Best value",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 4,
        "access_cbse": True,
        "daily_token_limit": 150000,
        "monthly_token_limit": 5000000,
        "included": [
            "Everything in Premium",
            "Up to 2 children with separate progress",
            "Exemplar Research & Lessons",
            "Formula & Concepts library",

            "10 Years of Board Papers with answers",
            "Learn More curated video library",
            "Family learning management",
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
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 184,
        "access_exam_prep": False,
        "access_exemplar": True,
        "key": "standard_6month",
        "label": "Premium — 6 Months",
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
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 366,
        "access_exam_prep": False,
        "access_exemplar": True,
        "key": "standard_annual",
        "label": "Premium — Annual",
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
        # Centralized feature flags — overridden by subscription_plan_settings DB
        "duration_days": 366,
        "access_exam_prep": False,
        "access_exemplar": True,
        "key": "family_annual",
        "label": "Family Premium — Annual",
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
        "daily_token_limit": 150000,
        "monthly_token_limit": 5000000,
        "included": [
            "Everything in Family Premium",
            "Up to 2 children",
            "Separate child progress",
            "Parent Dashboard",
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
    # ── EXAM PREP CENTER — bundled Grade 11–12 annual plan ────────────────────
    # Single ₹1,999/year plan covering ALL 6 exams together (JEE Main, NEET UG,
    # CUET UG, SAT, IELTS, TOEFL iBT) — independent of the CBSE subscription
    # tiers above. Grade 11–12 students only. This is now the ONLY exam prep
    # plan sold — the standalone per-exam packs (exam_prep_jee/neet/cuet) were
    # retired; no customer ever held one, so no legacy-access shim is needed.
    "exam_prep_center": {
        "duration_days": 366,
        "access_exam_prep": True,
        "access_exemplar": True,
        "key": "exam_prep_center",
        "label": "Exam Prep Center",
        "short_label": "Exam Prep",
        "price": 1999,
        "billing_label": "year",
        "audience": (
            "Grade 11–12 competitive & global exam prep — JEE Main, NEET UG, "
            "CUET UG, SAT, IELTS & TOEFL iBT, all in one annual plan — plus "
            "full CBSE Grade 11–12 lessons, doubts, and mock tests."
        ),
        "badge": "NEW",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 6,
        "access_cbse": True,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "JEE Main — Study Plan + Test Simulation",
            "NEET UG — Study Plan + Test Simulation",
            "CUET UG — Study Plan + Test Simulation",
            "SAT — Study Plan + Test Simulation",
            "IELTS — Study Plan + Test Simulation",
            "TOEFL iBT — Study Plan + Test Simulation",
            "AI step-by-step explanations",
            "Weak topic tracker",
            "Full CBSE Grade 11–12 lessons, doubts & mock tests",
            "Exemplar Research & Lessons",
            "Formula & Concepts library",
            "10 Years of Board Papers with answers",
        ],
        "not_included": [
            "CBSE lessons (Grade 5–10)",
        ],
        "comparison": {
            "children": "1",
            "aiUsage": "Unlimited (Gr 11–12)",
            "cbse": "Grade 11–12 only",
            "parentDashboard": "Full + analytics",
        },
        "exam_type": None,  # single, all-exam bundle — no per-exam packs anymore
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
