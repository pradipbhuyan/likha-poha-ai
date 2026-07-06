import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.schemas import LoginRequest, LoginResponse
from app.config import settings
from app.services.auth_service import admin_client, get_current_user
from app.services.rate_limit_service import (
    rate_limit_dependency,
    LOGIN_LIMITER,
    SIGNUP_LIMITER,
    PASSWORD_RESET_LIMITER,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants — defined here so /me and /oauth/complete-profile can use them
# ---------------------------------------------------------------------------

VALID_SIGNUP_ROLES = {"parent", "student", "teacher"}
# All grades the backend accepts — includes Grade 11/12 which are hidden from
# students until admin enables them in the Product Catalogue page.
from app.data.product_catalogue import ALL_GRADES_INCLUDING_HIDDEN  # noqa: E402
VALID_GRADES = set(ALL_GRADES_INCLUDING_HIDDEN)


# ---------------------------------------------------------------------------
# ── Reporter access helper ────────────────────────────────────────────────────
def _check_can_report_issues(user_id: str) -> bool:
    """Check if user is in the issue_reporters admin_settings list. No migration needed."""
    try:
        from .issues import _get_reporter_ids  # noqa: PLC0415
        return user_id in _get_reporter_ids()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers shared by /me and /oauth/complete-profile
# ---------------------------------------------------------------------------

def _build_me_response(auth_user, profile: dict, needs_role_selection: bool = False) -> dict:
    """
    Build the canonical /me response from an auth user + profile row.

    This is the single source of truth for what the frontend receives after
    every OAuth callback.  It mirrors the /profile endpoint fields but also
    includes the OAuth-onboarding flags.
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    expires_at_str = profile.get("subscription_expires_at")
    days_remaining = None
    expiring_soon = False
    if expires_at_str:
        try:
            exp = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if now > exp:
                days_remaining = 0
            else:
                days_remaining = max(0, (exp - now).days)
            expiring_soon = days_remaining is not None and days_remaining <= 3
        except Exception:
            pass

    return {
        "authenticated": True,
        "profile_complete": not needs_role_selection,
        "needs_role_selection": needs_role_selection,
        "id": profile.get("id"),
        "email": profile.get("email"),
        "username": profile.get("username"),
        "role": profile.get("role"),
        "grade": profile.get("grade"),
        "board": profile.get("board"),
        "parent_id": profile.get("parent_id"),
        "family_id": profile.get("family_id"),
        "subscription_plan": profile.get("subscription_plan") or "free",
        "account_status": profile.get("account_status") or "active",
        "access_cbse": bool(profile.get("access_cbse")),
        "access_sof_science": bool(profile.get("access_sof_science")),
        "access_sof_maths": bool(profile.get("access_sof_maths")),
        "access_sof_english": bool(profile.get("access_sof_english")),
        "cbse_subjects": profile.get("cbse_subjects") or [],
        "daily_token_limit": profile.get("daily_token_limit"),
        "monthly_token_limit": profile.get("monthly_token_limit"),
        "subscription_expires_at": expires_at_str,
        "subscription_days_remaining": days_remaining,
        "subscription_expiring_soon": expiring_soon,
        "avatar": profile.get("avatar") or "",
        "can_report_issues": _check_can_report_issues(profile.get("id") or ""),
    }

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
def login(data: LoginRequest, _rl=Depends(rate_limit_dependency(LOGIN_LIMITER))):
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


@router.post("/forgot-password")
def forgot_password(payload: dict, _rl=Depends(rate_limit_dependency(PASSWORD_RESET_LIMITER))):
    """
    Send a password reset email for a student.

    If the student has a parent_id, the reset link is also sent to the
    parent's email so they can help the child reset without needing to
    access the child's inbox.

    Payload: { "username": "likha1" }
    Silently succeeds even if the username is not found (security best practice).
    """
    from app.services.supabase_client import supabase as anon_client  # noqa: PLC0415

    username = (payload.get("username") or "").strip().lower()
    if not username:
        return {"success": True, "message": "If this account exists, a reset link was sent."}

    # Resolve the profile
    profile_result = (
        admin_client
        .table("profiles")
        .select("id, email, role, parent_id")
        .ilike("username", username)
        .limit(1)
        .execute()
    )
    if not profile_result.data:
        return {"success": True, "message": "If this account exists, a reset link was sent."}

    profile = profile_result.data[0]
    emails_to_notify = []

    # Always send to the user's own email
    if profile.get("email"):
        emails_to_notify.append(profile["email"])

    # For students, also send to the parent's email
    if profile.get("parent_id"):
        parent_result = (
            admin_client
            .table("profiles")
            .select("email")
            .eq("id", profile["parent_id"])
            .limit(1)
            .execute()
        )
        if parent_result.data and parent_result.data[0].get("email"):
            parent_email = parent_result.data[0]["email"]
            if parent_email not in emails_to_notify:
                emails_to_notify.append(parent_email)

    # Send reset emails (non-fatal — never block on email failure)
    sent_to = []
    for email in emails_to_notify:
        try:
            anon_client.auth.reset_password_for_email(
                email,
                options={"redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"},
            )
            sent_to.append(email)
        except Exception:
            pass

    # Also try Supabase admin link for the student's own email
    try:
        admin_client.auth.admin.generate_link({
            "type": "recovery",
            "email": profile["email"],
            "options": {"redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"},
        })
    except Exception:
        pass

    return {
        "success": True,
        "message": "If this account exists, a reset link was sent.",
        "sent_to_count": len(sent_to),
    }


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
# GET /me — canonical auth state endpoint used by OAuth callback
# ---------------------------------------------------------------------------

@router.get("/me")
def get_me(
    user=Depends(get_current_user),
    x_oauth_correlation_id: str = None,
):
    """
    Return the authenticated user's canonical profile + OAuth-onboarding flags.
    Accepts X-OAuth-Correlation-ID header for cross-device OAuth tracing.

    Returns:
      - profile_complete=True, needs_role_selection=False  → route to dashboard
      - profile_complete=False, needs_role_selection=True  → show role picker
      - authenticated=True with no profile row              → role picker (trigger disabled)

    This endpoint never returns 404 for authenticated users without profiles.
    That state is communicated via needs_role_selection=True so the frontend can
    show the role picker instead of interpreting it as a session error.

    Error mapping contract (for frontend):
      401 → session expired / invalid token
      403 → access denied (role mismatch) — NOT session expired
    """
    # Log correlation ID for OAuth tracing (never logs bearer token)
    corr = (x_oauth_correlation_id or "").strip()[:64] or None
    if corr:
        logging.info(
            "[auth.me.started] user_id=%s correlation_id=%s",
            user.id, corr,
        )

    profile_resp = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )

    if not profile_resp.data:
        logging.info(
            "[auth.me.profile_missing] user_id=%s correlation_id=%s",
            user.id, corr,
        )
        # Auth user exists but no profile row yet — new OAuth user whose
        # trigger did not fire (e.g. trigger was disabled).
        # Return 200 with needs_role_selection=True so the frontend shows the
        # role picker rather than treating this as an error / session expiry.
        meta = getattr(user, "user_metadata", {}) or {}
        return {
            "authenticated": True,
            "profile_complete": False,
            "needs_role_selection": True,
            "id": user.id,
            "email": user.email,
            "username": meta.get("full_name") or meta.get("name") or "",
            "avatar": meta.get("avatar_url") or "",
            "role": None,
        }

    profile = profile_resp.data[0]

    # oauth_profile_complete defaults to True for all existing email-signup users
    # (added by migration with DEFAULT TRUE).
    oauth_complete = profile.get("oauth_profile_complete")
    if oauth_complete is None:
        oauth_complete = True  # legacy row before migration — treat as complete
    needs_role_selection = not oauth_complete

    logging.info(
        "[auth.me.profile_complete] user_id=%s role=%s profile_complete=%s correlation_id=%s",
        user.id, profile.get("role"), not needs_role_selection, corr,
    )

    return _build_me_response(user, profile, needs_role_selection=needs_role_selection)


# ---------------------------------------------------------------------------
# POST /oauth/complete-profile — secure, idempotent OAuth role assignment
# ---------------------------------------------------------------------------

class OAuthCompleteProfileRequest(BaseModel):
    """Request body for completing an OAuth user's profile with their chosen role."""
    role: str
    full_name: Optional[str] = None
    grade: Optional[str] = None   # for students


@router.post("/oauth/complete-profile")
def oauth_complete_profile(
    data: OAuthCompleteProfileRequest,
    user=Depends(get_current_user),
):
    """
    Complete an OAuth user's profile by assigning their chosen platform role.

    Business rules enforced here (backend is authoritative):
    - Only valid roles: parent | student | teacher
    - If profile already has an explicitly confirmed role:
        same role  → idempotent success (safe to call multiple times)
        diff role  → 409 role_conflict (block silently; show friendly error)
    - If profile exists but role not yet confirmed (oauth_profile_complete=False):
        → update role + mark complete
    - If no profile row at all (trigger disabled):
        → create full FREE_TIER profile with selected role
    - NEVER grants paid access.
    - NEVER changes an already-confirmed role.
    - Creates family record for parent role.
    - All access flags start as False (Free Tier).
    - Emits audit event when available.

    Error mapping contract:
      400 → invalid role
      401 → bad/expired token
      409 → role conflict (existing confirmed role differs from requested)
    """
    role = (data.role or "").lower().strip()
    if role not in VALID_SIGNUP_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Must be one of: parent, student, teacher.",
        )

    # ── 1. Look up existing profile by auth user id (primary) ────────────────
    profile_resp = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )

    # ── 2. Fallback: look up by email (legacy rows created before id-based insert) ─
    if not profile_resp.data and user.email:
        profile_resp = (
            admin_client
            .table("profiles")
            .select("*")
            .eq("email", user.email.lower())
            .limit(1)
            .execute()
        )
        if profile_resp.data:
            logging.warning(
                "[oauth] Profile found by email fallback for user_id=%s email=%s — "
                "id mismatch; treating as legacy row.",
                user.id,
                user.email,
            )

    existing = profile_resp.data[0] if profile_resp.data else None

    if existing:
        oauth_complete = existing.get("oauth_profile_complete")
        if oauth_complete is None:
            oauth_complete = True  # legacy row before migration

        if oauth_complete:
            # ── State A / D: profile role already confirmed ──────────────────
            existing_role = (existing.get("role") or "").lower()
            if existing_role == role:
                # State A: same role — idempotent, return existing profile
                logging.info(
                    "[oauth] Idempotent complete-profile for user=%s role=%s",
                    user.id, role,
                )
                return _build_me_response(user, existing, needs_role_selection=False)
            else:
                # State D: role conflict — block and return 409
                logging.warning(
                    "[oauth] Role conflict for user=%s existing=%s requested=%s",
                    user.id, existing_role, role,
                )
                try:
                    admin_client.table("platform_audit_logs").insert({
                        "user_id": user.id,
                        "event": "auth.oauth_role_conflict",
                        "metadata": {
                            "existing_role": existing_role,
                            "requested_role": role,
                            "email": user.email,
                        },
                    }).execute()
                except Exception:
                    pass
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"This Google account is already registered as a "
                        f"{existing_role.title()}. "
                        f"Please continue as {existing_role.title()} or use "
                        f"a different Google account."
                    ),
                )

        else:
            # ── State B/C: placeholder profile from trigger — set role ────────
            display_name = (
                (data.full_name or "").strip()
                or existing.get("username")
                or (user.email.split("@")[0] if user.email else "User")
            )

            updates: dict = {
                "role": role,
                "oauth_profile_complete": True,
                "username": display_name,
                "account_status": "active",
                # Free Tier — no token quota, no CBSE access
                "access_cbse": False,
                "access_sof_science": False,
                "access_sof_maths": False,
                "access_sof_english": False,
                "subscription_plan": "free",
                "subscription_expires_at": None,
            }

            if role == "parent":
                # Ensure a family exists for the parent
                family_id = existing.get("family_id")
                if not family_id:
                    fam = (
                        admin_client
                        .table("families")
                        .insert({"family_name": f"{display_name}'s Family"})
                        .execute()
                    )
                    if fam.data:
                        updates["family_id"] = fam.data[0]["id"]
                updates["daily_token_limit"] = 0
                updates["monthly_token_limit"] = 0

            elif role == "student":
                grade = data.grade or existing.get("grade") or "Grade 9"
                if grade not in VALID_GRADES:
                    grade = "Grade 9"
                updates["grade"] = grade
                updates["board"] = "CBSE"
                updates["cbse_subjects"] = []
                updates["daily_token_limit"] = 0
                updates["monthly_token_limit"] = 0

            elif role == "teacher":
                updates["daily_token_limit"] = 0
                updates["monthly_token_limit"] = 0

            admin_client.table("profiles").update(updates).eq("id", existing["id"]).execute()

            # Fetch the freshly-updated profile
            fresh_resp = (
                admin_client
                .table("profiles")
                .select("*")
                .eq("id", existing["id"])
                .single()
                .execute()
            )

            try:
                admin_client.table("platform_audit_logs").insert({
                    "user_id": user.id,
                    "event": "auth.oauth_profile_completed",
                    "metadata": {"role": role, "email": user.email},
                }).execute()
            except Exception:
                pass

            # Welcome email — first time this Google user completes role selection
            try:
                from app.services.email_service import send_welcome_email  # noqa: PLC0415
                send_welcome_email(
                    to=user.email or "",
                    name=display_name,
                    role=role,
                    is_paid=False,
                    plan_name="",
                )
            except Exception:
                pass  # Email send must never block signup

            return _build_me_response(user, fresh_resp.data, needs_role_selection=False)

    else:
        # ── State B (no trigger): no profile row at all — create from scratch ─
        display_name = (
            (data.full_name or "").strip()
            or (user.email.split("@")[0] if user.email else "User")
        )

        # Duplicate guard: check email again (another request may have created it)
        dup_check = (
            admin_client
            .table("profiles")
            .select("id, role, oauth_profile_complete")
            .eq("email", (user.email or "").lower())
            .limit(1)
            .execute()
        )
        if dup_check.data:
            dup = dup_check.data[0]
            existing_role = (dup.get("role") or "").lower()
            if dup.get("oauth_profile_complete") and existing_role and existing_role != role:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"This Google account is already registered as a "
                        f"{existing_role.title()}. "
                        f"Please continue as {existing_role.title()} or use "
                        f"a different Google account."
                    ),
                )
            # Race condition: profile just created — re-fetch and return
            full_resp = admin_client.table("profiles").select("*").eq("id", dup["id"]).single().execute()
            return _build_me_response(user, full_resp.data, needs_role_selection=False)

        base_profile: dict = {
            "id": user.id,
            "email": (user.email or "").lower(),
            "username": display_name,
            "role": role,
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": True,
        }

        if role == "parent":
            fam = (
                admin_client
                .table("families")
                .insert({"family_name": f"{display_name}'s Family"})
                .execute()
            )
            if fam.data:
                base_profile["family_id"] = fam.data[0]["id"]

        elif role == "student":
            grade = data.grade or "Grade 9"
            if grade not in VALID_GRADES:
                grade = "Grade 9"
            base_profile["grade"] = grade
            base_profile["board"] = "CBSE"
            base_profile["cbse_subjects"] = []

        admin_client.table("profiles").insert(base_profile).execute()

        # Fetch freshly-created profile — fall back to base_profile if SELECT returns None
        # (can happen in test environments where the fake insert doesn't populate the table)
        created_resp = (
            admin_client
            .table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )
        final_profile = created_resp.data if created_resp.data else base_profile

        try:
            admin_client.table("platform_audit_logs").insert({
                "user_id": user.id,
                "event": "auth.oauth_profile_created",
                "metadata": {"role": role, "email": user.email},
            }).execute()
        except Exception:
            pass

        # Welcome email — new Google OAuth user, profile created from scratch
        try:
            from app.services.email_service import send_welcome_email  # noqa: PLC0415
            send_welcome_email(
                to=(user.email or ""),
                name=display_name,
                role=role,
                is_paid=False,
                plan_name="",
            )
        except Exception:
            pass  # Email send must never block signup

        return _build_me_response(user, final_profile, needs_role_selection=False)


# ---------------------------------------------------------------------------
# Public signup-with-payment endpoints
# ---------------------------------------------------------------------------


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


class OfferCodeSignupRequest(BaseModel):
    """Request body for creating an account using an offer code (no payment)."""
    role: str
    name: str
    email: str
    offer_code: str  # 8-char alphanumeric
    grade: Optional[str] = None   # for students
    school: Optional[str] = None  # for teachers
    password: Optional[str] = None  # when provided, skips email verification and enables direct login


class FreeSignupRequest(BaseModel):
    """Request body for creating a Free Tier account — no payment or offer code required."""
    role: str
    name: str
    email: str
    grade: Optional[str] = None    # for students
    school: Optional[str] = None   # for teachers
    password: Optional[str] = None # when provided, enables direct login without email verification


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
    """
    Load a subscription plan for signup.

    First checks the merged default+DB plan settings. If the plan key is
    not in the defaults (e.g. admin test plans like test_1rupee), falls back
    to a direct Supabase lookup so recently-created plans are found immediately.
    """
    from app.routes.admin_control import list_subscription_plan_settings, normalize_subscription_plan_row  # noqa: PLC0415
    payload = list_subscription_plan_settings()
    plan = (payload.get("plans") or {}).get(plan_key)

    # Fallback: plan not in defaults — look up directly in subscription_plan_settings table
    if not plan:
        try:
            db_result = admin_client.table("subscription_plan_settings").select("*").eq("key", plan_key).limit(1).execute()
            if db_result.data:
                plan = normalize_subscription_plan_row(db_result.data[0])
        except Exception:
            pass

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
    """Convert plan row into profile access fields (including subscription expiry)."""
    from app.routes.payments import plan_expires_at  # noqa: PLC0415
    return {
        "subscription_plan": plan["key"],
        "account_status": "active",
        "access_cbse": bool(plan.get("access_cbse")),
        "access_sof_science": bool(plan.get("access_sof_science")),
        "access_sof_maths": bool(plan.get("access_sof_maths")),
        "access_sof_english": bool(plan.get("access_sof_english")),
        "daily_token_limit": int(plan.get("daily_token_limit") or 50000),
        "monthly_token_limit": int(plan.get("monthly_token_limit") or 1000000),
        "subscription_expires_at": plan_expires_at(plan),
    }


# Authenticated profile endpoint — returns full profile + subscription status
# ---------------------------------------------------------------------------

@router.get("/profile")
def get_my_profile(user=Depends(get_current_user)):
    """
    Return the authenticated user's full profile including subscription_expires_at.

    Also auto-revokes access for expired time-limited plans (e.g. ₹99 / 8-day
    Premium Nano) so the student is reverted to the free tier on next login.
    Called by the frontend on app load to get fresh access state.
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    profile_resp = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = profile_resp.data[0]

    # ── Auto-revoke expired time-limited subscriptions ───────────────────────
    # If subscription_expires_at is set and is in the past, revoke CBSE/SOF
    # access flags so the student hits the subscription gate again.
    expires_at_str = profile.get("subscription_expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_at:
                # Subscription expired — revoke access flags
                admin_client.table("profiles").update({
                    "access_cbse": False,
                    "access_sof_science": False,
                    "access_sof_maths": False,
                    "access_sof_english": False,
                    "subscription_expires_at": None,  # clear so it doesn't trigger again
                }).eq("id", user.id).execute()
                # Update local profile dict to reflect revoked state
                profile["access_cbse"] = False
                profile["access_sof_science"] = False
                profile["access_sof_maths"] = False
                profile["access_sof_english"] = False
                profile["subscription_expires_at"] = None
        except Exception:
            pass  # Never block profile load on expiry check failure

    # Calculate days_remaining for the frontend expiry banner
    sub_expires_at = profile.get("subscription_expires_at")
    days_remaining = None
    expiring_soon = False
    if sub_expires_at:
        try:
            exp = datetime.fromisoformat(sub_expires_at.replace("Z", "+00:00"))
            days_remaining = max(0, (exp - datetime.now(timezone.utc)).days)
            expiring_soon = days_remaining <= 3
        except Exception:
            pass

    return {
        "success": True,
        "can_report_issues": _check_can_report_issues(user.id),
        "id": profile.get("id"),
        "email": profile.get("email"),
        "username": profile.get("username"),
        "role": profile.get("role"),
        "grade": profile.get("grade"),
        "board": profile.get("board"),
        "subscription_plan": profile.get("subscription_plan"),
        "access_cbse": bool(profile.get("access_cbse")),
        "access_sof_science": bool(profile.get("access_sof_science")),
        "access_sof_maths": bool(profile.get("access_sof_maths")),
        "access_sof_english": bool(profile.get("access_sof_english")),
        "cbse_subjects": profile.get("cbse_subjects") or [],
        "daily_token_limit": profile.get("daily_token_limit"),
        "monthly_token_limit": profile.get("monthly_token_limit"),
        "account_status": profile.get("account_status"),
        "subscription_expires_at": sub_expires_at,
        "subscription_days_remaining": days_remaining,
        "subscription_expiring_soon": expiring_soon,
    }


@router.post("/signup-order")
def create_signup_order(data: SignupOrderRequest, _rl=Depends(rate_limit_dependency(SIGNUP_LIMITER))):
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

    # ── Email duplicate check BEFORE taking any money ────────────────────
    # If the email already exists we must stop here — never open the payment
    # dialog. The customer should see a clear message to log in instead.
    existing = (
        admin_client
        .table("profiles")
        .select("id")
        .eq("email", data.email.strip().lower())
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email already exists. "
                "Please log in instead. "
                "If you've forgotten your password, use Forgot Password on the login page."
            ),
        )
    # ─────────────────────────────────────────────────────────────────────

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

    # Create auth user with email_confirm=True so the account is immediately active.
    # Then send a reset_password_for_email so the user gets a "Set your password" email
    # and can log in right after clicking the link — no separate invite flow needed.
    import secrets as _secrets  # noqa: PLC0415
    from app.services.supabase_client import supabase as anon_client  # noqa: PLC0415
    temp_password = _secrets.token_urlsafe(24)
    auth_user = create_auth_user(
        email=data.email.strip().lower(),
        password=temp_password,
        email_confirm=True,   # account immediately active
    )
    # Send the "set your password" email — user clicks the link → ResetPasswordPage → logs in
    email_sent = False
    email_error = None
    recovery_link = None
    try:
        anon_client.auth.reset_password_for_email(
            data.email.strip().lower(),
            options={"redirect_to": "https://likhapoha.in"},
        )
        email_sent = True
    except Exception as exc:
        email_error = str(exc)
        logging.warning(
            "reset_password_for_email failed for %s: %s — trying generate_link fallback",
            data.email.strip().lower(),
            email_error,
        )
        # Fallback: generate recovery link via admin API (no email quota used).
        # Useful when the anon-key reset is rate-limited or mis-configured.
        try:
            link_resp = admin_client.auth.admin.generate_link({
                "type": "recovery",
                "email": data.email.strip().lower(),
                "options": {"redirect_to": "https://likhapoha.in"},
            })
            recovery_link = getattr(link_resp, "properties", {}) or {}
            recovery_link = (
                recovery_link.get("action_link")
                or getattr(link_resp, "action_link", None)
            )
        except Exception as link_exc:
            logging.warning("generate_link fallback also failed: %s", link_exc)

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

    # Log the payment so admins can trace signup payments (non-critical — never blocks signup)
    try:
        admin_client.table("subscription_payments").upsert({
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
        }, on_conflict="razorpay_order_id").execute()
    except Exception:
        pass  # Table may not exist yet — run sql/subscription_payments.sql in Supabase

    # Auto-match sales lead claim (never blocks signup if it fails)
    try:
        from app.routes.sales import auto_match_lead_claim  # noqa: PLC0415
        auto_match_lead_claim(
            email=data.email.strip().lower(),
            student_id=auth_user.id,
            package_amount=_plan_amount(plan),
            package_key=plan["key"],
        )
    except Exception:
        pass

    # Welcome email — paid signup
    try:
        from app.services.email_service import send_welcome_email  # noqa: PLC0415
        from app.routes.payments import _paid_plan_name  # noqa: PLC0415 (reuse helper)
        _pn = _paid_plan_name(plan.get("key", "free"))
        send_welcome_email(
            to=data.email.strip().lower(),
            name=data.name.strip(),
            role=role,
            is_paid=True,
            plan_name=_pn,
        )
    except Exception:
        pass  # Email send must never block signup

    return {
        "success": True,
        "message": (
            "Account created and payment confirmed. "
            "Please check your email to verify your account before signing in."
        ),
        "role": role,
        "email_sent": email_sent,
        "email_error": email_error,
        "recovery_link": recovery_link,  # non-None only when reset email failed + admin fallback worked
    }


@router.post("/signup-free")
def signup_free(data: FreeSignupRequest, _rl=Depends(rate_limit_dependency(SIGNUP_LIMITER))):
    """
    Create a new Free Tier account — no payment or offer code required.

    Any user can call this endpoint to create an account and immediately
    access the platform at the Free Tier (limited access):
      - subscription_plan = "free"
      - access_cbse = False  (triggers DKB-only gate in lesson/doubt routes)
      - account_status = "active"

    Users can upgrade to a paid plan (Nano/Premium/Family) at any time through
    the payment flow.  Offer codes remain available as an optional upgrade path.

    If a password is provided, the user can log in immediately without
    email verification.  Otherwise a set-password email is sent.
    """
    from app.services.auth_service import create_auth_user  # noqa: PLC0415

    role = (data.role or "").lower().strip()
    if role not in VALID_SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    email_clean = (data.email or "").strip().lower()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required.")
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Name is required.")

    # Prevent duplicate accounts
    existing = (
        admin_client
        .table("profiles")
        .select("id")
        .eq("email", email_clean)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email already exists. "
                "Please log in instead."
            ),
        )

    # Create auth user — use provided password or generate a temp one
    import secrets as _secrets  # noqa: PLC0415
    from app.services.supabase_client import supabase as anon_client  # noqa: PLC0415

    user_password = (data.password.strip() if data.password and data.password.strip() else None)
    temp_password = user_password or _secrets.token_urlsafe(16)

    auth_user = create_auth_user(
        email=email_clean,
        password=temp_password,
        email_confirm=True,  # account immediately active
    )

    # Build Free Tier profile — no access flags, no expiry
    base_profile = {
        "id": auth_user.id,
        "email": email_clean,
        "username": data.name.strip(),
        "role": role,
        "parent_id": None,
        "family_id": None,
        "subscription_plan": "free",
        "account_status": "active",
        "access_cbse": False,        # Free Tier: DKB-only access
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 0,
        "monthly_token_limit": 0,
        # subscription_expires_at intentionally absent — free tier has no expiry
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

    admin_client.table("profiles").insert(base_profile).execute()

    # If no password provided, send a set-password email
    password_set_link = None
    if not user_password:
        try:
            link_response = admin_client.auth.admin.generate_link(
                {
                    "type": "recovery",
                    "email": email_clean,
                    "options": {
                        "redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"
                    },
                }
            )
            password_set_link = getattr(link_response, "properties", {})
            if hasattr(password_set_link, "action_link"):
                password_set_link = password_set_link.action_link
            elif isinstance(password_set_link, dict):
                password_set_link = password_set_link.get("action_link")
            else:
                password_set_link = None
        except Exception:
            pass

        try:
            anon_client.auth.reset_password_for_email(
                email_clean,
                options={"redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"},
            )
        except Exception:
            pass

    # Welcome email — free tier signup
    try:
        from app.services.email_service import send_welcome_email  # noqa: PLC0415
        send_welcome_email(
            to=email_clean,
            name=data.name.strip(),
            role=role,
            is_paid=False,
            plan_name="",
        )
    except Exception:
        pass  # Email send must never block signup

    return {
        "success": True,
        "message": (
            "Free account created! "
            + ("Log in with your password to start learning." if user_password
               else "Check your email to set your password, then log in.")
        ),
        "role": role,
        "tier": "free",
        "password_set_link": password_set_link,
    }


@router.get("/test-email")
def test_email(user=Depends(get_current_user)):
    """
    Admin-only: send a test welcome email to the caller's address.
    Call from live backend to verify email config on Railway.
    GET /api/auth/test-email  (requires auth token)
    """
    import os as _os  # noqa: PLC0415
    from app.services.email_service import _send, _get_smtp_config  # noqa: PLC0415

    resend_key = _os.getenv("RESEND_API_KEY", "").strip()
    resend_from = _os.getenv("EMAIL_FROM_ADDRESS", "").strip()
    smtp_cfg = _get_smtp_config()

    # Diagnostics — which channels are configured
    channels = {
        "resend": bool(resend_key and resend_from),
        "smtp": bool(smtp_cfg),
    }

    if not any(channels.values()):
        return {
            "success": False,
            "channels_configured": channels,
            "error": (
                "No email channel configured. "
                "Set RESEND_API_KEY + EMAIL_FROM_ADDRESS (recommended), "
                "or ALERT_SMTP_USER + ALERT_SMTP_PASSWORD in Railway env vars."
            ),
        }

    profile_resp = (
        admin_client.table("profiles").select("email, username, role")
        .eq("id", user.id).limit(1).execute()
    )
    profile = (profile_resp.data or [{}])[0]
    to_email = profile.get("email") or user.email or ""

    result = _send(
        to=to_email,
        subject="[Test] Likha Poha AI email is working ✓",
        html=(
            "<h2>✓ Email delivery confirmed</h2>"
            "<p>This test email was sent from the Railway backend.</p>"
            "<p>If you see this, welcome emails are working correctly.</p>"
        ),
        text="Email delivery confirmed from Railway backend. Email is working.",
    )

    return {
        "success": result,
        "to": to_email,
        "channels_configured": channels,
        "channel_used": "resend" if channels["resend"] else "smtp",
        "resend_from": resend_from if channels["resend"] else None,
        "smtp_user": smtp_cfg["user"] if smtp_cfg else None,
        "error": None if result else "Send failed — check Railway logs for email_service.failed or email_service.resend_failed",
    }


@router.post("/signup-with-offer-code")
def signup_with_offer_code(data: OfferCodeSignupRequest, _rl=Depends(rate_limit_dependency(SIGNUP_LIMITER))):
    """
    Create a new account using a valid offer code instead of paying.

    Flow:
    1. Validate offer code (active, within validity window, max_uses not exceeded)
    2. Check email not already registered
    3. Create Supabase auth account via invite (sends email verification)
    4. Create role-specific profile with free-plan access (offer grants time-limited access)
    5. Record offer redemption so student gains platform access on login
    6. Increment offer code usage counter

    The user must verify their email before they can log in (same as paid signup).
    """
    from app.services.auth_service import invite_parent_by_email
    from datetime import datetime, timezone

    role = (data.role or "").lower().strip()
    if role not in VALID_SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    code = (data.offer_code or "").strip().upper()
    if len(code) != 8:
        raise HTTPException(status_code=400, detail="Offer code must be exactly 8 characters.")

    # 1. Validate offer code
    code_result = (
        admin_client
        .table("offer_codes")
        .select("*")
        .eq("code", code)
        .limit(1)
        .execute()
    )
    if not code_result.data:
        raise HTTPException(status_code=404, detail="Invalid offer code.")

    offer = code_result.data[0]

    if not offer.get("is_active"):
        raise HTTPException(status_code=400, detail="This offer code is no longer active.")

    now = datetime.now(timezone.utc)
    try:
        valid_until = datetime.fromisoformat(
            (offer.get("valid_until") or "").replace("Z", "+00:00")
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Offer code has an invalid expiry date.")

    if now > valid_until:
        raise HTTPException(status_code=400, detail="This offer code has expired.")

    uses_count = int(offer.get("uses_count") or 0)
    max_uses = int(offer.get("max_uses") or 100)
    if uses_count >= max_uses:
        raise HTTPException(status_code=400, detail="This offer code has reached its maximum number of uses.")

    # 2. Check email not already registered
    email_clean = (data.email or "").strip().lower()
    existing = (
        admin_client
        .table("profiles")
        .select("id")
        .eq("email", email_clean)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")

    # 3. Create auth user with a temp password and email_confirm=True
    # (account is immediately active). Then trigger a password-reset email
    # so the user can set their own password.
    #
    # We use this instead of invite_user_by_email() because that API
    # validates email domains strictly and rejects many valid addresses
    # (e.g. mail.com, gmail.com aliases, etc).
    from app.services.auth_service import create_auth_user  # noqa: PLC0415
    import secrets  # noqa: PLC0415
    # Use provided password for direct-login flow; otherwise generate a temp one
    # that the user will replace via the set-password email link.
    user_password = (data.password.strip() if data.password and data.password.strip() else None)
    temp_password = user_password or secrets.token_urlsafe(16)
    auth_user = create_auth_user(
        email=email_clean,
        password=temp_password,
        email_confirm=True,  # immediately active
    )

    # When a password was provided (direct-login flow), skip email entirely.
    # When no password, generate a set-password link and send reset email.
    password_set_link = None
    if not user_password:
        try:
            link_response = admin_client.auth.admin.generate_link(
                {
                    "type": "recovery",
                    "email": email_clean,
                    "options": {
                        "redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"
                    },
                }
            )
            password_set_link = getattr(link_response, "properties", {})
            if hasattr(password_set_link, "action_link"):
                password_set_link = password_set_link.action_link
            elif isinstance(password_set_link, dict):
                password_set_link = password_set_link.get("action_link") or password_set_link.get("hashed_token")
            else:
                password_set_link = None
        except Exception:
            pass  # Link generation failure must not block account creation

        # Also try email as backup (may not arrive if SMTP is not configured)
        try:
            from app.services.supabase_client import supabase as anon_client  # noqa: PLC0415
            anon_client.auth.reset_password_for_email(
                email_clean,
                options={"redirect_to": f"{settings.FRONTEND_URL or 'https://likhapoha.in'}/reset-password"},
            )
        except Exception:
            pass  # Email send failure must not block account creation

    # 4. Create profile.
    # free_trial codes → access_cbse=False so the DKB-only offer gate activates.
    # discount codes → access_cbse=True because the user has PAID (at a discount);
    #   no LLM restrictions apply, full platform access granted immediately.
    is_discount_code = offer.get("code_type") == "discount"
    base_profile = {
        "id": auth_user.id,
        "email": email_clean,
        "username": data.name.strip(),
        "role": role,
        "parent_id": None,
        "family_id": None,
        "subscription_plan": "free",
        "account_status": "active",
        "access_cbse": is_discount_code,   # True for discount, False for free_trial
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 50000,
        "monthly_token_limit": 1000000,
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

    admin_client.table("profiles").insert(base_profile).execute()

    # 5. Record offer redemption (gives time-limited access after email verification)
    try:
        admin_client.table("offer_redemptions").insert({
            "code_id": offer["id"],
            "user_id": auth_user.id,
            "valid_until": offer["valid_until"],
        }).execute()

        # 6. Increment uses_count
        admin_client.table("offer_codes").update({
            "uses_count": uses_count + 1,
        }).eq("id", offer["id"]).execute()
    except Exception:
        pass  # Don't fail signup if redemption recording fails

    # Welcome email — offer code signup
    try:
        from app.services.email_service import send_welcome_email  # noqa: PLC0415
        send_welcome_email(
            to=email_clean,
            name=data.name.strip(),
            role=role,
            is_paid=False,
            plan_name="Offer Access",
        )
    except Exception:
        pass  # Email send must never block signup

    return {
        "success": True,
        "message": (
            "Account created using offer code. "
            "Please check your email to set your password, then log in. "
            f"Your access is valid until {str(offer['valid_until'])[:10]}."
        ),
        "role": role,
        "offer_valid_until": offer["valid_until"],
        "password_set_link": password_set_link,  # direct link if email not available
    }
