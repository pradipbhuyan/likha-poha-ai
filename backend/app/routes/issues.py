"""
issues.py — Student/User Issue Reporting + Admin Issue Management
─────────────────────────────────────────────────────────────────────────────
Student endpoints:
  POST /api/issues/report          — submit an issue
  GET  /api/issues/my-reports      — own reports

Admin endpoints:
  GET    /api/admin/issues          — list/filter all issues
  GET    /api/admin/issues/{id}     — get issue detail
  PATCH  /api/admin/issues/{id}     — update status/notes/assignee
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..services.auth_service import (
    admin_client, get_current_user, get_user_profile,
    require_admin,
)

router = APIRouter()

# ── Rate limit (in-memory, per user, per hour) ─────────────────────────────
_rate: dict[str, list[float]] = {}
_RATE_LIMIT = 10   # max issues per hour per user
_RATE_WINDOW = 3600  # seconds


def _check_rate(user_id: str) -> None:
    import time
    now = time.time()
    hits = [t for t in _rate.get(user_id, []) if now - t < _RATE_WINDOW]
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many issue reports. Try again later.")
    _rate[user_id] = hits + [now]


def _sanitize(text: str, max_len: int = 2000) -> str:
    """Strip HTML/script tags and truncate."""
    if not text:
        return text
    clean = html.escape(re.sub(r"<[^>]+>", "", text))
    return clean[:max_len]


VALID_ISSUE_TYPES = {
    "content_issue", "wrong_explanation", "missing_section",
    "wrong_formula", "wrong_answer", "broken_page", "login_issue", "other",
}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {"open", "triaged", "in_progress", "fixed", "wont_fix", "duplicate"}


# ── Pydantic models ────────────────────────────────────────────────────────────

class IssueReportIn(BaseModel):
    issue_type: str
    severity: str = "medium"
    title: Optional[str] = None
    description: str
    route: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_step: Optional[str] = None
    browser_info: Optional[dict] = None

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v):
        if v not in VALID_ISSUE_TYPES:
            raise ValueError(f"Invalid issue_type. Must be one of: {sorted(VALID_ISSUE_TYPES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        if v not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity. Must be one of: {sorted(VALID_SEVERITIES)}")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Description cannot be empty.")
        if len(v.strip()) < 10:
            raise ValueError("Description is too short (minimum 10 characters).")
        return v


class IssueUpdateIn(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    assigned_to_admin_id: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
        return v


def _sanitize_browser_info(bi: Optional[dict]) -> Optional[dict]:
    """Keep only safe browser info fields."""
    if not bi:
        return None
    safe_keys = {"userAgent", "platform", "language", "screenWidth", "screenHeight",
                 "timezone", "appVersion"}
    return {k: str(v)[:200] for k, v in bi.items() if k in safe_keys}


# ── Student: Submit Issue ──────────────────────────────────────────────────────

@router.post("/api/issues/report")
def report_issue(body: IssueReportIn, user=Depends(get_current_user)):
    _check_rate(user.id)

    profile = get_user_profile(user.id)
    role = profile.get("role", "unknown") if profile else "unknown"

    row = {
        "reporter_user_id": user.id,
        "reporter_role": role,
        "issue_type": body.issue_type,
        "severity": body.severity,
        "title": _sanitize(body.title or "", 200) or None,
        "description": _sanitize(body.description, 2000),
        "route": _sanitize(body.route or "", 500) or None,
        "grade": body.grade,
        "subject": body.subject,
        "chapter": _sanitize(body.chapter or "", 200) or None,
        "lesson_id": _sanitize(body.lesson_id or "", 200) or None,
        "lesson_step": _sanitize(body.lesson_step or "", 200) or None,
        "status": "open",
        "browser_info": _sanitize_browser_info(body.browser_info),
    }

    r = admin_client.table("product_issue_reports").insert(row).execute()
    if not r.data:
        raise HTTPException(500, "Failed to save issue report.")

    return {"success": True, "id": r.data[0]["id"],
            "message": "Thank you for reporting this issue. Our team will review it."}


# ── Student: My Reports ────────────────────────────────────────────────────────

@router.get("/api/issues/my-reports")
def get_my_reports(user=Depends(get_current_user)):
    r = (admin_client.table("product_issue_reports")
         .select("id,issue_type,severity,title,status,created_at,grade,subject,chapter")
         .eq("reporter_user_id", user.id)
         .order("created_at", desc=True)
         .limit(50)
         .execute())
    return {"success": True, "reports": r.data or []}


# ── Admin: List Issues ─────────────────────────────────────────────────────────

@router.get("/api/admin/issues")
def list_issues(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    _admin=Depends(require_admin),
):
    q = (admin_client.table("product_issue_reports")
         .select("*")
         .order("created_at", desc=True))
    if status:
        q = q.eq("status", status)
    if severity:
        q = q.eq("severity", severity)
    if issue_type:
        q = q.eq("issue_type", issue_type)
    if grade:
        q = q.eq("grade", grade)
    if subject:
        q = q.eq("subject", subject)
    if chapter:
        q = q.ilike("chapter", f"%{chapter}%")
    q = q.range(offset, offset + limit - 1)
    r = q.execute()

    # Summary counts for dashboard
    counts_r = (admin_client.table("product_issue_reports")
                .select("status,severity", count="exact").execute())

    return {
        "success": True,
        "total": len(r.data or []),
        "issues": r.data or [],
    }


@router.get("/api/admin/issues/summary")
def issues_summary(_admin=Depends(require_admin)):
    """Dashboard summary: open, critical, high, content, fixed this week."""
    try:
        all_r = (admin_client.table("product_issue_reports")
                 .select("status,severity,issue_type,created_at,resolved_at")
                 .execute())
        rows = all_r.data or []

        from datetime import timedelta
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        open_count = sum(1 for r in rows if r["status"] == "open")
        critical_count = sum(1 for r in rows if r["severity"] == "critical" and r["status"] not in ("fixed", "wont_fix"))
        high_count = sum(1 for r in rows if r["severity"] == "high" and r["status"] not in ("fixed", "wont_fix"))
        content_count = sum(1 for r in rows if r["issue_type"] in ("content_issue", "wrong_explanation", "missing_section", "wrong_formula", "wrong_answer"))
        fixed_this_week = sum(1 for r in rows
                              if r["status"] == "fixed" and r.get("resolved_at")
                              and datetime.fromisoformat(r["resolved_at"].replace("Z", "+00:00")) >= week_ago)

        return {
            "success": True,
            "open": open_count,
            "critical": critical_count,
            "high": high_count,
            "content_issues": content_count,
            "fixed_this_week": fixed_this_week,
            "total": len(rows),
        }
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.get("/api/admin/issues/{issue_id}")
def get_issue(issue_id: str, _admin=Depends(require_admin)):
    r = (admin_client.table("product_issue_reports")
         .select("*")
         .eq("id", issue_id)
         .single()
         .execute())
    if not r.data:
        raise HTTPException(404, "Issue not found.")
    return {"success": True, "issue": r.data}


@router.patch("/api/admin/issues/{issue_id}")
def update_issue(issue_id: str, body: IssueUpdateIn, admin_user=Depends(require_admin)):
    update_data: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if body.status:
        update_data["status"] = body.status
        if body.status in ("fixed", "wont_fix"):
            update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

    if body.admin_notes is not None:
        update_data["admin_notes"] = _sanitize(body.admin_notes, 5000)

    if body.assigned_to_admin_id is not None:
        update_data["assigned_to_admin_id"] = body.assigned_to_admin_id

    r = (admin_client.table("product_issue_reports")
         .update(update_data)
         .eq("id", issue_id)
         .execute())

    if not r.data:
        raise HTTPException(404, "Issue not found or update failed.")

    # Audit log
    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "issue_update",
            "target_id": issue_id,
            "details": json.dumps({k: v for k, v in update_data.items() if k != "updated_at"}),
        }).execute()
    except Exception:
        pass  # Non-critical

    return {"success": True, "issue": r.data[0]}


# ── Admin: Toggle can_report_issues per user ───────────────────────────────────

@router.patch("/api/admin/users/{user_id}/can-report-issues")
def toggle_can_report_issues(
    user_id: str,
    enabled: bool,
    admin_user=Depends(require_admin),
):
    """Allow or revoke a specific user's ability to see the Report Issue button."""
    try:
        try:
            r = admin_client.table("profiles").update(
                {"can_report_issues": enabled}
            ).eq("id", user_id).execute()
        except Exception as col_err:
            err_str = str(col_err).lower()
            if "can_report_issues" in err_str or "pgrst204" in err_str or "schema cache" in err_str:
                raise HTTPException(
                    status_code=503,
                    detail="Migration not applied: run migrations/20260629_can_report_issues.sql in Supabase Studio."
                )
            raise
        if not r.data:
            raise HTTPException(status_code=404, detail="User not found.")
        # Audit log
        try:
            admin_client.table("platform_audit_logs").insert({
                "admin_id": admin_user["auth_user"].id,
                "action": "toggle_can_report_issues",
                "target_id": user_id,
                "details": json.dumps({"enabled": enabled}),
            }).execute()
        except Exception:
            pass
        return {"success": True, "user_id": user_id, "can_report_issues": enabled}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/api/admin/users/issue-reporters")
def list_issue_reporters(admin_user=Depends(require_admin)):
    """List all users who have can_report_issues=true."""
    try:
        r = admin_client.table("profiles").select(
            "id,username,email,role,grade,can_report_issues"
        ).eq("can_report_issues", True).execute()
        return {"success": True, "reporters": r.data or []}
    except Exception as e:
        # Graceful fallback — column may not exist yet
        return {"success": True, "reporters": [], "note": "Migration pending: " + str(e)[:100]}


@router.get("/api/admin/users/search")
def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, le=50),
    admin_user=Depends(require_admin),
):
    """Search users by username or email for reporter access management."""
    try:
        # Try with can_report_issues first, fall back to base columns if column missing
        _select = "id,username,email,role,grade,can_report_issues"
        try:
            admin_client.table("profiles").select(_select).limit(1).execute()
        except Exception:
            _select = "id,username,email,role,grade"
        # Search by username
        r_username = (admin_client.table("profiles")
                      .select(_select)
                      .ilike("username", f"%{q}%")
                      .limit(limit)
                      .execute())
        # Search by email
        r_email = (admin_client.table("profiles")
                   .select(_select)
                   .ilike("email", f"%{q}%")
                   .limit(limit)
                   .execute())
        # Merge + deduplicate
        seen = set()
        users = []
        for row in (r_username.data or []) + (r_email.data or []):
            if row["id"] not in seen:
                seen.add(row["id"])
                # Graceful fallback for can_report_issues
                if "can_report_issues" not in row:
                    row["can_report_issues"] = False
                users.append(row)
        return {"success": True, "users": users[:limit]}
    except Exception as e:
        return {"success": False, "users": [], "error": str(e)[:200]}
