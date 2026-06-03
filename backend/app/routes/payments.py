import hashlib
import hmac
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.routes.admin_control import list_subscription_plan_settings
from app.services.auth_service import admin_client, require_parent
from app.services.parent_dashboard_service import get_child_by_id, get_children

router = APIRouter()


class CreatePaymentOrderRequest(BaseModel):
    child_id: str
    plan_key: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def razorpay_is_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def plan_display_amount(plan):
    price = int(plan.get("price") or 0)
    discount = int(plan.get("discount_percent") or 0)

    if discount <= 0:
        return price

    return max(0, round(price * (100 - discount) / 100))


def get_public_plan(plan_key: str):
    settings_payload = list_subscription_plan_settings()
    plan = (settings_payload.get("plans") or {}).get(plan_key)

    if not plan or plan.get("is_public") is False:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")

    return plan


def create_razorpay_order(amount_paise: int, receipt: str, notes: dict):
    response = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes,
        },
        timeout=20,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="Payment gateway could not create an order.",
        )

    return response.json()


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str):
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def save_payment_record(record: dict):
    response = (
        admin_client
        .table("subscription_payments")
        .upsert(record, on_conflict="razorpay_order_id")
        .execute()
    )

    return response.data[0] if response.data else record


def get_payment_by_order_id(order_id: str):
    response = (
        admin_client
        .table("subscription_payments")
        .select("*")
        .eq("razorpay_order_id", order_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    return rows[0] if rows else None


def profile_access_from_plan(plan):
    return {
        "subscription_plan": plan["key"],
        "account_status": "active",
        "access_cbse": bool(plan.get("access_cbse")),
        "access_sof_science": bool(plan.get("access_sof_science")),
        "access_sof_maths": bool(plan.get("access_sof_maths")),
        "access_sof_english": bool(plan.get("access_sof_english")),
        "daily_token_limit": int(plan.get("daily_token_limit") or 0),
        "monthly_token_limit": int(plan.get("monthly_token_limit") or 0),
    }


def activate_plan_for_payment(payment, plan, parent_profile):
    family_id = parent_profile.get("family_id")
    child_ids = [payment["child_id"]]

    if plan["key"] == "family_premium" and family_id:
        child_ids = [
            child["id"]
            for child in get_children(parent_profile["id"])
        ] or child_ids

    response = (
        admin_client
        .table("profiles")
        .update(profile_access_from_plan(plan))
        .in_("id", child_ids)
        .eq("role", "student")
        .execute()
    )

    return response.data or []


@router.get("/config")
def get_payment_config(parent=Depends(require_parent)):
    return {
        "success": True,
        "configured": razorpay_is_configured(),
        "provider": "razorpay",
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID if razorpay_is_configured() else None,
    }


@router.post("/create-order")
def create_payment_order(
    data: CreatePaymentOrderRequest,
    parent=Depends(require_parent),
):
    if not razorpay_is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Payment gateway is not configured yet. Admin can activate "
                "the plan manually until Razorpay keys are added."
            ),
        )

    parent_profile = parent["profile"]
    child = get_child_by_id(parent_profile["id"], data.child_id)

    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found.")

    plan = get_public_plan(data.plan_key)
    amount_rupees = plan_display_amount(plan)

    if amount_rupees <= 0:
        raise HTTPException(
            status_code=400,
            detail="Free plans do not need payment.",
        )

    amount_paise = amount_rupees * 100
    receipt = f"sub_{data.child_id[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
    notes = {
        "parent_id": parent_profile["id"],
        "child_id": data.child_id,
        "plan_key": plan["key"],
    }
    order = create_razorpay_order(amount_paise, receipt, notes)

    payment = save_payment_record({
        "razorpay_order_id": order["id"],
        "razorpay_payment_id": None,
        "parent_id": parent_profile["id"],
        "child_id": data.child_id,
        "family_id": parent_profile.get("family_id"),
        "plan_key": plan["key"],
        "amount": amount_rupees,
        "amount_paise": amount_paise,
        "currency": "INR",
        "status": "created",
        "provider": "razorpay",
        "metadata": {
            "receipt": receipt,
            "plan_label": plan.get("label"),
            "discount_percent": plan.get("discount_percent"),
            "discount_label": plan.get("discount_label"),
        },
    })

    return {
        "success": True,
        "configured": True,
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "order": order,
        "payment": payment,
        "plan": plan,
    }


@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    parent=Depends(require_parent),
):
    if not razorpay_is_configured():
        raise HTTPException(status_code=503, detail="Payment gateway is not configured.")

    payment = get_payment_by_order_id(data.razorpay_order_id)

    if not payment or payment.get("parent_id") != parent["profile"]["id"]:
        raise HTTPException(status_code=404, detail="Payment order not found.")

    if not verify_razorpay_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
    ):
        save_payment_record({
            **payment,
            "razorpay_payment_id": data.razorpay_payment_id,
            "status": "signature_failed",
        })
        raise HTTPException(status_code=400, detail="Payment verification failed.")

    plan = get_public_plan(payment["plan_key"])
    activated_profiles = activate_plan_for_payment(payment, plan, parent["profile"])
    verified_at = datetime.now(timezone.utc).isoformat()
    saved_payment = save_payment_record({
        **payment,
        "razorpay_payment_id": data.razorpay_payment_id,
        "status": "paid",
        "verified_at": verified_at,
    })

    return {
        "success": True,
        "payment": saved_payment,
        "activated_profiles": activated_profiles,
    }
