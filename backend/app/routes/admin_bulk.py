"""
admin_bulk.py  —  /api/admin/bulk/*
─────────────────────────────────────────────────────────────────────────────
Bulk admin operations — admin only.

All endpoints require role=admin via require_admin.
All sensitive actions are audited.
Plaintext passwords are NEVER logged or stored.

Endpoints:
  POST /assign-teacher      — bulk assign multiple students to a teacher
  POST /reset-passwords     — bulk generate new temp passwords for students
  POST /grant-access        — bulk grant admin access to selected users
  POST /export              — export selected users as CSV bytes (no secrets)
  POST /import-students     — import students from parsed CSV rows, optionally linked to a school
  POST /import-teachers     — import teachers from parsed CSV rows, optionally linked to a school

Account-creation logic for the last two lives in
app/services/bulk_import_service.py so the standalone Excel-import script
(scripts/bulk_import_from_excel.py) can reuse it directly, without going
through HTTP.
"""
from __future__ import annotations

import csv
import io
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from app.services import bulk_import_service
from app.services.auth_service import admin_client, require_admin
from app.services.audit_log_service import write_audit_event

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _safe_db(fn):
    """Run a Supabase query, return (data, error_str)."""
    try:
        r = fn()
        return (r.data or []), None
    except Exception as exc:
        return [], str(exc)[:200]


# ── 1. Bulk Assign Teacher ────────────────────────────────────────────────────

class BulkAssignRequest(BaseModel):
    teacher_id: str
    student_ids: list[str] = Field(..., min_length=1, max_length=100)
    grade: str | None = None
    subject: str | None = None
    section: str | None = None


@router.post("/assign-teacher")
def bulk_assign_teacher(req: BulkAssignRequest, admin=Depends(require_admin)):
    """
    Assign multiple students to a teacher in one call.
    Skips duplicate assignments (idempotent).
    Returns {assigned, skipped, failed, errors}.
    Admin-only. Audited.
    """
    # Validate teacher exists
    teachers, _ = _safe_db(
        lambda: admin_client.table("profiles")
        .select("id, username, role")
        .eq("id", req.teacher_id)
        .eq("role", "teacher")
        .limit(1)
        .execute()
    )
    if not teachers:
        return {"success": False, "error": "Teacher not found or not a teacher role."}

    # Check existing assignments to avoid duplicates
    existing, _ = _safe_db(
        lambda: admin_client.table("teacher_student_assignments")
        .select("student_id")
        .eq("teacher_id", req.teacher_id)
        .in_("student_id", req.student_ids)
        .execute()
    )
    already_assigned = {r["student_id"] for r in existing}

    assigned, skipped, failed, errors = 0, 0, 0, []

    for sid in req.student_ids:
        if sid in already_assigned:
            skipped += 1
            continue
        _, err = _safe_db(
            lambda sid=sid: admin_client.table("teacher_student_assignments")
            .insert({
                "teacher_id": req.teacher_id,
                "student_id": sid,
                "grade": req.grade or "Grade 9",
                "subject": req.subject or "General",
                "section": req.section or "",
            })
            .execute()
        )
        if err:
            failed += 1
            errors.append({"student_id": sid, "error": err})
        else:
            assigned += 1

    write_audit_event(
        event_type="bulk.assign_teacher",
        actor_user_id=admin.get("id"),
        entity_type="teacher",
        entity_id=req.teacher_id,
        metadata={
            "assigned": assigned,
            "skipped": skipped,
            "failed": failed,
            "student_count": len(req.student_ids),
        },
    )

    return {
        "success": True,
        "assigned": assigned,
        "skipped": skipped,
        "failed": failed,
        "errors": errors[:20],  # cap error list size
    }


# ── 2. Bulk Password Reset ────────────────────────────────────────────────────

class BulkResetRequest(BaseModel):
    student_ids: list[str] = Field(..., min_length=1, max_length=50)


@router.post("/reset-passwords")
def bulk_reset_passwords(req: BulkResetRequest, admin=Depends(require_admin)):
    """
    Generate and set new temporary passwords for selected students.

    Security guarantees:
    - Passwords are generated server-side using secrets.
    - Plaintext passwords are NEVER stored in audit logs or DB.
    - Each password is returned once only.
    - Caller is responsible for securely communicating passwords to students.
    Admin-only. Audited (without passwords).
    """
    results = []
    reset_count, failed_count = 0, 0

    for sid in req.student_ids:
        new_password = _generate_temp_password(12)

        # Fetch user to validate
        users, _ = _safe_db(
            lambda sid=sid: admin_client.table("profiles")
            .select("id, username, email, role")
            .eq("id", sid)
            .in_("role", ["student", "child"])
            .limit(1)
            .execute()
        )
        if not users:
            results.append({
                "student_id": sid,
                "success": False,
                "error": "User not found or not a student",
            })
            failed_count += 1
            continue

        u = users[0]

        # Update password via Supabase Auth admin API
        try:
            admin_client.auth.admin.update_user_by_id(
                sid, {"password": new_password}
            )
            results.append({
                "student_id": sid,
                "username": u.get("username", ""),
                "email": u.get("email", ""),
                "success": True,
                "temp_password": new_password,  # shown once only
            })
            reset_count += 1
        except Exception as exc:
            results.append({
                "student_id": sid,
                "success": False,
                "error": str(exc)[:100],
            })
            failed_count += 1

    # Audit without passwords
    write_audit_event(
        event_type="bulk.password_reset",
        actor_user_id=admin.get("id"),
        entity_type="student_batch",
        metadata={
            "reset_count": reset_count,
            "failed_count": failed_count,
            "student_count": len(req.student_ids),
            # NO passwords in audit metadata
        },
    )

    return {
        "success": True,
        "reset_count": reset_count,
        "failed_count": failed_count,
        "results": results,
        "warning": "Temp passwords shown once only. Share securely and advise students to change immediately.",
    }


# ── 3. Bulk Grant Access ──────────────────────────────────────────────────────

class BulkGrantRequest(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=200)
    # Do NOT overwrite active paid subscriptions unless confirmed
    skip_active_paid: bool = True


@router.post("/grant-access")
def bulk_grant_access(req: BulkGrantRequest, admin=Depends(require_admin)):
    """
    Grant admin access (access_cbse=True, subscription_plan='free',
    subscription_expires_at=None) to selected users.

    By default skips users with active paid subscriptions unless
    skip_active_paid=False.
    Admin-only. Audited.
    """
    now_iso = _now()
    granted, skipped_paid, failed, errors = 0, 0, 0, []

    # Fetch all profiles in one query
    profiles, fetch_err = _safe_db(
        lambda: admin_client.table("profiles")
        .select("id, access_cbse, subscription_plan, subscription_expires_at")
        .in_("id", req.user_ids)
        .execute()
    )
    if fetch_err:
        return {"success": False, "error": fetch_err}

    profile_map = {p["id"]: p for p in profiles}

    for uid in req.user_ids:
        profile = profile_map.get(uid)
        if not profile:
            failed += 1
            errors.append({"user_id": uid, "error": "User not found"})
            continue

        # Skip active paid subscriptions if requested
        if req.skip_active_paid:
            expires = profile.get("subscription_expires_at")
            plan = profile.get("subscription_plan", "free")
            has_paid = plan != "free" and expires and expires > now_iso
            if has_paid:
                skipped_paid += 1
                continue

        _, err = _safe_db(
            lambda uid=uid: admin_client.table("profiles")
            .update({
                "access_cbse": True,
                "subscription_plan": "free",
                "subscription_expires_at": None,
            })
            .eq("id", uid)
            .execute()
        )
        if err:
            failed += 1
            errors.append({"user_id": uid, "error": err})
        else:
            granted += 1

    write_audit_event(
        event_type="bulk.grant_access",
        actor_user_id=admin.get("id"),
        entity_type="user_batch",
        metadata={
            "granted": granted,
            "skipped_active_paid": skipped_paid,
            "failed": failed,
            "user_count": len(req.user_ids),
            "skip_active_paid": req.skip_active_paid,
        },
    )

    return {
        "success": True,
        "granted": granted,
        "skipped_active_paid": skipped_paid,
        "failed": failed,
        "errors": errors[:20],
    }


# ── 4. Bulk Export ────────────────────────────────────────────────────────────

class BulkExportRequest(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=1000)


@router.post("/export")
def bulk_export_users(req: BulkExportRequest, admin=Depends(require_admin)):
    """
    Export selected users as CSV.
    Excludes secrets, passwords, tokens, payment IDs.
    Admin-only. Audited.
    """
    profiles, err = _safe_db(
        lambda: admin_client.table("profiles")
        .select(
            "id, username, email, role, grade, board, "
            "subscription_plan, account_status, access_cbse, "
            "daily_token_limit, monthly_token_limit, created_at"
        )
        .in_("id", req.user_ids)
        .execute()
    )

    if err:
        return {"success": False, "error": err}

    # Build CSV in-memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "username", "email", "role", "grade", "board",
        "subscription_plan", "account_status", "access_cbse",
        "daily_token_limit", "monthly_token_limit", "created_at",
    ], extrasaction="ignore")
    writer.writeheader()
    for p in profiles:
        writer.writerow(p)

    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")

    write_audit_event(
        event_type="bulk.export_users",
        actor_user_id=admin.get("id"),
        entity_type="user_batch",
        metadata={"count": len(profiles)},
    )

    filename = f"bulk_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 5. Bulk Import Students ───────────────────────────────────────────────────

class CsvStudentRow(BaseModel):
    name: str
    grade: str = "Grade 9"
    stream: str | None = None   # required for Grade 11/12: PCM|PCB|PCMB|Commerce|Humanities
    email: str | None = None
    parent_email: str | None = None
    teacher_email: str | None = None
    temporary_password: str | None = None


class BulkImportRequest(BaseModel):
    rows: list[CsvStudentRow] = Field(..., min_length=1, max_length=1000)
    school_id: str | None = None   # if given, imported students are linked to this school
    confirmed: bool = False        # Must be True to actually run import


@router.post("/import-students")
def bulk_import_students(req: BulkImportRequest, admin=Depends(require_admin)):
    """
    Import students from parsed CSV rows.

    Two-phase:
    1. confirmed=False  → validate rows, return preview (no DB writes)
    2. confirmed=True   → create students using secure auth flow

    A row's teacher_email, if it matches an existing teacher, also creates a
    teacher_student_assignments link — best-effort, never blocks the import.

    Security:
    - Passwords never logged or audited in plaintext.
    - If temporary_password omitted, generates one server-side.
    - Uses supabase.auth.admin.create_user for secure creation.
    Admin-only. Audited.
    """
    if req.school_id and not bulk_import_service.school_exists(req.school_id):
        return {"success": False, "error": f"No school found for school_id={req.school_id}"}

    row_dicts = [r.model_dump() for r in req.rows]
    preview_rows, validation_errors = bulk_import_service.validate_student_rows(row_dicts)

    if not req.confirmed:
        return {
            "success": True,
            "preview": True,
            "total": len(req.rows),
            "valid_count": len(req.rows) - len(validation_errors),
            "error_count": len(validation_errors),
            "validation_errors": validation_errors[:20],
            "preview_rows": preview_rows[:10],
            "message": "Set confirmed=true to proceed with import after reviewing.",
        }

    if validation_errors:
        return {
            "success": False,
            "error": f"{len(validation_errors)} row(s) have validation errors. Fix before importing.",
            "validation_errors": validation_errors[:20],
        }

    outcome = bulk_import_service.import_students(row_dicts, school_id=req.school_id)

    # Audit import summary — NO passwords in metadata
    write_audit_event(
        event_type="bulk.import_students",
        actor_user_id=admin.get("id"),
        entity_type="student_batch",
        metadata={
            "created": outcome["created"],
            "failed": outcome["failed"],
            "total_rows": len(req.rows),
            "school_id": req.school_id,
        },
    )

    return {
        "success": True,
        "created": outcome["created"],
        "failed": outcome["failed"],
        "results": outcome["results"],
        "warning": "Temp passwords shown once only. Store securely and share with students.",
    }


# ── 6. Bulk Import Teachers ───────────────────────────────────────────────────

class CsvTeacherRow(BaseModel):
    name: str
    email: str
    temporary_password: str | None = None


class BulkImportTeachersRequest(BaseModel):
    rows: list[CsvTeacherRow] = Field(..., min_length=1, max_length=1000)
    school_id: str | None = None   # if given, imported teachers are linked to this school
    confirmed: bool = False        # Must be True to actually run import


@router.post("/import-teachers")
def bulk_import_teachers(req: BulkImportTeachersRequest, admin=Depends(require_admin)):
    """
    Import teachers from parsed CSV rows — same two-phase contract as
    /import-students. Unlike students, a teacher's email is required (they
    need it to log in themselves).
    """
    if req.school_id and not bulk_import_service.school_exists(req.school_id):
        return {"success": False, "error": f"No school found for school_id={req.school_id}"}

    row_dicts = [r.model_dump() for r in req.rows]
    preview_rows, validation_errors = bulk_import_service.validate_teacher_rows(row_dicts)

    if not req.confirmed:
        return {
            "success": True,
            "preview": True,
            "total": len(req.rows),
            "valid_count": len(req.rows) - len(validation_errors),
            "error_count": len(validation_errors),
            "validation_errors": validation_errors[:20],
            "preview_rows": preview_rows[:10],
            "message": "Set confirmed=true to proceed with import after reviewing.",
        }

    if validation_errors:
        return {
            "success": False,
            "error": f"{len(validation_errors)} row(s) have validation errors. Fix before importing.",
            "validation_errors": validation_errors[:20],
        }

    outcome = bulk_import_service.import_teachers(row_dicts, school_id=req.school_id)

    write_audit_event(
        event_type="bulk.import_teachers",
        actor_user_id=admin.get("id"),
        entity_type="teacher_batch",
        metadata={
            "created": outcome["created"],
            "failed": outcome["failed"],
            "total_rows": len(req.rows),
            "school_id": req.school_id,
        },
    )

    return {
        "success": True,
        "created": outcome["created"],
        "failed": outcome["failed"],
        "results": outcome["results"],
        "warning": "Temp passwords shown once only. Store securely and share with teachers.",
    }
