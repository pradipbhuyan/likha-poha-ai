"""
study_planner.py — Study Planner API routes
============================================
All routes require exam prep access (Grade 11/12 + Premium).

Routes:
  GET  /api/exam-prep/study-planner              — get plan + today's tasks + weekly overview
  POST /api/exam-prep/study-planner/generate     — generate / regenerate plan via LLM
  PATCH /api/exam-prep/study-planner/tasks/{id}  — mark task done/skipped/pending
  POST /api/exam-prep/study-planner/migrate      — create DB tables (first-time setup)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import study_planner_service as svc
from app.routes.exam_prep import _require_exam_prep_access  # reuse same access guard

router = APIRouter(prefix="/api/exam-prep/study-planner", tags=["study-planner"])


# ── Request / Response schemas ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    exam_type: str
    daily_hours: int = 4


class TaskUpdateRequest(BaseModel):
    status: str  # done | skipped | pending


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def get_plan(
    exam_type: str = "jee_main",
    ctx=Depends(_require_exam_prep_access),
):
    """
    Return the current study plan for the authenticated user.
    Includes: countdown info, today's tasks, weekly timeline, completion stats.
    If no plan exists, returns has_plan=False + countdown + weak_topics.
    """
    user = ctx["user"]
    plan = svc.get_plan(user_id=user.id, exam_type=exam_type)
    return {"success": True, **plan}


@router.post("/generate")
def generate_plan(
    req: GenerateRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """
    Generate (or regenerate) a study plan using the LLM.
    Saves the plan + all daily tasks to DB.
    This may take 30–120 seconds depending on weeks remaining.
    """
    user = ctx["user"]
    if req.daily_hours < 1 or req.daily_hours > 12:
        raise HTTPException(400, "daily_hours must be between 1 and 12")
    plan = svc.generate_plan(
        user_id=user.id,
        exam_type=req.exam_type,
        daily_hours=req.daily_hours,
    )
    return {"success": True, **plan}


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """
    Mark a task as done, skipped, or pending.
    Only the task owner can update.
    """
    user = ctx["user"]
    updated = svc.update_task_status(
        task_id=task_id,
        user_id=user.id,
        status=req.status,
    )
    return {"success": True, "task": updated}


@router.post("/migrate")
def migrate_tables(ctx=Depends(_require_exam_prep_access)):
    """
    Create study_plans and study_plan_tasks tables in Supabase.
    Safe to run multiple times. Run once before first use.
    """
    user = ctx["user"]
    result = svc.run_migration(user_id=user.id)
    return result


@router.get("/countdown")
def countdown(
    exam_type: str = "jee_main",
    ctx=Depends(_require_exam_prep_access),
):
    """
    Return exam countdown info only (Phase 1 — no DB needed).
    Fast endpoint for the Study Planner card on ExamPrepPage.
    """
    info = svc.get_countdown_info(exam_type)
    return {"success": True, **info}
