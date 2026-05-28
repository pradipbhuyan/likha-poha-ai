import os

from dotenv import load_dotenv

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from supabase import create_client

load_dotenv()

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_ANON_KEY:
    raise Exception("SUPABASE_ANON_KEY missing")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_ANON_KEY
)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:

        response = supabase.auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return response.user

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )