from fastapi import APIRouter, HTTPException
from app.models.schemas import LoginRequest, LoginResponse
from app.config import settings

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
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )

    if USERS[username]["password"] != data.password:
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )

    return LoginResponse(
        success=True,
        username=username,
        role=USERS[username]["role"],
        message="Login successful"
    )
    
@router.get("/lookup-email/{username}")
def lookup_email(username: str):
    """
    Resolve a friendly username to an email address for Supabase login.

    The admin alias fallback lets the UI log in as "admin" even when the profile
    row stores a display name rather than that exact username.
    """

    from app.services.auth_service import admin_client

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
        raise HTTPException(
            status_code=404,
            detail="Username not found",
        )

    return {
        "email": rows[0]["email"],
    }
