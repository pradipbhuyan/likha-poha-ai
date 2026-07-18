import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from app.services.logger_service import get_logger, PlatformError

_log = get_logger("routes.payments")

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.routes.admin_control import list_subscription_contact_settings, list_subscription_plan_settings
from app.services.auth_service import admin_client, require_parent, require_admin, get_current_user
from app.services.parent_dashboard_service import get_child_by_id, get_children
from app.services.rate_limit_service import (
    rate_limit_dependency,
    PAYMENT_CREATE_LIMITER,
    PAYMENT_VERIFY_LIMITER,
    ADMIN_TEST_PAYMENT_LIMITER,
)
from app.services.audit_log_service import write_audit_event
from app.services.subscription_timeline_service import (
    write_timeline_event,
    activation_idempotency_key,
)
from app.services.metrics_service import increment as metrics_increment

router = APIRouter()


def _plan_key_to_canonical(plan_key: str) -> str:
    """Map raw DB plan key to canonical event prefix for timeline events."""
    mapping = {
        "free": "NANO",
        "starter": "PREMIUM",
        "family_premium": "FAMILY_PREMIUM",
    }
    return mapping.get(plan_key, "PREMIUM")


def _paid_plan_name(plan_key: str) -> str:
    """Return a human-readable plan display name for email notifications."""
    mapping = {
        "free":           "Free Tier",
        "starter":        "Premium Plan",
        "family_premium": "Family Premium Plan",
    }
    return mapping.get(str(plan_key or "").lower(), "Premium Plan")


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


# Maps billing_label values to duration in days for subscription expiry.
# Used as FALLBACK when duration_days is not explicitly set in the DB plan.
# Plans without an entry here are treated as non-expiring (NULL expires_at).
_BILLING_LABEL_TO_DAYS: dict[str, int] = {
    "8 days": 8,
    "month": 30,      # Business rule: 30 days (not 31)
    "6 months": 184,
    "year": 366,
}


def plan_expires_at(plan) -> str | None:
    """
    Calculate the UTC ISO-8601 expiry timestamp for a plan, or None if perpetual.

    Priority:
      1. plan["duration_days"]  — explicit DB value set by admin (fully centralized)
      2. billing_label lookup   — legacy fallback from _BILLING_LABEL_TO_DAYS
      3. None                   — no expiry (perpetual / admin-granted)

    Perpetual/admin-granted access leaves subscription_expires_at as NULL.
    """
    # 1. Prefer explicit duration_days from DB (admin-configurable)
    duration_days = plan.get("duration_days")
    if duration_days:
        try:
            days = int(duration_days)
            if days > 0:
                return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        except (TypeError, ValueError):
            pass

    # 2. Fallback: derive from billing_label string
    billing_label = (plan.get("billing_label") or "").strip().lower()
    days = _BILLING_LABEL_TO_DAYS.get(billing_label)
    if not days:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def profile_access_from_plan(plan):
    """
    Convert a subscription plan row into profile access fields.

    This is the single mapping that decides which CBSE flags and AI token
    limits are applied after a successful payment or family premium activation.
    Includes subscription_expires_at so time-limited plans (e.g. ₹99/8-day
    Premium Nano) revert to free tier automatically after the access window.
    """
    fields = {
        "subscription_plan": plan["key"],
        "account_status": "active",
        "access_cbse": bool(plan.get("access_cbse")),
        "daily_token_limit": int(plan.get("daily_token_limit") or 0),
        "monthly_token_limit": int(plan.get("monthly_token_limit") or 0),
        "subscription_expires_at": plan_expires_at(plan),
    }
    return fields


def activate_plan_for_payment(payment, plan, parent_profile):
    """
    Apply a verified paid plan to the correct student profile or family.

    Family Premium intentionally updates all children in the parent's family;
    single-child plans update only the child attached to the payment record.

    For Family Premium the parent's own profile also receives subscription_plan
    and subscription_expires_at so the subscription resolver correctly identifies
    the parent as FAMILY_PREMIUM and allows adding a second child.
    """
    family_id = parent_profile.get("family_id")
    child_ids = [payment["child_id"]]

    if plan["key"] == "family_premium" and family_id:
        child_ids = [
            child["id"]
            for child in get_children(parent_profile["id"])
        ] or child_ids

    # Update children (role=student) with full plan access flags
    response = (
        admin_client
        .table("profiles")
        .update(profile_access_from_plan(plan))
        .in_("id", child_ids)
        .eq("role", "student")
        .execute()
    )

    # For Family Premium: also update the parent's subscription_plan and
    # subscription_expires_at so the resolver detects FAMILY_PREMIUM for the
    # parent and allows adding a second child.
    # Do NOT set access_cbse on the parent — parents use the subscription
    # resolver, not the student AI-access flag.
    if plan["key"] == "family_premium":
        parent_id = parent_profile.get("id") or payment.get("parent_id")
        if parent_id:
            try:
                admin_client.table("profiles").update({
                    "subscription_plan": plan["key"],
                    "subscription_expires_at": plan_expires_at(plan),
                }).eq("id", parent_id).eq("role", "parent").execute()
            except Exception as _err:
                _log.warning(
                    "activate_plan_for_payment: failed to update parent profile",
                    parent_id=parent_id,
                    error=str(_err)[:120],
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
    _rl=Depends(rate_limit_dependency(PAYMENT_CREATE_LIMITER)),
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
    _rl=Depends(rate_limit_dependency(PAYMENT_VERIFY_LIMITER)),
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

    # ── Idempotency guard: already verified → return existing result ─────────
    if payment.get("status") == "paid":
        _log.info(
            "payment.verify.already_paid",
            order_id=data.razorpay_order_id,
            parent_id=parent["profile"]["id"],
        )
        return {
            "success": True,
            "payment": payment,
            "activated_profiles": [],   # already activated on first verify
            "idempotent": True,
        }

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

    # ── Upgrade email ────────────────────────────────────────────────────────
    try:
        from app.services.email_service import send_upgrade_email  # noqa: PLC0415
        from app.services.subscription_resolver_service import resolve_user_subscription  # noqa: PLC0415
        _sub = resolve_user_subscription(parent["profile"]["id"])
        send_upgrade_email(
            to=parent["profile"].get("email", ""),
            name=parent["profile"].get("username", ""),
            role="parent",
            plan_name=_paid_plan_name(payment["plan_key"]),
            expires_at=_sub.get("valid_until"),
            days_remaining=_sub.get("days_remaining"),
        )
    except Exception:
        pass  # Email must never block payment flow

    # ── Audit + timeline + metrics (fire-and-forget — never block main flow) ──
    try:
        metrics_increment("payment.verified", plan_key=payment["plan_key"])
        write_audit_event(
            event_type="payment.verified",
            actor_user_id=parent["profile"]["id"],
            target_user_id=payment.get("child_id"),
            entity_type="payment",
            entity_id=data.razorpay_order_id,
            metadata={
                "plan_key": payment["plan_key"],
                "amount": payment.get("amount"),
                "razorpay_order_id": data.razorpay_order_id,
            },
        )
        write_timeline_event(
            user_id=payment["child_id"],
            event_type=f"{_plan_key_to_canonical(payment['plan_key'])}.activated",
            to_plan=payment["plan_key"],
            source="PAID",
            payment_id=data.razorpay_payment_id,
            order_id=data.razorpay_order_id,
            expires_at=saved_payment.get("metadata", {}).get("subscription_expires_at"),
            idempotency_key=activation_idempotency_key(
                data.razorpay_order_id, data.razorpay_payment_id
            ),
            metadata={"plan_key": payment["plan_key"], "amount": payment.get("amount")},
        )
    except Exception as _obs_err:
        _log.warning("payment.verify.observability_failed", error=str(_obs_err))

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
    _rl=Depends(rate_limit_dependency(PAYMENT_CREATE_LIMITER)),
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
    _rl=Depends(rate_limit_dependency(PAYMENT_VERIFY_LIMITER)),
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

    # ── Idempotency guard ────────────────────────────────────────────────────
    if payment.get("status") == "paid":
        return {"success": True, "payment": payment, "plan": None, "idempotent": True}

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

    # ── Upgrade email (student self-service) ─────────────────────────────────
    try:
        from app.services.email_service import send_upgrade_email  # noqa: PLC0415
        from app.services.subscription_resolver_service import resolve_user_subscription  # noqa: PLC0415
        _sub = resolve_user_subscription(user.id)
        _profile_r = admin_client.table("profiles").select("email, username").eq("id", user.id).limit(1).execute()
        _prof = (_profile_r.data or [{}])[0]
        send_upgrade_email(
            to=_prof.get("email", ""),
            name=_prof.get("username", ""),
            role="student",
            plan_name=_paid_plan_name(payment["plan_key"]),
            expires_at=_sub.get("valid_until"),
            days_remaining=_sub.get("days_remaining"),
        )
    except Exception:
        pass  # Email must never block payment flow

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


# ── Admin ₹1 Test Upgrade endpoints ─────────────────────────────────────────
# Admin-only: simulate real plan upgrades using ₹1 test transactions.
# The Razorpay order is for ₹1; the intended plan (Nano / Premium / Family)
# is stored in metadata and used for subscription activation — not the charge amount.

# Allowed plan keys for admin test upgrades and their display metadata
ADMIN_TEST_UPGRADE_PLANS = {
    "free": {
        "label": "Premium Nano",
        "test_description": "₹99 / 8 days",
        "validity_label": "8 days",
        "child_limit": 1,
    },
    "starter": {
        "label": "Premium",
        "test_description": "₹299 / 30 days",
        "validity_label": "30 days",
        "child_limit": 1,
    },
    "family_premium": {
        "label": "Family Premium",
        "test_description": "₹499 / 30 days",
        "validity_label": "30 days",
        "child_limit": 2,
    },
}

ADMIN_TEST_CHARGE_RUPEES = 1   # ₹1 — the only override vs the real flow


class AdminTestOrderRequest(BaseModel):
    target_user_id: str
    intended_plan_key: str   # "free" | "starter" | "family_premium"


class AdminTestVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def get_plan_any(plan_key: str):
    """
    Look up a plan by key regardless of is_public flag.
    Used only by admin test endpoints — never exposed to normal user flows.
    """
    settings_payload = list_subscription_plan_settings()
    plan = (settings_payload.get("plans") or {}).get(plan_key)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_key}' not found.")
    return plan


@router.post("/admin-test-create-order")
def admin_test_create_order(
    data: AdminTestOrderRequest,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_dependency(ADMIN_TEST_PAYMENT_LIMITER)),
):
    """
    Admin-only: create a Razorpay order for ₹1 that will activate a real paid plan.

    Security:
    - Admin role required — normal users cannot call this endpoint.
    - Normal checkout endpoints are unaffected; they still charge the full plan price.
    - The ₹1 override is ONLY applied here; all other payment paths use plan_display_amount().
    - Payment record stores full audit metadata: testMode, adminTriggered, intendedPlan, chargedAmount.
    """
    if not razorpay_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured. Cannot run test upgrade.",
        )

    intended_plan_key = data.intended_plan_key
    if intended_plan_key not in ADMIN_TEST_UPGRADE_PLANS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid intended_plan_key '{intended_plan_key}'. "
                f"Allowed: {list(ADMIN_TEST_UPGRADE_PLANS.keys())}"
            ),
        )

    # Verify target user exists and is a Free Tier student
    target_resp = (
        admin_client
        .table("profiles")
        .select("id, username, email, role, subscription_plan, access_cbse")
        .eq("id", data.target_user_id)
        .limit(1)
        .execute()
    )
    target_rows = target_resp.data or []
    if not target_rows:
        raise HTTPException(status_code=404, detail="Target user not found.")

    target = target_rows[0]
    if target.get("role") not in ("student", "parent"):
        raise HTTPException(
            status_code=400,
            detail=f"Target user role must be student or parent (got '{target.get('role')}').",
        )

    # Look up the INTENDED plan (to store its real price in metadata for audit)
    intended_plan = get_plan_any(intended_plan_key)
    intended_amount = plan_display_amount(intended_plan)
    plan_meta = ADMIN_TEST_UPGRADE_PLANS[intended_plan_key]

    admin_id = admin["profile"]["id"]
    amount_paise = ADMIN_TEST_CHARGE_RUPEES * 100
    receipt = f"admtest_{data.target_user_id[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
    notes = {
        "admin_id": admin_id,
        "target_user_id": data.target_user_id,
        "intended_plan_key": intended_plan_key,
        "test_mode": "true",
    }
    order = create_razorpay_order(amount_paise, receipt, notes)

    payment = save_payment_record({
        "razorpay_order_id": order["id"],
        "razorpay_payment_id": None,
        "parent_id": admin_id,          # admin is the payer for audit
        "child_id": data.target_user_id,
        "family_id": None,
        "plan_key": intended_plan_key,  # REAL plan key — used by activation logic
        "amount": ADMIN_TEST_CHARGE_RUPEES,
        "amount_paise": amount_paise,
        "currency": "INR",
        "status": "created",
        "provider": "razorpay",
        "metadata": {
            "testMode": True,
            "adminTriggered": True,
            "adminId": admin_id,
            "targetUserId": data.target_user_id,
            "targetUsername": target.get("username"),
            "intendedPlanKey": intended_plan_key,
            "intendedPlanLabel": plan_meta["label"],
            "intendedPlanAmount": intended_amount,
            "chargedAmount": ADMIN_TEST_CHARGE_RUPEES,
            "receipt": receipt,
        },
    })

    return {
        "success": True,
        "configured": True,
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "order": order,
        "payment": payment,
        "intended_plan": {
            "key": intended_plan_key,
            "label": plan_meta["label"],
            "description": plan_meta["test_description"],
            "validity": plan_meta["validity_label"],
            "child_limit": plan_meta["child_limit"],
            "actual_price": intended_amount,
        },
        "charged_amount": ADMIN_TEST_CHARGE_RUPEES,
        "target_user": {
            "id": target["id"],
            "username": target.get("username"),
            "email": target.get("email"),
        },
    }


@router.post("/admin-test-verify")
def admin_test_verify(
    data: AdminTestVerifyRequest,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_dependency(ADMIN_TEST_PAYMENT_LIMITER)),
):
    """
    Admin-only: verify a ₹1 test payment and activate the intended paid plan.

    Uses the REAL subscription activation logic (profile_access_from_plan).
    The plan is resolved from the payment record's plan_key (the intended plan),
    NOT from the charged amount — so the correct access window and flags are applied.

    Security:
    - Admin role required.
    - Rejects payments where metadata.testMode != True or metadata.adminTriggered != True.
    - Normal /verify and /student-verify endpoints are unaffected.
    """
    if not razorpay_is_configured():
        raise HTTPException(status_code=503, detail="Payment gateway is not configured.")

    payment = get_payment_by_order_id(data.razorpay_order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found.")

    # Guard: only process admin test payments on this endpoint
    meta = payment.get("metadata") or {}
    if not meta.get("testMode") or not meta.get("adminTriggered"):
        raise HTTPException(
            status_code=403,
            detail="This endpoint only processes admin test payments.",
        )

    # ── Idempotency guard ────────────────────────────────────────────────────
    if payment.get("status") == "paid":
        plan_meta = ADMIN_TEST_UPGRADE_PLANS.get(payment["plan_key"], {})
        return {
            "success": True,
            "payment": payment,
            "activated_profile": {},
            "intended_plan": {
                "key": payment["plan_key"],
                "label": plan_meta.get("label", payment["plan_key"]),
                "validity": plan_meta.get("validity_label", ""),
                "child_limit": plan_meta.get("child_limit", 1),
            },
            "target_user_id": payment.get("child_id"),
            "charged_amount": meta.get("chargedAmount", 1),
            "intended_amount": meta.get("intendedPlanAmount"),
            "idempotent": True,
        }

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

    # Activate the INTENDED plan (plan_key = intended plan key, NOT the ₹1 test plan)
    intended_plan = get_plan_any(payment["plan_key"])
    target_user_id = payment["child_id"]

    activated = (
        admin_client
        .table("profiles")
        .update(profile_access_from_plan(intended_plan))
        .eq("id", target_user_id)
        .execute()
    )
    activated_profile = (activated.data or [{}])[0]

    verified_at = datetime.now(timezone.utc).isoformat()
    saved_payment = save_payment_record({
        **payment,
        "razorpay_payment_id": data.razorpay_payment_id,
        "status": "paid",
        "verified_at": verified_at,
        "metadata": {
            **meta,
            "webhook_source": "admin_test_verify",
        },
    })

    plan_meta = ADMIN_TEST_UPGRADE_PLANS.get(payment["plan_key"], {})

    # ── Audit + timeline + metrics (fire-and-forget — never block main flow) ──
    try:
        metrics_increment("payment.admin_test_verified", plan_key=payment["plan_key"])
        write_audit_event(
            event_type="payment.admin_test_verified",
            actor_user_id=admin["profile"]["id"],
            target_user_id=target_user_id,
            entity_type="payment",
            entity_id=data.razorpay_order_id,
            metadata={
                "plan_key": payment["plan_key"],
                "intendedPlanLabel": plan_meta.get("label"),
                "chargedAmount": meta.get("chargedAmount"),
            },
        )
        write_timeline_event(
            user_id=target_user_id,
            event_type="admin_test.activated",
            to_plan=payment["plan_key"],
            source="PAID",
            payment_id=data.razorpay_payment_id,
            order_id=data.razorpay_order_id,
            idempotency_key=activation_idempotency_key(
                data.razorpay_order_id, data.razorpay_payment_id
            ),
            metadata={"chargedAmount": meta.get("chargedAmount"), "intended": payment["plan_key"]},
        )
    except Exception as _obs_err:
        _log.warning("payment.admin_test_verify.observability_failed", error=str(_obs_err))

    return {
        "success": True,
        "payment": saved_payment,
        "activated_profile": activated_profile,
        "intended_plan": {
            "key": payment["plan_key"],
            "label": plan_meta.get("label", payment["plan_key"]),
            "validity": plan_meta.get("validity_label", ""),
            "child_limit": plan_meta.get("child_limit", 1),
        },
        "target_user_id": target_user_id,
        "charged_amount": meta.get("chargedAmount", 1),
        "intended_amount": meta.get("intendedPlanAmount"),
    }


@router.get("/admin-test-user-status/{user_id}")
def admin_test_user_status(user_id: str, admin=Depends(require_admin)):
    """
    Admin-only: fetch current subscription state for a user after a test upgrade.

    Returns the profile fields that the subscription resolver uses so the admin
    can confirm the upgrade took effect correctly.
    """
    resp = (
        admin_client
        .table("profiles")
        .select(
            "id, username, email, role, subscription_plan, "
            "access_cbse, subscription_expires_at, account_status"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="User not found.")

    profile = rows[0]
    expires_at = profile.get("subscription_expires_at")
    is_active = (
        profile.get("access_cbse")
        and (not expires_at or expires_at > datetime.now(timezone.utc).isoformat())
    )

    return {
        "success": True,
        "profile": profile,
        "subscription_active": is_active,
        "expires_at": expires_at,
    }


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
