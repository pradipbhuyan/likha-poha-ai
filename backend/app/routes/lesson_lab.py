"""
lesson_lab.py — Admin Lesson Experience Lab endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only REST API for the Lesson Experience Lab prototype.

ALL endpoints require admin role (require_admin). Non-admins receive 403.
NEVER writes to lesson_cache or any student-facing table.
NEVER publishes content automatically.
NEVER exposes admin-only assets to non-admins.

Endpoints:
  GET  /api/admin/lesson-lab/lessons             — lesson metadata list
  GET  /api/admin/lesson-lab/lesson/{lesson_id}  — normalized lesson detail
  POST /api/admin/lesson-lab/preview-transform   — preview-only transform
  GET  /api/admin/lesson-lab/visuals             — textbook visual assets
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.auth_service import require_admin
from app.services.lesson_lab_service import (
    get_lesson_detail,
    get_lesson_list,
    get_visuals,
    preview_transform,
)

router = APIRouter()

VALID_PREVIEW_MODES = {"structure_only", "student_friendly", "sectioned", "summary_only"}


class PreviewTransformRequest(BaseModel):
    lesson_id: str
    mode: str = "structure_only"
    use_llm: bool = False
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/lessons")
def list_lessons(
    grade:   Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """
    Return lesson metadata for the lab selector.
    No lesson content — just grades, subjects, chapters, lesson stubs.
    Read-only.
    """
    result = get_lesson_list(grade=grade, subject=subject, chapter=chapter)
    return {"success": True, **result}


@router.get("/lesson/{lesson_id}")
def get_lesson(
    lesson_id: str,
    grade:   Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """
    Return full normalized lesson data including per-step analysis.
    lesson_id may be a DB uuid or a "Grade|Subject|Chapter" composite key.
    Read-only — never writes.
    """
    result = get_lesson_detail(lesson_id, grade=grade, subject=subject, chapter=chapter)
    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=422, detail=result["error"])
    return {"success": True, **result}


@router.post("/preview-transform")
def post_preview_transform(
    req: PreviewTransformRequest,
    admin=Depends(require_admin),
):
    """
    Generate a deterministic or LLM-enhanced preview of a lesson.

    NEVER saves output.
    NEVER publishes to lesson_cache.
    LLM only runs when use_llm=True.
    Output is preview JSON only.
    """
    if req.mode not in VALID_PREVIEW_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {sorted(VALID_PREVIEW_MODES)}",
        )

    result = preview_transform(
        lesson_id=req.lesson_id,
        mode=req.mode,
        use_llm=req.use_llm,
        grade=req.grade,
        subject=req.subject,
        chapter=req.chapter,
    )

    if "error" in result:
        if "not found" in str(result["error"]).lower():
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=422, detail=result["error"])

    return {"success": True, **result}


@router.get("/visuals")
def get_lesson_visuals(
    grade:     Optional[str] = Query(None),
    subject:   Optional[str] = Query(None),
    chapter:   Optional[str] = Query(None),
    lesson_id: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """
    Return available textbook visual assets for a lesson context.
    Only existing uploaded/approved assets — never generates visuals.
    Returns friendly empty state if none are available.
    Admin-only — assets never exposed to students from this endpoint.
    """
    result = get_visuals(
        grade=grade,
        subject=subject,
        chapter=chapter,
        lesson_id=lesson_id,
    )
    return {"success": True, **result}
