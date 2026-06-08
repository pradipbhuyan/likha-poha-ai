from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_service import require_admin
from app.services.onboarding_guide_service import (
    get_onboarding_guide_settings,
    save_onboarding_guide_settings,
)


router = APIRouter()


class OnboardingGuideSettingsRequest(BaseModel):
    """Admin-editable first-time guide settings."""

    enabled: bool = True
    active_theme: str = "quest"
    rotation_enabled: bool = False
    rotation_days: int = Field(default=14, ge=7, le=60)
    student_theme: str = "quest"
    parent_theme: str = "clean"
    teacher_theme: str = "forest"
    show_once_per_theme: bool = True
    auto_open: bool = True
    message: str = ""


@router.get("/settings")
def read_onboarding_guide_settings():
    """Return public, non-sensitive guide settings for the app shell."""
    return {
        "success": True,
        **get_onboarding_guide_settings(),
    }


@router.put("/settings")
def update_onboarding_guide_settings(
    payload: OnboardingGuideSettingsRequest,
    admin=Depends(require_admin),
):
    """Save admin-controlled onboarding guide settings."""
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        result = save_onboarding_guide_settings(
            data,
            updated_by=admin["profile"].get("id"),
        )
        return {
            "success": True,
            **result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to save onboarding guide settings: {exc}",
        ) from exc
