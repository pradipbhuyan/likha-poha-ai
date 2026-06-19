"""
Offer Code Redemption Route
===========================
Authenticated students (and other roles) can redeem an 8-character offer code
to gain platform access for the code's validity period.

Endpoints:
  POST /api/offer/redeem    — redeem a code
  GET  /api/offer/my-access — check if current user has valid offer access
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import get_current_user, admin_client

router = APIRouter()


class RedeemCodeRequest(BaseModel):
    code: str


@router.post("/redeem")
def redeem_offer_code(data: RedeemCodeRequest, user=Depends(get_current_user)):
    """
    Redeem an offer code for the current user.

    Checks:
    1. Code exists and is_active
    2. Code is within its valid_from → valid_until window
    3. max_uses not exceeded
    4. User hasn't already redeemed this code

    On success: creates an offer_redemptions row and increments uses_count.
    Returns: the valid_until date so the frontend can display "Access until …"
    """
    code = (data.code or "").strip().upper()
    if len(code) != 8:
        raise HTTPException(status_code=400, detail="Offer code must be exactly 8 characters.")

    # 1. Look up the code
    result = (
        admin_client
        .table("offer_codes")
        .select("*")
        .eq("code", code)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Invalid offer code.")

    offer = result.data[0]

    if not offer.get("is_active"):
        raise HTTPException(status_code=400, detail="This offer code is no longer active.")

    now = datetime.now(timezone.utc)

    # 2. Check validity window
    valid_from_str = offer.get("valid_from") or ""
    valid_until_str = offer.get("valid_until") or ""

    try:
        valid_until = datetime.fromisoformat(valid_until_str.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Offer code has an invalid expiry date.")

    if now > valid_until:
        raise HTTPException(status_code=400, detail="This offer code has expired.")

    if valid_from_str:
        try:
            valid_from = datetime.fromisoformat(valid_from_str.replace("Z", "+00:00"))
            if now < valid_from:
                raise HTTPException(status_code=400, detail="This offer code is not yet active.")
        except HTTPException:
            raise
        except Exception:
            pass  # Ignore invalid valid_from — treat as now

    # 3. Check max uses
    uses_count = int(offer.get("uses_count") or 0)
    max_uses = int(offer.get("max_uses") or 100)
    if uses_count >= max_uses:
        raise HTTPException(status_code=400, detail="This offer code has reached its maximum number of uses.")

    # 4. Check if user already redeemed this code
    user_id = user["profile"]["id"]
    code_id = offer["id"]

    existing_redemption = (
        admin_client
        .table("offer_redemptions")
        .select("id, valid_until")
        .eq("user_id", user_id)
        .eq("code_id", code_id)
        .limit(1)
        .execute()
    )

    if existing_redemption.data:
        # Already redeemed — return their existing access info
        existing = existing_redemption.data[0]
        return {
            "success": True,
            "already_redeemed": True,
            "valid_until": existing["valid_until"],
            "message": f"You already redeemed this code. Access valid until {existing['valid_until'][:10]}.",
        }

    # 5. Create redemption record
    try:
        admin_client.table("offer_redemptions").insert({
            "code_id": code_id,
            "user_id": user_id,
            "valid_until": valid_until_str,
        }).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to redeem offer code. Error: {str(exc)}",
        )

    # 6. Increment uses_count on offer_codes
    admin_client.table("offer_codes").update({
        "uses_count": uses_count + 1,
    }).eq("id", code_id).execute()

    return {
        "success": True,
        "already_redeemed": False,
        "valid_until": valid_until_str,
        "message": f"🎉 Offer code applied! You have access until {valid_until_str[:10]}.",
    }


@router.get("/my-access")
def get_my_offer_access(user=Depends(get_current_user)):
    """
    Check whether the current user has a valid (non-expired) offer redemption.

    Child accounts inherit offer validity from their parent — if the parent
    has a valid redemption, the child sees the same valid_until date.

    Returns:
      has_offer_access: bool
      valid_until: ISO string or null
      days_remaining: int
      expiring_soon: bool (<=7 days)
      expired_on: ISO string or null
    """
    user_id = user["profile"]["id"]
    parent_id = user["profile"].get("parent_id")
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Check own redemptions first, then parent's (for child accounts)
        candidate_ids = [user_id]
        if parent_id:
            candidate_ids.append(parent_id)

        # Active redemption — check each candidate in order
        for cid in candidate_ids:
            r = (
                admin_client
                .table("offer_redemptions")
                .select("id, valid_until, code_id")
                .eq("user_id", cid)
                .gte("valid_until", now_iso)
                .order("valid_until", desc=True)
                .limit(1)
                .execute()
            )
            if r.data:
                valid_until = r.data[0]["valid_until"]
                expiry = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
                days_left = (expiry - datetime.now(timezone.utc)).days
                return {
                    "has_offer_access": True,
                    "valid_until": valid_until,
                    "days_remaining": max(0, days_left),
                    "expiring_soon": days_left <= 7,
                    "expired_on": None,
                }

        # No active redemption — check for most recent expired one to show expiry date
        expired_result = (
            admin_client
            .table("offer_redemptions")
            .select("id, valid_until")
            .eq("user_id", user_id)
            .lt("valid_until", now_iso)
            .order("valid_until", desc=True)
            .limit(1)
            .execute()
        )

        return {
            "has_offer_access": False,
            "valid_until": None,
            "expired_on": expired_result.data[0]["valid_until"] if expired_result.data else None,
            "days_remaining": 0,
            "expiring_soon": False,
        }
    except Exception:
        return {
            "has_offer_access": False,
            "valid_until": None,
            "expired_on": None,
            "days_remaining": 0,
            "expiring_soon": False,
        }
