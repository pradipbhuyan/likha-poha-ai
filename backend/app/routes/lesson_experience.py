"""
lesson_experience.py — Admin Lesson Experience endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only REST API for the polished "Lesson Experience" page.

This is a clean, student-facing-style preview of published lesson content.
It reuses lesson_lab_service for data retrieval.

NEVER writes to any lesson table.
NEVER exposes repair/audit/QA metadata to the caller.
NEVER calls LLM by default.
Admin-only — 403 for all non-admins.

Endpoints:
  GET /api/admin/lesson-experience/catalog           — lesson hierarchy
  GET /api/admin/lesson-experience/lesson/{id}       — lesson detail (steps)
  GET /api/admin/lesson-experience/visuals           — linked visuals
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.auth_service import require_admin
from app.services.lesson_lab_service import (
    get_lesson_detail,
    get_lesson_list,
    get_visuals,
)

router = APIRouter()


@router.get("/catalog")
def get_catalog(
    grade:   Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """
    Return the full lesson hierarchy for the selector panel.

    Reuses lesson_lab_service.get_lesson_list() — returns published content only.
    Read-only. Admin-only.
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
    Return full normalized lesson detail including step content.

    lesson_id may be a DB UUID or "Grade|Subject|Chapter" composite key.
    Reads latest published content. Read-only. Admin-only.
    """
    result = get_lesson_detail(lesson_id, grade=grade, subject=subject, chapter=chapter)
    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=422, detail=result["error"])
    # Strip any internal audit/repair metadata before returning
    result.pop("repair_job_id", None)
    result.pop("audit_summary", None)
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
    Return linked textbook visuals for the current lesson context.

    Uses existing uploaded/approved visual assets only.
    Returns safe empty state if none available.
    Admin-only. No private asset internals exposed.
    """
    result = get_visuals(
        grade=grade,
        subject=subject,
        chapter=chapter,
        lesson_id=lesson_id,
    )
    return {"success": True, **result}
