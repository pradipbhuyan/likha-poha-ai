from fastapi import APIRouter, Depends
from app.services.auth_service import (
    admin_client as supabase,  # uses service_role to bypass RLS
    require_self_by_username,
)
from app.services.recommendation_service import build_study_recommendations

router = APIRouter()


@router.get("/{username}")
def get_recommendations(username: str, _auth=Depends(require_self_by_username)):
    """
    Build study recommendations from a student's stored test history.

    Self, or any student when called by an admin/teacher. The query below uses
    the service-role client, which bypasses row-level security — so the guard
    on this route is the only thing scoping the read.
    """
    result = (
        supabase.table("test_history")
        .select("*")
        .eq("username", username)
        .order("created_at")
        .execute()
    )

    history = result.data or []

    return {
        "success": True,
        "recommendations": build_study_recommendations(history),
    }
