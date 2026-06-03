DEFAULT_SUBSCRIPTION_PLANS = {
    "free": {
        "key": "free",
        "label": "Free Trial",
        "short_label": "Free",
        "price": 0,
        "billing_label": "14 days",
        "audience": (
            "Best for exploring lessons, doubts, and basic progress before "
            "choosing a paid plan."
        ),
        "badge": "Current starter",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 1,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 50000,
        "monthly_token_limit": 1000000,
        "included": [
            "1 child profile",
            "Limited AI lessons and doubt solving",
            "Basic CBSE practice and progress view",
        ],
        "not_included": [
            "SOF mock tests",
            "Advanced analytics",
        ],
        "comparison": {
            "children": "1",
            "aiUsage": "Limited",
            "cbse": "Limited",
            "sof": "Locked",
            "ragSof": "Locked",
            "parentDashboard": "Basic",
        },
    },
    "starter": {
        "key": "starter",
        "label": "Standard",
        "short_label": "Standard",
        "price": 499,
        "billing_label": "month",
        "audience": (
            "Best for regular CBSE learning with higher AI limits and parent "
            "tracking."
        ),
        "badge": "",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 2,
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 75000,
        "monthly_token_limit": 1500000,
        "included": [
            "Everything in Free Trial",
            "Higher AI lessons, doubts, and explanations",
            "CBSE mock tests and chapter revision",
            "Full parent dashboard",
        ],
        "not_included": [
            "SOF RAG mock tests",
        ],
        "comparison": {
            "children": "1",
            "aiUsage": "Higher limit",
            "cbse": "Included",
            "sof": "Locked",
            "ragSof": "Locked",
            "parentDashboard": "Full",
        },
    },
    "premium": {
        "key": "premium",
        "label": "Premium SOF",
        "short_label": "Premium",
        "price": 999,
        "billing_label": "month",
        "audience": (
            "Best for CBSE plus Science, Maths, and English Olympiad "
            "preparation."
        ),
        "badge": "Recommended",
        "recommended": True,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 3,
        "access_cbse": True,
        "access_sof_science": True,
        "access_sof_maths": True,
        "access_sof_english": True,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "included": [
            "Everything in Standard",
            "SOF Science, Maths, and English access",
            "RAG-based SOF mock tests from uploaded workbook content",
            "Highest AI usage limit",
            "Advanced analytics and weak-area recommendations",
        ],
        "not_included": [],
        "comparison": {
            "children": "1",
            "aiUsage": "Highest limit",
            "cbse": "Included",
            "sof": "Included",
            "ragSof": "Included",
            "parentDashboard": "Full + analytics",
        },
    },
    "family_premium": {
        "key": "family_premium",
        "label": "Family Premium",
        "short_label": "Family Premium",
        "price": 1499,
        "billing_label": "month",
        "audience": (
            "Best discounted plan for two children who both need every CBSE "
            "and SOF feature."
        ),
        "badge": "Best value",
        "recommended": False,
        "discount_percent": 0,
        "discount_label": "",
        "is_public": True,
        "display_order": 4,
        "access_cbse": True,
        "access_sof_science": True,
        "access_sof_maths": True,
        "access_sof_english": True,
        "daily_token_limit": 150000,
        "monthly_token_limit": 5000000,
        "included": [
            "Everything in Premium SOF for two children",
            "Discounted two-child family pricing",
            "SOF Science, Maths, and English for both children",
            "Expanded monthly AI usage",
            "Family progress and usage view",
        ],
        "not_included": [],
        "comparison": {
            "children": "2",
            "aiUsage": "Family limit",
            "cbse": "Included",
            "sof": "Included",
            "ragSof": "Included",
            "parentDashboard": "Full + analytics",
        },
    },
}


def get_default_subscription_plans():
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
    return [
        key
        for key, _plan in sorted(
            plans.items(),
            key=lambda item: item[1].get("display_order", 999),
        )
    ]
