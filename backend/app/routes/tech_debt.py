"""
tech_debt.py — Admin-approval-gated tech debt backlog
─────────────────────────────────────────────────────────────────────────────
Admin endpoints:
  GET   /api/admin/tech-debt            — list/filter, sorted by criticality
  GET   /api/admin/tech-debt/summary    — dashboard counts by status
  POST  /api/admin/tech-debt            — create (from feedback items, or manual)
  PATCH /api/admin/tech-debt/{id}       — approve / reject / move status
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

from ..services.auth_service import admin_client, require_admin
from .feedback import tier_from_score

router = APIRouter()

VALID_STATUSES = {"proposed", "approved", "rejected", "in_progress", "done"}
_TIER_DEFAULT_SCORE = {"critical": 75, "high": 55, "medium": 35, "low": 15}


def _sanitize(text: Optional[str], max_len: int = 2000) -> Optional[str]:
    if not text:
        return None
    clean = html.escape(re.sub(r"<[^>]+>", "", text))
    return clean[:max_len] or None


# ── Pydantic models ─────────────────────────────────────────────────────────

class TechDebtCreateIn(BaseModel):
    title: str
    description: Optional[str] = None
    source_feedback_ids: list[str] = []
    criticality_tier_override: Optional[str] = None  # only used when no sources (manual entry)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("title is required.")
        return v.strip()

    @field_validator("criticality_tier_override")
    @classmethod
    def validate_tier(cls, v):
        if v and v not in _TIER_DEFAULT_SCORE:
            raise ValueError(f"Invalid tier. Must be one of: {sorted(_TIER_DEFAULT_SCORE)}")
        return v


class TechDebtUpdateIn(BaseModel):
    status: Optional[str] = None
    rejection_reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
        return v


# ── Admin: Create (convert feedback, or add manually) ───────────────────────

@router.post("/api/admin/tech-debt")
def create_tech_debt(body: TechDebtCreateIn, admin_user=Depends(require_admin)):
    source_ids = body.source_feedback_ids

    if source_ids:
        src_r = (admin_client.table("user_feedback")
                 .select("id,criticality_score")
                 .in_("id", source_ids)
                 .execute())
        rows = src_r.data or []
        if not rows:
            raise HTTPException(404, "None of the given feedback items were found.")
        score = max(r["criticality_score"] for r in rows)
        source_type = "feedback"
    else:
        score = float(_TIER_DEFAULT_SCORE.get(body.criticality_tier_override, _TIER_DEFAULT_SCORE["low"]))
        source_type = "manual"

    tier = tier_from_score(score)

    insert_r = (admin_client.table("tech_debt_items").insert({
        "title": _sanitize(body.title, 300),
        "description": _sanitize(body.description, 4000),
        "source_type": source_type,
        "source_feedback_ids": source_ids,
        "criticality_score": score,
        "criticality_tier": tier,
        "status": "proposed",
    }).execute())
    if not insert_r.data:
        raise HTTPException(500, "Failed to create tech debt item.")
    item = insert_r.data[0]

    if source_ids:
        admin_client.table("user_feedback").update({
            "status": "converted",
            "linked_tech_debt_id": item["id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).in_("id", source_ids).execute()

    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "tech_debt_created",
            "target_id": item["id"],
            "details": json.dumps({"source_type": source_type, "source_count": len(source_ids)}),
        }).execute()
    except Exception:
        pass

    return {"success": True, "tech_debt": item}


# ── Admin: List / Summary ────────────────────────────────────────────────────

@router.get("/api/admin/tech-debt")
def list_tech_debt(
    status: Optional[str] = Query(None),
    criticality_tier: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    _admin=Depends(require_admin),
):
    q = (admin_client.table("tech_debt_items")
         .select("*")
         .order("criticality_score", desc=True)
         .order("created_at", desc=True))
    if status:
        q = q.eq("status", status)
    if criticality_tier:
        q = q.eq("criticality_tier", criticality_tier)
    q = q.range(offset, offset + limit - 1)
    r = q.execute()
    return {"success": True, "tech_debt": r.data or []}


@router.get("/api/admin/tech-debt/summary")
def tech_debt_summary(_admin=Depends(require_admin)):
    try:
        all_r = admin_client.table("tech_debt_items").select("status").execute()
        rows = all_r.data or []
        return {
            "success": True,
            "proposed": sum(1 for r in rows if r["status"] == "proposed"),
            "approved": sum(1 for r in rows if r["status"] == "approved"),
            "in_progress": sum(1 for r in rows if r["status"] == "in_progress"),
            "rejected": sum(1 for r in rows if r["status"] == "rejected"),
            "done": sum(1 for r in rows if r["status"] == "done"),
            "total": len(rows),
        }
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


# ── Admin: Approve / Reject / Move status ────────────────────────────────────

@router.patch("/api/admin/tech-debt/{item_id}")
def update_tech_debt(item_id: str, body: TechDebtUpdateIn, admin_user=Depends(require_admin)):
    if not body.status:
        raise HTTPException(400, "status is required.")
    if body.status == "rejected" and not (body.rejection_reason or "").strip():
        raise HTTPException(400, "rejection_reason is required when rejecting.")

    update_data: dict = {
        "status": body.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.status in ("approved", "rejected"):
        update_data["reviewed_by_admin_id"] = admin_user["auth_user"].id
        update_data["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    if body.status == "rejected":
        update_data["rejection_reason"] = _sanitize(body.rejection_reason, 1000)

    r = admin_client.table("tech_debt_items").update(update_data).eq("id", item_id).execute()
    if not r.data:
        raise HTTPException(404, "Tech debt item not found or update failed.")

    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "tech_debt_reviewed",
            "target_id": item_id,
            "details": json.dumps({"status": body.status}),
        }).execute()
    except Exception:
        pass

    return {"success": True, "tech_debt": r.data[0]}
