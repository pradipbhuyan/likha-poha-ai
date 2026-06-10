"""
Cache Management Routes
=======================
Admin-only endpoints for grade-level lesson pre-warming,
question bank building, status tracking, and cache clearing.
"""

import threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from app.services.auth_service import require_admin
from app.services.prewarm_service import (
    prewarm_lessons_for_grade,
    build_question_bank_for_grade,
    get_grade_status_summary,
    clear_lesson_cache_for_grade,
    clear_question_bank_for_grade,
    is_job_running,
)

router = APIRouter()

ALL_GRADES = [f"Grade {n}" for n in range(1, 11)]


@router.get("/status")
def get_cache_status(admin=Depends(require_admin)):
    """
    Return lesson cache and question bank status for all grades.

    Used by the admin cache management panel to show progress,
    disable completed generate buttons, and highlight running jobs.
    """
    return {
        "success": True,
        "grades": get_grade_status_summary(ALL_GRADES),
    }


@router.post("/prewarm/lessons/{grade_slug}")
def start_lesson_prewarm(
    grade_slug: str,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start lesson pre-warming for a grade as a background task.

    The API returns immediately. Generation runs in the background.
    Poll GET /status to see progress. Already-cached steps are skipped.
    Disabled automatically once the grade is complete.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"lessons_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Lesson pre-warming for {grade} is already running.",
        }

    background_tasks.add_task(prewarm_lessons_for_grade, grade)

    return {
        "success": True,
        "message": f"Lesson pre-warming started for {grade}. Poll /status for progress.",
        "grade": grade,
    }


@router.post("/prewarm/questions/{grade_slug}")
def start_question_bank_build(
    grade_slug: str,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start question bank building for a grade as a background task.

    The API returns immediately. Generation runs in the background.
    Poll GET /status to see progress.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"questions_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Question bank building for {grade} is already running.",
        }

    background_tasks.add_task(build_question_bank_for_grade, grade)

    return {
        "success": True,
        "message": f"Question bank building started for {grade}. Poll /status for progress.",
        "grade": grade,
    }


@router.delete("/cache/lessons/{grade_slug}")
def clear_lessons(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Clear all cached lessons for a grade.

    Use this to force re-generation after RAG content is updated,
    or to reset a grade before re-running pre-warming.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"lessons_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot clear cache while pre-warming is running for {grade}.",
        )

    deleted = clear_lesson_cache_for_grade(grade)

    return {
        "success": True,
        "message": f"Cleared lesson cache for {grade}.",
        "deleted": deleted,
        "grade": grade,
    }


@router.delete("/cache/questions/{grade_slug}")
def clear_questions(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Clear all question bank entries for a grade.

    Use this to force re-generation after RAG content is updated,
    or to reset before re-running the bank builder.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"questions_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot clear bank while building is running for {grade}.",
        )

    deleted = clear_question_bank_for_grade(grade)

    return {
        "success": True,
        "message": f"Cleared question bank for {grade}.",
        "deleted": deleted,
        "grade": grade,
    }
