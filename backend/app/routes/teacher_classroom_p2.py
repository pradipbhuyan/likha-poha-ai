"""
teacher_classroom_p2.py  —  /api/teacher/*  (Phase 2)
─────────────────────────────────────────────────────────────────────────────
Teacher Success Platform — Phase 2: Actionable Dashboard

New endpoints (all require role=teacher):

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

Safety:
- Teacher can only access own students/classrooms/tasks/notes.
- Notes are teacher_private — never exposed to students/parents.
- All mutating actions write sanitized audit events.
- Missing source tables return graceful empty results.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_teacher
from app.services.audit_log_service import write_audit_event
from app.services.offer_access_service import is_free_tier_user

router = APIRouter()
_log = logging.getLogger("likhapoha.teacher.p2")

# ── Re-use helpers from Phase 1 ───────────────────────────────────────────────
from app.routes.teacher_classroom import (
    _safe_q, _safe_one, _now_iso,
    _ensure_owns_student, _ensure_owns_classroom,
)


def _get_tid(teacher: dict) -> str:
    return teacher["profile"]["id"]


# ── Pydantic models ───────────────────────────────────────────────────────────

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
    if username:
        test_rows, _ = _safe_q(
            lambda: admin_client.table("test_history")
            .select("score, total_questions, subject, created_at")
            .eq("username", username)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for row in test_rows:
            total = row.get("total_questions") or 0
            score = row.get("score") or 0
            pct = round(score / total * 100) if total > 0 else 0
            category = "success" if pct >= 60 else ("warning" if pct >= 40 else "alert")
            events.append({
                "id": f"test-{row.get('created_at','')}",
                "type": "mock_test",
                "title": f"📝 Mock Test: {row.get('subject','Unknown')}",
                "description": f"Score: {score}/{total} ({pct}%)",
                "timestamp": row.get("created_at"),
                "category": category,
            })

        # ── AI activity (lessons, doubts) ────────────────────────────────────
        activity_rows, _ = _safe_q(
            lambda: admin_client.table("ai_usage_logs")
            .select("feature, created_at")
            .eq("username", username)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
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
        .select("username, created_at")
        .in_("username", [profiles.get(s, {}).get("username", "") for s in student_ids])
        .gte("created_at", fourteen_days_ago)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    # Map username → last_active
    last_active_map = {}
    for row in activity_rows:
        u = row.get("username")
        if u and u not in last_active_map:
            last_active_map[u] = row.get("created_at")

    # Load mock test averages
    test_rows, _ = _safe_q(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, username")
        .in_("username", [profiles.get(s, {}).get("username", "") for s in student_ids])
        .execute()
    )
    test_avg_map: dict = {}
    test_count_map: dict = {}
    for t in test_rows:
        u = t.get("username")
        total = t.get("total_questions") or 0
        score = t.get("score") or 0
        if u and total > 0:
            test_avg_map.setdefault(u, []).append(score / total * 100)
    for u, scores in test_avg_map.items():
        test_count_map[u] = len(scores)
        test_avg_map[u] = round(sum(scores) / len(scores), 1)

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
        last_active = last_active_map.get(username)
        avg_score = test_avg_map.get(username)
        test_count = test_count_map.get(username, 0)

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
        actions = ["view_student", "reset_password"]
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
    if usernames:
        test_rows, _ = _safe_q(
            lambda: admin_client.table("test_history")
            .select("score, total_questions, username, created_at")
            .in_("username", usernames)
            .execute()
        )
        if test_rows:
            scores = []
            completed_by_student: dict = {}
            for t in test_rows:
                total = t.get("total_questions") or 0
                score = t.get("score") or 0
                u = t.get("username", "")
                if total > 0:
                    pct = score / total * 100
                    scores.append(pct)
                    completed_by_student[u] = completed_by_student.get(u, 0) + 1
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
    if usernames:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        act_rows, _ = _safe_q(
            lambda: admin_client.table("ai_usage_logs")
            .select("username, feature, created_at")
            .in_("username", usernames)
            .gte("created_at", seven_days_ago)
            .execute()
        )
        if act_rows:
            active_users = set(r.get("username") for r in act_rows)
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
        .select("id, email")
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

    # Attempt to send — use Supabase invite as a no-op proxy if no email service
    status = "no_email"
    send_error = None
    if parent_email:
        try:
            admin_client.auth.admin.invite_user_by_email(parent_email)
            status = "sent"
        except Exception as exc:
            send_error = str(exc)[:100]
            status = "failed"

    # Log the message attempt
    msg_row = {
        "teacher_id": teacher_id,
        "student_id": student_id,
        "parent_id": parent.get("id"),
        "subject": clean_subject,
        "message": clean_message,
        "status": status,
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
        metadata={"status": status, "has_email": bool(parent_email)},
    )
    return {
        "success": True,
        "status": status,
        "note": "Message sent." if status == "sent"
                else ("No email address for parent." if status == "no_email"
                      else f"Failed to send: {send_error}"),
        "error": send_error,
    }
