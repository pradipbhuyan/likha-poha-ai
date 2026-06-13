"""
Product Catalogue admin routes.

GET  /api/product-catalogue          — return full catalogue (admin only)
PATCH /api/product-catalogue/grade   — toggle a grade's visibility
PATCH /api/product-catalogue/program — toggle a coaching program's visibility
"""

import copy
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.data.product_catalogue import DEFAULT_PRODUCT_CATALOGUE
from app.routes.admin_control import require_admin  # reuse existing admin guard

router = APIRouter()

_CATALOGUE_KEY = "product_catalogue"


def _load_catalogue() -> dict:
    """
    Return the live catalogue from admin_settings DB row, falling back to
    the hardcoded defaults when no row exists yet.
    """
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", _CATALOGUE_KEY)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]["value"]
    except Exception:
        pass
    return copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE)


def _save_catalogue(catalogue: dict) -> None:
    """Upsert the catalogue into admin_settings."""
    from app.services.auth_service import admin_client  # noqa: PLC0415
    admin_client.table("admin_settings").upsert(
        {"key": _CATALOGUE_KEY, "value": catalogue},
        on_conflict="key",
    ).execute()


# ── Request models ────────────────────────────────────────────────────────────

class GradeVisibilityRequest(BaseModel):
    grade: str
    visible: bool


class ProgramVisibilityRequest(BaseModel):
    program: str
    visible: bool


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
def get_product_catalogue(admin=Depends(require_admin)):
    """Return the full product catalogue for the admin console."""
    catalogue = _load_catalogue()
    return {"success": True, "catalogue": catalogue}


@router.patch("/grade")
def set_grade_visibility(
    data: GradeVisibilityRequest,
    admin=Depends(require_admin),
):
    """
    Toggle a grade's student-facing visibility.
    Grade 11 / Grade 12 start hidden and are enabled here when content
    is uploaded and the admin is ready to launch.
    """
    catalogue = _load_catalogue()

    if data.grade not in catalogue.get("grades", {}):
        raise HTTPException(status_code=404, detail=f"Grade '{data.grade}' not found in catalogue.")

    catalogue["grades"][data.grade]["visible"] = data.visible
    _save_catalogue(catalogue)

    action = "visible to students" if data.visible else "hidden from students"
    return {
        "success": True,
        "message": f"{data.grade} is now {action}.",
        "catalogue": catalogue,
    }


@router.patch("/program")
def set_program_visibility(
    data: ProgramVisibilityRequest,
    admin=Depends(require_admin),
):
    """
    Toggle a coaching program's student-facing visibility.
    JEE / NEET / CUET start hidden until content + dedicated UI is ready.
    """
    catalogue = _load_catalogue()

    if data.program not in catalogue.get("coaching_programs", {}):
        raise HTTPException(
            status_code=404,
            detail=f"Program '{data.program}' not found in catalogue.",
        )

    catalogue["coaching_programs"][data.program]["visible"] = data.visible
    _save_catalogue(catalogue)

    action = "visible to students" if data.visible else "hidden from students"
    return {
        "success": True,
        "message": f"{data.program} is now {action}.",
        "catalogue": catalogue,
    }
