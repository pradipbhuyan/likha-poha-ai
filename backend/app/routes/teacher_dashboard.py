from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.admin_control import build_activity_by_profile_id
from app.services.auth_service import admin_client, require_teacher, create_auth_user
from app.services.offer_access_service import is_free_tier_user

router = APIRouter()

# ── Plan-based student limits ──────────────────────────────────────────────
FREE_TEACHER_MAX_STUDENTS = 10
PAID_TEACHER_MAX_STUDENTS = 30

_TEACHER_EMAIL_DOMAIN = "teacher.likhapoha.in"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TeacherNoteRequest(BaseModel):
    student_id: str
    subject: str = ""
    chapter: str = ""
    note: str


class CreateStudentRequest(BaseModel):
    """Teacher-initiated student creation request."""
    username: str                   # student display name — required
    grade: str                      # e.g. "Grade 9" — required
    password: str                   # temporary password — required, never returned
    email: Optional[str] = None     # optional — real email or omit for synthetic
    subject: Optional[str] = None   # initial subject assignment (default "General")
    section: Optional[str] = None   # optional class section


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def load_teacher_assignments(teacher_id: str):
    """Load every student assignment owned by the signed-in teacher."""
    response = (
        admin_client
        .table("teacher_student_assignments")
        .select("*")
        .eq("teacher_id", teacher_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def load_profiles_by_id(profile_ids: list[str]):
    """Load profile rows for assigned students and return them keyed by id."""
    if not profile_ids:
        return {}
    response = (
        admin_client
        .table("profiles")
        .select("*")
        .in_("id", profile_ids)
        .execute()
    )
    return {
        row.get("id"): row
        for row in response.data or []
        if row.get("id")
    }


def load_progress_by_profile_id(profile_ids: list[str]):
    """Load chapter progress keyed by immutable assigned-student profile ID."""
    if not profile_ids:
        return {}
    response = (
        admin_client
        .table("student_progress")
        .select("*")
        .in_("profile_id", profile_ids)
        .order("updated_at", desc=True)
        .execute()
    )
    progress_by_profile_id = {profile_id: [] for profile_id in profile_ids}
    for row in response.data or []:
        profile_id = row.get("profile_id")
        if profile_id in progress_by_profile_id:
            progress_by_profile_id[profile_id].append(row)
    return progress_by_profile_id


def load_test_history_by_profile_id(profile_ids: list[str]):
    """Load mock-test results keyed by immutable assigned-student profile ID."""
    if not profile_ids:
        return {}

    response = (
        admin_client
        .table("test_history")
        .select("profile_id, username, subject, chapter, grade, mode, exam_type, difficulty, "
                "final_score, max_score, percentage, submitted_at")
        .in_("profile_id", profile_ids)
        .order("submitted_at", desc=True)
        .execute()
    )

    history_by_profile_id: dict[str, list] = {profile_id: [] for profile_id in profile_ids}
    for row in response.data or []:
        profile_id = row.get("profile_id")
        if profile_id in history_by_profile_id:
            history_by_profile_id[profile_id].append(row)

    return history_by_profile_id


def load_notes_by_student(teacher_id: str, student_ids: list[str]):
    """Load teacher notes for the dashboard student cards."""
    if not student_ids:
        return {}
    response = (
        admin_client
        .table("teacher_notes")
        .select("*")
        .eq("teacher_id", teacher_id)
        .in_("student_id", student_ids)
        .order("created_at", desc=True)
        .execute()
    )
    notes_by_student = {student_id: [] for student_id in student_ids}
    for row in response.data or []:
        student_id = row.get("student_id")
        if student_id in notes_by_student:
            notes_by_student[student_id].append(row)
    return notes_by_student


def ensure_assigned_student(teacher_id: str, student_id: str):
    """Reject teacher operations for students not assigned to that teacher."""
    response = (
        admin_client
        .table("teacher_student_assignments")
        .select("*")
        .eq("teacher_id", teacher_id)
        .eq("student_id", student_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=403,
            detail="Student is not assigned to this teacher.",
        )


def _count_assigned_active_students(teacher_id: str) -> int:
    """Count the number of students currently assigned to a teacher."""
    result = (
        admin_client
        .table("teacher_student_assignments")
        .select("student_id")
        .eq("teacher_id", teacher_id)
        .execute()
    )
    return len(result.data or [])


def _resolve_student_auth_email(requested_email: str | None, username: str) -> str:
    """
    Return the email used for Supabase auth for teacher-created students.
    Real email provided → use it. No email → synthetic so Supabase auth succeeds.
    """
    raw = (requested_email or "").strip()
    if raw and _EMAIL_RE.match(raw):
        return raw
    safe = re.sub(r"[^a-zA-Z0-9._-]", "", username) or "student"
    return f"{safe}@{_TEACHER_EMAIL_DOMAIN}"


def _is_synthetic_email(email: str) -> bool:
    """Return True if the email is a system-generated synthetic address."""
    return (
        (email or "").endswith(f"@{_TEACHER_EMAIL_DOMAIN}")
        or (email or "").endswith("@child.likhapoha.in")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/student-limit")
def get_student_limit(teacher=Depends(require_teacher)):
    """
    Return the teacher's current student count and plan-based maximum.

    Uses the canonical subscription resolver (is_free_tier_user):
      - Free Tier          → max 10 students
      - Active paid plan   → max 30 students
      - Expired paid plan  → falls back to Free Tier limit
    """
    teacher_id = teacher["profile"]["id"]
    is_free = is_free_tier_user(teacher_id)
    count = _count_assigned_active_students(teacher_id)
    max_students = FREE_TEACHER_MAX_STUDENTS if is_free else PAID_TEACHER_MAX_STUDENTS

    return {
        "success": True,
        "count": count,
        "max": max_students,
        "is_paid": not is_free,
        "at_limit": count >= max_students,
    }


@router.post("/create-student")
def create_student(data: CreateStudentRequest, teacher=Depends(require_teacher)):
    """
    Teacher creates a new student and auto-assigns them to their roster.

    Limits (enforced on backend, not just UI):
      - Free Tier teacher:  max 10 students
      - Paid plan teacher:  max 30 students
      - Expired paid plan:  Free Tier limit applies

    Security:
      - Temporary password is hashed by Supabase immediately — never stored in plain text.
      - Password is never returned in the API response or logged.
      - Student is auto-assigned to the creating teacher.
    """
    teacher_profile = teacher["profile"]
    teacher_id = teacher_profile["id"]

    # ── Input validation ─────────────────────────────────────────────────
    username = (data.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="NAME_REQUIRED")

    grade = (data.grade or "").strip()
    if not grade:
        raise HTTPException(status_code=400, detail="INVALID_GRADE")

    password = (data.password or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="PASSWORD_REQUIRED")
    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Temporary password must be at least 6 characters.",
        )

    from app.data.product_catalogue import ALL_GRADES_INCLUDING_HIDDEN  # noqa: PLC0415
    if grade not in ALL_GRADES_INCLUDING_HIDDEN:
        raise HTTPException(
            status_code=400,
            detail=f"INVALID_GRADE: '{grade}' is not a recognised grade.",
        )

    # Username uniqueness remains required for stable display names and older
    # compatibility paths. Ownership-sensitive dashboard queries now use the
    # student's immutable profile id. See
    # docs/sql/2026-08-16_check_username_uniqueness.sql and the "likha"
    # incident it predicted (2026-08-20).
    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(username)
    _reject_taken_username(username, client=admin_client)

    # ── Enforce student limit (backend) ──────────────────────────────────
    is_free = is_free_tier_user(teacher_id)
    max_students = FREE_TEACHER_MAX_STUDENTS if is_free else PAID_TEACHER_MAX_STUDENTS
    current_count = _count_assigned_active_students(teacher_id)

    if current_count >= max_students:
        tier_label = "Free Tier" if is_free else "paid plan"
        raise HTTPException(
            status_code=403,
            detail=(
                f"STUDENT_LIMIT_REACHED: You have reached the {max_students}-student limit "
                f"for your {tier_label}. Please contact admin to add more students."
            ),
        )

    # ── Resolve auth email ────────────────────────────────────────────────
    auth_email = _resolve_student_auth_email(data.email, username)

    # ── Create Supabase auth user ─────────────────────────────────────────
    # Supabase hashes the password immediately — it is never stored in plain text.
    auth_user = create_auth_user(
        email=auth_email,
        password=password,
        email_confirm=True,
    )

    # ── Build and insert profile ──────────────────────────────────────────
    student_profile = {
        "id": auth_user.id,
        "email": auth_email,
        "username": username,
        "role": "student",
        "parent_id": None,
        "family_id": None,
        "board": "CBSE",
        "grade": grade,
        "subscription_plan": "free",
        "account_status": "active",
        "access_cbse": False,   # Free Tier — limited access (DKB-only lessons, limited mock tests)
        "daily_token_limit": 0,
        "monthly_token_limit": 0,
        "cbse_subjects": [],
        "ai_model_preference": "default",
    }

    profile_resp = (
        admin_client
        .table("profiles")
        .insert(student_profile)
        .execute()
    )
    created_profile = profile_resp.data[0] if profile_resp.data else student_profile

    # ── Auto-assign student to this teacher ───────────────────────────────
    assignment_row = {
        "teacher_id": teacher_id,
        "student_id": auth_user.id,
        "grade": grade,
        "subject": (data.subject or "General").strip() or "General",
        "section": (data.section or "").strip(),   # empty string, not None — column is NOT NULL
    }
    admin_client.table("teacher_student_assignments").insert(assignment_row).execute()

    # ── Return safe profile — password NEVER included ─────────────────────
    return {
        "success": True,
        "student": {
            "id": created_profile.get("id") or auth_user.id,
            "username": created_profile.get("username", username),
            "grade": created_profile.get("grade", grade),
            "email": created_profile.get("email", auth_email),
            "has_real_email": not _is_synthetic_email(auth_email),
            "account_status": "active",
        },
        "student_count": current_count + 1,
        "max_students": max_students,
        "is_paid": not is_free,
    }


@router.post("/email-credentials/{student_id}")
def email_student_credentials(student_id: str, teacher=Depends(require_teacher)):
    """
    Send a password-reset link to a student's real email (paid teachers only).

    Security model:
      - Passwords are never read, decrypted, or transmitted — only a Supabase
        password-reset link is sent, so the student sets their own password.
      - Free-tier teachers cannot call this endpoint (checked on backend).
      - Only students assigned to this teacher can receive emails.
      - Students with synthetic/no email are blocked at this endpoint.
    """
    from app.services.supabase_client import supabase as anon_client  # noqa: PLC0415
    from app.config import settings  # noqa: PLC0415

    teacher_id = teacher["profile"]["id"]

    # ── Paid plan check (backend enforcement — not just UI) ───────────────
    if is_free_tier_user(teacher_id):
        raise HTTPException(
            status_code=403,
            detail="PAID_PLAN_REQUIRED: Email credentials feature requires a paid plan.",
        )

    # ── Student must be assigned to this teacher ──────────────────────────
    ensure_assigned_student(teacher_id, student_id)

    # ── Load student profile ──────────────────────────────────────────────
    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, email, username, role")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    student = profile_resp.data[0]
    student_email = student.get("email") or ""

    # ── Real email check ──────────────────────────────────────────────────
    if not student_email or _is_synthetic_email(student_email):
        raise HTTPException(
            status_code=400,
            detail="EMAIL_REQUIRED_FOR_CREDENTIAL_EMAIL: This student has no real email address.",
        )

    # ── Send password reset link — no password in email ───────────────────
    try:
        anon_client.auth.reset_password_for_email(
            student_email,
            options={
                "redirect_to": (
                    f"{getattr(settings, 'FRONTEND_URL', 'https://likhapoha.in')}"
                    "/reset-password"
                )
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to send email: {str(exc)}",
        )

    return {
        "success": True,
        "message": (
            f"Password reset link sent to {student_email}. "
            "The student can use it to set or reset their password."
        ),
        "student_username": student.get("username"),
    }


@router.get("/summary")
def get_teacher_summary(teacher=Depends(require_teacher)):
    """
    Return the teacher dashboard roster, progress, usage, and notes.

    The response is scoped to teacher_student_assignments, making the same API
    work for school teachers and independent tutors.
    """
    profile = teacher["profile"]
    teacher_id = profile["id"]

    assignments = load_teacher_assignments(teacher_id)
    student_ids = sorted({
        item.get("student_id")
        for item in assignments
        if item.get("student_id")
    })

    profiles_by_id = load_profiles_by_id(student_ids)
    activity_by_profile_id = build_activity_by_profile_id(profiles_by_id)
    progress_by_profile_id = load_progress_by_profile_id(student_ids)
    notes_by_student = load_notes_by_student(teacher_id, student_ids)
    test_history_by_profile_id = load_test_history_by_profile_id(student_ids)

    students = []

    for student_id in student_ids:
        student = profiles_by_id.get(student_id)
        if not student:
            continue

        username = student.get("username") or ""
        student_assignments = [
            item
            for item in assignments
            if item.get("student_id") == student_id
        ]
        progress_rows = progress_by_profile_id.get(student_id, [])
        completed_count = len([
            item for item in progress_rows
            if item.get("completed")
        ])

        # Determine if this student has a real email for credential sending
        student_email = student.get("email") or ""
        has_real_email = bool(student_email) and not _is_synthetic_email(student_email)

        # Mock test summary
        test_rows = test_history_by_profile_id.get(student_id, [])
        test_summary = {}
        if test_rows:
            percentages = [float(r.get("percentage") or 0) for r in test_rows]
            test_summary = {
                "total_tests": len(test_rows),
                "average_score": round(sum(percentages) / len(percentages), 1),
                "best_score": round(max(percentages), 1),
                "last_test_at": test_rows[0].get("submitted_at", "")[:19] if test_rows else None,
            }

        students.append({
            "profile": {**student, "has_real_email": has_real_email},
            "assignments": student_assignments,
            "activity": activity_by_profile_id.get(student_id, {}),
            "recent_progress": progress_rows[:5],
            "progress_summary": {
                "tracked_chapters": len(progress_rows),
                "completed_chapters": completed_count,
            },
            "recent_tests": test_rows[:10],
            "test_summary": test_summary,
            "notes": notes_by_student.get(student_id, [])[:5],
        })

    grades = sorted({
        item.get("grade")
        for item in assignments
        if item.get("grade")
    })
    subjects = sorted({
        item.get("subject")
        for item in assignments
        if item.get("subject")
    })

    # Include student limit info in the summary
    is_free = is_free_tier_user(teacher_id)
    max_students = FREE_TEACHER_MAX_STUDENTS if is_free else PAID_TEACHER_MAX_STUDENTS

    return {
        "success": True,
        "teacher": profile,
        "summary": {
            "assigned_students": len(students),
            "active_grades": grades,
            "subjects": subjects,
            "total_assignments": len(assignments),
            "student_limit": {
                "count": len(students),
                "max": max_students,
                "is_paid": not is_free,
                "at_limit": len(students) >= max_students,
            },
        },
        "students": students,
    }


@router.post("/notes")
def create_teacher_note(
    data: TeacherNoteRequest,
    teacher=Depends(require_teacher),
):
    """Create a teacher note for an assigned student."""
    note = data.note.strip()

    if not note:
        raise HTTPException(
            status_code=400,
            detail="Note cannot be empty.",
        )

    teacher_id = teacher["profile"]["id"]
    ensure_assigned_student(teacher_id, data.student_id)

    payload = {
        "teacher_id": teacher_id,
        "student_id": data.student_id,
        "subject": data.subject or "",
        "chapter": data.chapter or "",
        "note": note,
    }

    response = (
        admin_client
        .table("teacher_notes")
        .insert(payload)
        .execute()
    )

    return {
        "success": True,
        "note": response.data[0] if response.data else payload,
    }
