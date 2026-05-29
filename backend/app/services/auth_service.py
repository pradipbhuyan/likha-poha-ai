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
    token = credentials.credentials

    try:
        response = admin_client.auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        return response.user

    except Exception as e:
        print("AUTH ERROR:", str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


def get_user_profile(user_id: str):
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
    profile = get_user_profile(user.id)

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