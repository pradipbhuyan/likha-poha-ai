"""
subscription.py  —  /api/subscription/*
─────────────────────────────────────────────────────────────────────────────
Endpoints that surface a user's canonical subscription state.

GET /api/subscription/resolve
    Returns the resolved subscription state for the authenticated user using
    the single canonical resolver (subscription_resolver_service).
    The frontend uses this to drive both access-control gates and UI display,
    ensuring they always agree.
"""
from fastapi import APIRouter, Depends

from app.services.auth_service import get_current_user, require_admin
from app.services.subscription_resolver_service import (
    resolve_user_subscription,
    _PLAN_LIMITS,
)

router = APIRouter()

# ── Canonical plan catalog (source of truth for parity tests) ────────────────
# These values define what each plan provides.
# Any frontend plan config must match these exactly.
CANONICAL_PLAN_CATALOG = {
    "FREE_TIER": {
        "canonical_plan_key": "FREE_TIER",
        "db_plan_key": None,        # not a purchasable plan — display-only
        "plan_name": "Free Tier",
        "price_inr": 0,
        "billing_label": "forever",
        "duration_days": None,
        "has_full_access": False,
        "child_limit": None,
        "student_limit": None,
        "access_cbse": False,
        "restrictions": _PLAN_LIMITS["FREE_TIER"]["restrictions"],
    },
    "NANO": {
        "canonical_plan_key": "NANO",
        "db_plan_key": "free",      # raw DB value for subscription_plan column
        "plan_name": "Premium Nano",
        "price_inr": 99,
        "billing_label": "8 days",
        "duration_days": 8,
        "has_full_access": True,
        "child_limit": 1,
        "student_limit": None,
        "access_cbse": True,
        "restrictions": [],
    },
    "PREMIUM": {
        "canonical_plan_key": "PREMIUM",
        "db_plan_key": "starter",
        "plan_name": "Premium",
        "price_inr": 299,
        "billing_label": "month",
        "duration_days": 30,
        "has_full_access": True,
        "child_limit": 1,
        "student_limit": None,
        "access_cbse": True,
        "restrictions": [],
    },
    "FAMILY_PREMIUM": {
        "canonical_plan_key": "FAMILY_PREMIUM",
        "db_plan_key": "family_premium",
        "plan_name": "Family Premium",
        "price_inr": 499,
        "billing_label": "month",
        "duration_days": 30,
        "has_full_access": True,
        "child_limit": 2,
        "student_limit": None,
        "access_cbse": True,
        "restrictions": [],
    },
}


@router.get("/resolve")
def resolve_subscription(user=Depends(get_current_user)):
    """
    Return the canonical subscription state for the authenticated user.

    This endpoint is the single source of truth for subscription status.
    Both the frontend UI and backend access-control must derive their
    decisions from the same resolver to prevent conflicting states.

    Returns
    -------
    JSON object with:
        active_tier    : "FREE" | "PREMIUM"
        plan_name      : human-readable plan label (e.g. "Premium Nano",
                         "Offer / Free Access", "Premium", "Free")
        access_source  : "PAID" | "OFFER_CODE" | "ADMIN_GRANT" | "NONE"
        has_full_access: bool  (False triggers DKB-only gate for offer users)
        valid_until    : ISO datetime string | null
        days_remaining : int | null
        expiring_soon  : bool

    Precedence used by the resolver:
        1. Active paid subscription  (subscription_expires_at in future)
        2. Perpetual paid plan       (access flag + non-free plan key)
        3. Valid offer / free-trial  (offer_redemptions row valid now)
        4. Admin-granted access      (access_cbse / SOF flags, no expiry)
        5. Default free tier
    """
    result = resolve_user_subscription(user.id)
    return {"success": True, **result}


@router.post("/run-expiry-job")
def run_expiry_job(admin=Depends(require_admin)):
    """
    Admin-only: trigger the subscription expiry job manually.

    Finds all expired paid subscriptions, revokes access flags, and writes
    audit + timeline events.  Safe to run multiple times (idempotent).
    """
    from app.services.expiry_job_service import run_expiry_job as _run  # noqa: PLC0415
    summary = _run()
    return {"success": True, **summary}


@router.get("/metrics")
def get_metrics(admin=Depends(require_admin)):
    """
    Admin-only: return current in-process metric counters.

    These counters are process-local and reset on server restart.
    Use for quick diagnostics — not a replacement for persistent analytics.
    """
    from app.services.metrics_service import get_counters  # noqa: PLC0415
    return {"success": True, "counters": get_counters()}


@router.get("/catalog")
def get_plan_catalog():
    """
    Return the canonical plan catalog — the single source of truth for plan
    definitions shared between frontend and backend.

    This endpoint is public (no auth required) because plan metadata is
    display information, not access-controlled data.

    Use this for:
      - Frontend/backend plan config parity tests
      - Verifying prices, durations, child limits, and access levels
      - Any code that needs to branch on plan properties
    """
    return {
        "success": True,
        "catalog": CANONICAL_PLAN_CATALOG,
        "version": "2",   # bump when catalog schema changes
    }
