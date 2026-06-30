"""
lesson_lab.py — Admin Lesson Experience Lab endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only REST API for the Lesson Experience Lab prototype.

ALL endpoints require admin role (require_admin). Non-admins receive 403.
NEVER writes to lesson_cache or any student-facing table.
NEVER publishes content automatically.
NEVER exposes admin-only assets to non-admins.

Endpoints:
  GET  /api/admin/lesson-lab/lessons               — lesson metadata list
  GET  /api/admin/lesson-lab/lesson/{lesson_id}    — normalized lesson detail
  POST /api/admin/lesson-lab/preview-transform     — preview-only transform
  GET  /api/admin/lesson-lab/visuals               — textbook visual assets
  POST /api/admin/lesson-lab/repair-step-preview   — AI repair draft (no publish)
  POST /api/admin/lesson-lab/repair-step-approve   — approve repair task
  POST /api/admin/lesson-lab/repair-step-publish   — publish approved task
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
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

_log = logging.getLogger("likhapoha.lesson_lab_routes")

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


# ── Repair-with-AI endpoints ──────────────────────────────────────────────────

class RepairStepPreviewRequest(BaseModel):
    lesson_id: str
    grade: str = ""
    subject: str = ""
    chapter: str = ""
    step_number: int
    step_title: str
    step_content: str                       # current raw content of the step
    all_step_contents: list[str] = []       # all steps for cross-step context
    audit_issues: list[dict] = []           # issues for this specific step
    previous_step_content: str = ""
    next_step_content: str = ""
    use_llm: bool = True
    override_api_key: Optional[str] = None  # session-only, never stored/logged


class RepairStepApproveRequest(BaseModel):
    task_id: str


class RepairStepPublishRequest(BaseModel):
    task_id: str


@router.post("/repair-step-preview")
def repair_step_preview(
    req: RepairStepPreviewRequest,
    admin=Depends(require_admin),
):
    """
    Generate an AI repair draft for a single step.

    - Creates a lesson_repair_task in DB (status: ready_for_review if valid, else failed)
    - Returns before/after content, validation result, and step-sequence scores
    - NEVER publishes to lesson_cache
    - NEVER runs LLM automatically — requires use_llm=True
    - override_api_key is session-only, never logged, never stored
    """
    from app.services.lesson_repair_service import (  # noqa: PLC0415
        run_llm_repair,
        validate_repaired_draft,
        _db_insert_task,
    )
    from app.services.step_sequence_service import score_step  # noqa: PLC0415
    from app.services.step_sequence_service import write_bulk_apply_audit_event  # noqa: PLC0415

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"

    # Build the audit stub expected by run_llm_repair
    issues_for_repair = [
        {
            "severity": i.get("severity", "medium"),
            "section": i.get("issue_type", "content"),
            "issue": i.get("issue_message", ""),
        }
        for i in (req.audit_issues or [])
    ]
    lesson_audit = {
        "grade":       req.grade,
        "subject":     req.subject,
        "chapter":     req.chapter,
        "step_title":  req.step_title,
        "all_issues":  issues_for_repair,
    }

    # Compute before-scores using step_sequence_service
    all_texts = req.all_step_contents or [req.step_content]
    step_idx = max(0, req.step_number - 1)
    before_scores = score_step(step_idx, req.step_content, all_texts)

    if not req.use_llm:
        return {
            "success": False,
            "message": "Enable LLM to generate repair. Set use_llm=true.",
            "task_id": None,
        }

    # Run LLM repair (never raises — errors returned in result)
    repair_result = run_llm_repair(
        lesson_audit=lesson_audit,
        admin_username=f"lab:{admin_id}",
        override_api_key=req.override_api_key,
    )

    if not repair_result["success"]:
        return {
            "success": False,
            "message": repair_result.get("error", "LLM repair failed."),
            "task_id": None,
            "before_content": req.step_content,
            "before_scores": {
                "overall": before_scores["overall_step_score"],
                "uniqueness": before_scores["step_uniqueness_score"],
                "depth": before_scores["depth_progression_score"],
                "repetition": before_scores["cross_step_repetition_score"],
                "completeness": before_scores["step_completeness_score"],
            },
        }

    draft = repair_result["draft"]

    # Validate the repaired draft
    validation = validate_repaired_draft(draft)

    # Build repaired text for score comparison
    repaired_text = "\n\n".join(
        str(v) for v in (draft.get("sections") or {}).values() if v
    )
    after_all_texts = list(all_texts)
    if step_idx < len(after_all_texts):
        after_all_texts[step_idx] = repaired_text
    else:
        after_all_texts = after_all_texts + [repaired_text]
    after_scores_raw = score_step(step_idx, repaired_text, after_all_texts)

    # Create a repair task in DB for tracking + approve/publish
    now = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "job_id": None,   # lab repairs have no job
        "grade": req.grade,
        "subject": req.subject,
        "chapter": req.chapter,
        "step_title": req.step_title,
        "original_lesson_cache_id": req.lesson_id if "|" not in req.lesson_id else None,
        "status": "ready_for_review" if validation["valid"] else "validation_failed",
        "issues_json": issues_for_repair,
        "original_content_json": {
            "step_content": req.step_content,
            "step_number": req.step_number,
            "step_title": req.step_title,
            "lesson_id": req.lesson_id,
            "grade": req.grade,
            "subject": req.subject,
            "chapter": req.chapter,
            "before_overall": before_scores["overall_step_score"],
        },
        "repaired_content_json": draft,
        "validation_result_json": validation,
        "audit_before_score": before_scores["overall_step_score"],
        "audit_after_score": after_scores_raw["overall_step_score"],
        "created_at": now,
        "updated_at": now,
    }
    _db_insert_task(task)

    return {
        "success": True,
        "task_id": task_id,
        "task_status": task["status"],
        "before_content": req.step_content,
        "after_content": repaired_text,
        "after_sections": draft.get("sections", {}),
        "issues_fixed": [i.get("issue", "") for i in issues_for_repair],
        "repair_rationale": draft.get("repair_rationale", ""),
        "new_value_added": draft.get("new_value_added", ""),
        "validation_result": validation,
        "before_scores": {
            "overall": before_scores["overall_step_score"],
            "uniqueness": before_scores["step_uniqueness_score"],
            "depth": before_scores["depth_progression_score"],
            "repetition": before_scores["cross_step_repetition_score"],
            "completeness": before_scores["step_completeness_score"],
        },
        "after_scores": {
            "overall": after_scores_raw["overall_step_score"],
            "uniqueness": after_scores_raw["step_uniqueness_score"],
            "depth": after_scores_raw["depth_progression_score"],
            "repetition": after_scores_raw["cross_step_repetition_score"],
            "completeness": after_scores_raw["step_completeness_score"],
        },
        "validation_checks": {
            "no_critical_issues": not any(
                i["severity"] == "critical" for i in (validation.get("issues") or [])
            ),
            "uniqueness_improved": (
                after_scores_raw["step_uniqueness_score"] >
                before_scores["step_uniqueness_score"]
            ),
            "depth_improved": (
                after_scores_raw["depth_progression_score"] >=
                before_scores["depth_progression_score"]
            ),
            "validation_passed": validation["valid"],
            "overall_above_threshold": after_scores_raw["overall_step_score"] >= 85,
            "sections_complete": validation.get("section_compliance", 0) >= 75,
        },
    }


@router.post("/repair-step-approve")
def repair_step_approve(
    req: RepairStepApproveRequest,
    admin=Depends(require_admin),
):
    """
    Approve a repair task generated from Lesson Lab.
    Delegates to the existing Lesson Repair approve endpoint logic.
    Task must be in ready_for_review status and have passed validation.
    """
    from app.services.lesson_repair_service import _db_get_task, _db_update_task  # noqa: PLC0415

    task = _db_get_task(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Repair task not found.")

    if task.get("status") not in ("ready_for_review",):
        raise HTTPException(
            status_code=422,
            detail=f"Task must be in 'ready_for_review' status to approve. Current: {task.get('status')}",
        )

    validation = task.get("validation_result_json") or {}
    if not validation.get("valid"):
        raise HTTPException(
            status_code=422,
            detail="Cannot approve: validation failed. Regenerate repair first.",
        )

    _db_update_task(req.task_id, {
        "status": "approved",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "task_id": req.task_id, "message": "Task approved. Use publish to write to lesson_cache."}


@router.post("/repair-step-publish")
def repair_step_publish(
    req: RepairStepPublishRequest,
    admin=Depends(require_admin),
):
    """
    Publish an approved step repair to lesson_cache.

    Safety:
    - Task must be approved
    - Validation must have passed
    - original_content_json preserved for rollback
    - Audit event written
    """
    from app.services.lesson_repair_service import _db_get_task, _db_update_task, publish_repaired_task  # noqa: PLC0415
    from app.services.step_sequence_service import write_bulk_apply_audit_event  # noqa: PLC0415

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"

    task = _db_get_task(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Repair task not found.")

    if task.get("status") != "approved":
        raise HTTPException(
            status_code=422,
            detail=f"Task must be 'approved' before publishing. Current: {task.get('status')}",
        )

    validation = task.get("validation_result_json") or {}
    if not validation.get("valid"):
        raise HTTPException(
            status_code=422,
            detail="Cannot publish: validation failed. Approve a valid repair first.",
        )

    result = publish_repaired_task(task)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["message"])

    _db_update_task(req.task_id, {
        "status": "published",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    # Write audit event
    write_bulk_apply_audit_event(
        task_id=req.task_id,
        grade=task.get("grade", ""),
        subject=task.get("subject", ""),
        chapter=task.get("chapter", ""),
        step_title=task.get("step_title", ""),
        admin_id=admin_id,
        published=True,
    )

    _log.info(
        "[lesson_lab:repair_publish] task=%s published by admin=%s grade=%s subject=%s",
        req.task_id, admin_id, task.get("grade"), task.get("subject"),
    )

    return {
        "success": True,
        "task_id": req.task_id,
        "message": result["message"],
        "original_content_preserved": True,
    }
