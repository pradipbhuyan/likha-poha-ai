"""
Product Catalogue admin routes.

GET  /api/product-catalogue          — return full catalogue (admin only)
PATCH /api/product-catalogue/program — toggle a coaching program's visibility

There is deliberately no grade-visibility toggle here anymore. Grades are
always the full ALL_GRADES list (see app.data.product_catalogue) — a
per-grade admin toggle used to exist but had no frontend ever wired to it,
and a stale DB row it left behind silently demoted Grade 12 signups to
Grade 9. Removed rather than fixed, so it can't happen again.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin  # reuse existing admin guard
from app.services.product_catalogue_service import (
    load_product_catalogue as _load_catalogue,
    save_product_catalogue as _save_catalogue,
)

router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class ProgramVisibilityRequest(BaseModel):
    program: str
    visible: bool


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
def get_product_catalogue(admin=Depends(require_admin)):
    """Return the full product catalogue for the admin console."""
    catalogue = _load_catalogue()
    return {"success": True, "catalogue": catalogue}


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
