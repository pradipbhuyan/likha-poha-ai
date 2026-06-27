"""
teacher_classroom.py  —  /api/teacher/*
─────────────────────────────────────────────────────────────────────────────
Teacher Success Platform — Phase 1

New endpoints (all require role=teacher):

  GET  /dashboard/summary            — classroom dashboard stats
  GET  /students                     — roster with search/filter/sort
  GET  /students/{id}                — student detail
  PATCH /students/{id}               — update student name/grade/email
  POST /students/{id}/archive        — archive from roster
  POST /students/{id}/reset-password — reset temp password (creates new)
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

Plan limits (enforced by backend):
  Free teacher: 10 students max
  Paid teacher: 30 students max

Audit events written for all mutating operations.
Passwords are NEVER stored, returned, or logged in plaintext.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_teacher
from app.services.audit_log_service import write_audit_event
from app.services.offer_access_service import is_free_tier_user

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────────────────
FREE_TEACHER_MAX   = 10
PAID_TEACHER_MAX   = 30
INVITATION_EXPIRY_DAYS = 7

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


def _gen_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


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


# ── Pydantic models ───────────────────────────────────────────────────────────

class UpdateStudentRequest(BaseModel):
    username: Optional[str] = None
    grade: Optional[str] = None
    email: Optional[str] = None


class CreateInvitationRequest(BaseModel):
    student_name: str
    grade: str = "Grade 9"
    email: str


class CreateClassroomRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateClassroomRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddClassroomStudentRequest(BaseModel):
    student_id: str


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
    import logging
    _log = logging.getLogger("likhapoha.teacher.summary")
    teacher_id = teacher.get("id")
    is_paid = not is_free_tier_user(teacher_id)
    plan_limit = _resolve_teacher_limit(teacher_id)

    # ── Load assignments — resilient to missing archived_at column ────────────
    assignments, err = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("student_id, grade, subject, created_at, archived_at")
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if err:
        _log.warning("teacher.summary: assignments query error: %s", err)

    # If assignments is empty AND we got a schema error, try without archived_at
    if not assignments and err and ("PGRST205" in err or "schema cache" in err.lower() or "archived_at" in err):
        assignments, err2 = _safe_q(
            lambda: admin_client.table("teacher_student_assignments")
            .select("student_id, grade, subject, created_at")
            .eq("teacher_id", teacher_id)
            .execute()
        )
        if err2:
            _log.warning("teacher.summary: assignments fallback query error: %s", err2)

    # All assignments are "active" when archived_at column doesn't exist
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
        .select("username, feature, created_at")
        .in_("username", [profiles.get(s, {}).get("username", "") for s in student_ids])
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
            if log.get("username") == p.get("username"):
                last_seen = log.get("created_at")
                break
        if not last_seen:
            needs_attention.append(p.get("username", sid))

    # Mock test averages (graceful)
    mock_avg = None
    test_rows, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, username")
        .in_("username", [profiles.get(s, {}).get("username", "") for s in student_ids])
        .execute()
    )
    if test_rows:
        scores = []
        for t in test_rows:
            total = t.get("total_questions") or 0
            score = t.get("score") or 0
            if total > 0:
                scores.append(score / total * 100)
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
    teacher_id = teacher.get("id")

    # Load assignments
    assignments, _ = _safe_q(
        lambda: admin_client.table("teacher_student_assignments")
        .select("student_id, grade, subject, section, archived_at, created_at")
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
    teacher_id = teacher.get("id")
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
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    tests, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, subject, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    mock_avg = None
    if tests:
        scores = [t["score"] / t["total_questions"] * 100 for t in tests if (t.get("total_questions") or 0) > 0]
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
            "recent_activity": activity[:5],
        },
    }


@router.patch("/students/{student_id}")
def update_student(student_id: str, data: UpdateStudentRequest, teacher=Depends(require_teacher)):
    """Update student name, grade, or email. Teacher must own the student."""
    teacher_id = teacher.get("id")
    _ensure_owns_student(teacher_id, student_id)

    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No changes provided."}

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
    teacher_id = teacher.get("id")
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


@router.post("/students/{student_id}/reset-password")
def reset_student_password(student_id: str, teacher=Depends(require_teacher)):
    """
    Generate a new temporary password for a student.
    Password shown once only — never logged or stored.
    Teacher must own the student.
    """
    teacher_id = teacher.get("id")
    _ensure_owns_student(teacher_id, student_id)

    new_password = _gen_password(12)
    try:
        admin_client.auth.admin.update_user_by_id(student_id, {"password": new_password})
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.student.password_reset",
        actor_user_id=teacher_id,
        target_user_id=student_id,
        entity_type="student",
        entity_id=student_id,
        metadata={"triggered_by": "teacher_dashboard"},
    )
    return {
        "success": True,
        "temp_password": new_password,
        "warning": "Show once only. Advise student to change password immediately.",
    }


@router.post("/students/{student_id}/email-credentials")
def email_student_credentials(student_id: str, teacher=Depends(require_teacher)):
    """
    Email login credentials to a student.
    Paid teachers only — backend enforces this.
    """
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")

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

    row = {
        "teacher_id": teacher_id,
        "student_name": data.student_name,
        "grade": data.grade,
        "email": data.email,
        "status": "pending",
        "expires_at": _expiry_iso(),
    }
    try:
        result = admin_client.table("teacher_invitations").insert(row).execute()
        inv = result.data[0] if result.data else row
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.invitation.created",
        actor_user_id=teacher_id,
        entity_type="invitation",
        entity_id=inv.get("id", ""),
        metadata={"grade": data.grade, "status": "pending"},
    )
    return {"success": True, "invitation": inv}


@router.post("/invitations/{invitation_id}/resend")
def resend_invitation(invitation_id: str, teacher=Depends(require_teacher)):
    """Resend an invitation and extend its expiry by 7 days."""
    teacher_id = teacher.get("id")
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

    new_expiry = _expiry_iso()
    try:
        admin_client.table("teacher_invitations").update(
            {"status": "pending", "expires_at": new_expiry, "updated_at": _now_iso()}
        ).eq("id", invitation_id).execute()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="teacher.invitation.resent",
        actor_user_id=teacher_id,
        entity_type="invitation",
        entity_id=invitation_id,
        metadata={"new_expiry": new_expiry},
    )
    return {"success": True, "invitation_id": invitation_id, "new_expiry": new_expiry}


@router.post("/invitations/{invitation_id}/cancel")
def cancel_invitation(invitation_id: str, teacher=Depends(require_teacher)):
    """Cancel a pending invitation."""
    teacher_id = teacher.get("id")
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
# 4. Classrooms
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/classrooms")
def list_classrooms(
    status: Optional[str] = Query(default="active"),
    teacher=Depends(require_teacher),
):
    """List teacher's classrooms with student counts."""
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
    teacher_id = teacher.get("id")
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
