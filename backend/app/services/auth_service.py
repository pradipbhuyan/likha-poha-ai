import os

from dotenv import load_dotenv

# SSL fix for macOS Python 3.13
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

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
    """
    token = credentials.credentials

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

    except Exception as e:
        print("AUTH ERROR:", str(e))
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
        .select("id, email, username, role, parent_id, family_id")
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
    FastAPI dependency that allows only student profile users.

    Use this for routes that should not be reachable by parents or admins.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "student":
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
    
def create_auth_user(email: str, password: str):
    """
    Create a confirmed Supabase auth user from server-side admin credentials.

    This is used by admin/parent onboarding flows that need an auth account and
    a profile row to be created as one controlled operation.
    """
    try:
        response = admin_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })

        return response.user

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to create auth user: {str(e)}",
        )
