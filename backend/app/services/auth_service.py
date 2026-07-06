import os

from dotenv import load_dotenv

from app.services.ssl_service import enable_system_truststore

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

enable_system_truststore()

load_dotenv()

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

admin_client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Validate the bearer token from the request and return the Supabase auth user.

    All protected routes depend on this function, so failures are deliberately
    normalized to HTTP 401 instead of leaking provider-specific auth errors.

    Retries up to 2 times on transient HTTP/2 connection drops (Render free tier
    occasionally terminates the connection pool mid-request, causing ConnectionTerminated
    or ReadError errors that are not auth failures).
    """
    import time as _time  # noqa: PLC0415

    token = credentials.credentials
    last_exc = None

    for attempt in range(3):
        try:
            response = admin_client.auth.get_user(token)

            if not response.user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token",
                )

            print("AUTH USER ID:", response.user.id)
            print("AUTH USER EMAIL:", response.user.email)

            return response.user

        except HTTPException:
            raise  # Auth failures are not retried

        except Exception as e:
            err_str = str(e).lower()
            # Retry only on transient network errors, not real auth failures
            is_transient = any(k in err_str for k in (
                "connectionterminated", "connection terminated",
                "read error", "errno 11", "resource temporarily unavailable",
                "reset by peer", "broken pipe", "connection reset",
            ))
            if is_transient and attempt < 2:
                last_exc = e
                print(f"AUTH ERROR (retry {attempt + 1}): {e}")
                _time.sleep(0.3 * (attempt + 1))
                continue
            print("AUTH ERROR:", str(e))
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

    # All retries exhausted — still a transient error, return 401
    print("AUTH ERROR (all retries failed):", str(last_exc))
    raise HTTPException(
        status_code=401,
        detail="Invalid or expired token",
    )

def get_user_profile(user_id: str):
    """
    Load the application profile row that belongs to an authenticated user id.

    Supabase auth confirms identity, while the profile row provides app-level
    role and family metadata used by route guards.
    """
    response = (
        admin_client
        .table("profiles")
        .select("id, email, username, role, parent_id, family_id, grade, stream, cbse_subjects")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data


def require_parent(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only users whose profile role is parent.

    Returns both the raw auth user and profile so parent routes can safely scope
    child/family lookups to the signed-in parent.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "parent":
        raise HTTPException(
            status_code=403,
            detail="Parent access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_student(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows student and child profile users.

    Children created by admins (role='child') are functionally students —
    they use the same lesson, quiz, and practice question features.
    Both 'student' and 'child' roles are accepted here.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") not in ("student", "child"):
        raise HTTPException(
            status_code=403,
            detail="Student access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_admin(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only admin profile users.

    Admin-only routes can mutate access, families, plans, and user records, so
    they must use this guard before touching service-role Supabase APIs.
    """
    profile = get_user_profile(user.id)

    print("ADMIN PROFILE:", profile)

    if not profile or profile.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_teacher(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only teacher profile users.

    Teacher accounts are created by admins, not public signup, and this guard
    scopes teacher dashboard endpoints to those admin-created profiles.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Teacher access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_sales(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only sales profile users.

    Sales accounts are admin-created and can only see their own onboarding and
    incentive data.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "sales":
        raise HTTPException(
            status_code=403,
            detail="Sales access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_admin_or_sales(user=Depends(get_current_user)):
    """
    FastAPI dependency for routes shared by admins and sales users.

    Admins receive the full sales dashboard; salespeople receive data scoped to
    their own profile id.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") not in {"admin", "sales"}:
        raise HTTPException(
            status_code=403,
            detail="Admin or sales access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }
    
def create_auth_user(email: str, password: str, email_confirm: bool = True):
    """
    Create a Supabase auth user using the service-role admin API.

    email_confirm=True  (default) — account is immediately active, no email
                                    sent. Use this for admin-created children,
                                    teachers, and in-person parent onboarding.

    email_confirm=False            — account is created but NOT confirmed; the
                                    user cannot log in. Use this only when you
                                    will immediately follow up with
                                    invite_parent_by_email() to send the real
                                    confirmation email via Supabase.

    NOTE: Supabase admin create_user with email_confirm=False does NOT send
    any email automatically. To send a real invite/confirmation email, use
    invite_parent_by_email() instead.
    """
    try:
        response = admin_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        })

        return response.user

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to create auth user: {str(e)}",
        )


def invite_parent_by_email(email: str, username: str) -> object:
    """
    Create a parent account and send a real invitation email via Supabase.

    Supabase's invite_user_by_email:
    - Creates the auth user in an unconfirmed state
    - Sends an invitation email with a confirmation link
    - The parent clicks the link to verify their email and set their password
    - The account cannot be used until the parent confirms

    This is the correct way to enforce email confirmation for parent signups.
    Use this for all parent-initiated invites and for admin-created parent
    accounts that should require email verification.
    """
    try:
        response = admin_client.auth.admin.invite_user_by_email(
            email,
            options={"data": {"username": username, "role": "parent"}},
        )

        return response.user

    except Exception as e:
        err_msg = str(e).lower()

        if "rate limit" in err_msg or "email_rate_limit" in err_msg or "over_email" in err_msg:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many invitation emails have been sent recently. "
                    "Please wait a few minutes before creating another parent account, "
                    "or use the in-person onboarding option to set a password directly."
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=f"Unable to send parent invitation: {str(e)}",
        )
