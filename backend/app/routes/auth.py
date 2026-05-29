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

    from app.services.auth_service import admin_client

    clean_username = username.strip().lower()

    response = (
        admin_client
        .table("profiles")
        .select("email")
        .ilike("username", clean_username)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Username not found",
        )

    return {
        "email": response.data["email"],
    }