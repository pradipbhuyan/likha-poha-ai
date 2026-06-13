import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.schemas import LoginRequest, LoginResponse
from app.config import settings
from app.services.auth_service import admin_client

router = APIRouter()

USERS = {
    "akshita": {
        "password": settings.AKSHITA_PASSWORD,
        "role": "student"
    },
    "pradip": {
        "password": settings.PRADIP_PASSWORD,
        "role": "parent"
    },
    "admin": {
        "password": settings.ADMIN_PASSWORD,
        "role": "admin"
    }
}


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    """
    Legacy username/password login endpoint for seeded demo users.

    Most current UI auth flows use Supabase directly, but this endpoint remains
    for compatibility with older tests and local demo access.
    """
    username = data.username.lower()
    if username not in USERS:
        return LoginResponse(success=False, message="Invalid username or password")
    if USERS[username]["password"] != data.password:
        return LoginResponse(success=False, message="Invalid username or password")
    return LoginResponse(
        success=True,
        username=username,
        role=USERS[username]["role"],
        message="Login successful",
    )


@router.get("/lookup-email/{username}")
def lookup_email(username: str):
    """
    Resolve a friendly username to an email address for Supabase login.

    The admin alias fallback lets the UI log in as "admin" even when the profile
    row stores a display name rather than that exact username.
    """
    clean_username = username.strip().lower()
    response = (
        admin_client
        .table("profiles")
        .select("email")
        .ilike("username", clean_username)
        .limit(1)
        .execute()
    )
    rows = response.data or []

    if not rows and clean_username == "admin":
        response = (
            admin_client
            .table("profiles")
            .select("email")
            .eq("role", "admin")
            .limit(1)
            .execute()
        )
        rows = response.data or []

    if not rows:
        raise HTTPException(status_code=404, detail="Username not found")

    return {"email": rows[0]["email"]}


# ---------------------------------------------------------------------------
# Public signup-with-payment endpoints
# ---------------------------------------------------------------------------

VALID_SIGNUP_ROLES = {"parent", "student", "teacher"}
# All grades the backend accepts — includes Grade 11/12 which are hidden from
# students until admin enables them in the Product Catalogue page.
from app.data.product_catalogue import ALL_GRADES_INCLUDING_HIDDEN  # noqa: E402
VALID_GRADES = set(ALL_GRADES_INCLUDING_HIDDEN)


class SignupOrderRequest(BaseModel):
    """Request body for creating a Razorpay order before account creation."""
    email: str
    plan_key: str


class CompleteSignupRequest(BaseModel):
    """Request body for completing signup after successful Razorpay payment."""
    role: str
    name: str
    email: str
    plan_key: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    grade: Optional[str] = None
    school: Optional[str] = None


def _razorpay_is_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay webhook signature using HMAC-SHA256."""
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get_plan(plan_key: str) -> dict:
    """Load a public subscription plan for signup."""
    from app.routes.admin_control import list_subscription_plan_settings
    payload = list_subscription_plan_settings()
    plan = (payload.get("plans") or {}).get(plan_key)
    if not plan or plan.get("is_public") is False:
        raise HTTPException(status_code=400, detail="Invalid plan selected.")
    return plan


def _plan_amount(plan: dict) -> int:
    """Return rupee amount after discount."""
    price = int(plan.get("price") or 0)
    discount = int(plan.get("discount_percent") or 0)
    if discount <= 0:
        return price
    return max(0, round(price * (100 - discount) / 100))


def _profile_access_fields(plan: dict) -> dict:
    """Convert plan row into profile access fields."""
    return {
        "subscription_plan": plan["key"],
        "account_status": "active",
        "access_cbse": bool(plan.get("access_cbse")),
        "access_sof_science": bool(plan.get("access_sof_science")),
        "access_sof_maths": bool(plan.get("access_sof_maths")),
        "access_sof_english": bool(plan.get("access_sof_english")),
        "daily_token_limit": int(plan.get("daily_token_limit") or 50000),
        "monthly_token_limit": int(plan.get("monthly_token_limit") or 1000000),
    }


@router.post("/signup-order")
def create_signup_order(data: SignupOrderRequest):
    """
    Create a Razorpay payment order for a new self-signup (no auth required).

    Called before account creation so the user pays first. The order is keyed
    to the email address and plan to help trace any failed signups.
    """
    if not _razorpay_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment is not yet configured. Please contact support to sign up.",
        )
    plan = _get_plan(data.plan_key)
    amount_rupees = _plan_amount(plan)
    if amount_rupees <= 0:
        raise HTTPException(status_code=400, detail="This plan has no payable amount.")

    import requests as req_lib
    receipt = f"signup_{data.plan_key}_{int(time.time())}"
    response = req_lib.post(
        "https://api.razorpay.com/v1/orders",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={
            "amount": amount_rupees * 100,
            "currency": "INR",
            "receipt": receipt,
            "notes": {"email": data.email, "plan_key": data.plan_key},
        },
        timeout=20,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Payment gateway could not create an order.")

    order = response.json()
    return {
        "success": True,
        "order_id": order["id"],
        "amount": amount_rupees,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "plan": {"key": plan["key"], "label": plan.get("label"), "billing_label": plan.get("billing_label")},
    }


@router.post("/complete-signup")
def complete_signup(data: CompleteSignupRequest):
    """
    Verify Razorpay payment and create a new user account with plan active.

    Called after the user completes Razorpay checkout. On success:
    - Verifies the payment signature
    - Creates a Supabase auth account via invite (sends email verification)
    - Creates the role-specific profile with the paid plan already activated
    - For parents: creates a family record
    - For students: stores grade; linked to a family later by admin/parent
    - For teachers: stores school name; account_status = active

    The user must verify their email before they can log in.
    """
    from app.services.auth_service import invite_parent_by_email, create_auth_user

    role = data.role.lower().strip()
    if role not in VALID_SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    if not _razorpay_is_configured():
        raise HTTPException(status_code=503, detail="Payment not configured.")

    if not _verify_signature(data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed. Please contact support.")

    plan = _get_plan(data.plan_key)
    access = _profile_access_fields(plan)

    # Check if email is already registered
    existing = (
        admin_client
        .table("profiles")
        .select("id")
        .eq("email", data.email.strip().lower())
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")

    # Create Supabase auth user via invite — sends email verification automatically.
    # All roles use the invite flow so email verification is enforced.
    auth_user = invite_parent_by_email(
        email=data.email.strip().lower(),
        username=data.name.strip(),
    )

    base_profile = {
        "id": auth_user.id,
        "email": data.email.strip().lower(),
        "username": data.name.strip(),
        "role": role,
        "parent_id": None,
        "family_id": None,
        **access,
    }

    if role == "parent":
        family_resp = (
            admin_client
            .table("families")
            .insert({"family_name": f"{data.name.strip()}'s Family"})
            .execute()
        )
        if family_resp.data:
            base_profile["family_id"] = family_resp.data[0]["id"]

    elif role == "student":
        grade = data.grade or "Grade 9"
        if grade not in VALID_GRADES:
            grade = "Grade 9"
        base_profile["grade"] = grade
        base_profile["board"] = "CBSE"
        base_profile["cbse_subjects"] = []
        base_profile["ai_model_preference"] = "default"

    elif role == "teacher":
        if data.school:
            base_profile["school_name"] = data.school.strip()

    (
        admin_client
        .table("profiles")
        .insert(base_profile)
        .execute()
    )

    # Log the payment so admins can trace signup payments
    (
        admin_client
        .table("subscription_payments")
        .upsert({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "parent_id": auth_user.id,
            "child_id": auth_user.id,
            "plan_key": plan["key"],
            "amount": _plan_amount(plan),
            "currency": "INR",
            "status": "paid",
            "provider": "razorpay",
            "metadata": {"signup_role": role, "signup_email": data.email},
        }, on_conflict="razorpay_order_id")
        .execute()
    )

    return {
        "success": True,
        "message": (
            "Account created and payment confirmed. "
            "Please check your email to verify your account before signing in."
        ),
        "role": role,
    }
