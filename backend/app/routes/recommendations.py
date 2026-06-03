from fastapi import APIRouter
from app.services.supabase_client import supabase
from app.services.recommendation_service import build_study_recommendations

router = APIRouter()


@router.get("/{username}")
def get_recommendations(username: str):
    """Build study recommendations from a student's stored test history."""
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
