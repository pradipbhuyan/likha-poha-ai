"""
principal_dashboard.py  —  /api/principal/*
─────────────────────────────────────────────────────────────────────────────
Principal-facing school oversight: teacher/student rosters, free-vs-paid
tier tracking, and the school-level incentive program.

Design boundary (deliberate, not incidental): every route here either (a)
reads aggregate/roster data already linked to the caller's school, or (b)
links/unlinks an *existing* account's profiles.school_id. Nothing here
creates a login, changes a role, or mutates a student's/teacher's
subscription plan or feature access — those stay exactly where they already
live (self-signup, teacher-created-student, payments.py). A school "reward"
is redeemed by the principal but fulfilled by the LikhaPohai team outside
this API — it never auto-grants anything to an individual account.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_principal
from app.services.offer_access_service import is_free_tier_user
from app.services.school_service import (
    SCHOOL_REWARD_CATALOG,
    compute_school_tier,
    next_tier_progress,
    rewards_unlocked_through,
)

router = APIRouter()


class LinkAccountRequest(BaseModel):
    email: str


class RedeemRewardRequest(BaseModel):
    reward_key: str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_school_or_404(principal_id: str) -> dict:
    resp = (
        admin_client
        .table("schools")
        .select("*")
        .eq("principal_id", principal_id)
        .limit(1)
        .execute()
    )
    school = (resp.data or [None])[0]
    if not school:
        raise HTTPException(status_code=404, detail="No school found for this principal account.")
    return school


def _load_last_active_by_profile_id(profile_ids: list[str]) -> dict[str, str | None]:
    """
    last_active_date lives on student_profiles (the gamification table), not
    on profiles itself — mirrors load_progress_by_profile_id's batch-by-id
    pattern in teacher_dashboard.py.
    """
    if not profile_ids:
        return {}
    resp = (
        admin_client
        .table("student_profiles")
        .select("profile_id, last_active_date")
        .in_("profile_id", profile_ids)
        .execute()
    )
    return {row["profile_id"]: row.get("last_active_date") for row in (resp.data or [])}


def _load_school_students(school_id: str) -> list[dict]:
    resp = (
        admin_client
        .table("profiles")
        .select(
            "id, username, email, grade, role, access_cbse, "
            "subscription_plan, subscription_expires_at, created_at"
        )
        .eq("school_id", school_id)
        .in_("role", ["student", "child"])
        .order("created_at", desc=True)
        .execute()
    )
    students = resp.data or []
    last_active_by_id = _load_last_active_by_profile_id([s["id"] for s in students])
    return [
        {**student, "last_active_date": last_active_by_id.get(student["id"])}
        for student in students
    ]


def _load_school_teachers(school_id: str) -> list[dict]:
    resp = (
        admin_client
        .table("profiles")
        .select("id, username, email, created_at, account_status")
        .eq("school_id", school_id)
        .eq("role", "teacher")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def _assigned_student_counts(teacher_ids: list[str]) -> dict[str, int]:
    """Count active assignments per teacher — mirrors teacher_dashboard.py's own counter."""
    if not teacher_ids:
        return {}
    resp = (
        admin_client
        .table("teacher_student_assignments")
        .select("teacher_id, student_id")
        .in_("teacher_id", teacher_ids)
        .execute()
    )
    counts: dict[str, int] = {tid: 0 for tid in teacher_ids}
    for row in resp.data or []:
        tid = row.get("teacher_id")
        if tid in counts:
            counts[tid] += 1
    return counts


def _split_free_paid(students: list[dict]) -> tuple[list[dict], list[dict]]:
    free, paid = [], []
    for student in students:
        (free if is_free_tier_user(student["id"], profile=student) else paid).append(student)
    return free, paid


# ─────────────────────────────────────────────────────────────────────────────
# School profile
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/school")
def get_school(principal=Depends(require_principal)):
    """Return the signed-in principal's own school profile, code, and status."""
    school = _get_school_or_404(principal["profile"]["id"])
    return {
        "success": True,
        "school": {
            "id": school["id"],
            "name": school["name"],
            "school_code": school["school_code"],
            "status": school["status"],
            "udise_code": school.get("udise_code"),
            "city": school.get("city", ""),
            "state": school.get("state", ""),
            "tier": school.get("tier", "bronze"),
        },
    }


@router.get("/dashboard-summary")
def get_dashboard_summary(principal=Depends(require_principal)):
    """
    One combined payload for the Overview tab: teacher/student counts,
    free-vs-paid split, and incentive-tier progress.
    """
    school = _get_school_or_404(principal["profile"]["id"])
    school_id = school["id"]

    teachers = _load_school_teachers(school_id)
    students = _load_school_students(school_id)
    free_students, paid_students = _split_free_paid(students)

    paid_count = len(paid_students)
    tier = compute_school_tier(paid_count)
    progress = next_tier_progress(paid_count)

    total_students = len(students)
    conversion_rate = round((paid_count / total_students) * 100, 1) if total_students else 0.0

    return {
        "success": True,
        "school": {"id": school_id, "name": school["name"], "status": school["status"]},
        "teacher_count": len(teachers),
        "student_count": total_students,
        "free_student_count": len(free_students),
        "paid_student_count": paid_count,
        "conversion_rate": conversion_rate,
        "tier": tier,
        "next_tier": progress,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Teachers
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/teachers")
def list_teachers(principal=Depends(require_principal)):
    """Roster of teachers linked to this school, with assigned-student counts."""
    school = _get_school_or_404(principal["profile"]["id"])
    teachers = _load_school_teachers(school["id"])
    counts = _assigned_student_counts([t["id"] for t in teachers])

    return {
        "success": True,
        "teachers": [
            {
                "id": t["id"],
                "username": t["username"],
                "email": t.get("email"),
                "account_status": t.get("account_status"),
                "assigned_students": counts.get(t["id"], 0),
                "joined_at": t.get("created_at"),
            }
            for t in teachers
        ],
    }


@router.post("/teachers/link")
def link_teacher(data: LinkAccountRequest, principal=Depends(require_principal)):
    """
    Link an *existing* teacher account to this school by email.

    Never creates an account or changes anything about it besides
    profiles.school_id — the teacher's login, plan, and role are untouched.
    """
    school = _get_school_or_404(principal["profile"]["id"])

    email_clean = (data.email or "").strip().lower()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required.")

    resp = (
        admin_client
        .table("profiles")
        .select("id, username, email, role, school_id")
        .eq("email", email_clean)
        .eq("role", "teacher")
        .limit(1)
        .execute()
    )
    teacher = (resp.data or [None])[0]
    if not teacher:
        raise HTTPException(status_code=404, detail="No teacher account found for that email.")

    admin_client.table("profiles").update({"school_id": school["id"]}).eq("id", teacher["id"]).execute()

    return {
        "success": True,
        "teacher": {"id": teacher["id"], "username": teacher["username"], "email": teacher["email"]},
    }


@router.delete("/teachers/{profile_id}")
def unlink_teacher(profile_id: str, principal=Depends(require_principal)):
    """Remove a teacher from this school's roster — only clears school_id."""
    school = _get_school_or_404(principal["profile"]["id"])

    resp = (
        admin_client
        .table("profiles")
        .select("id, school_id, role")
        .eq("id", profile_id)
        .limit(1)
        .execute()
    )
    teacher = (resp.data or [None])[0]
    if not teacher or teacher.get("role") != "teacher" or teacher.get("school_id") != school["id"]:
        raise HTTPException(status_code=404, detail="Teacher is not on your school roster.")

    admin_client.table("profiles").update({"school_id": None}).eq("id", profile_id).execute()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Students
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/students")
def list_students(tier: str = "", principal=Depends(require_principal)):
    """
    Roster of students linked to this school.

    `tier` filters to "free" or "paid"; omit/"" for all. Tier is shown so the
    principal can direct support where it's needed — it never changes what
    the student can already do, and doubt/chat content is never exposed here.
    """
    school = _get_school_or_404(principal["profile"]["id"])
    students = _load_school_students(school["id"])

    rows = []
    for s in students:
        is_free = is_free_tier_user(s["id"], profile=s)
        if tier == "free" and not is_free:
            continue
        if tier == "paid" and is_free:
            continue
        rows.append({
            "id": s["id"],
            "username": s["username"],
            "grade": s.get("grade"),
            "tier": "free" if is_free else "paid",
            "subscription_plan": s.get("subscription_plan"),
            "last_active_date": s.get("last_active_date"),
            "joined_at": s.get("created_at"),
        })

    return {"success": True, "students": rows}


@router.post("/students/link")
def link_student(data: LinkAccountRequest, principal=Depends(require_principal)):
    """Link an existing student account to this school by email — same contract as link_teacher."""
    school = _get_school_or_404(principal["profile"]["id"])

    email_clean = (data.email or "").strip().lower()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required.")

    resp = (
        admin_client
        .table("profiles")
        .select("id, username, email, role, school_id")
        .eq("email", email_clean)
        .in_("role", ["student", "child"])
        .limit(1)
        .execute()
    )
    student = (resp.data or [None])[0]
    if not student:
        raise HTTPException(status_code=404, detail="No student account found for that email.")

    admin_client.table("profiles").update({"school_id": school["id"]}).eq("id", student["id"]).execute()

    return {
        "success": True,
        "student": {"id": student["id"], "username": student["username"], "email": student["email"]},
    }


@router.delete("/students/{profile_id}")
def unlink_student(profile_id: str, principal=Depends(require_principal)):
    """Remove a student from this school's roster — only clears school_id."""
    school = _get_school_or_404(principal["profile"]["id"])

    resp = (
        admin_client
        .table("profiles")
        .select("id, school_id, role")
        .eq("id", profile_id)
        .limit(1)
        .execute()
    )
    student = (resp.data or [None])[0]
    if not student or student.get("role") not in ("student", "child") or student.get("school_id") != school["id"]:
        raise HTTPException(status_code=404, detail="Student is not on your school roster.")

    admin_client.table("profiles").update({"school_id": None}).eq("id", profile_id).execute()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Incentives
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/incentives")
def get_incentives(principal=Depends(require_principal)):
    """Tier, progress to next tier, unlocked rewards, and redemption history."""
    school = _get_school_or_404(principal["profile"]["id"])
    students = _load_school_students(school["id"])
    _, paid_students = _split_free_paid(students)
    paid_count = len(paid_students)

    tier = compute_school_tier(paid_count)
    progress = next_tier_progress(paid_count)

    history_resp = (
        admin_client
        .table("school_reward_redemptions")
        .select("id, reward_key, reward_label, status, created_at")
        .eq("school_id", school["id"])
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "success": True,
        "tier": tier,
        "paid_student_count": paid_count,
        "next_tier": progress,
        "unlocked_rewards": rewards_unlocked_through(tier),
        "catalog": SCHOOL_REWARD_CATALOG,
        "redemption_history": history_resp.data or [],
    }


@router.post("/incentives/redeem")
def redeem_reward(data: RedeemRewardRequest, principal=Depends(require_principal)):
    """
    Request a reward from the catalog unlocked at the school's current tier.

    This only logs a redemption request for the LikhaPohai team to fulfill —
    it never auto-grants anything to an individual student or teacher account.
    """
    school = _get_school_or_404(principal["profile"]["id"])
    students = _load_school_students(school["id"])
    _, paid_students = _split_free_paid(students)
    tier = compute_school_tier(len(paid_students))

    unlocked_keys = {r["key"] for r in rewards_unlocked_through(tier)}
    if data.reward_key not in unlocked_keys:
        raise HTTPException(
            status_code=403,
            detail="This reward isn't unlocked at your school's current tier yet.",
        )

    reward_label = next(
        (r["label"] for tier_rewards in SCHOOL_REWARD_CATALOG.values() for r in tier_rewards
         if r["key"] == data.reward_key),
        data.reward_key,
    )

    resp = (
        admin_client
        .table("school_reward_redemptions")
        .insert({
            "school_id": school["id"],
            "principal_id": principal["profile"]["id"],
            "reward_key": data.reward_key,
            "reward_label": reward_label,
            "tier_at_redemption": tier,
            "status": "requested",
        })
        .execute()
    )

    return {
        "success": True,
        "redemption": resp.data[0] if resp.data else None,
    }
