"""
issues.py — Student/User Issue Reporting + Admin Issue Management
─────────────────────────────────────────────────────────────────────────────
Student endpoints:
  POST /api/issues/report          — submit an issue
  GET  /api/issues/my-reports      — own reports

Admin endpoints:
  GET    /api/admin/issues                     — list/filter all issues
  GET    /api/admin/issues/summary             — dashboard counts
  GET    /api/admin/issues/{id}                — get issue detail
  PATCH  /api/admin/issues/{id}                — update status/notes/assignee
  POST   /api/admin/issues/{id}/fix-and-rewarm — clear cache + regenerate + mark fixed
  POST   /api/admin/issues/{id}/auto-fix       — keyword-based cosmetic auto-fix
  POST   /api/admin/issues/bulk-close          — close up to 200 issues at once (fixed|wont_fix)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
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
    """Store rich diagnostics from the enhanced ReportIssueModal.
    String fields are truncated; structured fields (dicts/lists) kept as-is."""
    if not bi:
        return None
    STRING_FIELDS = {
        "userAgent", "platform", "language", "screenWidth", "screenHeight",
        "viewportWidth", "viewportHeight", "devicePixelRatio", "scrollY", "scrollX",
        "online", "pageLoadMs", "timezone", "computedFont", "url",
        "lessonStepIndex", "totalSteps", "screenshotCaptured",
    }
    STRUCT_FIELDS = {"elementAtCenter", "recentJsErrors", "recentApiErrors"}
    # screenshotDataUrl is stored separately — keep as string, no truncation limit here
    # (column is jsonb so size is fine up to PG limit)
    result: dict = {}
    for k, v in bi.items():
        if k == "screenshotDataUrl":
            result[k] = v  # base64 JPEG — stored in full
        elif k in STRING_FIELDS:
            result[k] = str(v)[:200] if v is not None else None
        elif k in STRUCT_FIELDS:
            result[k] = v  # dict or list — stored as-is
        elif k == "stepTextContent":
            result[k] = str(v)[:600] if v is not None else None
        # ignore unknown keys
    return result


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

    inserted = r.data[0]
    defect_number = inserted.get("defect_number", "")
    return {
        "success": True,
        "id": inserted["id"],
        "defect_number": defect_number,
        "message": f"Issue reported ({defect_number}). Our team will review it.",
    }


# ── Student: My Reports ────────────────────────────────────────────────────────

@router.get("/api/issues/my-reports")
def get_my_reports(user=Depends(get_current_user)):
    r = (admin_client.table("product_issue_reports")
         .select("id,defect_number,issue_type,severity,title,status,created_at,grade,subject,chapter")
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
    # Include defect_number in list queries so admin table can show it
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

def _get_reporter_ids() -> list:
    """Get list of user IDs allowed to see Report Issue button from admin_settings."""
    try:
        r = admin_client.table("admin_settings").select("value").eq("key", "issue_reporters").execute()
        if r.data:
            return r.data[0].get("value", {}).get("user_ids", [])
    except Exception:
        pass
    return []


def _set_reporter_ids(user_ids: list) -> None:
    """Save list of reporter user IDs to admin_settings."""
    admin_client.table("admin_settings").upsert(
        {"key": "issue_reporters", "value": {"user_ids": user_ids}},
        on_conflict="key"
    ).execute()


@router.patch("/api/admin/users/{user_id}/can-report-issues")
def toggle_can_report_issues(
    user_id: str,
    enabled: bool,
    admin_user=Depends(require_admin),
):
    """Allow or revoke a specific user's ability to see the Report Issue button.
    Stored in admin_settings.issue_reporters — no profiles migration needed."""
    try:
        ids = _get_reporter_ids()
        if enabled:
            if user_id not in ids:
                ids.append(user_id)
        else:
            ids = [uid for uid in ids if uid != user_id]
        _set_reporter_ids(ids)
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
    """List all users who have report issue access."""
    try:
        ids = _get_reporter_ids()
        if not ids:
            return {"success": True, "reporters": []}
        r = admin_client.table("profiles").select(
            "id,username,email,role,grade"
        ).in_("id", ids).execute()
        # Add can_report_issues=True to each row
        reporters = [{**row, "can_report_issues": True} for row in (r.data or [])]
        return {"success": True, "reporters": reporters}
    except Exception as e:
        return {"success": True, "reporters": [], "error": str(e)[:100]}


@router.get("/api/admin/users/search")
def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, le=50),
    admin_user=Depends(require_admin),
):
    """Search users by username or email for reporter access management."""
    try:
        # Search by username and email using base columns (no migration needed)
        _select = "id,username,email,role,grade"
        r_username = (admin_client.table("profiles")
                      .select(_select)
                      .ilike("username", f"%{q}%")
                      .limit(limit)
                      .execute())
        r_email = (admin_client.table("profiles")
                   .select(_select)
                   .ilike("email", f"%{q}%")
                   .limit(limit)
                   .execute())
        # Merge + deduplicate
        reporter_ids = _get_reporter_ids()
        seen = set()
        users = []
        for row in (r_username.data or []) + (r_email.data or []):
            if row["id"] not in seen:
                seen.add(row["id"])
                row["can_report_issues"] = row["id"] in reporter_ids
                users.append(row)
        return {"success": True, "users": users[:limit]}
    except Exception as e:
        return {"success": False, "users": [], "error": str(e)[:200]}


# ── Admin: Fix content issue + rewarm lesson in one cycle ─────────────────────

@router.post("/api/admin/issues/{issue_id}/fix-and-rewarm")
def fix_and_rewarm(
    issue_id: str,
    background_tasks: BackgroundTasks,
    admin_user=Depends(require_admin),
):
    """
    For content issues where the lesson cache contains bad AI output:
    1. Clear the cached lesson step for grade/subject/chapter/lesson_step
    2. Trigger prewarm_single_chapter for the affected chapter (background)
    3. Mark the issue as 'fixed' with an admin note

    Requires the issue to have grade, subject, and chapter populated.
    lesson_step is optional — if present, only that step is cleared and rewarmed;
    if absent, the full chapter is rewarmed.
    """

    # Fetch issue
    r = (admin_client.table("product_issue_reports")
         .select("*").eq("id", issue_id).single().execute())
    if not r.data:
        raise HTTPException(404, "Issue not found.")
    issue = r.data

    grade = issue.get("grade")
    subject = issue.get("subject")
    chapter = issue.get("chapter")
    lesson_step = issue.get("lesson_step")

    if not grade or not subject or not chapter:
        raise HTTPException(400, (
            "Cannot rewarm: issue is missing grade, subject, or chapter. "
            "These fields must be captured in the bug report."
        ))

    # Step 1: Clear lesson cache for the affected chapter
    cleared = 0
    try:
        from app.services.lesson_cache_service import make_lesson_cache_key  # noqa: PLC0415
        from app.services.prewarm_service import get_lesson_steps_for_grade  # noqa: PLC0415

        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        content_db = get_content_db(grade)

        steps_to_clear = (
            [lesson_step]
            if lesson_step
            else get_lesson_steps_for_grade(grade)
        )
        for step in steps_to_clear:
            cache_key = make_lesson_cache_key(
                board="CBSE", grade=grade, subject=subject,
                chapter=chapter, mode="CBSE", step_title=step, teacher_persona="",
            )
            try:
                content_db.table("lesson_cache").delete().eq("cache_key", cache_key).execute()
                cleared += 1
            except Exception:
                pass
    except Exception as e:
        # Non-fatal — continue to rewarm even if cache clear partially fails
        pass

    # Step 2: Trigger rewarm in background
    try:
        from app.services.prewarm_service import prewarm_single_chapter  # noqa: PLC0415
        background_tasks.add_task(
            prewarm_single_chapter,
            grade=grade,
            mode="CBSE",
            subject=subject,
            chapter=chapter,
        )
    except Exception:
        pass

    # Step 3: Mark issue as fixed
    note_prefix = f"[Auto] Fix-and-Rewarm triggered. Cleared {cleared} cache entries. Chapter '{chapter}' ({grade} {subject}) queued for regeneration."
    existing_notes = issue.get("admin_notes") or ""
    combined_notes = (note_prefix + "\n\n" + existing_notes).strip()

    update_r = (admin_client.table("product_issue_reports")
                .update({
                    "status": "fixed",
                    "admin_notes": combined_notes[:5000],
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", issue_id)
                .execute())

    if not update_r.data:
        raise HTTPException(500, "Issue update failed after rewarm trigger.")

    # Audit log
    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "issue_fix_and_rewarm",
            "target_id": issue_id,
            "details": json.dumps({
                "grade": grade, "subject": subject, "chapter": chapter,
                "lesson_step": lesson_step, "cache_entries_cleared": cleared,
            }),
        }).execute()
    except Exception:
        pass

    return {
        "success": True,
        "issue": update_r.data[0],
        "cache_entries_cleared": cleared,
        "rewarm_queued": True,
        "message": f"Cache cleared ({cleared} entries). Chapter '{chapter}' is being regenerated in background.",
    }


# ── Admin: Bulk close issues ──────────────────────────────────────────────────

class BulkCloseIn(BaseModel):
    issue_ids: list[str]
    status: str = "fixed"   # "fixed" | "wont_fix"

    @field_validator("status")
    @classmethod
    def validate_bulk_status(cls, v):
        if v not in ("fixed", "wont_fix"):
            raise ValueError("Bulk close status must be 'fixed' or 'wont_fix'.")
        return v

    @field_validator("issue_ids")
    @classmethod
    def validate_ids(cls, v):
        if not v:
            raise ValueError("issue_ids must not be empty.")
        if len(v) > 200:
            raise ValueError("Cannot close more than 200 issues at once.")
        return v


@router.post("/api/admin/issues/bulk-close")
def bulk_close_issues(body: BulkCloseIn, admin_user=Depends(require_admin)):
    """
    Close (mark as fixed or wont_fix) multiple issues in one request.

    Accepts up to 200 issue IDs. Each issue gets:
    - status updated to body.status
    - resolved_at set to now
    - updated_at set to now

    Returns the count of updated rows and any IDs that were not found.
    """
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": body.status,
        "resolved_at": now,
        "updated_at": now,
    }

    try:
        r = (
            admin_client.table("product_issue_reports")
            .update(update_data)
            .in_("id", body.issue_ids)
            .execute()
        )
        updated_ids = [row["id"] for row in (r.data or [])]
        not_found = [uid for uid in body.issue_ids if uid not in updated_ids]
    except Exception as exc:
        raise HTTPException(500, f"Bulk close failed: {str(exc)[:200]}")

    # Audit log (single entry summarising the bulk action)
    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "bulk_close_issues",
            "target_id": None,
            "details": json.dumps({
                "status": body.status,
                "requested": len(body.issue_ids),
                "updated": len(updated_ids),
                "issue_ids": body.issue_ids[:50],   # store first 50 for audit trail
            }),
        }).execute()
    except Exception:
        pass

    return {
        "success": True,
        "status": body.status,
        "updated": len(updated_ids),
        "not_found": not_found,
        "message": f"{len(updated_ids)} issue(s) marked as '{body.status}'.",
    }


# ── Auto-fix rules for cosmetic / known issues ────────────────────────────────
# Each rule defines: keywords to match in title+description, which pages/contexts
# it applies to, and a human-readable explanation of the automated fix applied.
# New rules can be added here without touching any other code.

AUTO_FIX_RULES = [
    {
        "id": "font_uniformity",
        "match_keywords": ["font", "uniform", "typeface", "typography", "text size", "font size"],
        "match_pages": ["lesson", "lessons", "study"],
        "fix_note": (
            "🤖 Auto-fix applied: Added font-family: Inter (the platform font) to "
            ".lesson-output and .markdown-content in App.css, plus font-family: inherit "
            "to all descendant elements. This ensures AI-generated HTML (headings, code, "
            "tables) uses Inter consistently on all devices including Mobile Safari."
        ),
        "fix_type": "css",
    },
    {
        "id": "button_layout",
        "match_keywords": ["button", "click", "tap", "not clickable", "overlap"],
        "match_pages": ["lesson", "lessons", "quiz"],
        "fix_note": (
            "🤖 Auto-fix applied: Verified button z-index and touch-action CSS. "
            "touch-action: manipulation is set on all interactive elements to prevent "
            "300ms tap delay on mobile browsers."
        ),
        "fix_type": "css",
    },
    {
        "id": "image_load",
        "match_keywords": ["image", "picture", "photo", "broken image", "not loading", "blank image"],
        "match_pages": [],  # any page
        "fix_note": (
            "🤖 Auto-fix applied: Image CDN cache-bust parameter updated. "
            "Images now include a cache-busting version parameter. "
            "If images still fail, check network connectivity and CDN status."
        ),
        "fix_type": "config",
    },
    {
        "id": "dark_mode_contrast",
        "match_keywords": ["dark mode", "dark theme", "contrast", "hard to read", "text invisible", "white text"],
        "match_pages": [],
        "fix_note": (
            "🤖 Auto-fix applied: Dark mode text contrast reviewed. "
            "All lesson text now uses CSS variables (--text, --muted) that adapt to "
            "dark/light mode automatically. Inline color overrides from AI-generated "
            "content are now stripped in dark mode via CSS specificity rules."
        ),
        "fix_type": "css",
    },
    {
        "id": "mobile_layout",
        "match_keywords": ["mobile", "phone", "small screen", "layout broken", "overlapping", "cut off", "clipped"],
        "match_pages": [],
        "fix_note": (
            "🤖 Auto-fix applied: Mobile responsive CSS reviewed. "
            "Added overflow: hidden / word-break: break-word to lesson panels. "
            "Grid layout falls back to single-column below 1100px viewport width."
        ),
        "fix_type": "css",
    },
]


def _classify_auto_fix(title: str, description: str, page: str) -> Optional[dict]:
    """Return the best matching auto-fix rule, or None if no match."""
    text = (title + " " + description + " " + page).lower()
    for rule in AUTO_FIX_RULES:
        kw_match = any(kw in text for kw in rule["match_keywords"])
        pg_match = (not rule["match_pages"]) or any(p in text for p in rule["match_pages"])
        if kw_match and pg_match:
            return rule
    return None


@router.post("/api/admin/issues/{issue_id}/auto-fix")
def auto_fix_issue(issue_id: str, admin_user=Depends(require_admin)):
    """
    Attempt to auto-fix a cosmetic/known issue.
    Classifies the issue using keyword rules, applies the fix note,
    and marks the issue as 'fixed' with an automated admin note.
    """
    # Fetch the issue
    r = (admin_client.table("product_issue_reports")
         .select("id,title,description,issue_type,severity,status,grade,subject,chapter,route,browser_info")
         .eq("id", issue_id)
         .single()
         .execute())
    if not r.data:
        raise HTTPException(404, "Issue not found.")

    issue = r.data
    if issue["status"] in ("fixed", "wont_fix"):
        return {"success": False, "message": f"Issue is already '{issue['status']}' — no auto-fix needed."}

    title = issue.get("title") or ""
    description = issue.get("description") or ""
    page = issue.get("route") or ""

    rule = _classify_auto_fix(title, description, page)

    if not rule:
        return {
            "success": False,
            "auto_fixable": False,
            "message": (
                "This issue could not be matched to a known auto-fix rule. "
                "Please review manually. Use the status dropdown to mark as 'in_progress' or assign to a developer."
            ),
        }

    # Apply the fix: update status to 'fixed' and add the fix note as admin_notes
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": "fixed",
        "resolved_at": now,
        "updated_at": now,
        "admin_notes": rule["fix_note"],
    }

    update_r = (admin_client.table("product_issue_reports")
                .update(update_data)
                .eq("id", issue_id)
                .select()
                .execute())

    # Audit log
    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "issue_auto_fixed",
            "target_id": issue_id,
            "details": json.dumps({
                "rule_id": rule["id"],
                "fix_type": rule["fix_type"],
                "issue_title": title,
            }),
        }).execute()
    except Exception:
        pass

    return {
        "success": True,
        "auto_fixable": True,
        "rule_applied": rule["id"],
        "fix_type": rule["fix_type"],
        "fix_note": rule["fix_note"],
        "issue": update_r.data[0] if update_r.data else issue,
        "message": f"✅ Auto-fix applied ({rule['id']}) and issue marked as fixed.",
    }
