"""
admin_associations.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Admin management of teacher-student assignments and parent-child links,
plus the user-search endpoint that backs both association UIs.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client

router = APIRouter()


class AssignTeacherStudentRequest(BaseModel):
    teacher_id: str
    student_id: str
    grade: str = "Grade 9"
    subject: str = ""
    section: str = ""


class LinkParentChildRequest(BaseModel):
    parent_id: str
    child_id: str


@router.post("/teacher-assignments")
def assign_teacher_student(
    data: AssignTeacherStudentRequest,
    admin=Depends(require_admin),
):
    """Assign one student to one teacher for a subject/section context."""
    response = (
        admin_client
        .table("teacher_student_assignments")
        .upsert(
            {
                "teacher_id": data.teacher_id,
                "student_id": data.student_id,
                "grade": data.grade or "Grade 9",
                "subject": data.subject or "",
                "section": data.section or "",
            },
            on_conflict="teacher_id,student_id,subject",
        )
        .execute()
    )

    return {
        "success": True,
        "assignment": response.data[0] if response.data else {
            "teacher_id": data.teacher_id,
            "student_id": data.student_id,
            "grade": data.grade or "Grade 9",
            "subject": data.subject or "",
            "section": data.section or "",
        },
    }


@router.delete("/teacher-assignments/{assignment_id}")
def delete_teacher_assignment(
    assignment_id: str,
    admin=Depends(require_admin),
):
    """Remove one teacher-student assignment from the admin panel."""
    admin_client.table("teacher_student_assignments").delete().eq(
        "id",
        assignment_id,
    ).execute()

    return {
        "success": True,
        "message": "Teacher assignment removed.",
    }


@router.get("/search-users")
def search_users(q: str = "", role: str = "", limit: int = 20, admin=Depends(require_admin)):
    """
    Search users by username or email for the parent-child association UI.

    Parameters
    ----------
    q    : search query (username or email, case-insensitive)
    role : optional filter — "parent" | "student" | "" (all roles)
    """
    q = q.strip()
    query = admin_client.table("profiles").select(
        "id, username, email, role, grade, parent_id, family_id"
    )
    if role:
        query = query.eq("role", role)
    if q:
        # Supabase ilike on username OR email — run two queries and merge
        username_res = (
            admin_client.table("profiles")
            .select("id, username, email, role, grade, parent_id, family_id")
            .ilike("username", f"%{q}%")
            .eq("role", role) if role else
            admin_client.table("profiles")
            .select("id, username, email, role, grade, parent_id, family_id")
            .ilike("username", f"%{q}%")
        ).limit(limit).execute()

        email_res = (
            admin_client.table("profiles")
            .select("id, username, email, role, grade, parent_id, family_id")
            .ilike("email", f"%{q}%")
            .eq("role", role) if role else
            admin_client.table("profiles")
            .select("id, username, email, role, grade, parent_id, family_id")
            .ilike("email", f"%{q}%")
        ).limit(limit).execute()

        seen = set()
        merged = []
        for row in (username_res.data or []) + (email_res.data or []):
            if row["id"] not in seen:
                seen.add(row["id"])
                merged.append(row)
        return {"success": True, "users": merged[:limit]}

    result = query.limit(limit).execute()
    return {"success": True, "users": result.data or []}


@router.get("/parent-child-associations")
def list_parent_child_associations(
    q: str = "",
    limit: int = 50,
    admin=Depends(require_admin),
):
    """
    List all parent-child associations with profile details.
    Optionally filter by parent or child username/email query.
    """
    # Fetch students who have a parent_id set
    query = (
        admin_client
        .table("profiles")
        .select("id, username, email, grade, role, parent_id, family_id")
        .eq("role", "student")
        .not_.is_("parent_id", "null")
        .limit(limit)
    )
    if q:
        result = (
            admin_client
            .table("profiles")
            .select("id, username, email, grade, role, parent_id, family_id")
            .eq("role", "student")
            .not_.is_("parent_id", "null")
            .ilike("username", f"%{q}%")
            .limit(limit)
            .execute()
        )
    else:
        result = query.execute()

    children = result.data or []

    # Load parent profiles for each child
    parent_ids = list({c["parent_id"] for c in children if c.get("parent_id")})
    parents_by_id = {}
    if parent_ids:
        p_result = (
            admin_client
            .table("profiles")
            .select("id, username, email, role")
            .in_("id", parent_ids)
            .execute()
        )
        parents_by_id = {p["id"]: p for p in (p_result.data or [])}

    associations = [
        {
            "child": {
                "id": c["id"],
                "username": c.get("username"),
                "email": c.get("email"),
                "grade": c.get("grade"),
            },
            "parent": parents_by_id.get(c["parent_id"], {
                "id": c["parent_id"],
                "username": "(not found)",
                "email": None,
            }),
        }
        for c in children
    ]

    return {"success": True, "associations": associations, "count": len(associations)}


@router.post("/link-parent-child")
def link_parent_to_child(data: LinkParentChildRequest, admin=Depends(require_admin)):
    """
    Associate a parent with a child/student.

    Sets parent_id and family_id on the child's profile.
    Only admins can create or change parent-child associations.

    Rules:
    - The parent must have role="parent".
    - The child must have role="student".
    - A child can only have one parent_id at a time.
    - The child is also linked to the parent's family if the parent has one.
    """
    # Load parent profile
    parent_resp = (
        admin_client
        .table("profiles")
        .select("id, role, family_id, username")
        .eq("id", data.parent_id)
        .limit(1)
        .execute()
    )
    if not parent_resp.data:
        raise HTTPException(status_code=404, detail="Parent profile not found.")

    parent = parent_resp.data[0]
    if parent.get("role") != "parent":
        raise HTTPException(
            status_code=400,
            detail="UNAUTHORIZED: The selected user is not a parent.",
        )

    # Load child profile
    child_resp = (
        admin_client
        .table("profiles")
        .select("id, role, username, parent_id")
        .eq("id", data.child_id)
        .limit(1)
        .execute()
    )
    if not child_resp.data:
        raise HTTPException(status_code=404, detail="Child profile not found.")

    child = child_resp.data[0]
    if child.get("role") != "student":
        raise HTTPException(
            status_code=400,
            detail="UNAUTHORIZED: The selected user is not a student.",
        )

    # Update the child's parent_id and family_id
    update_payload: dict = {"parent_id": data.parent_id}
    if parent.get("family_id"):
        update_payload["family_id"] = parent["family_id"]

    admin_client.table("profiles").update(update_payload).eq("id", data.child_id).execute()

    return {
        "success": True,
        "message": (
            f"Student '{child.get('username')}' is now linked to "
            f"parent '{parent.get('username')}'."
        ),
        "child_id": data.child_id,
        "parent_id": data.parent_id,
        "family_id": parent.get("family_id"),
    }


@router.get("/teacher-student-associations")
def list_teacher_student_associations(
    q: str = "",
    limit: int = 100,
    admin=Depends(require_admin),
):
    """
    List all teacher-student assignments with teacher and student profile details.
    Optionally filter by teacher or student username/email query.
    """
    query = (
        admin_client
        .table("teacher_student_assignments")
        .select("id, teacher_id, student_id, grade, subject, section")
        .limit(limit)
    )
    result = query.execute()
    assignments = result.data or []

    # Load all teacher and student profiles in batch
    teacher_ids = list({a["teacher_id"] for a in assignments if a.get("teacher_id")})
    student_ids = list({a["student_id"] for a in assignments if a.get("student_id")})

    profiles: dict = {}
    if teacher_ids + student_ids:
        p_result = (
            admin_client
            .table("profiles")
            .select("id, username, email, role, grade")
            .in_("id", teacher_ids + student_ids)
            .execute()
        )
        profiles = {p["id"]: p for p in (p_result.data or [])}

    enriched = []
    for a in assignments:
        teacher = profiles.get(a.get("teacher_id"), {})
        student = profiles.get(a.get("student_id"), {})
        # Apply search filter on teacher or student username
        if q:
            q_lower = q.lower()
            if q_lower not in (teacher.get("username") or "").lower() and \
               q_lower not in (student.get("username") or "").lower():
                continue
        enriched.append({
            "id": a["id"],
            "teacher": {
                "id": a.get("teacher_id"),
                "username": teacher.get("username"),
                "email": teacher.get("email"),
            },
            "student": {
                "id": a.get("student_id"),
                "username": student.get("username"),
                "email": student.get("email"),
                "grade": student.get("grade"),
            },
            "grade": a.get("grade"),
            "subject": a.get("subject"),
            "section": a.get("section"),
        })

    return {"success": True, "associations": enriched, "count": len(enriched)}


@router.delete("/link-parent-child/{child_id}")
def unlink_parent_from_child(child_id: str, admin=Depends(require_admin)):
    """
    Remove the parent-child association for a student.
    Clears parent_id and family_id from the student's profile.
    Only admins can remove parent-child associations.
    """
    child_resp = (
        admin_client
        .table("profiles")
        .select("id, role, username, parent_id")
        .eq("id", child_id)
        .limit(1)
        .execute()
    )
    if not child_resp.data:
        raise HTTPException(status_code=404, detail="Child profile not found.")

    child = child_resp.data[0]
    if child.get("role") != "student":
        raise HTTPException(status_code=400, detail="Profile is not a student.")

    admin_client.table("profiles").update(
        {"parent_id": None, "family_id": None}
    ).eq("id", child_id).execute()

    return {
        "success": True,
        "message": f"Parent association removed from student '{child.get('username')}'.",
        "child_id": child_id,
    }
