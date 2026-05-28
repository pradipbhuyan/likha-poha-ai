import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


def get_children(parent_id: str):
    response = (
        supabase.table("profiles")
        .select("id, email, username, role, parent_id")
        .eq("parent_id", parent_id)
        .eq("role", "student")
        .execute()
    )

    return response.data