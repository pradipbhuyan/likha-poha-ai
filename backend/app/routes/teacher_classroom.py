"""
teacher_classroom.py  —  /api/teacher/*
─────────────────────────────────────────────────────────────────────────────
Teacher Success Platform — consolidated (formerly split across
teacher_classroom.py / teacher_classroom_p2.py). Single router, single prefix.

Phase 1 endpoints (all require role=teacher):

  GET  /dashboard/summary            — classroom dashboard stats
  GET  /students                     — roster with search/filter/sort
  GET  /students/{id}                — student detail
  PATCH /students/{id}               — update student name/grade/email
  POST /students/{id}/archive        — archive from roster
  POST /students/{id}/email-credentials — email credentials (paid only)

  GET  /invitations                  — list invitations
  POST /invitations                  — create invitation
  POST /invitations/{id}/resend      — resend invitation
  POST /invitations/{id}/cancel      — cancel invitation

  GET  /classrooms                   — list classrooms
  POST /classrooms                   — create classroom
  PATCH /classrooms/{id}             — rename/update classroom
  POST /classrooms/{id}/archive      — archive classroom
  POST /classrooms/{id}/students     — add student to classroom
  DELETE /classrooms/{id}/students/{student_id} — remove from classroom

Phase 2 endpoints — Actionable Dashboard (all require role=teacher):

  Feature 1 — Student Timeline:
    GET  /students/{id}/timeline

  Feature 2 — Intervention Queue:
    GET  /interventions

  Feature 3 — Teacher Tasks:
    GET  /tasks
    POST /tasks
    PATCH /tasks/{task_id}
    POST /tasks/{task_id}/complete
    POST /tasks/{task_id}/dismiss

  Feature 4 — Classroom Analytics:
    GET  /classrooms/{classroom_id}/analytics

  Feature 5 — Teacher Notes:
    GET  /students/{id}/notes
    POST /students/{id}/notes
    PATCH /students/{id}/notes/{note_id}
    DELETE /students/{id}/notes/{note_id}

  Feature 6 — Parent Communication:
    GET  /students/{id}/parent-contact
    POST /students/{id}/message-parent

Plan limits (enforced by backend):
  Free teacher: 10 students max
  Paid teacher: 30 students max

Safety:
- Teacher can only access own students/classrooms/tasks/notes.
- Notes are teacher_private — never exposed to students/parents.
- All mutating actions write sanitized audit events.
- Missing source tables return graceful empty results.
- Teachers cannot set or view a student's password, and have no way to log
  into a student's account — email-credentials sends a Supabase-generated
  invite link straight to the student's own inbox instead.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services.auth_service import admin_client, require_teacher, create_auth_user
from app.services.audit_log_service import write_audit_event
from app.services.email_service import (
    configured_email_provider,
    send_teacher_parent_message,
    send_student_invitation_email,
)
from app.services.offer_access_service import is_free_tier_user

router = APIRouter()
_log = logging.getLogger("likhapoha.teacher")

# ── Constants ────────────────────────────────────────────────────────────────
FREE_TEACHER_MAX   = 10
PAID_TEACHER_MAX   = 30
INVITATION_EXPIRY_DAYS = 7
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry_iso(days: int = INVITATION_EXPIRY_DAYS) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _is_expired(expires_at_str: str | None) -> bool:
    """Return True if the ISO timestamp is in the past (UTC-aware)."""
    if not expires_at_str:
        return False
    try:
        expires = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < datetime.now(timezone.utc)
    except Exception:
        return False


def _grade_sort_key(grade_str: str | None) -> int:
    """Extract numeric grade for correct sort: Grade 1 < Grade 9 < Grade 10."""
    if not grade_str:
        return 999
    try:
        return int("".join(filter(str.isdigit, grade_str)) or "999")
    except Exception:
        return 999


def _test_percentage(row: dict) -> float | None:
    """Read a score from the current test_history schema, with safe fallback."""
    try:
        if row.get("percentage") is not None:
            value = float(row["percentage"])
            if 0 <= value <= 100:
                return round(value, 1)
    except (TypeError, ValueError):
        pass

    try:
        if row.get("max_score") is not None and float(row["max_score"]) > 0:
            return round(float(row.get("final_score") or 0) / float(row["max_score"]) * 100, 1)
    except (TypeError, ValueError):
        pass
    return None


def _safe_q(fn):
    """Run a Supabase query, return (data, error_str | None)."""
    try:
        r = fn()
        return r.data or [], None
    except Exception as exc:
        err = str(exc)
        if "PGRST205" in err or "schema cache" in err.lower():
            return [], None
        return [], err[:200]


def _safe_one(fn):
    rows, err = _safe_q(fn)
    return (rows[0] if rows else None), err


def _resolve_teacher_limit(teacher_id: str) -> int:
    """Return max allowed students for this teacher based on their plan."""
    free = is_free_tier_user(teacher_id)
    return FREE_TEACHER_MAX if free else PAID_TEACHER_MAX


def _count_active_assignments(teacher_id: str) -> int:
    """Count non-archived assignments for this teacher."""
    try:
        r = (
            admin_client.table("teacher_student_assignments")
            .select("id", count="exact")
            .eq("teacher_id", teacher_id)
            .is_("archived_at", "null")
            .execute()
        )
        return r.count or 0
    except Exception:
        # archived_at column may not exist yet — fall back to unfiltered count
        try:
            r = (
                admin_client.table("teacher_student_assignments")
                .select("id", count="exact")
                .eq("teacher_id", teacher_id)
                .execute()
            )
            return r.count or 0
        except Exception:
            return 0


def _ensure_owns_student(teacher_id: str, student_id: str):
    """Raise if teacher does not have an active assignment for this student."""
    row, _ = _safe_one(
        lambda: admin_client.table("teacher_student_assignments")
        .select("id")
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .limit(1)
        .execute()
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Student not assigned to you.")


def _ensure_owns_classroom(teacher_id: str, classroom_id: str):
    """Raise if teacher does not own this classroom."""
    row, _ = _safe_one(
        lambda: admin_client.table("teacher_classrooms")
        .select("id")
        .eq("id", classroom_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Classroom not found or not yours.")


def _get_tid(teacher: dict) -> str:
    return teacher["profile"]["id"]


def _invite_link(token: str) -> str:
    base = (getattr(settings, "FRONTEND_URL", "") or "https://likhapoha.in").rstrip("/")
    return f"{base}/accept-invite?token={token}"


def _teacher_display_name(teacher: dict) -> str:
    profile = teacher.get("profile") or {}
    return profile.get("username") or profile.get("email") or "Your teacher"


# ── Pydantic models ───────────────────────────────────────────────────────────

class UpdateStudentRequest(BaseModel):
    username: Optional[str] = None
    grade: Optional[str] = None
    email: Optional[str] = None


class CreateInvitationRequest(BaseModel):
    student_name: str
    grade: str = "Grade 9"
    email: str
    stream: Optional[str] = None    # required for Grade 11/12: PCM|PCB|PCMB|Commerce|Humanities


class ResendInvitationRequest(BaseModel):
    email: Optional[str] = None     # set to change the invitation's email before resending


class CreateClassroomRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateClassroomRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddClassroomStudentRequest(BaseModel):
    student_id: str


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: str = "medium"
    student_id: Optional[str] = None
    due_date: Optional[str] = None
    source: str = "manual"


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class CreateNoteRequest(BaseModel):
    note: str


class UpdateNoteRequest(BaseModel):
    note: str


class MessageParentRequest(BaseModel):
    subject: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dashboard Summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/summary")
def teacher_dashboard_summary(teacher=Depends(require_teacher)):
    """
    Canonical single-fetch dashboard summary.
    Returns all KPI data the Overview tab needs — one aggregation, one DTO.
    Resilient: if archived_at column does not exist yet (migration pending),
    falls back to selecting without it and treats all assignments as active.
    """
    teacher_id = teacher["profile"]["id"]
    is_paid = not is_free_tier_user(teacher_id)
    plan_limit = _resolve_teacher_limit(teacher_id)

    # ── Load assignments — resilient to missing/stale archived_at column ─────
    # Use select("*") so PostgREST schema cache staleness never causes PGRST205.
    # When archived_at column does not exist in cache, it simply won't appear in
    # results → a.get("archived_at") returns None → treated as active (correct).
    # When archived_at exists, rows with a value are filtered out below.
    assignments, err = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("*")
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if err:
        _log.warning("teacher.summary: assignments query error: %s", err)

    # Filter archived rows — safe even if archived_at column doesn't exist
    active_assignments = [a for a in assignments if not a.get("archived_at")]
    student_ids = [a["student_id"] for a in active_assignments if a.get("student_id")]
    students_used = len(student_ids)

    # Student profiles
    profiles = {}
    if student_ids:
        p_rows, _ = _safe_q(
            lambda: admin_client.table("profiles")
            .select("id, username, email, grade, account_status, created_at")
            .in_("id", student_ids)
            .execute()
        )
        profiles = {r["id"]: r for r in p_rows}

    # Status counts
    active_count = sum(
        1 for sid in student_ids
        if profiles.get(sid, {}).get("account_status", "active") == "active"
    )
    inactive_count = len(student_ids) - active_count

    # Pending invitations
    pending_invitations = 0
    inv_rows, _ = _safe_q(
        lambda: admin_client.table("teacher_invitations")
        .select("id")
        .eq("teacher_id", teacher_id)
        .eq("status", "pending")
        .execute()
    )
    pending_invitations = len(inv_rows)

    # Recent activity — last 7 days (graceful if table missing)
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_activity, _ = _safe_q(
        lambda: admin_client.table("ai_usage_logs")
        .select("profile_id, username, feature, created_at")
        .in_("profile_id", student_ids)
        .gte("created_at", seven_days_ago)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )

    # Students needing attention (inactive 7+ days)
    needs_attention = []
    for sid in student_ids:
        p = profiles.get(sid, {})
        last_seen = None
        for log in recent_activity:
            if log.get("profile_id") == sid:
                last_seen = log.get("created_at")
                break
        if not last_seen:
            needs_attention.append(p.get("username", sid))

    # Mock test averages (graceful)
    mock_avg = None
    test_rows, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("profile_id, percentage, final_score, max_score")
        .in_("profile_id", student_ids)
        .execute()
    )
    if test_rows:
        scores = [score for score in (_test_percentage(t) for t in test_rows) if score is not None]
        if scores:
            mock_avg = round(sum(scores) / len(scores), 1)

    # ── Classroom count ───────────────────────────────────────────────────────
    classroom_rows, _ = _safe_q(
        lambda: admin_client.table("teacher_classrooms")
        .select("id")
        .eq("teacher_id", teacher_id)
        .eq("status", "active")
        .execute()
    )
    classroom_count = len(classroom_rows)

    return {
        "success": True,
        # ── Subscription section ─────────────────────────────────────────────
        "subscription": {
            "plan": "paid" if is_paid else "free",
            "student_limit": plan_limit,
            "students_used": students_used,
            "is_paid": is_paid,
        },
        # ── Students section (all counts derived from same assignment dataset) ─
        "students": {
            "total_students": students_used,
            "active_students": active_count,
            "inactive_students": inactive_count,
            "pending_invitations": pending_invitations,
            "needs_attention_count": len(needs_attention),
        },
        # ── Classrooms section ───────────────────────────────────────────────
        "classrooms": {
            "classroom_count": classroom_count,
        },
        # ── Learning section ─────────────────────────────────────────────────
        "learning": {
            "average_mock_score": mock_avg,
            "recent_activity": [
                {
                    "username": r.get("username"),
                    "feature": r.get("feature"),
                    "at": r.get("created_at"),
                }
                for r in recent_activity[:10]
            ],
            "attention_students": needs_attention[:5],
        },
        # ── Backward-compatible flat fields (existing tests) ─────────────────
        "is_paid": is_paid,
        "plan_limit": plan_limit,
        "totals": {
            "total_students": students_used,
            "active_students": active_count,
            "inactive_students": inactive_count,
            "pending_invitations": pending_invitations,
            "needs_attention_count": len(needs_attention),
        },
        "averages": {
            "mock_test_avg": mock_avg,
        },
        "needs_attention": needs_attention[:5],
        "recent_activity": [
            {
                "username": r.get("username"),
                "feature": r.get("feature"),
                "at": r.get("created_at"),
            }
            for r in recent_activity[:10]
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Student Roster
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/students")
def list_students(
    q: Optional[str] = Query(default=None),
    grade: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),  # active | inactive | archived
    sort: Optional[str] = Query(default="name"),  # name | grade | last_active
    teacher=Depends(require_teacher),
):
    """
    Roster of assigned students with optional search/filter/sort.
    Archived students only appear when status=archived is requested.
    Teacher can only see their own students.
    """
    teacher_id = teacher["profile"]["id"]

    # Load assignments — use select("*") to avoid PGRST205 on stale schema cache.
    # archived_at will be absent if migration hasn't been applied → treated as active.
    assignments, _ = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("*")
        .eq("teacher_id", teacher_id)
        .execute()
    )

    # Filter archived
    if status == "archived":
        assignments = [a for a in assignments if a.get("archived_at")]
    else:
        assignments = [a for a in assignments if not a.get("archived_at")]

    if not assignments:
        return {"success": True, "students": [], "count": 0}

    student_ids = [a["student_id"] for a in assignments if a.get("student_id")]
    assignment_map = {a["student_id"]: a for a in assignments}

    # Load profiles
    profiles, _ = _safe_q(
        lambda: admin_client.table("profiles")
        .select("id, username, email, grade, account_status, created_at")
        .in_("id", student_ids)
        .execute()
    )

    # Filter by name/email query
    if q:
        q_lower = q.lower()
        profiles = [
            p for p in profiles
            if q_lower in (p.get("username") or "").lower()
            or q_lower in (p.get("email") or "").lower()
        ]

    # Filter by grade
    if grade:
        profiles = [p for p in profiles if p.get("grade") == grade]

    # Filter by account status (active/inactive)
    if status and status not in ("archived",):
        profiles = [
            p for p in profiles
            if p.get("account_status", "active") == status
        ]

    # Sort
    if sort == "grade":
        profiles.sort(key=lambda p: _grade_sort_key(p.get("grade")))
    else:
        profiles.sort(key=lambda p: (p.get("username") or "").lower())

    # Enrich with assignment info
    result = []
    for p in profiles:
        a = assignment_map.get(p["id"], {})
        result.append({
            **p,
            "assignment_grade": a.get("grade"),
            "subject": a.get("subject"),
            "section": a.get("section"),
            "archived_at": a.get("archived_at"),
            "assigned_at": a.get("created_at"),
        })

    return {"success": True, "students": result, "count": len(result)}


@router.get("/students/{student_id}")
def get_student_detail(student_id: str, teacher=Depends(require_teacher)):
    """
    Full student detail for the drawer/detail page.
    Includes learning signals if available (graceful fallbacks).
    Teacher can only view assigned students.
    """
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_student(teacher_id, student_id)

    profile, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email, grade, board, subscription_plan, account_status, access_cbse, created_at")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found.")

    # Classroom memberships
    classrooms, _ = _safe_q(
        lambda: admin_client.table("teacher_classroom_students")
        .select("classroom_id")
        .eq("student_id", student_id)
        .eq("teacher_id", teacher_id)
        .execute()
    )
    classroom_ids = [c["classroom_id"] for c in classrooms]
    classroom_details = []
    if classroom_ids:
        cls_rows, _ = _safe_q(
            lambda: admin_client.table("teacher_classrooms")
            .select("id, name, status")
            .in_("id", classroom_ids)
            .execute()
        )
        classroom_details = cls_rows

    # Learning signals (all graceful)
    username = profile.get("username", "")
    activity, _ = _safe_q(
        lambda: admin_client.table("ai_usage_logs")
        .select("feature, total_tokens, created_at")
        .eq("profile_id", student_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    tests, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("profile_id, percentage, final_score, max_score, subject, chapter, submitted_at, created_at")
        .eq("profile_id", student_id)
        .order("submitted_at", desc=True)
        .limit(20)
        .execute()
    )
    mock_avg = None
    if tests:
        scores = [score for score in (_test_percentage(t) for t in tests) if score is not None]
        if scores:
            mock_avg = round(sum(scores) / len(scores), 1)

    last_active = activity[0]["created_at"] if activity else None
    lessons = sum(1 for a in activity if a.get("feature") == "lesson")
    doubts = sum(1 for a in activity if a.get("feature") == "doubt")

    return {
        "success": True,
        "student": profile,
        "classrooms": classroom_details,
        "learning": {
            "last_active": last_active,
            "lessons_generated": lessons,
            "doubts_asked": doubts,
            "mock_tests_completed": len(tests),
            "mock_test_avg": mock_avg,
            "recent_tests": [
                {
                    "subject": row.get("subject"),
                    "chapter": row.get("chapter"),
                    "score": _test_percentage(row),
                    "submitted_at": row.get("submitted_at") or row.get("created_at"),
                }
                for row in tests[:10]
            ],
            "recent_activity": activity[:5],
        },
    }


@router.patch("/students/{student_id}")
def update_student(student_id: str, data: UpdateStudentRequest, teacher=Depends(require_teacher)):
    """Update student name, grade, or email. Teacher must own the student."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_student(teacher_id, student_id)

    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No changes provided."}

    if "username" in updates:
        from app.routes.auth import _reject_reserved_username, _reject_taken_username

        clean_username = updates["username"].strip()
        if not clean_username:
            raise HTTPException(status_code=400, detail="Username cannot be empty.")
        _reject_reserved_username(clean_username)
        current, _ = _safe_one(
            lambda: admin_client.table("profiles")
            .select("username")
            .eq("id", student_id)
            .limit(1)
            .execute()
        )
        if not current or clean_username.casefold() != (current.get("username") or "").strip().casefold():
            _reject_taken_username(clean_username, client=admin_client)
        updates["username"] = clean_username

    try:
        admin_client.table("profiles").update(updates).eq("id", student_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.student.updated",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="student",
        entity_id=student_id,
        metadata={"fields_updated": list(updates.keys())},
    )
    return {"success": True, "updated": list(updates.keys())}


@router.post("/students/{student_id}/archive")
def archive_student(student_id: str, teacher=Depends(require_teacher)):
    """Archive a student from this teacher's roster (soft delete)."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_student(teacher_id, student_id)

    now = _now_iso()
    try:
        admin_client.table("teacher_student_assignments").update(
            {"archived_at": now}
        ).eq("teacher_id", teacher_id).eq("student_id", student_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.student.archived",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="student",
        entity_id=student_id,
        metadata={},
    )
    return {"success": True, "archived_at": now}


@router.post("/students/{student_id}/email-credentials")
def email_student_credentials(student_id: str, teacher=Depends(require_teacher)):
    """
    Email login credentials to a student.
    Paid teachers only — backend enforces this.
    """
    teacher_id = teacher["profile"]["id"]
    if is_free_tier_user(teacher_id):
        return {
            "success": False,
            "error": "Upgrade to a paid plan to email login details.",
            "upgrade_required": True,
        }
    _ensure_owns_student(teacher_id, student_id)

    profile, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    if not profile or not profile.get("email"):
        return {"success": False, "error": "Student has no email address."}

    invite_sent = False
    invite_error = None
    try:
        admin_client.auth.admin.invite_user_by_email(profile["email"])
        invite_sent = True
    except Exception as exc:
        invite_error = str(exc)[:100]

    write_audit_event(
        event_type="teacher.student.credentials_emailed",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="student",
        entity_id=student_id,
        metadata={"invite_sent": invite_sent},
    )
    return {
        "success": True,
        "invite_sent": invite_sent,
        "note": "If invite_sent=false, share login link manually.",
        "error": invite_error,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Invitations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/invitations")
def list_invitations(
    status: Optional[str] = Query(default=None),
    teacher=Depends(require_teacher),
):
    """List all invitations created by this teacher."""
    teacher_id = teacher["profile"]["id"]
    query = (
        admin_client.table("teacher_invitations")
        .select("id, student_name, grade, email, status, expires_at, accepted_at, created_at")
        .eq("teacher_id", teacher_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    invitations, err = _safe_q(lambda: query.execute())
    # Check-on-read: mark pending invitations as expired if past their expiry date.
    # This avoids needing a background expiry job.
    now = datetime.now(timezone.utc)
    for inv in invitations:
        if inv.get("status") == "pending" and _is_expired(inv.get("expires_at")):
            inv["status"] = "expired"
    return {"success": True, "invitations": invitations, "error": err}


@router.post("/invitations")
def create_invitation(data: CreateInvitationRequest, teacher=Depends(require_teacher)):
    """
    Create a student invitation by email.
    Checks plan limit — cannot exceed student cap.
    """
    teacher_id = teacher["profile"]["id"]

    # Check plan limit
    current = _count_active_assignments(teacher_id)
    limit = _resolve_teacher_limit(teacher_id)
    if current >= limit:
        return {
            "success": False,
            "error": f"Student limit reached ({current}/{limit}). "
                     + ("Contact admin to increase limit." if limit == PAID_TEACHER_MAX else "Upgrade to a paid plan for more students."),
            "at_limit": True,
        }

    # Grade 11/12: stream is required — the student gets access to exactly
    # this stream's subjects the moment they accept, mirroring the rule
    # enforced for parent-added children and self-signup.
    stream = ""
    if data.grade in ("Grade 11", "Grade 12"):
        valid_streams = {"PCM", "PCB", "PCMB", "Commerce", "Humanities"}
        stream = (data.stream or "").strip()
        if stream not in valid_streams:
            return {
                "success": False,
                "error": f"Stream is required for {data.grade} students. "
                         f"Choose one of: PCM, PCB, PCMB, Commerce, Humanities",
            }

    # Fail fast if this email already has an account — the invitation would
    # otherwise sit as "pending" forever because acceptance can never create
    # a second Supabase auth user for the same address.
    existing, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id")
        .eq("email", data.email.strip().lower())
        .limit(1)
        .execute()
    )
    if existing:
        return {
            "success": False,
            "error": "An account with this email already exists. "
                     "Ask them to log in directly, or invite a different email address.",
        }

    row = {
        "teacher_id": teacher_id,
        "student_name": data.student_name,
        "grade": data.grade,
        "email": data.email,
        "stream": stream or None,
        "status": "pending",
        "expires_at": _expiry_iso(),
    }
    try:
        result = admin_client.table("teacher_invitations").insert(row).execute()
        inv = result.data[0] if result.data else row
    except Exception as exc:
        err = str(exc)
        is_missing_stream_column = "stream" in err and ("PGRST204" in err or "column" in err.lower())
        if is_missing_stream_column and stream:
            # A stream was required (Grade 11/12) but the DB migration that adds
            # the `stream` column hasn't run yet — do NOT silently drop it and
            # create an invitation with no stream. That produced a real bug:
            # the accepted student got zero cbse_subjects, i.e. ALL subjects
            # instead of just their chosen stream's.
            return {
                "success": False,
                "error": "Stream selection isn't available on the server yet "
                         "(missing database migration). Contact your admin before "
                         "inviting Grade 11/12 students.",
            }
        if is_missing_stream_column:
            # Non-11/12 invitation — stream is empty anyway, safe to drop.
            row.pop("stream", None)
            try:
                result = admin_client.table("teacher_invitations").insert(row).execute()
                inv = result.data[0] if result.data else row
            except Exception as exc2:
                return {"success": False, "error": str(exc2)[:150]}
        else:
            return {"success": False, "error": err[:150]}

    email_sent = False
    if inv.get("token"):
        email_sent = send_student_invitation_email(
            to=data.email,
            student_name=data.student_name,
            teacher_name=_teacher_display_name(teacher),
            grade=data.grade,
            invite_link=_invite_link(inv["token"]),
            expiry_days=INVITATION_EXPIRY_DAYS,
            stream=stream,
        )
        if not email_sent:
            _log.warning("teacher.invitation.email_not_sent", extra={"invitation_id": inv.get("id")})

    write_audit_event(
        event_type="teacher.invitation.created",
        actor_user_id=teacher_id,
        entity_type="invitation",
        entity_id=inv.get("id", ""),
        metadata={"grade": data.grade, "status": "pending", "email_sent": email_sent},
    )
    return {
        "success": True,
        "invitation": inv,
        "email_sent": email_sent,
        "warning": None if email_sent else (
            "Invitation saved, but the email could not be sent. "
            "Check RESEND_API_KEY / EMAIL_FROM_ADDRESS configuration, or share the invite link manually."
        ),
    }


@router.post("/invitations/{invitation_id}/resend")
def resend_invitation(
    invitation_id: str,
    data: ResendInvitationRequest = ResendInvitationRequest(),
    teacher=Depends(require_teacher),
):
    """
    Resend an invitation and extend its expiry by 7 days.
    Optionally pass a new `email` to redirect the invite before resending —
    e.g. when the original address already had an account, was mistyped,
    or the invite needs to go to someone else.
    """
    teacher_id = teacher["profile"]["id"]
    inv, _ = _safe_one(
        lambda: admin_client.table("teacher_invitations")
        .select("*")
        .eq("id", invitation_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not inv:
        return {"success": False, "error": "Invitation not found or not yours."}
    if inv.get("status") not in ("pending", "expired"):
        return {"success": False, "error": f"Cannot resend invitation with status '{inv.get('status')}'."}

    new_email = (data.email or "").strip().lower()
    target_email = inv.get("email")
    update_fields = {"status": "pending", "expires_at": _expiry_iso(), "updated_at": _now_iso()}

    if new_email and new_email != (inv.get("email") or "").strip().lower():
        if not _EMAIL_RE.match(new_email):
            return {"success": False, "error": "Please enter a valid email address."}
        existing, _ = _safe_one(
            lambda: admin_client.table("profiles")
            .select("id")
            .eq("email", new_email)
            .limit(1)
            .execute()
        )
        if existing:
            return {
                "success": False,
                "error": "An account with this email already exists. "
                         "Ask them to log in directly, or use a different email address.",
            }
        update_fields["email"] = new_email
        target_email = new_email

    new_expiry = update_fields["expires_at"]
    try:
        admin_client.table("teacher_invitations").update(update_fields).eq("id", invitation_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    email_sent = False
    if inv.get("token") and target_email:
        email_sent = send_student_invitation_email(
            to=target_email,
            student_name=inv.get("student_name", ""),
            teacher_name=_teacher_display_name(teacher),
            grade=inv.get("grade", ""),
            invite_link=_invite_link(inv["token"]),
            expiry_days=INVITATION_EXPIRY_DAYS,
            stream=inv.get("stream") or "",
        )
        if not email_sent:
            _log.warning("teacher.invitation.resend_email_not_sent", extra={"invitation_id": invitation_id})

    write_audit_event(
        event_type="teacher.invitation.resent",
        actor_user_id=teacher_id,
        entity_type="invitation",
        entity_id=invitation_id,
        metadata={"new_expiry": new_expiry, "email_sent": email_sent, "email_changed": "email" in update_fields},
    )
    return {
        "success": True,
        "invitation_id": invitation_id,
        "new_expiry": new_expiry,
        "email": target_email,
        "email_sent": email_sent,
        "warning": None if email_sent else (
            "Expiry extended, but the email could not be resent. "
            "Check RESEND_API_KEY / EMAIL_FROM_ADDRESS configuration."
        ),
    }


@router.post("/invitations/{invitation_id}/cancel")
def cancel_invitation(invitation_id: str, teacher=Depends(require_teacher)):
    """Cancel a pending invitation."""
    teacher_id = teacher["profile"]["id"]
    inv, _ = _safe_one(
        lambda: admin_client.table("teacher_invitations")
        .select("id, status, teacher_id")
        .eq("id", invitation_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not inv:
        return {"success": False, "error": "Invitation not found or not yours."}
    if inv.get("status") == "accepted":
        return {"success": False, "error": "Cannot cancel an already accepted invitation."}

    try:
        admin_client.table("teacher_invitations").update(
            {"status": "cancelled", "updated_at": _now_iso()}
        ).eq("id", invitation_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.invitation.cancelled",
        actor_user_id=teacher_id,
        entity_type="invitation",
        entity_id=invitation_id,
        metadata={},
    )
    return {"success": True, "invitation_id": invitation_id, "status": "cancelled"}


# ─────────────────────────────────────────────────────────────────────────────
# 3b. Public invitation acceptance — NO auth (the student has no account yet).
#     Reachable via the emailed accept-invitation link.
# ─────────────────────────────────────────────────────────────────────────────

class AcceptInvitationRequest(BaseModel):
    username: str
    password: str


def _invitation_status_error(inv: dict) -> Optional[str]:
    """Return a human-readable error if this invitation is not acceptable, else None."""
    status = inv.get("status")
    if status == "accepted":
        return "This invitation has already been accepted."
    if status == "cancelled":
        return "This invitation has been cancelled. Ask your teacher to send a new one."
    if status == "expired" or _is_expired(inv.get("expires_at")):
        return "This invitation has expired. Ask your teacher to resend it."
    return None


@router.get("/invitations/token/{token}")
def get_invitation_by_token(token: str):
    """Public — look up a pending invitation by its token (used by the accept-invitation page)."""
    inv, _ = _safe_one(
        lambda: admin_client.table("teacher_invitations")
        .select("id, student_name, grade, email, status, expires_at, teacher_id")
        .eq("token", token)
        .limit(1)
        .execute()
    )
    if not inv:
        return {"success": False, "error": "Invitation not found."}

    status_error = _invitation_status_error(inv)
    if status_error:
        return {"success": False, "error": status_error}

    teacher_profile, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("username")
        .eq("id", inv["teacher_id"])
        .limit(1)
        .execute()
    )
    return {
        "success": True,
        "invitation": {
            "student_name": inv.get("student_name"),
            "grade": inv.get("grade"),
            "email": inv.get("email"),
            "teacher_name": (teacher_profile or {}).get("username", "Your teacher"),
        },
    }


@router.post("/invitations/token/{token}/accept")
def accept_invitation(token: str, data: AcceptInvitationRequest):
    """
    Public — accept an invitation: create the student's auth account + profile,
    auto-assign them to the inviting teacher, and mark the invitation accepted.
    """
    inv, _ = _safe_one(
        lambda: admin_client.table("teacher_invitations")
        .select("*")
        .eq("token", token)
        .limit(1)
        .execute()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    status_error = _invitation_status_error(inv)
    if status_error:
        raise HTTPException(status_code=400, detail=status_error)

    username = (data.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    password = (data.password or "").strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(username)
    _reject_taken_username(username, client=admin_client)

    teacher_id = inv["teacher_id"]
    grade = inv.get("grade") or "Grade 9"
    email = inv["email"]

    # Re-check the teacher's plan limit at acceptance time (it may have changed
    # or filled up with other students since the invite was sent).
    current = _count_active_assignments(teacher_id)
    limit = _resolve_teacher_limit(teacher_id)
    if current >= limit:
        raise HTTPException(
            status_code=403,
            detail="Your teacher's student limit has been reached. Please contact them.",
        )

    # Re-check for an existing account with this email — it may have been
    # created (e.g. self-signup) after the invitation was sent.
    existing, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id")
        .eq("email", email.strip().lower())
        .limit(1)
        .execute()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Please sign in directly "
                   "instead of accepting this invitation, or ask your teacher to resend "
                   "the invitation to a different email address.",
        )

    # Supabase hashes the password immediately — it is never stored in plain text.
    try:
        auth_user = create_auth_user(email=email, password=password, email_confirm=True)
    except HTTPException as exc:
        if "already been registered" in str(exc.detail).lower():
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in directly "
                       "instead of accepting this invitation, or ask your teacher to resend "
                       "the invitation to a different email address.",
            )
        raise

    student_profile = {
        "id": auth_user.id,
        "email": email,
        "username": username,
        "role": "student",
        "parent_id": None,
        "family_id": None,
        "board": "CBSE",
        "grade": grade,
        "subscription_plan": "free",
        "account_status": "active",
        "access_cbse": False,   # Free Tier — limited access, matches teacher-created students
        "daily_token_limit": 0,
        "monthly_token_limit": 0,
        "cbse_subjects": [],
        "ai_model_preference": "default",
    }

    # Grade 11/12: apply the stream the teacher chose at invite time, so the
    # student gets access to exactly that stream's subjects on first login.
    stream = (inv.get("stream") or "").strip()
    if grade in ("Grade 11", "Grade 12") and stream:
        stream_subjects = {
            "PCM":        ["Physics", "Chemistry", "Mathematics", "English", "Hindi"],
            "PCB":        ["Physics", "Chemistry", "Biology", "English", "Hindi"],
            "PCMB":       ["Physics", "Chemistry", "Mathematics", "Biology", "English", "Hindi"],
            "Commerce":   ["Mathematics", "Business Studies", "Accountancy", "Economics", "English", "Hindi"],
            "Humanities": ["History", "Geography", "Political Science", "Sociology", "English", "Hindi"],
        }
        student_profile["stream"] = stream
        student_profile["cbse_subjects"] = stream_subjects.get(stream, [])

    try:
        profile_resp = admin_client.table("profiles").insert(student_profile).execute()
        created_profile = profile_resp.data[0] if profile_resp.data else student_profile
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to create student profile: {str(exc)[:150]}")

    try:
        admin_client.table("teacher_student_assignments").insert({
            "teacher_id": teacher_id,
            "student_id": auth_user.id,
            "grade": grade,
            "subject": "General",
            "section": "",   # empty string, not None — column is NOT NULL
        }).execute()
    except Exception as exc:
        _log.warning("teacher.invitation.assignment_insert_failed: %s", str(exc)[:200])

    admin_client.table("teacher_invitations").update({
        "status": "accepted",
        "accepted_at": _now_iso(),
        "student_id": auth_user.id,
        "updated_at": _now_iso(),
    }).eq("id", inv["id"]).execute()

    write_audit_event(
        event_type="teacher.invitation.accepted",
        actor_user_id=auth_user.id,
        entity_type="invitation",
        entity_id=inv["id"],
        metadata={"teacher_id": teacher_id, "grade": grade},
    )

    return {
        "success": True,
        "student": {
            "id": created_profile.get("id") or auth_user.id,
            "username": created_profile.get("username", username),
            "grade": created_profile.get("grade", grade),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Classrooms
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/classrooms")
def list_classrooms(
    status: Optional[str] = Query(default="active"),
    teacher=Depends(require_teacher),
):
    """List teacher's classrooms with student counts."""
    teacher_id = teacher["profile"]["id"]
    query = (
        admin_client.table("teacher_classrooms")
        .select("*")
        .eq("teacher_id", teacher_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    classrooms, err = _safe_q(lambda: query.execute())

    # Enrich with student count — exclude archived students
    # Load non-archived assignment student_ids for this teacher (once)
    active_assignments, _ = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("student_id")
        .eq("teacher_id", teacher_id)
        .is_("archived_at", "null")
        .execute()
    )
    active_student_ids = {a["student_id"] for a in active_assignments if a.get("student_id")}

    enriched = []
    for cls in classrooms:
        members, _ = _safe_q(
            lambda c=cls: admin_client.table("teacher_classroom_students")
            .select("student_id")
            .eq("classroom_id", c["id"])
            .execute()
        )
        # Only count members who are not archived
        active_count = sum(1 for m in members if m.get("student_id") in active_student_ids)
        enriched.append({**cls, "student_count": active_count})

    return {"success": True, "classrooms": enriched, "error": err}


@router.post("/classrooms")
def create_classroom(data: CreateClassroomRequest, teacher=Depends(require_teacher)):
    """Create a new classroom."""
    teacher_id = teacher["profile"]["id"]
    row = {
        "teacher_id": teacher_id,
        "name": data.name.strip(),
        "description": data.description or "",
        "status": "active",
    }
    try:
        result = admin_client.table("teacher_classrooms").insert(row).execute()
        cls = result.data[0] if result.data else row
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.classroom.created",
        actor_user_id=teacher_id,
        entity_type="classroom",
        entity_id=cls.get("id", ""),
        metadata={"name": data.name},
    )
    return {"success": True, "classroom": cls}


@router.patch("/classrooms/{classroom_id}")
def update_classroom(classroom_id: str, data: UpdateClassroomRequest, teacher=Depends(require_teacher)):
    """Rename or update a classroom description."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_classroom(teacher_id, classroom_id)

    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = _now_iso()
    try:
        admin_client.table("teacher_classrooms").update(updates).eq("id", classroom_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.classroom.updated",
        actor_user_id=teacher_id,
        entity_type="classroom",
        entity_id=classroom_id,
        metadata={"fields_updated": list(data.dict(exclude_none=True).keys())},
    )
    return {"success": True, "classroom_id": classroom_id}


@router.post("/classrooms/{classroom_id}/archive")
def archive_classroom(classroom_id: str, teacher=Depends(require_teacher)):
    """Archive a classroom (soft delete)."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_classroom(teacher_id, classroom_id)

    try:
        admin_client.table("teacher_classrooms").update(
            {"status": "archived", "updated_at": _now_iso()}
        ).eq("id", classroom_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.classroom.archived",
        actor_user_id=teacher_id,
        entity_type="classroom",
        entity_id=classroom_id,
        metadata={},
    )
    return {"success": True, "classroom_id": classroom_id, "status": "archived"}


@router.post("/classrooms/{classroom_id}/students")
def add_student_to_classroom(
    classroom_id: str,
    data: AddClassroomStudentRequest,
    teacher=Depends(require_teacher),
):
    """Add an assigned student to a classroom. Duplicate is safely ignored."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_classroom(teacher_id, classroom_id)
    _ensure_owns_student(teacher_id, data.student_id)

    row = {
        "classroom_id": classroom_id,
        "student_id": data.student_id,
        "teacher_id": teacher_id,
    }
    try:
        admin_client.table("teacher_classroom_students").upsert(
            row, on_conflict="classroom_id,student_id"
        ).execute()
    except Exception as exc:
        err = str(exc)
        # Duplicate key — not an error from teacher's perspective
        if "duplicate" in err.lower() or "23505" in err:
            return {"success": True, "note": "Student already in classroom."}
        return {"success": False, "error": err[:150]}

    write_audit_event(
        event_type="teacher.classroom.student_added",
        actor_user_id=teacher_id,
        target_user_id=data.student_id,
        entity_type="classroom",
        entity_id=classroom_id,
        metadata={},
    )
    return {"success": True, "classroom_id": classroom_id, "student_id": data.student_id}


@router.delete("/classrooms/{classroom_id}/students/{student_id}")
def remove_student_from_classroom(
    classroom_id: str,
    student_id: str,
    teacher=Depends(require_teacher),
):
    """Remove a student from a classroom."""
    teacher_id = teacher["profile"]["id"]
    _ensure_owns_classroom(teacher_id, classroom_id)

    try:
        admin_client.table("teacher_classroom_students").delete().eq(
            "classroom_id", classroom_id
        ).eq("student_id", student_id).eq("teacher_id", teacher_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.classroom.student_removed",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="classroom",
        entity_id=classroom_id,
        metadata={},
    )
    return {"success": True, "classroom_id": classroom_id, "student_id": student_id}


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2 — Actionable Dashboard (formerly teacher_classroom_p2.py)
# ═════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# Feature 1: Student Timeline
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/timeline")
def get_student_timeline(student_id: str, teacher=Depends(require_teacher)):
    """
    Unified sorted timeline of events for a student.
    Pulls from all available sources gracefully.
    Teacher ownership enforced.
    """
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    # Get student's username for activity lookups
    profile, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, grade")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    username = profile.get("username", "") if profile else ""

    events = []

    # ── Audit events (sanitised) ─────────────────────────────────────────────
    audit_rows, _ = _safe_q(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, entity_type, created_at")
        .eq("target_user_id", student_id)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )
    AUDIT_TITLES = {
        "teacher.student.password_reset":   ("🔑 Password Reset",  "Teacher reset student password"),
        "teacher.student.credentials_emailed": ("📧 Credentials Emailed", "Login details emailed"),
        "teacher.student.archived":         ("🗄 Archived",       "Student archived from roster"),
        "teacher.student.updated":          ("✏️ Profile Updated", "Student details updated"),
        "teacher.classroom.student_added":  ("🏫 Classroom Added", "Added to a classroom"),
        "teacher.classroom.student_removed":("🏫 Classroom Removed","Removed from a classroom"),
        "teacher.invitation.accepted":      ("✅ Invitation Accepted","Joined via invitation"),
        "support.password_reset":           ("🔑 Admin Password Reset","Admin reset password"),
    }
    for row in audit_rows:
        et = row.get("event_type", "")
        if et in AUDIT_TITLES:
            title, desc = AUDIT_TITLES[et]
            events.append({
                "id": f"audit-{row.get('created_at','')}",
                "type": "audit",
                "title": title,
                "description": desc,
                "timestamp": row.get("created_at"),
                "category": "info",
            })

    # ── Teacher notes (titles only — content private) ────────────────────────
    note_rows, _ = _safe_q(
        lambda: admin_client.table("teacher_student_notes")
        .select("id, created_at, updated_at")
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    for row in note_rows:
        events.append({
            "id": f"note-{row.get('id','')}",
            "type": "note",
            "title": "📝 Teacher Note Added",
            "description": "A private note was recorded by the teacher.",
            "timestamp": row.get("created_at"),
            "category": "info",
        })

    # ── Mock test results ────────────────────────────────────────────────────
    test_rows, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("percentage, final_score, max_score, subject, submitted_at, created_at")
        .eq("profile_id", student_id)
        .order("submitted_at", desc=True)
        .limit(20)
        .execute()
    )
    for row in test_rows:
        pct = _test_percentage(row) or 0
        category = "success" if pct >= 60 else ("warning" if pct >= 40 else "alert")
        timestamp = row.get("submitted_at") or row.get("created_at")
        events.append({
            "id": f"test-{timestamp or ''}",
            "type": "mock_test",
            "title": f"📝 Mock Test: {row.get('subject','Unknown')}",
            "description": f"Score: {pct}%",
            "timestamp": timestamp,
            "category": category,
        })

    # ── AI activity (lessons, doubts) ────────────────────────────────────────
    activity_rows, _ = _safe_q(
        lambda: admin_client.table("ai_usage_logs")
        .select("feature, created_at")
        .eq("profile_id", student_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    if activity_rows:
        FEATURE_LABELS = {
            "lesson": ("📖 Lesson Generated", "Student generated an AI lesson"),
            "doubt":  ("❓ Doubt Asked",       "Student asked an AI doubt"),
            "mock_test": ("📝 Mock Test Started","Student started a mock test"),
        }
        for row in activity_rows:
            feat = row.get("feature", "")
            if feat in FEATURE_LABELS:
                title, desc = FEATURE_LABELS[feat]
                events.append({
                    "id": f"activity-{feat}-{row.get('created_at','')}",
                    "type": "activity",
                    "title": title,
                    "description": desc,
                    "timestamp": row.get("created_at"),
                    "category": "info",
                })

    # ── Sort all events by timestamp descending ──────────────────────────────
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)

    return {
        "success": True,
        "student_id": student_id,
        "events": events[:50],
        "count": len(events[:50]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2: Intervention Queue
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/interventions")
def get_interventions(teacher=Depends(require_teacher)):
    """
    Prioritised intervention queue for teacher's students.
    Only includes teacher's own assigned students.
    Uses available data only — graceful if tables missing.
    """
    teacher_id = _get_tid(teacher)

    # Load active assignments
    assignments, _ = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("*")
        .eq("teacher_id", teacher_id)
        .execute()
    )
    active = [a for a in assignments if not a.get("archived_at")]
    student_ids = [a["student_id"] for a in active if a.get("student_id")]

    if not student_ids:
        return {"success": True, "interventions": [], "count": 0}

    # Load profiles
    p_rows, _ = _safe_q(
        lambda: admin_client.table("profiles")
        .select("id, username, email, grade, account_status")
        .in_("id", student_ids)
        .execute()
    )
    profiles = {r["id"]: r for r in p_rows}

    # Load recent activity (last 14 days)
    fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    activity_rows, _ = _safe_q(
        lambda: admin_client.table("ai_usage_logs")
        .select("profile_id, created_at")
        .in_("profile_id", student_ids)
        .gte("created_at", fourteen_days_ago)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    # Map immutable profile id → last_active
    last_active_map = {}
    for row in activity_rows:
        profile_id = row.get("profile_id")
        if profile_id and profile_id not in last_active_map:
            last_active_map[profile_id] = row.get("created_at")

    # Load mock test averages
    test_rows, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("profile_id, percentage, final_score, max_score")
        .in_("profile_id", student_ids)
        .execute()
    )
    test_avg_map: dict = {}
    test_count_map: dict = {}
    for t in test_rows:
        profile_id = t.get("profile_id")
        score = _test_percentage(t)
        if profile_id and score is not None:
            test_avg_map.setdefault(profile_id, []).append(score)
    for profile_id, scores in test_avg_map.items():
        test_count_map[profile_id] = len(scores)
        test_avg_map[profile_id] = round(sum(scores) / len(scores), 1)

    # Load pending invitations
    pending_inv, _ = _safe_q(
        lambda: admin_client.table("teacher_invitations")
        .select("id, email, student_name")
        .eq("teacher_id", teacher_id)
        .eq("status", "pending")
        .execute()
    )

    now = datetime.now(timezone.utc)
    interventions = []

    # Build per-student interventions
    for sid in student_ids:
        p = profiles.get(sid, {})
        username = p.get("username", sid)
        last_active = last_active_map.get(sid)
        avg_score = test_avg_map.get(sid)
        test_count = test_count_map.get(sid, 0)

        reasons = []
        actions = []
        severity = "low"

        # Inactivity checks
        if not last_active:
            reasons.append("No recent activity recorded")
            severity = "medium"
        else:
            try:
                la_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                if la_dt.tzinfo is None:
                    la_dt = la_dt.replace(tzinfo=timezone.utc)
                days_inactive = (now - la_dt).days
                if days_inactive >= 14:
                    reasons.append(f"Inactive for {days_inactive} days")
                    severity = "critical"
                elif days_inactive >= 7:
                    reasons.append(f"Inactive for {days_inactive} days")
                    if severity != "critical":
                        severity = "medium"
            except Exception:
                pass

        # Mock test performance
        if test_count > 0 and avg_score is not None:
            if avg_score < 40:
                reasons.append(f"Low mock test average: {avg_score}%")
                if severity != "critical":
                    severity = "medium"
        elif test_count == 0:
            reasons.append("No mock tests completed")
            if severity == "low":
                severity = "low"

        # Actions
        actions = ["view_student"]
        if not is_free_tier_user(teacher_id):
            actions.append("email_credentials")
        actions.append("add_note")
        if p.get("account_status") != "active":
            reasons.append(f"Account status: {p.get('account_status','unknown')}")
            severity = "critical"

        if reasons:
            interventions.append({
                "student_id": sid,
                "student_name": username,
                "grade": p.get("grade") or "—",
                "severity": severity,
                "reasons": reasons,
                "recommended_actions": actions,
                "last_active_at": last_active,
            })

    # Add pending invitation interventions
    for inv in pending_inv:
        interventions.append({
            "student_id": None,
            "student_name": inv.get("student_name", "Invited Student"),
            "grade": "—",
            "severity": "low",
            "reasons": ["Pending invitation not yet accepted"],
            "recommended_actions": ["resend_invitation", "cancel_invitation"],
            "last_active_at": None,
        })

    # Sort: critical → medium → low
    sev_order = {"critical": 0, "medium": 1, "low": 2}
    interventions.sort(key=lambda x: sev_order.get(x["severity"], 3))

    return {"success": True, "interventions": interventions, "count": len(interventions)}


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3: Teacher Tasks
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tasks")
def list_tasks(
    status: Optional[str] = Query(default="open"),
    teacher=Depends(require_teacher),
):
    """List teacher's tasks, default to open tasks."""
    teacher_id = _get_tid(teacher)
    query = (
        admin_client.table("teacher_tasks")
        .select("*")
        .eq("teacher_id", teacher_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    tasks, err = _safe_q(lambda: query.execute())
    return {"success": True, "tasks": tasks, "error": err}


@router.post("/tasks")
def create_task(data: CreateTaskRequest, teacher=Depends(require_teacher)):
    """Create a new teacher task. If linked to student, ownership is enforced."""
    teacher_id = _get_tid(teacher)

    # If task linked to a student, ensure teacher owns them
    if data.student_id:
        _ensure_owns_student(teacher_id, data.student_id)

    row = {
        "teacher_id": teacher_id,
        "title": data.title.strip(),
        "description": data.description or "",
        "priority": data.priority,
        "status": "open",
        "source": data.source,
        "student_id": data.student_id,
        "due_date": data.due_date,
    }
    try:
        result = admin_client.table("teacher_tasks").insert(row).execute()
        task = result.data[0] if result.data else row
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.task.created",
        actor_user_id=teacher_id,
        target_user_id=data.student_id,
        entity_type="task",
        entity_id=task.get("id", ""),
        metadata={"title": data.title, "priority": data.priority, "source": data.source},
    )
    return {"success": True, "task": task}


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, data: UpdateTaskRequest, teacher=Depends(require_teacher)):
    """Update a teacher task. Teacher must own it."""
    teacher_id = _get_tid(teacher)

    # Verify ownership
    existing, _ = _safe_one(
        lambda: admin_client.table("teacher_tasks")
        .select("id, teacher_id, student_id")
        .eq("id", task_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Task not found or not yours.")

    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = _now_iso()
    try:
        admin_client.table("teacher_tasks").update(updates).eq("id", task_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.task.updated",
        actor_user_id=teacher_id,
        entity_type="task",
        entity_id=task_id,
        metadata={"fields_updated": list(updates.keys())},
    )
    return {"success": True, "task_id": task_id}


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, teacher=Depends(require_teacher)):
    """Mark a task as completed."""
    teacher_id = _get_tid(teacher)
    existing, _ = _safe_one(
        lambda: admin_client.table("teacher_tasks")
        .select("id")
        .eq("id", task_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Task not found or not yours.")

    now = _now_iso()
    try:
        admin_client.table("teacher_tasks").update(
            {"status": "completed", "completed_at": now, "updated_at": now}
        ).eq("id", task_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.task.completed",
        actor_user_id=teacher_id,
        entity_type="task",
        entity_id=task_id,
        metadata={},
    )
    return {"success": True, "task_id": task_id, "status": "completed"}


@router.post("/tasks/{task_id}/dismiss")
def dismiss_task(task_id: str, teacher=Depends(require_teacher)):
    """Dismiss a task."""
    teacher_id = _get_tid(teacher)
    existing, _ = _safe_one(
        lambda: admin_client.table("teacher_tasks")
        .select("id")
        .eq("id", task_id)
        .eq("teacher_id", teacher_id)
        .limit(1)
        .execute()
    )
    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Task not found or not yours.")

    now = _now_iso()
    try:
        admin_client.table("teacher_tasks").update(
            {"status": "dismissed", "updated_at": now}
        ).eq("id", task_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.task.dismissed",
        actor_user_id=teacher_id,
        entity_type="task",
        entity_id=task_id,
        metadata={},
    )
    return {"success": True, "task_id": task_id, "status": "dismissed"}


# ─────────────────────────────────────────────────────────────────────────────
# Feature 4: Classroom Analytics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/classrooms/{classroom_id}/analytics")
def get_classroom_analytics(classroom_id: str, teacher=Depends(require_teacher)):
    """
    Analytics for a specific classroom.
    Teacher must own the classroom.
    Missing learning sources return available=false.
    """
    teacher_id = _get_tid(teacher)
    _ensure_owns_classroom(teacher_id, classroom_id)

    # Get classroom members
    members, _ = _safe_q(
        lambda: admin_client.table("teacher_classroom_students")
        .select("student_id")
        .eq("classroom_id", classroom_id)
        .execute()
    )
    student_ids = [m["student_id"] for m in members if m.get("student_id")]

    if not student_ids:
        return {
            "success": True, "classroom_id": classroom_id,
            "student_count": 0, "active_count": 0, "inactive_count": 0,
            "mock_test": {"available": False, "reason": "No students in classroom"},
            "activity": {"available": False, "reason": "No students in classroom"},
        }

    # Load profiles
    p_rows, _ = _safe_q(
        lambda: admin_client.table("profiles")
        .select("id, username, account_status")
        .in_("id", student_ids)
        .execute()
    )
    profiles = {r["id"]: r for r in p_rows}
    active_count = sum(1 for p in profiles.values() if p.get("account_status", "active") == "active")
    usernames = [p.get("username", "") for p in profiles.values() if p.get("username")]

    # Mock test analytics
    mock_analytics = {"available": False, "reason": "No test data"}
    if student_ids:
        test_rows, _ = _safe_q(
            lambda: admin_client.table("test_history")
            .select("profile_id, percentage, final_score, max_score, submitted_at, created_at")
            .in_("profile_id", student_ids)
            .execute()
        )
        if test_rows:
            scores = []
            completed_by_student: dict = {}
            for t in test_rows:
                profile_id = t.get("profile_id")
                pct = _test_percentage(t)
                if profile_id and pct is not None:
                    scores.append(pct)
                    completed_by_student[profile_id] = completed_by_student.get(profile_id, 0) + 1
            if scores:
                avg = round(sum(scores) / len(scores), 1)
                mock_analytics = {
                    "available": True,
                    "average_score": avg,
                    "total_tests": len(test_rows),
                    "students_tested": len(completed_by_student),
                    "score_distribution": {
                        "0-40": sum(1 for s in scores if s < 40),
                        "40-60": sum(1 for s in scores if 40 <= s < 60),
                        "60-80": sum(1 for s in scores if 60 <= s < 80),
                        "80-100": sum(1 for s in scores if s >= 80),
                    },
                }
            else:
                mock_analytics = {"available": False, "reason": "No valid test scores"}
        else:
            mock_analytics = {"available": False, "reason": "No test history"}

    # Activity analytics
    activity_analytics = {"available": False, "reason": "No activity data"}
    if student_ids:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        act_rows, _ = _safe_q(
            lambda: admin_client.table("ai_usage_logs")
            .select("profile_id, feature, created_at")
            .in_("profile_id", student_ids)
            .gte("created_at", seven_days_ago)
            .execute()
        )
        if act_rows:
            active_users = set(r.get("profile_id") for r in act_rows if r.get("profile_id"))
            feature_counts: dict = {}
            for r in act_rows:
                f = r.get("feature", "other")
                feature_counts[f] = feature_counts.get(f, 0) + 1
            activity_analytics = {
                "available": True,
                "active_last_7_days": len(active_users),
                "total_ai_requests": len(act_rows),
                "feature_breakdown": feature_counts,
            }
        else:
            activity_analytics = {"available": False, "reason": "No recent activity"}

    return {
        "success": True,
        "classroom_id": classroom_id,
        "student_count": len(student_ids),
        "active_count": active_count,
        "inactive_count": len(student_ids) - active_count,
        "mock_test": mock_analytics,
        "activity": activity_analytics,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 5: Teacher Notes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/notes")
def list_notes(student_id: str, teacher=Depends(require_teacher)):
    """List teacher's private notes for a student."""
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    notes, err = _safe_q(
        lambda: admin_client.table("teacher_student_notes")
        .select("id, note, visibility, created_at, updated_at")
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return {"success": True, "notes": notes, "error": err}


@router.post("/students/{student_id}/notes")
def create_note(student_id: str, data: CreateNoteRequest, teacher=Depends(require_teacher)):
    """Create a private note for a student."""
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    sanitized = html.escape(data.note.strip())[:2000]
    if not sanitized:
        return {"success": False, "error": "Note cannot be empty."}

    row = {
        "teacher_id": teacher_id,
        "student_id": student_id,
        "note": sanitized,
        "visibility": "teacher_private",
    }
    try:
        result = admin_client.table("teacher_student_notes").insert(row).execute()
        note = result.data[0] if result.data else row
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.note.created",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="note",
        entity_id=note.get("id", ""),
        metadata={},  # note content never in audit log
    )
    return {"success": True, "note": note}


@router.patch("/students/{student_id}/notes/{note_id}")
def update_note(student_id: str, note_id: str, data: UpdateNoteRequest, teacher=Depends(require_teacher)):
    """Update a teacher note."""
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    existing, _ = _safe_one(
        lambda: admin_client.table("teacher_student_notes")
        .select("id")
        .eq("id", note_id)
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Note not found or not yours.")

    sanitized = html.escape(data.note.strip())[:2000]
    if not sanitized:
        return {"success": False, "error": "Note cannot be empty."}

    now = _now_iso()
    try:
        admin_client.table("teacher_student_notes").update(
            {"note": sanitized, "updated_at": now}
        ).eq("id", note_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.note.updated",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="note",
        entity_id=note_id,
        metadata={},
    )
    return {"success": True, "note_id": note_id}


@router.delete("/students/{student_id}/notes/{note_id}")
def delete_note(student_id: str, note_id: str, teacher=Depends(require_teacher)):
    """Soft-delete a teacher note."""
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    existing, _ = _safe_one(
        lambda: admin_client.table("teacher_student_notes")
        .select("id")
        .eq("id", note_id)
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Note not found or not yours.")

    now = _now_iso()
    try:
        admin_client.table("teacher_student_notes").update(
            {"deleted_at": now, "updated_at": now}
        ).eq("id", note_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.note.deleted",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="note",
        entity_id=note_id,
        metadata={},
    )
    return {"success": True, "note_id": note_id, "deleted": True}


# ─────────────────────────────────────────────────────────────────────────────
# Feature 6: Parent Communication
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/parent-contact")
def get_parent_contact(student_id: str, teacher=Depends(require_teacher)):
    """
    Return linked parent info for a student if available.
    Teacher must be assigned to student.
    Returns parent email only — no sensitive data.
    """
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    # Get student's parent_id
    student, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, grade, parent_id")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    if not student or not student.get("parent_id"):
        return {
            "success": True,
            "has_parent": False,
            "parent": None,
            "note": "No parent linked to this student.",
        }

    parent, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email")
        .eq("id", student["parent_id"])
        .limit(1)
        .execute()
    )
    if not parent:
        return {"success": True, "has_parent": False, "parent": None}

    return {
        "success": True,
        "has_parent": True,
        "parent": {
            "id": parent.get("id"),
            "username": parent.get("username"),
            "has_email": bool(parent.get("email")),
        },
    }


@router.post("/students/{student_id}/message-parent")
def message_parent(student_id: str, data: MessageParentRequest, teacher=Depends(require_teacher)):
    """
    Send a message to the student's linked parent.
    Teacher must be assigned to student.
    If no email service, creates a draft/no-op log.
    Message body is sanitized.
    """
    teacher_id = _get_tid(teacher)
    _ensure_owns_student(teacher_id, student_id)

    # Get parent
    student, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, parent_id")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    if not student or not student.get("parent_id"):
        return {"success": False, "error": "No parent linked to this student."}

    parent, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email")
        .eq("id", student["parent_id"])
        .limit(1)
        .execute()
    )
    if not parent:
        return {"success": False, "error": "Parent profile not found."}

    parent_email = parent.get("email")

    # Sanitize message
    clean_subject = html.escape(data.subject.strip())[:200]
    clean_message = html.escape(data.message.strip())[:2000]

    # Send through the transactional email provider. Supabase invitations are
    # account-creation operations and reject parents who are already registered.
    status = "no_email"
    send_error = None
    provider = configured_email_provider()
    if parent_email:
        try:
            sent = send_teacher_parent_message(
                to=parent_email,
                parent_name=parent.get("username") or "Parent",
                teacher_name=teacher.get("profile", {}).get("username") or "Teacher",
                student_name=student.get("username") or "your child",
                subject=data.subject.strip(),
                message=data.message.strip(),
            )
            status = "sent" if sent else "failed"
            if not sent:
                send_error = "provider_failed" if provider != "unconfigured" else "not_configured"
        except Exception as exc:
            _log.warning("teacher.parent_message_send_failed", error=str(exc)[:200])
            send_error = "provider_exception"
            status = "failed"

    # Log the message attempt
    msg_row = {
        "teacher_id": teacher_id,
        "student_id": student_id,
        "parent_id": parent.get("id"),
        "subject": clean_subject,
        "message": clean_message,
        "status": status,
        "provider": provider,
        "error_code": send_error,
        "sent_at": _now_iso() if status == "sent" else None,
    }
    try:
        admin_client.table("teacher_parent_messages").insert(msg_row).execute()
    except Exception:
        pass  # Don't fail the request just because logging failed

    write_audit_event(
        event_type="teacher.parent.message_sent",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="parent_message",
        entity_id="",
        metadata={
            "status": status,
            "has_email": bool(parent_email),
            "provider": provider,
            "error_code": send_error,
        },
    )
    return {
        "success": True,
        "status": status,
        "note": "Message sent." if status == "sent"
                else ("No email address for parent." if status == "no_email"
                      else "Email service is unavailable. Please try again later."),
        "error": None if status != "failed" else "Email service is unavailable. Please try again later.",
        "provider": provider,
        "error_code": send_error,
    }
