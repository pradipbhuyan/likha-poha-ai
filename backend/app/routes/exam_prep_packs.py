"""
exam_prep_packs.py — JEE / NEET / CUET Exam Prep Pack Purchase API
===================================================================
These packs are independent of the CBSE subscription tiers.
Any Grade 11/12 student (Free tier or Premium) can purchase them.

Endpoints:
  GET  /api/exam-prep/my-packs          — which packs the user has active
  GET  /api/exam-prep/pack-prices       — prices from admin settings (no auth)
  POST /api/exam-prep/pack-order        — create Razorpay order for a pack
  POST /api/exam-prep/pack-verify       — verify payment + activate pack
  POST /api/exam-prep/admin-grant-pack  — admin: grant pack to a user (test/manual)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests as req_lib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.auth_service import admin_client, get_current_user, get_user_profile, require_admin
from app.services.rate_limit_service import rate_limit_dependency, PAYMENT_CREATE_LIMITER, PAYMENT_VERIFY_LIMITER

_log = logging.getLogger("exam_prep_packs")

router = APIRouter(prefix="/api/exam-prep", tags=["exam-prep-packs"])

# ── Pack plan key → exam type mapping ────────────────────────────────────────
PACK_TO_EXAM_TYPE = {
    "exam_prep_jee":  "jee_main",
    "exam_prep_neet": "neet_ug",
    "exam_prep_cuet": "cuet_ug",
}
EXAM_TYPE_TO_PACK = {v: k for k, v in PACK_TO_EXAM_TYPE.items()}
VALID_EXAM_TYPES = set(PACK_TO_EXAM_TYPE.values())
TEST_USERS = {"akshita.teststudent"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _get_pack_plan(plan_key: str) -> dict:
    """Load exam prep pack plan from merged defaults+DB settings."""
    from app.services.subscription_settings_service import list_subscription_plan_settings  # noqa: PLC0415
    payload = list_subscription_plan_settings()
    plan = (payload.get("plans") or {}).get(plan_key)
    if not plan:
        raise HTTPException(404, f"Pack plan '{plan_key}' not found.")
    return plan


def _pack_charge(plan: dict) -> int:
    """Calculate rupee amount after discount."""
    price = int(plan.get("price") or 0)
    discount = int(plan.get("discount_percent") or 0)
    if discount <= 0:
        return price
    return max(0, round(price * (100 - discount) / 100))


def _pack_expires_at(plan: dict) -> str | None:
    """Calculate pack expiry ISO timestamp."""
    days = plan.get("duration_days")
    if not days:
        return None
    try:
        return (datetime.now(timezone.utc) + timedelta(days=int(days))).isoformat()
    except Exception:
        return None


def _get_active_packs(user_id: str) -> dict:
    """
    Return active packs for a user.
    Returns: { "jee_main": {"active": bool, "expires_at": str|None}, ... }
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {"jee_main": {"active": False, "expires_at": None},
              "neet_ug":  {"active": False, "expires_at": None},
              "cuet_ug":  {"active": False, "expires_at": None}}
    try:
        rows = (
            admin_client
            .table("exam_prep_subscriptions")
            .select("exam_type, status, expires_at")
            .eq("user_id", user_id)
            .execute()
        ).data or []
        for row in rows:
            et = row.get("exam_type")
            if et not in result:
                continue
            if row.get("status") != "active":
                continue
            exp = row.get("expires_at")
            if exp and exp < now:
                # Expired — mark in DB asynchronously (non-blocking)
                try:
                    admin_client.table("exam_prep_subscriptions").update(
                        {"status": "expired"}
                    ).eq("user_id", user_id).eq("exam_type", et).execute()
                except Exception:
                    pass
                continue
            result[et] = {"active": True, "expires_at": exp}
    except Exception as e:
        _log.warning("_get_active_packs error for user %s: %s", user_id[:8], e)
    return result


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/my-packs")
def get_my_packs(user=Depends(get_current_user)):
    """Return which exam prep packs the current user has active."""
    profile = get_user_profile(user.id)
    if not profile:
        raise HTTPException(403, "Profile not found")
    grade = profile.get("grade", "")
    username = profile.get("username", "")
    role = profile.get("role", "")

    # Admin and test users get all packs active
    if role == "admin" or username in TEST_USERS:
        return {
            "success": True,
            "packs": {
                "jee_main": {"active": True, "expires_at": None},
                "neet_ug":  {"active": True, "expires_at": None},
                "cuet_ug":  {"active": True, "expires_at": None},
            },
            "grade_eligible": True,
        }

    grade_eligible = grade in ("Grade 11", "Grade 12") and role == "student"
    packs = _get_active_packs(user.id) if grade_eligible else {
        "jee_main": {"active": False, "expires_at": None},
        "neet_ug":  {"active": False, "expires_at": None},
        "cuet_ug":  {"active": False, "expires_at": None},
    }
    return {"success": True, "packs": packs, "grade_eligible": grade_eligible}


@router.get("/pack-prices")
def get_pack_prices():
    """
    Return current pack prices from admin settings.
    No auth required — shown on the preview/landing page.
    """
    from app.services.subscription_settings_service import list_subscription_plan_settings  # noqa: PLC0415
    payload = list_subscription_plan_settings()
    plans = payload.get("plans") or {}
    result = {}
    for pack_key, exam_type in PACK_TO_EXAM_TYPE.items():
        plan = plans.get(pack_key, {})
        charge = _pack_charge(plan)
        result[exam_type] = {
            "plan_key":    pack_key,
            "label":       plan.get("label", pack_key),
            "price":       plan.get("price", 0),
            "charge":      charge,            # after discount
            "discount_pct": plan.get("discount_percent", 0),
            "discount_label": plan.get("discount_label", ""),
            "duration_days": plan.get("duration_days", 120),
            "billing_label": plan.get("billing_label", "season"),
            "included":    plan.get("included", []),
            "badge":       plan.get("badge", ""),
        }
    return {"success": True, "prices": result, "razorpay_configured": _razorpay_configured()}


class PackOrderRequest(BaseModel):
    exam_type: str   # jee_main | neet_ug | cuet_ug


@router.post("/pack-order")
def create_pack_order(
    data: PackOrderRequest,
    user=Depends(get_current_user),
    _rl=Depends(rate_limit_dependency(PAYMENT_CREATE_LIMITER)),
):
    """Create a Razorpay order for an exam prep pack purchase."""
    if not _razorpay_configured():
        raise HTTPException(503, "Payment gateway not configured.")

    if data.exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, f"Invalid exam_type. Must be one of: {sorted(VALID_EXAM_TYPES)}")

    profile = get_user_profile(user.id)
    if not profile:
        raise HTTPException(403, "Profile not found")

    grade = profile.get("grade", "")
    role = profile.get("role", "")
    if role != "student" or grade not in ("Grade 11", "Grade 12"):
        raise HTTPException(403, "Exam prep packs are only available for Grade 11 & 12 students.")

    # Check not already purchased
    packs = _get_active_packs(user.id)
    if packs[data.exam_type]["active"]:
        raise HTTPException(409, f"You already have an active {data.exam_type} pack.")

    pack_key = EXAM_TYPE_TO_PACK[data.exam_type]
    plan = _get_pack_plan(pack_key)
    amount_rupees = _pack_charge(plan)
    if amount_rupees <= 0:
        raise HTTPException(400, "Pack has no charge amount. Contact admin.")

    import time  # noqa: PLC0415
    receipt = f"ep_{data.exam_type[:3]}_{user.id[:8]}_{int(time.time())}"
    resp = req_lib.post(
        "https://api.razorpay.com/v1/orders",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={"amount": amount_rupees * 100, "currency": "INR", "receipt": receipt,
              "notes": {"user_id": user.id, "exam_type": data.exam_type, "pack_key": pack_key}},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(502, "Payment gateway could not create an order.")

    order = resp.json()

    # Pre-record order (status=created)
    try:
        admin_client.table("exam_prep_subscriptions").upsert({
            "user_id": user.id,
            "exam_type": data.exam_type,
            "status": "created",   # temp — updated after verification
            "plan_key": pack_key,
            "razorpay_order_id": order["id"],
            "amount_paid": amount_rupees,
        }, on_conflict="user_id,exam_type").execute()
    except Exception as e:
        _log.warning("pack-order pre-record failed: %s", e)

    return {
        "success": True,
        "order_id": order["id"],
        "amount": amount_rupees,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "exam_type": data.exam_type,
        "plan_label": plan.get("label", pack_key),
        "duration_days": plan.get("duration_days", 120),
    }


class PackVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    exam_type: str


@router.post("/pack-verify")
def verify_pack_payment(
    data: PackVerifyRequest,
    user=Depends(get_current_user),
    _rl=Depends(rate_limit_dependency(PAYMENT_VERIFY_LIMITER)),
):
    """Verify Razorpay payment and activate exam prep pack immediately."""
    if not _razorpay_configured():
        raise HTTPException(503, "Payment gateway not configured.")

    if data.exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, "Invalid exam_type.")

    # Verify signature
    if not _verify_razorpay_signature(data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature):
        raise HTTPException(400, "Payment verification failed. Contact support.")

    # Look up the pre-recorded order
    rows = (
        admin_client.table("exam_prep_subscriptions")
        .select("*").eq("user_id", user.id).eq("exam_type", data.exam_type)
        .limit(1).execute()
    ).data or []

    if not rows:
        raise HTTPException(404, "Payment order not found. Contact support.")

    row = rows[0]

    # Idempotency — already activated
    if row.get("status") == "active" and row.get("razorpay_payment_id"):
        return {
            "success": True,
            "exam_type": data.exam_type,
            "expires_at": row.get("expires_at"),
            "idempotent": True,
        }

    # Calculate expiry
    pack_key = EXAM_TYPE_TO_PACK[data.exam_type]
    plan = _get_pack_plan(pack_key)
    expires_at = _pack_expires_at(plan)

    # Activate pack
    admin_client.table("exam_prep_subscriptions").update({
        "status": "active",
        "razorpay_payment_id": data.razorpay_payment_id,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user.id).eq("exam_type", data.exam_type).execute()

    _log.info("exam_prep_pack.activated user=%s exam=%s expires=%s", user.id[:8], data.exam_type, expires_at)

    # Audit log (non-critical)
    try:
        admin_client.table("platform_audit_logs").insert({
            "user_id": user.id,
            "event": "exam_prep_pack.purchased",
            "metadata": {
                "exam_type": data.exam_type,
                "plan_key": pack_key,
                "amount": row.get("amount_paid"),
                "order_id": data.razorpay_order_id,
                "payment_id": data.razorpay_payment_id,
                "expires_at": expires_at,
            },
        }).execute()
    except Exception:
        pass

    return {
        "success": True,
        "exam_type": data.exam_type,
        "expires_at": expires_at,
        "duration_days": plan.get("duration_days"),
        "plan_label": plan.get("label"),
    }


class AdminGrantPackRequest(BaseModel):
    user_id: str
    exam_type: str
    duration_days: int = 120


@router.post("/admin-grant-pack")
def admin_grant_pack(
    data: AdminGrantPackRequest,
    admin=Depends(require_admin),
):
    """Admin: manually grant an exam prep pack to a user (for testing or support)."""
    if data.exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, f"Invalid exam_type. Must be one of: {sorted(VALID_EXAM_TYPES)}")

    expires_at = (datetime.now(timezone.utc) + timedelta(days=data.duration_days)).isoformat()
    pack_key = EXAM_TYPE_TO_PACK[data.exam_type]

    admin_client.table("exam_prep_subscriptions").upsert({
        "user_id": data.user_id,
        "exam_type": data.exam_type,
        "status": "active",
        "plan_key": pack_key,
        "expires_at": expires_at,
        "amount_paid": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,exam_type").execute()

    _log.info("admin_grant_pack admin=%s user=%s exam=%s", admin["profile"]["id"][:8], data.user_id[:8], data.exam_type)

    return {
        "success": True,
        "user_id": data.user_id,
        "exam_type": data.exam_type,
        "expires_at": expires_at,
        "duration_days": data.duration_days,
    }


@router.delete("/admin-revoke-pack/{user_id}/{exam_type}")
def admin_revoke_pack(user_id: str, exam_type: str, admin=Depends(require_admin)):
    """Admin: revoke an exam prep pack from a user."""
    if exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, "Invalid exam_type.")

    admin_client.table("exam_prep_subscriptions").update({
        "status": "revoked",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).eq("exam_type", exam_type).execute()

    return {"success": True, "user_id": user_id, "exam_type": exam_type, "status": "revoked"}


# ─────────────────────────────────────────────────────────────────────────────
# Admin ₹1 test endpoints for Exam Prep Pack payment flow
# ─────────────────────────────────────────────────────────────────────────────

ADMIN_TEST_CHARGE_RUPEES = 1  # ₹1 real transaction for testing


class AdminTestPackOrderRequest(BaseModel):
    target_user_id: str
    exam_type: str  # jee_main | neet_ug | cuet_ug


class AdminTestPackVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    target_user_id: str
    exam_type: str


@router.post("/admin-test-pack-order")
def admin_test_pack_order(
    data: AdminTestPackOrderRequest,
    admin=Depends(require_admin),
):
    """
    Admin-only: create a Razorpay ₹1 order that will activate a real exam prep pack.

    Security:
    - Admin role required — normal Grade 11/12 students cannot call this.
    - Normal pack-order endpoint is unaffected; it still charges the full pack price.
    - Target user can be any grade/role (for testing purposes — admin bypasses grade gate).
    - Payment record stores full audit metadata: exam_type, target_user_id, adminTriggered.
    """
    if not _razorpay_configured():
        raise HTTPException(503, "Razorpay not configured.")

    if data.exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, f"Invalid exam_type. Must be one of: {sorted(VALID_EXAM_TYPES)}")

    # Verify target user exists
    target_resp = (
        admin_client.table("profiles")
        .select("id, username, email, role, grade")
        .eq("id", data.target_user_id).limit(1).execute()
    )
    if not (target_resp.data or []):
        raise HTTPException(404, "Target user not found.")

    target = target_resp.data[0]
    admin_id = admin["profile"]["id"]

    import time  # noqa: PLC0415
    pack_key = EXAM_TYPE_TO_PACK[data.exam_type]
    plan = _get_pack_plan(pack_key)

    receipt = f"admpk_{data.exam_type[:3]}_{data.target_user_id[:8]}_{int(time.time())}"
    notes = {
        "admin_id": admin_id,
        "target_user_id": data.target_user_id,
        "exam_type": data.exam_type,
        "pack_key": pack_key,
        "intended_price": str(plan.get("price", 0)),
        "charged_amount": str(ADMIN_TEST_CHARGE_RUPEES),
        "test_mode": "true",
    }

    resp = req_lib.post(
        "https://api.razorpay.com/v1/orders",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={"amount": ADMIN_TEST_CHARGE_RUPEES * 100, "currency": "INR",
              "receipt": receipt, "notes": notes},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(502, "Razorpay could not create order.")

    order = resp.json()

    # Pre-record order
    try:
        admin_client.table("exam_prep_subscriptions").upsert({
            "user_id": data.target_user_id,
            "exam_type": data.exam_type,
            "status": "created",
            "plan_key": pack_key,
            "razorpay_order_id": order["id"],
            "amount_paid": ADMIN_TEST_CHARGE_RUPEES,
        }, on_conflict="user_id,exam_type").execute()
    except Exception as e:
        _log.warning("admin_test_pack_order pre-record failed: %s", e)

    return {
        "success": True,
        "order_id": order["id"],
        "amount": ADMIN_TEST_CHARGE_RUPEES,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "exam_type": data.exam_type,
        "target_user": {"id": target["id"], "username": target.get("username"), "grade": target.get("grade")},
        "intended_pack": plan.get("label", pack_key),
        "intended_price": plan.get("price", 0),
        "duration_days": plan.get("duration_days", 120),
    }


@router.post("/admin-test-pack-verify")
def admin_test_pack_verify(
    data: AdminTestPackVerifyRequest,
    admin=Depends(require_admin),
):
    """
    Admin-only: verify ₹1 payment and activate the INTENDED exam prep pack for target user.
    The pack activated is the full-duration intended pack — only the charge was ₹1.
    """
    if not _razorpay_configured():
        raise HTTPException(503, "Razorpay not configured.")

    if data.exam_type not in VALID_EXAM_TYPES:
        raise HTTPException(400, "Invalid exam_type.")

    if not _verify_razorpay_signature(data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature):
        raise HTTPException(400, "Payment verification failed.")

    pack_key = EXAM_TYPE_TO_PACK[data.exam_type]
    plan = _get_pack_plan(pack_key)
    expires_at = _pack_expires_at(plan)
    admin_id = admin["profile"]["id"]

    # Activate pack for target user
    admin_client.table("exam_prep_subscriptions").update({
        "status": "active",
        "razorpay_payment_id": data.razorpay_payment_id,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", data.target_user_id).eq("exam_type", data.exam_type).execute()

    _log.info("admin_test_pack_verify.activated admin=%s target=%s exam=%s expires=%s",
              admin_id[:8], data.target_user_id[:8], data.exam_type, expires_at)

    # Audit log
    try:
        admin_client.table("platform_audit_logs").insert({
            "user_id": admin_id,
            "event": "exam_prep_pack.admin_test_activated",
            "metadata": {
                "target_user_id": data.target_user_id,
                "exam_type": data.exam_type,
                "pack_key": pack_key,
                "expires_at": expires_at,
                "charged_amount": ADMIN_TEST_CHARGE_RUPEES,
                "intended_price": plan.get("price"),
                "order_id": data.razorpay_order_id,
                "payment_id": data.razorpay_payment_id,
            },
        }).execute()
    except Exception:
        pass

    # Fetch updated pack state
    updated_packs = _get_active_packs(data.target_user_id)

    return {
        "success": True,
        "exam_type": data.exam_type,
        "target_user_id": data.target_user_id,
        "expires_at": expires_at,
        "duration_days": plan.get("duration_days"),
        "pack_label": plan.get("label"),
        "charged_amount": ADMIN_TEST_CHARGE_RUPEES,
        "intended_price": plan.get("price"),
        "active_packs": updated_packs,
    }
