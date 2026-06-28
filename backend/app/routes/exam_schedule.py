"""
exam_schedule.py  —  Student Exam Schedule endpoints
─────────────────────────────────────────────────────────────────────────────

Student endpoints:
  GET  /api/student/exams          — list own upcoming exams
  POST /api/student/exams          — add own exam
  PATCH /api/student/exams/{id}    — update own exam
  DELETE /api/student/exams/{id}   — cancel own exam

Parent endpoints:
  GET  /api/parent/children/{child_id}/exams  — list child exams
  POST /api/parent/children/{child_id}/exams  — add exam for child

Safety rules:
- Student can only access own exams (student_id = current user)
- Parent can only access linked child exams (_verify_child_ownership)
- Past exams excluded from upcoming queries
- status='cancelled'/'completed' excluded from upcoming
- created_by_user_id and created_by_role always set from auth token
- No admin audit metadata exposed
"""
from __future__ import annotations

import logging
from datetime import date, timezone, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.auth_service import require_student, require_parent, admin_client
from app.routes.parent_dashboard_v2 import _safe_query, _safe_one, _verify_child_ownership

router = APIRouter()
_log = logging.getLogger("likhapoha.exam_schedule")

TABLE = "student_exam_schedule"
def TODAY() -> str:
    return date.today().isoformat()


# ── Pydantic models ───────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    title: str
    subject: str
    exam_date: str          # ISO date string: YYYY-MM-DD
    exam_type: Optional[str] = None
    notes: Optional[str] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    exam_date: Optional[str] = None
    exam_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None   # active / cancelled / completed


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upcoming_query(student_id: str):
    """Return upcoming active exams for a student (exam_date >= today, status=active)."""
    rows, err = _safe_query(
        lambda: admin_client.table(TABLE)
        .select("id, title, subject, exam_date, exam_type, notes, status, created_by_role, created_at")
        .eq("student_id", student_id)
        .eq("status", "active")
        .gte("exam_date", TODAY())
        .order("exam_date", desc=False)
        .execute()
    )
    return rows, err


def _days_until(exam_date_str: str) -> int:
    try:
        ed = date.fromisoformat(exam_date_str)
        return (ed - date.today()).days
    except Exception:
        return -1


def _format_exam(row: dict) -> dict:
    """Add computed days_until to exam row."""
    return {
        **row,
        "days_until": _days_until(row.get("exam_date", "")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STUDENT endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/exams")
def get_student_exams(student=Depends(require_student)):
    """Return upcoming active exams for the authenticated student."""
    uid = student["profile"]["id"]
    rows, err = _upcoming_query(uid)
    if err:
        _log.warning("get_student_exams error: %s", err)
    return {
        "success": True,
        "exams": [_format_exam(r) for r in rows],
        "nearest": _format_exam(rows[0]) if rows else None,
    }


@router.post("/exams")
def add_student_exam(data: ExamCreate, student=Depends(require_student)):
    """Student adds their own exam date."""
    uid = student["profile"]["id"]
    # Validate date is in the future
    days = _days_until(data.exam_date)
    if days < 0:
        raise HTTPException(status_code=400, detail="Exam date must be in the future.")

    payload = {
        "student_id": uid,
        "title": data.title.strip(),
        "subject": data.subject.strip(),
        "exam_date": data.exam_date,
        "exam_type": data.exam_type,
        "notes": data.notes,
        "created_by_user_id": uid,
        "created_by_role": "student",
        "status": "active",
    }
    result = admin_client.table(TABLE).insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not save exam. Please try again.")
    return {
        "success": True,
        "exam": _format_exam(result.data[0]),
    }


@router.patch("/exams/{exam_id}")
def update_student_exam(exam_id: str, data: ExamUpdate, student=Depends(require_student)):
    """Student updates own exam. Ownership enforced."""
    uid = student["profile"]["id"]
    existing, _ = _safe_one(
        lambda: admin_client.table(TABLE).select("id, student_id").eq("id", exam_id).eq("student_id", uid).limit(1).execute()
    )
    if not existing:
        raise HTTPException(status_code=403, detail="Exam not found or not yours.")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")

    if "exam_date" in updates and _days_until(updates["exam_date"]) < 0:
        raise HTTPException(status_code=400, detail="Exam date must be in the future.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = admin_client.table(TABLE).update(updates).eq("id", exam_id).eq("student_id", uid).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not update exam.")
    return {"success": True, "exam": _format_exam(result.data[0])}


@router.delete("/exams/{exam_id}")
def delete_student_exam(exam_id: str, student=Depends(require_student)):
    """Student cancels own exam (sets status=cancelled, not deleted)."""
    uid = student["profile"]["id"]
    existing, _ = _safe_one(
        lambda: admin_client.table(TABLE).select("id, student_id").eq("id", exam_id).eq("student_id", uid).limit(1).execute()
    )
    if not existing:
        raise HTTPException(status_code=403, detail="Exam not found or not yours.")

    admin_client.table(TABLE).update({"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", exam_id).execute()
    return {"success": True, "message": "Exam cancelled."}


# ─────────────────────────────────────────────────────────────────────────────
# PARENT endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/exams")
def get_child_exams(child_id: str, parent=Depends(require_parent)):
    """Parent lists upcoming exams for linked child."""
    parent_id = parent["profile"]["id"]
    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    rows, _ = _upcoming_query(child_id)
    return {
        "success": True,
        "exams": [_format_exam(r) for r in rows],
        "nearest": _format_exam(rows[0]) if rows else None,
    }


@router.post("/children/{child_id}/exams")
def add_child_exam(child_id: str, data: ExamCreate, parent=Depends(require_parent)):
    """Parent adds exam date for linked child."""
    parent_id = parent["profile"]["id"]
    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    days = _days_until(data.exam_date)
    if days < 0:
        raise HTTPException(status_code=400, detail="Exam date must be in the future.")

    payload = {
        "student_id": child_id,
        "title": data.title.strip(),
        "subject": data.subject.strip(),
        "exam_date": data.exam_date,
        "exam_type": data.exam_type,
        "notes": data.notes,
        "created_by_user_id": parent_id,
        "created_by_role": "parent",
        "status": "active",
    }
    result = admin_client.table(TABLE).insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not save exam. Please try again.")
    return {
        "success": True,
        "exam": _format_exam(result.data[0]),
    }
