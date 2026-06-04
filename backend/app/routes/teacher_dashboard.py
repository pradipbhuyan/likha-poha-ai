from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.admin_control import build_activity_by_username
from app.services.auth_service import admin_client, require_teacher

router = APIRouter()


class TeacherNoteRequest(BaseModel):
    student_id: str
    subject: str = ""
    chapter: str = ""
    note: str


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


def load_progress_by_username(usernames: list[str]):
    """Load recent chapter-progress rows for assigned students."""
    if not usernames:
        return {}

    response = (
        admin_client
        .table("student_progress")
        .select("*")
        .in_("username", usernames)
        .order("updated_at", desc=True)
        .execute()
    )

    progress_by_username = {username: [] for username in usernames}

    for row in response.data or []:
        username = row.get("username")
        if username in progress_by_username:
            progress_by_username[username].append(row)

    return progress_by_username


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
    """Reject teacher note writes for students not assigned to that teacher."""
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
    usernames = [
        profile_row.get("username")
        for profile_row in profiles_by_id.values()
        if profile_row.get("username")
    ]

    activity_by_username = build_activity_by_username(usernames)
    progress_by_username = load_progress_by_username(usernames)
    notes_by_student = load_notes_by_student(teacher_id, student_ids)

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
        progress_rows = progress_by_username.get(username, [])
        completed_count = len([
            item for item in progress_rows
            if item.get("completed")
        ])

        students.append({
            "profile": student,
            "assignments": student_assignments,
            "activity": activity_by_username.get(username, {}),
            "recent_progress": progress_rows[:5],
            "progress_summary": {
                "tracked_chapters": len(progress_rows),
                "completed_chapters": completed_count,
            },
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

    return {
        "success": True,
        "teacher": profile,
        "summary": {
            "assigned_students": len(students),
            "active_grades": grades,
            "subjects": subjects,
            "total_assignments": len(assignments),
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
