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

from app.services.auth_service import get_current_user
from app.services.subscription_resolver_service import resolve_user_subscription

router = APIRouter()


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
