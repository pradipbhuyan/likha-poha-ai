import hashlib
import hmac
from datetime import datetime, timezone
from app.services.logger_service import get_logger, PlatformError

_log = get_logger("routes.payments")

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.routes.admin_control import list_subscription_contact_settings, list_subscription_plan_settings
from app.services.auth_service import admin_client, require_parent, get_current_user
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
    """Return whether Razorpay keys are present enough to enable checkout."""
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def plan_display_amount(plan):
    """
    Calculate the parent-facing payable amount after any admin discount.

    Prices are stored in rupees; Razorpay conversion to paise happens later.
    """
    price = int(plan.get("price") or 0)
    discount = int(plan.get("discount_percent") or 0)

    if discount <= 0:
        return price

    return max(0, round(price * (100 - discount) / 100))


def get_public_plan(plan_key: str):
    """
    Fetch a plan that parents are allowed to purchase.

    Hidden/non-public plans may still exist for admin use but should not be used
    to create public payment orders.
    """
    settings_payload = list_subscription_plan_settings()
    plan = (settings_payload.get("plans") or {}).get(plan_key)

    if not plan or plan.get("is_public") is False:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")

    return plan


def create_razorpay_order(amount_paise: int, receipt: str, notes: dict):
    """
    Create a Razorpay order and translate gateway failures into HTTP 502.

    The local payment record is saved only after Razorpay returns an order id,
    so the database never stores an order that Razorpay did not create.
    """
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
    """
    Verify the Razorpay checkout callback using HMAC SHA-256.

    Constant-time comparison protects the signature check from timing leaks.
    """
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def save_payment_record(record: dict):
    """
    Upsert the local payment record keyed by Razorpay order id.

    Upsert keeps order creation idempotent if the frontend retries after a
    transient network issue.
    """
    response = (
        admin_client
        .table("subscription_payments")
        .upsert(record, on_conflict="razorpay_order_id")
        .execute()
    )

    return response.data[0] if response.data else record


def get_payment_by_order_id(order_id: str):
    """Load the local payment record associated with a Razorpay order id."""
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
    """
    Convert a subscription plan row into profile access fields.

    This is the single mapping that decides which CBSE/SOF flags and AI token
    limits are applied after a successful payment or family premium activation.
    """
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
    """
    Apply a verified paid plan to the correct student profile or family.

    Family Premium intentionally updates all children in the parent's family;
    single-child plans update only the child attached to the payment record.
    """
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
    """Return safe frontend checkout configuration for a signed-in parent."""
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
    """
    Create a paid subscription order for one child under the signed-in parent.

    The child lookup is parent-scoped before plan/payment creation, preventing a
    parent from buying or changing a plan for someone else's child id.
    """
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
    """
    Verify Razorpay callback data, mark payment paid, and activate access.

    The local payment row must belong to the signed-in parent before signature
    validation or plan activation, which prevents cross-family order reuse.
    """
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
        _log.error(
            "payment.verify.signature_failed",
            error_code=PlatformError.PAY_VERIFY_FAILED,
            order_id=data.razorpay_order_id,
            payment_id=data.razorpay_payment_id,
            parent_id=parent["profile"]["id"],
        )
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

    _log.info(
        "payment.verify.success",
        order_id=data.razorpay_order_id,
        payment_id=data.razorpay_payment_id,
        plan_key=payment["plan_key"],
        parent_id=parent["profile"]["id"],
        activated_count=len(activated_profiles),
    )

    return {
        "success": True,
        "payment": saved_payment,
        "activated_profiles": activated_profiles,
    }


# ── Student self-service payment endpoints ───────────────────────────────────
# For standalone students (parent_id=None) who signed up via the public Signup
# flow and manage their own subscription without a parent account.


class StudentCreateOrderRequest(BaseModel):
    plan_key: str


@router.get("/student-config")
def get_student_payment_config(user=Depends(get_current_user)):
    """Return safe Razorpay configuration for a standalone student."""
    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, role, parent_id")
        .eq("id", user.id)
        .single()
        .execute()
    )
    profile = profile_resp.data or {}
    if profile.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student account required.")
    if profile.get("parent_id"):
        raise HTTPException(
            status_code=403,
            detail="This account is managed by a parent. Ask your parent to upgrade.",
        )
    return {
        "success": True,
        "configured": razorpay_is_configured(),
        "provider": "razorpay",
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID if razorpay_is_configured() else None,
    }


@router.post("/student-create-order")
def student_create_payment_order(
    data: StudentCreateOrderRequest,
    user=Depends(get_current_user),
):
    """
    Create a Razorpay subscription order for a standalone student paying for themselves.

    Only allowed when the student has no parent_id (self-registered).
    Parent-linked students must go through their parent's account.
    """
    if not razorpay_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured yet.",
        )

    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, role, parent_id, email, username")
        .eq("id", user.id)
        .single()
        .execute()
    )
    profile = profile_resp.data or {}

    if profile.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student account required.")

    if profile.get("parent_id"):
        raise HTTPException(
            status_code=403,
            detail="This account is managed by a parent. Ask your parent to upgrade.",
        )

    plan = get_public_plan(data.plan_key)
    amount_rupees = plan_display_amount(plan)

    if amount_rupees <= 0:
        raise HTTPException(status_code=400, detail="Free plans do not need payment.")

    student_id = profile["id"]
    amount_paise = amount_rupees * 100
    receipt = f"stu_{student_id[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
    notes = {
        "student_id": student_id,
        "plan_key": plan["key"],
        "source": "student_self_service",
    }
    order = create_razorpay_order(amount_paise, receipt, notes)

    payment = save_payment_record({
        "razorpay_order_id": order["id"],
        "razorpay_payment_id": None,
        "parent_id": student_id,   # reuse parent_id column to store payer id
        "child_id": student_id,    # student is both payer and beneficiary
        "family_id": None,
        "plan_key": plan["key"],
        "amount": amount_rupees,
        "amount_paise": amount_paise,
        "currency": "INR",
        "status": "created",
        "provider": "razorpay",
        "metadata": {
            "receipt": receipt,
            "plan_label": plan.get("label"),
            "source": "student_self_service",
            "student_username": profile.get("username"),
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


@router.post("/student-verify")
def student_verify_payment(
    data: VerifyPaymentRequest,
    user=Depends(get_current_user),
):
    """
    Verify Razorpay callback for a standalone student self-service payment.

    Activates the plan directly on the student's own profile.
    """
    if not razorpay_is_configured():
        raise HTTPException(status_code=503, detail="Payment gateway is not configured.")

    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, role, parent_id")
        .eq("id", user.id)
        .single()
        .execute()
    )
    profile = profile_resp.data or {}

    if profile.get("role") != "student" or profile.get("parent_id"):
        raise HTTPException(status_code=403, detail="Not authorised for self-service payment.")

    payment = get_payment_by_order_id(data.razorpay_order_id)

    if not payment or payment.get("child_id") != user.id:
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

    # Activate plan on the student's own profile
    admin_client.table("profiles").update(
        profile_access_from_plan(plan)
    ).eq("id", user.id).eq("role", "student").execute()

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
        "plan": plan,
    }


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Receive Razorpay webhook events and process payment.captured.

    Razorpay sends a POST with JSON body and X-Razorpay-Signature header.
    We verify the signature with HMAC-SHA256 using RAZORPAY_WEBHOOK_SECRET,
    then activate the subscription for the order if not already done.

    This is a safety net for cases where:
    - The student's browser closed before /verify was called
    - Network errors prevented the frontend from completing signup
    - Any payment that Razorpay captured but we never processed

    Always returns 200 so Razorpay stops retrying (even on errors).
    """
    import hashlib
    import hmac as hmac_lib
    import logging

    logger = logging.getLogger(__name__)

    try:
        raw_body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")

        # If webhook secret is configured, verify signature
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        if webhook_secret:
            expected = hmac_lib.new(
                webhook_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac_lib.compare_digest(expected, signature):
                logger.warning("Razorpay webhook: invalid signature — ignoring")
                return {"status": "ignored", "reason": "invalid_signature"}

        payload = await request.json() if not raw_body else __import__("json").loads(raw_body)
        event = payload.get("event", "")
        logger.info("Razorpay webhook received: %s", event)

        if event != "payment.captured":
            # We only care about payment.captured; acknowledge all others
            return {"status": "ok", "event": event}

        # Extract order id from webhook payload
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        order_id   = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not order_id:
            logger.warning("Razorpay webhook: payment.captured has no order_id")
            return {"status": "ok", "note": "no_order_id"}

        # Check if we already processed this payment
        payment = get_payment_by_order_id(order_id)
        if not payment:
            logger.warning("Razorpay webhook: order %s not in local DB — ignoring", order_id)
            return {"status": "ok", "note": "order_not_found"}

        if payment.get("status") == "paid":
            logger.info("Razorpay webhook: order %s already paid — skipping", order_id)
            return {"status": "ok", "note": "already_processed"}

        # Activate the plan
        try:
            plan = get_public_plan(payment["plan_key"])
            parent_profile_resp = (
                admin_client
                .table("profiles")
                .select("*")
                .eq("id", payment["parent_id"])
                .limit(1)
                .execute()
            )
            parent_profile = (parent_profile_resp.data or [{}])[0]
            activate_plan_for_payment(payment, plan, parent_profile)

            save_payment_record({
                **payment,
                "razorpay_payment_id": payment_id,
                "status": "paid",
                "verified_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "metadata": {**(payment.get("metadata") or {}), "webhook_confirmed": True},
            })
            logger.info("Razorpay webhook: activated plan %s for order %s", payment["plan_key"], order_id)
        except Exception as activation_err:
            logger.error("Razorpay webhook: activation failed for order %s: %s", order_id, activation_err)

    except Exception as exc:
        # Always return 200 so Razorpay stops retrying
        logging.getLogger(__name__).error("Razorpay webhook error: %s", exc)

    return {"status": "ok"}


@router.get("/contact")
def get_public_contact():
    """
    Return the admin-configured support contact for public pages (no auth required).

    Used by the landing page footer to stay in sync with the admin contact settings.
    """
    result = list_subscription_contact_settings()
    contact = result.get("contact") or {}
    return {
        "success": True,
        "email": contact.get("email") or "hello@likhapoha.in",
        "phone": contact.get("phone") or "",
        "whatsapp": contact.get("whatsapp") or "",
    }
