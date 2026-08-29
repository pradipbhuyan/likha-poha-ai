"""
admin_school_outreach.py  —  /api/admin/outreach/*
─────────────────────────────────────────────────────────────────────────────
Admin console for the CBSE principal outreach campaign: browse/filter/select
principals and trigger sends (initial pitch or the one-time 7-day reminder),
backed by Supabase (school_outreach_principals) instead of a script-local
file — see app/services/school_outreach_service.py for the actual sending
and query logic.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.auth_service import require_admin
from app.services import school_outreach_service as svc

router = APIRouter()


class SendRequest(BaseModel):
    emails: list[str]
    type: str = "initial"  # "initial" | "reminder"


class MarkRespondedRequest(BaseModel):
    emails: list[str]


@router.get("/summary")
def get_summary(admin=Depends(require_admin)):
    return {"success": True, "summary": svc.get_summary()}


@router.get("/principals")
def list_principals(
    status: str = "",
    needs_reminder: bool = False,
    q: str = "",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(require_admin),
):
    result = svc.list_principals(status=status, needs_reminder=needs_reminder, q=q, limit=limit, offset=offset)
    return {"success": True, "principals": result["rows"], "total": result["total"]}


@router.post("/send")
def send_to_selected(data: SendRequest, admin=Depends(require_admin)):
    if data.type not in ("initial", "reminder"):
        raise HTTPException(status_code=400, detail="type must be 'initial' or 'reminder'")
    if not data.emails:
        raise HTTPException(status_code=400, detail="No emails selected.")

    queued = svc.queue_send(data.emails, email_type=data.type)
    return {
        "success": True,
        "queued": queued,
        "message": (
            f"Queued {queued} email(s) — sending in the background, ~2s apart. "
            "Refresh the summary in a moment to see progress."
        ),
    }


@router.post("/mark-responded")
def mark_responded(data: MarkRespondedRequest, admin=Depends(require_admin)):
    if not data.emails:
        raise HTTPException(status_code=400, detail="No emails given.")
    updated = svc.mark_responded(data.emails)
    return {"success": True, "updated": updated}
