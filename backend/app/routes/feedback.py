"""
feedback.py — General user feedback (not bug reports) + admin triage
─────────────────────────────────────────────────────────────────────────────
Student/user endpoints:
  GET  /api/feedback/eligibility   — is this "serious user" due for a prompt?
  POST /api/feedback/prompt-shown  — record that the prompt was shown (starts cooldown)
  POST /api/feedback/report        — submit feedback
  GET  /api/feedback/mine          — own submitted feedback

Admin endpoints:
  GET   /api/admin/feedback           — list/filter all feedback
  GET   /api/admin/feedback/summary   — dashboard counts
  PATCH /api/admin/feedback/{id}      — update status/notes
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import html
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..services.auth_service import admin_client, get_current_user, get_user_profile, require_admin
from ..services.feedback_eligibility_service import check_eligibility, mark_prompt_shown

router = APIRouter()

# ── Rate limit (in-memory, per user, per hour) ─────────────────────────────
_rate: dict[str, list[float]] = {}
_RATE_LIMIT = 10
_RATE_WINDOW = 3600


def _check_rate(user_id: str) -> None:
    now = time.time()
    hits = [t for t in _rate.get(user_id, []) if now - t < _RATE_WINDOW]
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many feedback submissions. Try again later.")
    _rate[user_id] = hits + [now]


def _sanitize(text: Optional[str], max_len: int = 2000) -> Optional[str]:
    if not text:
        return None
    clean = html.escape(re.sub(r"<[^>]+>", "", text))
    return clean[:max_len] or None


VALID_FEEDBACK_TYPES = {"bug", "feature_request", "content_suggestion", "praise", "other"}

# Base criticality by type, bumped when the user also gave a low star rating —
# a fixed, explainable score rather than an opaque model.
_TYPE_BASE_SCORE = {"bug": 60, "content_suggestion": 45, "feature_request": 30, "other": 20, "praise": 5}
_LOW_RATING_BUMP = 25


def compute_criticality(feedback_type: str, rating: Optional[int]) -> float:
    score = _TYPE_BASE_SCORE.get(feedback_type, 20)
    if rating is not None and rating <= 2:
        score += _LOW_RATING_BUMP
    return float(score)


def tier_from_score(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


# ── Pydantic models ─────────────────────────────────────────────────────────

class FeedbackReportIn(BaseModel):
    feedback_type: str
    rating: Optional[int] = None
    message: str
    trigger_event: Optional[str] = None
    route: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None

    @field_validator("feedback_type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type. Must be one of: {sorted(VALID_FEEDBACK_TYPES)}")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("rating must be between 1 and 5.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty.")
        if len(v.strip()) < 5:
            raise ValueError("Message is too short.")
        return v


class FeedbackUpdateIn(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in ("new", "reviewed", "converted", "dismissed"):
            raise ValueError("Invalid status.")
        return v


# ── Student: eligibility + prompt tracking ─────────────────────────────────

@router.get("/api/feedback/eligibility")
def feedback_eligibility(user=Depends(get_current_user)):
    profile = get_user_profile(user.id) or {}
    result = check_eligibility(
        user_id=user.id,
        username=profile.get("username"),
        last_prompt_at=profile.get("last_feedback_prompt_at"),
    )
    return {"success": True, **result}


@router.post("/api/feedback/prompt-shown")
def feedback_prompt_shown(user=Depends(get_current_user)):
    mark_prompt_shown(user.id)
    return {"success": True}


# ── Student: Submit Feedback ────────────────────────────────────────────────

@router.post("/api/feedback/report")
def report_feedback(body: FeedbackReportIn, user=Depends(get_current_user)):
    _check_rate(user.id)

    profile = get_user_profile(user.id)
    role = profile.get("role", "unknown") if profile else "unknown"
    username = profile.get("username") if profile else None

    score = compute_criticality(body.feedback_type, body.rating)

    row = {
        "user_id": user.id,
        "user_role": role,
        "username": username,
        "feedback_type": body.feedback_type,
        "rating": body.rating,
        "message": _sanitize(body.message, 2000),
        "trigger_event": _sanitize(body.trigger_event, 100),
        "route": _sanitize(body.route, 200),
        "grade": _sanitize(body.grade, 50),
        "subject": _sanitize(body.subject, 100),
        "chapter": _sanitize(body.chapter, 200),
        "criticality_score": score,
        "criticality_tier": tier_from_score(score),
        "status": "new",
    }

    r = admin_client.table("user_feedback").insert(row).execute()
    if not r.data:
        raise HTTPException(500, "Failed to save feedback.")

    return {"success": True, "id": r.data[0]["id"], "message": "Thanks for the feedback — our team reads every note."}


@router.get("/api/feedback/mine")
def get_my_feedback(user=Depends(get_current_user)):
    r = (admin_client.table("user_feedback")
         .select("id,feedback_type,rating,message,status,created_at")
         .eq("user_id", user.id)
         .order("created_at", desc=True)
         .limit(50)
         .execute())
    return {"success": True, "feedback": r.data or []}


# ── Admin: List / Summary / Update ──────────────────────────────────────────

@router.get("/api/admin/feedback")
def list_feedback(
    status: Optional[str] = Query(None),
    feedback_type: Optional[str] = Query(None),
    criticality_tier: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    _admin=Depends(require_admin),
):
    q = (admin_client.table("user_feedback")
         .select("*")
         .order("criticality_score", desc=True)
         .order("created_at", desc=True))
    if status:
        q = q.eq("status", status)
    if feedback_type:
        q = q.eq("feedback_type", feedback_type)
    if criticality_tier:
        q = q.eq("criticality_tier", criticality_tier)
    q = q.range(offset, offset + limit - 1)
    r = q.execute()
    return {"success": True, "feedback": r.data or []}


@router.get("/api/admin/feedback/summary")
def feedback_summary(_admin=Depends(require_admin)):
    try:
        all_r = admin_client.table("user_feedback").select("status,criticality_tier,created_at").execute()
        rows = all_r.data or []

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        open_count = sum(1 for r in rows if r["status"] in ("new", "reviewed"))
        critical_count = sum(1 for r in rows if r["criticality_tier"] == "critical" and r["status"] not in ("converted", "dismissed"))
        this_week = sum(1 for r in rows
                         if r.get("created_at")
                         and datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= week_ago)
        converted = sum(1 for r in rows if r["status"] == "converted")

        return {
            "success": True,
            "open": open_count,
            "critical": critical_count,
            "this_week": this_week,
            "converted": converted,
            "total": len(rows),
        }
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


@router.patch("/api/admin/feedback/{feedback_id}")
def update_feedback(feedback_id: str, body: FeedbackUpdateIn, admin_user=Depends(require_admin)):
    update_data: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.status:
        update_data["status"] = body.status
    if body.admin_notes is not None:
        update_data["admin_notes"] = _sanitize(body.admin_notes, 2000)

    r = admin_client.table("user_feedback").update(update_data).eq("id", feedback_id).execute()
    if not r.data:
        raise HTTPException(404, "Feedback not found or update failed.")
    return {"success": True, "feedback": r.data[0]}
