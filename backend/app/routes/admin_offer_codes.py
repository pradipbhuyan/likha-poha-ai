"""
admin_offer_codes.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Offer code creation/management, influencer tracking, and the admin
offer-gate test harness.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client

router = APIRouter()


class CreateOfferCodeRequest(BaseModel):
    description: str = ""
    valid_until: str  # ISO datetime string e.g. "2026-12-31T23:59:59"
    max_uses: int = 100
    valid_from: str | None = None  # defaults to now if omitted
    # Influencer tracking fields
    influencer_name: str = ""
    influencer_email: str = ""
    code_type: str = "free_trial"   # "free_trial" or "discount"
    discount_percent: int = 0        # 0 for free_trial; 5-10 for discount
    incentive_inr: int = 0           # INR per confirmed redemption to pay influencer


def _generate_offer_code() -> str:
    """Generate a unique 8-character alphanumeric offer code (uppercase)."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=8))
        # Ensure no existing code collision
        existing = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", code)
            .execute()
        )
        if not existing.data:
            return code


@router.get("/offer-codes")
def list_offer_codes(admin=Depends(require_admin)):
    """Return all offer codes with usage stats for the admin panel."""
    try:
        result = (
            admin_client
            .table("offer_codes")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "offer_codes": result.data or []}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Offer codes table not found. Run backend/scripts/migration_offer_codes.sql "
                f"in Supabase first. Error: {str(exc)}"
            ),
        )


@router.post("/offer-codes")
def create_offer_code(data: CreateOfferCodeRequest, admin=Depends(require_admin)):
    """
    Create a new offer code.

    The 8-char alphanumeric code is auto-generated and guaranteed unique.
    The admin provides description, validity window, and max redemptions.
    """
    code = _generate_offer_code()
    admin_id = admin["profile"]["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "code": code,
        "description": (data.description or "").strip(),
        "valid_from": data.valid_from or now_iso,
        "valid_until": data.valid_until,
        "max_uses": max(1, data.max_uses),
        "uses_count": 0,
        "created_by": admin_id,
        "is_active": True,
        # Influencer tracking fields
        "influencer_name": (data.influencer_name or "").strip(),
        "influencer_email": (data.influencer_email or "").strip(),
        "code_type": data.code_type if data.code_type in ("free_trial", "discount") else "free_trial",
        "discount_percent": max(0, min(100, int(data.discount_percent or 0))),
        "incentive_inr": max(0, int(data.incentive_inr or 0)),
        "incentive_paid": False,
    }

    try:
        result = admin_client.table("offer_codes").insert(row).execute()
        saved = result.data[0] if result.data else row
        return {"success": True, "offer_code": saved}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create offer code. Run migration_offer_codes.sql and "
                "migration_offer_codes_influencer.sql in Supabase. "
                f"Error: {str(exc)}"
            ),
        )


@router.get("/offer-codes/influencer-summary")
def get_influencer_summary(admin=Depends(require_admin)):
    """
    Return per-influencer redemption stats for the admin tracking dashboard.

    Aggregates all codes with non-empty influencer_name, counts redemptions
    from offer_redemptions, and calculates total incentive payable.
    """
    try:
        codes = (
            admin_client
            .table("offer_codes")
            .select("*")
            .neq("influencer_name", "")
            .execute()
        ).data or []
    except Exception:
        return {"success": True, "influencers": []}

    if not codes:
        return {"success": True, "influencers": []}

    # Get redemption counts per code
    code_ids = [c["id"] for c in codes]
    try:
        redemptions = (
            admin_client
            .table("offer_redemptions")
            .select("code_id, user_id")
            .in_("code_id", code_ids)
            .execute()
        ).data or []
    except Exception:
        redemptions = []

    redemptions_by_code: dict = {}
    for r in redemptions:
        cid = r["code_id"]
        redemptions_by_code[cid] = redemptions_by_code.get(cid, 0) + 1

    # Aggregate by influencer name (one influencer may have multiple codes)
    by_influencer: dict = {}
    for code in codes:
        name = code.get("influencer_name") or "Unknown"
        if name not in by_influencer:
            by_influencer[name] = {
                "influencer_name": name,
                "influencer_email": code.get("influencer_email") or "",
                "codes": [],
                "total_redemptions": 0,
                "total_incentive_payable": 0,
                "incentive_paid": True,  # False if any code unpaid
            }
        redemption_count = redemptions_by_code.get(code["id"], 0)
        incentive = int(code.get("incentive_inr") or 0) * redemption_count
        paid = bool(code.get("incentive_paid"))
        by_influencer[name]["codes"].append({
            **code,
            "redemption_count": redemption_count,
            "incentive_due": incentive,
        })
        by_influencer[name]["total_redemptions"] += redemption_count
        by_influencer[name]["total_incentive_payable"] += incentive
        if not paid:
            by_influencer[name]["incentive_paid"] = False

    return {
        "success": True,
        "influencers": list(by_influencer.values()),
        "total_payable": sum(i["total_incentive_payable"] for i in by_influencer.values() if not i["incentive_paid"]),
    }


@router.get("/offer-codes/enrollments")
def get_offer_code_enrollments(admin=Depends(require_admin)):
    """
    Return all student enrollments grouped by offer code.

    For each active offer code, returns:
    - Code details (code, influencer, valid_until, uses_count)
    - List of enrolled students (username, email, grade, enrolled_at)

    Joins offer_redemptions + offer_codes + profiles in Python
    (Supabase free tier has no cross-table joins via REST).
    """
    try:
        # Load all offer codes
        codes_result = admin_client.table("offer_codes").select("*").order("created_at", desc=True).execute()
        codes = {c["id"]: c for c in (codes_result.data or [])}
    except Exception:
        return {"success": True, "codes": []}

    if not codes:
        return {"success": True, "codes": []}

    # Load all redemptions
    try:
        redemptions_result = admin_client.table("offer_redemptions").select("*").order("redeemed_at", desc=True).execute()
        redemptions = redemptions_result.data or []
    except Exception:
        redemptions = []

    # Load profiles for all redeemed user_ids
    user_ids = list({r["user_id"] for r in redemptions})
    profiles_by_id: dict = {}
    if user_ids:
        try:
            batch = admin_client.table("profiles").select("id,username,email,grade,board,created_at").in_("id", user_ids).execute()
            profiles_by_id = {p["id"]: p for p in (batch.data or [])}
        except Exception:
            pass

    # Group redemptions by code
    enrollments_by_code: dict = {}
    for r in redemptions:
        cid = r["code_id"]
        if cid not in enrollments_by_code:
            enrollments_by_code[cid] = []
        profile = profiles_by_id.get(r["user_id"], {})
        enrollments_by_code[cid].append({
            "user_id": r["user_id"],
            "username": profile.get("username") or "—",
            "email": profile.get("email") or "—",
            "grade": profile.get("grade") or "—",
            "board": profile.get("board") or "CBSE",
            "enrolled_at": r.get("redeemed_at", "")[:19],
            "access_until": r.get("valid_until", "")[:10],
        })

    # Build response: all codes with their enrollments
    result = []
    for code in codes.values():
        result.append({
            "id": code["id"],
            "code": code["code"],
            "description": code.get("description") or "",
            "influencer_name": code.get("influencer_name") or "",
            "influencer_email": code.get("influencer_email") or "",
            "code_type": code.get("code_type") or "free_trial",
            "valid_until": (code.get("valid_until") or "")[:10],
            "is_active": code.get("is_active", False),
            "max_uses": code.get("max_uses", 0),
            "uses_count": code.get("uses_count", 0),
            "incentive_inr": code.get("incentive_inr", 0),
            "enrollments": enrollments_by_code.get(code["id"], []),
            "enrollment_count": len(enrollments_by_code.get(code["id"], [])),
        })

    return {
        "success": True,
        "codes": result,
        "total_enrollments": sum(c["enrollment_count"] for c in result),
    }


@router.patch("/offer-codes/{code_id}/mark-incentive-paid")
def mark_influencer_incentive_paid(code_id: str, admin=Depends(require_admin)):
    """Mark a specific offer code's influencer incentive as paid."""
    result = (
        admin_client
        .table("offer_codes")
        .update({
            "incentive_paid": True,
            "incentive_paid_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", code_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")
    return {"success": True, "offer_code": result.data[0]}


@router.post("/offer-codes/regenerate-promo-images")
def regenerate_promo_images(payload: dict, admin=Depends(require_admin)):
    """
    Regenerate all WhatsApp promo images with a new offer code banner and
    re-upload them to the sales-collaterals/whatsapp/ Supabase bucket.

    Payload: { "offer_code": "L3YT1HAD", "valid_until": "30 June 2026" }
    """
    import subprocess
    import sys
    import pathlib

    offer_code = (payload.get("offer_code") or "").strip().upper()
    valid_until = (payload.get("valid_until") or "").strip()

    if not offer_code:
        raise HTTPException(status_code=400, detail="offer_code is required.")

    script = pathlib.Path(
        "/Users/a0247716/Pradips_Project/LikhaPohaAI-ReelBot/"
        "likha-poha-reel-factory/tools/create_whatsapp_promos.py"
    )
    if not script.exists():
        raise HTTPException(status_code=500, detail="Promo generation script not found.")

    # Step 1 — generate images
    cmd = [sys.executable, str(script), "--offer-code", offer_code]
    if valid_until:
        cmd += ["--valid-until", valid_until]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Image generation timed out.")

    # Step 2 — upload to Supabase
    promo_dir = pathlib.Path(
        "/Users/a0247716/Pradips_Project/LikhaPohaAI-ReelBot/"
        "likha-poha-reel-factory/output/whatsapp-promos"
    )
    bucket = "sales-collaterals"
    folder = "whatsapp"
    uploaded = []
    errors = []

    for img_path in sorted(promo_dir.glob("*.png")):
        fname = img_path.name
        dest = f"{folder}/{fname}"
        with open(img_path, "rb") as f:
            data = f.read()
        try:
            try:
                admin_client.storage.from_(bucket).update(dest, data, {"content-type": "image/png", "upsert": "true"})
            except Exception:
                admin_client.storage.from_(bucket).upload(dest, data, {"content-type": "image/png"})
            pub = admin_client.storage.from_(bucket).get_public_url(dest)
            uploaded.append({"file": fname, "url": pub})
        except Exception as exc:
            errors.append({"file": fname, "error": str(exc)})

    return {
        "success": True,
        "offer_code": offer_code,
        "valid_until": valid_until,
        "uploaded": len(uploaded),
        "errors": errors,
        "files": uploaded,
    }


@router.patch("/offer-codes/{code_id}/extend-validity")
def extend_offer_code_validity(code_id: str, payload: dict, admin=Depends(require_admin)):
    """
    Extend the valid_until date for an offer code AND propagate the new date
    to every existing redemption linked to that code.

    Payload: { "valid_until": "2026-12-31T23:59:59" }

    This means any student or parent who already redeemed the code will
    automatically get the extended access window — no manual update needed.
    """
    new_valid_until = (payload.get("valid_until") or "").strip()
    if not new_valid_until:
        raise HTTPException(status_code=400, detail="valid_until is required.")

    # 1. Update the offer code itself
    code_resp = (
        admin_client
        .table("offer_codes")
        .update({"valid_until": new_valid_until})
        .eq("id", code_id)
        .execute()
    )
    if not code_resp.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")

    # 2. Cascade: update all redemptions linked to this code
    redemption_resp = (
        admin_client
        .table("offer_redemptions")
        .update({"valid_until": new_valid_until})
        .eq("code_id", code_id)
        .execute()
    )
    updated_redemptions = len(redemption_resp.data or [])

    return {
        "success": True,
        "code_id": code_id,
        "valid_until": new_valid_until,
        "redemptions_updated": updated_redemptions,
        "message": (
            f"Validity extended to {new_valid_until[:10]}. "
            f"{updated_redemptions} existing redemption(s) updated."
        ),
    }


@router.patch("/offer-codes/{code_id}/deactivate")
def deactivate_offer_code(code_id: str, admin=Depends(require_admin)):
    """Deactivate an offer code so it can no longer be redeemed."""
    result = (
        admin_client
        .table("offer_codes")
        .update({"is_active": False})
        .eq("id", code_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")
    return {"success": True, "offer_code": result.data[0]}


@router.patch("/offer-codes/{code_id}/reactivate")
def reactivate_offer_code(code_id: str, admin=Depends(require_admin)):
    """Reactivate a previously deactivated offer code."""
    result = (
        admin_client
        .table("offer_codes")
        .update({"is_active": True})
        .eq("id", code_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")
    return {"success": True, "offer_code": result.data[0]}


@router.post("/redeem-offer-code")
def redeem_offer_code(
    payload: dict,
    current_user=Depends(require_admin),
):
    """
    Placeholder — actual redemption is handled by /api/offer/redeem (no admin required).
    This route exists for admin-initiated redemption testing only.
    """
    return {"success": False, "message": "Use /api/offer/redeem for student redemptions."}


# ── Offer-gate test harness (admin only) ─────────────────────────────────────

@router.post("/offer-gate-test")
def offer_gate_test(
    payload: dict,
    admin=Depends(require_admin),
):
    """
    Admin-only endpoint to toggle offer-gate mode on any user without touching
    Supabase directly.

    Actions:
      enable  — strip paid access flags, insert a 30-day test offer redemption.
      disable — restore access_cbse=True, delete all test offer redemptions.
      status  — return current gate state without changing anything.

    Payload: {"username": "akshita.teststudent", "action": "enable|disable|status"}
    """
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415

    username = str(payload.get("username") or "").strip().casefold()
    action = str(payload.get("action") or "status").strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="username is required.")

    if action not in ("enable", "disable", "status"):
        raise HTTPException(status_code=400, detail="action must be enable, disable, or status.")

    # Resolve user profile
    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, username, role, access_cbse")
        .ilike("username", username)
        .limit(1)
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    profile = profile_resp.data[0]
    user_id = profile["id"]

    # Determine current state
    has_paid_access = bool(profile.get("access_cbse"))
    now_iso = datetime.now(timezone.utc).isoformat()
    redemption_resp = (
        admin_client
        .table("offer_redemptions")
        .select("id, valid_until, code_id")
        .eq("user_id", user_id)
        .gte("valid_until", now_iso)
        .limit(1)
        .execute()
    )
    is_currently_gated = not has_paid_access and bool(redemption_resp.data)

    if action == "status":
        return {
            "success": True,
            "username": profile.get("username"),
            "user_id": user_id,
            "is_offer_gated": is_currently_gated,
            "has_paid_access": has_paid_access,
            "access_cbse": bool(profile.get("access_cbse")),
            "active_redemptions": len(redemption_resp.data or []),
            "redemption_ids": [r["id"] for r in (redemption_resp.data or [])],
        }

    if action == "enable":
        # 1. Strip all paid access flags
        admin_client.table("profiles").update({
            "access_cbse": False,
        }).eq("id", user_id).execute()

        # 2. Ensure a test offer code exists
        test_code_label = "ADMTST01"
        existing_code = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", test_code_label)
            .limit(1)
            .execute()
        )
        if existing_code.data:
            code_id = existing_code.data[0]["id"]
        else:
            valid_until_far = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            new_code = admin_client.table("offer_codes").insert({
                "code": test_code_label,
                "description": "Admin Offer-Gate Test Code (auto-created)",
                "is_active": True,
                "valid_from": datetime.now(timezone.utc).isoformat(),
                "valid_until": valid_until_far,
                "max_uses": 9999,
                "uses_count": 0,
                "influencer_name": "",
                "influencer_email": "",
                "code_type": "free_trial",
                "discount_percent": 0,
                "incentive_inr": 0,
                "incentive_paid": False,
            }).execute()
            code_id = new_code.data[0]["id"]

        # 3. Upsert a 30-day test redemption for this user
        valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        # Remove any existing redemptions for this code+user first to avoid duplicates
        admin_client.table("offer_redemptions").delete().eq("user_id", user_id).eq("code_id", code_id).execute()
        admin_client.table("offer_redemptions").insert({
            "user_id": user_id,
            "code_id": code_id,
            "valid_until": valid_until,
        }).execute()

        return {
            "success": True,
            "action": "enabled",
            "username": profile.get("username"),
            "message": f"Offer gate ENABLED for {profile.get('username')}. "
                       f"access_cbse=False, test redemption valid until {valid_until[:10]}. "
                       "Ask Doubt and Lesson follow-up are now DKB-only.",
        }

    if action == "disable":
        # 1. Restore paid access
        admin_client.table("profiles").update({
            "access_cbse": True,
        }).eq("id", user_id).execute()

        # 2. Delete the test redemption for ADMTST01 if it exists
        test_code = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", "ADMTST01")
            .limit(1)
            .execute()
        )
        if test_code.data:
            admin_client.table("offer_redemptions").delete().eq("user_id", user_id).eq("code_id", test_code.data[0]["id"]).execute()

        return {
            "success": True,
            "action": "disabled",
            "username": profile.get("username"),
            "message": f"Offer gate DISABLED for {profile.get('username')}. "
                       "access_cbse restored to True. Full LLM access is back.",
        }
