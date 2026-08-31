"""
bulk_import_service.py
─────────────────────────────────────────────────────────────────────────────
Core logic for bulk-creating student/teacher accounts from parsed rows —
shared by the admin API (app/routes/admin_bulk.py) and the standalone
Excel-import script (scripts/bulk_import_from_excel.py), so both go through
the exact same validation and account-creation path.

Design boundary: this only ever CREATES new accounts (via Supabase's secure
auth.admin.create_user) and links them to a school by setting profiles.
school_id — it never mutates an existing account beyond that, and never
touches subscription/payment fields.
"""
from __future__ import annotations

import secrets
import string

from app.routes.auth import STREAM_SUBJECTS, VALID_STREAMS
from app.services.auth_service import admin_client

# Single source of truth for the Excel template's column headers, shared by
# scripts/generate_bulk_import_template.py (writes these) and
# scripts/bulk_import_from_excel.py (reads these back and maps to the dict
# keys validate_*_rows/import_* expect) — the two scripts can never drift
# out of sync with each other since both import this mapping.
GRADE_OPTIONS = [f"Grade {n}" for n in range(5, 13)]
STREAM_OPTIONS = sorted(VALID_STREAMS)

TEACHER_COLUMNS = {
    "Teacher Name": "name",
    "Email": "email",
    "Temporary Password (optional — auto-generated if blank)": "temporary_password",
}

STUDENT_COLUMNS = {
    "Student Name": "name",
    "Grade": "grade",
    "Stream (required for Grade 11/12 only — PCM, PCB, PCMB, Commerce, or Humanities)": "stream",
    "Email (optional)": "email",
    "Assigned Teacher Email (optional, must match a row in the Teachers sheet)": "teacher_email",
    "Temporary Password (optional — auto-generated if blank)": "temporary_password",
}


def generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def school_exists(school_id: str) -> bool:
    resp = admin_client.table("schools").select("id").eq("id", school_id).limit(1).execute()
    return bool(resp.data)


def _username_taken(username: str) -> bool:
    resp = admin_client.table("profiles").select("id").ilike("username", username).limit(1).execute()
    return bool(resp.data)


def unique_username(desired: str) -> str:
    """
    Auto-disambiguate a bulk-import username against the platform-wide,
    case-insensitive unique index on profiles.username (see
    app/routes/auth.py's _reject_taken_username: two profiles sharing a
    username let each other's test scores/progress leak through legacy
    username-keyed queries — this is not just cosmetic).

    A bulk import of hundreds of real names WILL hit common-name collisions
    (multiple "Priya Sharma"s across a school or the platform), so unlike
    the one-by-one signup/create-student flow — which rejects and asks the
    human to pick another name — this appends " (2)", " (3)", ... until the
    name is free, so a common name never fails or blocks the rest of the
    batch.
    """
    clean = desired.strip()
    candidate = clean
    n = 2
    while _username_taken(candidate):
        candidate = f"{clean} ({n})"
        n += 1
    return candidate


def _find_teacher_id_by_email(email: str, school_id: str | None) -> str | None:
    if not email:
        return None
    query = admin_client.table("profiles").select("id, school_id").eq("email", email.strip().lower()).eq("role", "teacher")
    resp = query.limit(1).execute()
    teacher = (resp.data or [None])[0]
    return teacher["id"] if teacher else None


# ── Students ──────────────────────────────────────────────────────────────────

def validate_student_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (preview_rows, validation_errors) — no DB writes."""
    preview_rows, validation_errors = [], []
    for i, row in enumerate(rows):
        issues = []
        name = (row.get("name") or "").strip()
        grade = (row.get("grade") or "").strip()
        email = (row.get("email") or "").strip()
        stream = (row.get("stream") or "").strip()

        if not name:
            issues.append("name is required")
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            issues.append(f"invalid email: {email}")
        if not grade.startswith("Grade "):
            issues.append(f"grade must start with 'Grade ': {grade}")
        elif grade in ("Grade 11", "Grade 12") and stream not in VALID_STREAMS:
            # A Grade 11/12 student's subject list is derived from their
            # stream — without one they'd get zero cbse_subjects, same class
            # of bug the auth.py signup path was fixed for on 2026-08-27.
            issues.append(
                f"stream is required for {grade}: choose one of {', '.join(sorted(VALID_STREAMS))}"
            )

        preview_rows.append({
            "row": i + 1,
            "name": name,
            "grade": grade,
            "stream": stream,
            "email": email or f"student{i + 1}@temp.local",
            "has_email": bool(email),
            "errors": issues,
        })
        if issues:
            validation_errors.append({"row": i + 1, "issues": issues})
    return preview_rows, validation_errors


def import_students(rows: list[dict], school_id: str | None = None) -> dict:
    """
    Create student accounts from already-validated rows.

    Each row may include a "teacher_email" — if it matches an existing
    teacher account, the new student is also linked via
    teacher_student_assignments (best-effort, never blocks account creation).
    """
    created, failed, results = 0, 0, []

    for i, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        grade = (row.get("grade") or "").strip()
        email = (row.get("email") or "").strip() or f"student_{secrets.token_hex(6)}@auto.local"
        password = (row.get("temporary_password") or "").strip() or generate_temp_password(12)
        teacher_email = (row.get("teacher_email") or "").strip()
        stream = (row.get("stream") or "").strip()

        try:
            auth_resp = admin_client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
            })
            user_id = auth_resp.user.id if auth_resp.user else None
            if not user_id:
                results.append({"row": i + 1, "name": name, "success": False, "error": "Auth user creation returned no user"})
                failed += 1
                continue

            username = unique_username(name)
            profile = {
                "id": user_id,
                "username": username,
                "email": email,
                "role": "student",
                "grade": grade,
                "board": "CBSE",
                "account_status": "active",
                "access_cbse": False,
                "subscription_plan": "free",
            }
            if grade in ("Grade 11", "Grade 12") and stream in VALID_STREAMS:
                profile["stream"] = stream
                profile["cbse_subjects"] = STREAM_SUBJECTS[stream]
            if school_id:
                profile["school_id"] = school_id
            admin_client.table("profiles").upsert(profile).execute()

            teacher_link = None
            if teacher_email:
                teacher_id = _find_teacher_id_by_email(teacher_email, school_id)
                if teacher_id:
                    admin_client.table("teacher_student_assignments").insert({
                        "teacher_id": teacher_id,
                        "student_id": user_id,
                        "grade": grade or "Grade 9",
                        "subject": "General",
                        "section": "",
                    }).execute()
                    teacher_link = "linked"
                else:
                    teacher_link = "teacher not found — create the teacher first"

            result_row = {
                "row": i + 1, "name": name, "username": username, "email": email, "success": True,
                "user_id": user_id, "temp_password": password,
            }
            if teacher_email:
                result_row["teacher_link"] = teacher_link
            results.append(result_row)
            created += 1
        except Exception as exc:
            results.append({"row": i + 1, "name": name, "email": email, "success": False, "error": str(exc)[:120]})
            failed += 1

    return {"created": created, "failed": failed, "results": results}


# ── Teachers ──────────────────────────────────────────────────────────────────

def validate_teacher_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (preview_rows, validation_errors) — no DB writes."""
    preview_rows, validation_errors = [], []
    for i, row in enumerate(rows):
        issues = []
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip()

        if not name:
            issues.append("name is required")
        if not email:
            issues.append("email is required for a teacher account")
        elif "@" not in email or "." not in email.split("@")[-1]:
            issues.append(f"invalid email: {email}")

        preview_rows.append({"row": i + 1, "name": name, "email": email, "errors": issues})
        if issues:
            validation_errors.append({"row": i + 1, "issues": issues})
    return preview_rows, validation_errors


def import_teachers(rows: list[dict], school_id: str | None = None) -> dict:
    """Create teacher accounts from already-validated rows."""
    created, failed, results = 0, 0, []

    for i, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip()
        password = (row.get("temporary_password") or "").strip() or generate_temp_password(12)

        try:
            auth_resp = admin_client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
            })
            user_id = auth_resp.user.id if auth_resp.user else None
            if not user_id:
                results.append({"row": i + 1, "name": name, "success": False, "error": "Auth user creation returned no user"})
                failed += 1
                continue

            username = unique_username(name)
            profile = {
                "id": user_id,
                "username": username,
                "email": email,
                "role": "teacher",
                "account_status": "active",
            }
            if school_id:
                profile["school_id"] = school_id
            admin_client.table("profiles").upsert(profile).execute()

            results.append({
                "row": i + 1, "name": name, "username": username, "email": email, "success": True,
                "user_id": user_id, "temp_password": password,
            })
            created += 1
        except Exception as exc:
            results.append({"row": i + 1, "name": name, "email": email, "success": False, "error": str(exc)[:120]})
            failed += 1

    return {"created": created, "failed": failed, "results": results}
