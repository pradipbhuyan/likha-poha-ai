"""
Unanswered Questions Review — Admin API
=========================================
Tracks questions that could not be answered by:
  - Chatbot widget (hit default fallback)
  - Ask Doubt (DKB miss + LLM answered)
  - Lesson follow-up (DKB miss + LLM answered)

Admin can review these, write an answer, and approve it to:
  - DKB (doubt_kb table) — for Ask Doubt and Lesson follow-up misses
  - Chatbot KB (chatbot_faq table) — for chatbot misses
  - Reject (marks as rejected, hides from review)

This enables controlled, human-approved progressive intelligence growth.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.auth_service import admin_client as supabase, require_admin

router = APIRouter()

# ── Models ────────────────────────────────────────────────────────────────────

class LogUnansweredRequest(BaseModel):
    question: str
    source: str          # "chatbot" | "doubt" | "lesson_followup"
    grade: str | None = None
    subject: str | None = None
    chapter: str | None = None
    mode: str | None = None
    username: str | None = None


class ApproveRequest(BaseModel):
    answer: str
    target: str          # "dkb" | "chatbot"
    grade: str | None = None
    subject: str | None = None
    chapter: str | None = None
    mode: str | None = None


# ── Public logging endpoint (no auth — called from chatbot/doubt) ─────────────

@router.post("/log")
async def log_unanswered(body: LogUnansweredRequest):
    """Log a question that could not be answered. Called internally by services."""
    try:
        supabase.table("unanswered_questions").insert({
            "question": body.question[:500],
            "source": body.source,
            "grade": body.grade,
            "subject": body.subject,
            "chapter": body.chapter,
            "mode": body.mode,
            "username": body.username,
            "status": "pending",
        }).execute()
        return {"success": True}
    except Exception as e:
        # Never fail silently in a way that breaks the main flow
        return {"success": False, "error": str(e)}


# ── Admin endpoints (require admin role) ─────────────────────────────────────

@router.get("")
async def list_unanswered(
    status: str = "pending",
    source: str = "",
    limit: int = 50,
    admin=Depends(require_admin),
):
    """List unanswered questions pending review."""
    query = (
        supabase.table("unanswered_questions")
        .select("*")
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if source:
        query = query.eq("source", source)

    result = query.execute()
    return {"items": result.data or [], "total": len(result.data or [])}


@router.post("/{item_id}/approve")
async def approve_question(
    item_id: str,
    body: ApproveRequest,
    admin=Depends(require_admin),
):
    """
    Approve a question with an admin-written answer.
    Saves to DKB (doubt_kb) or Chatbot KB (chatbot_approved_qa).
    Marks the item as approved.
    """
    admin_username = admin.get("profile", {}).get("username", "admin")

    # Fetch the question
    row = supabase.table("unanswered_questions").select("*").eq("id", item_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Question not found.")
    item = row.data[0]

    if body.target == "dkb":
        # Save to doubt_kb with admin-approved source
        from app.services.doubt_kb_service import store_in_doubt_kb  # noqa: PLC0415
        doc_id = store_in_doubt_kb(
            question=item["question"],
            answer=body.answer,
            grade=body.grade or item.get("grade") or "Grade 9",
            subject=body.subject or item.get("subject") or "General",
            chapter=body.chapter or item.get("chapter"),
            mode=body.mode or item.get("mode") or "CBSE",
            board="CBSE",
            source="admin_approved",
        )
        target_id = doc_id

    elif body.target == "chatbot":
        # Save to chatbot_approved_qa table
        result = supabase.table("chatbot_approved_qa").insert({
            "question": item["question"],
            "answer": body.answer,
            "approved_by": admin_username,
            "status": "active",
        }).execute()
        target_id = result.data[0]["id"] if result.data else None

    else:
        raise HTTPException(status_code=400, detail="target must be 'dkb' or 'chatbot'")

    # Mark as approved
    supabase.table("unanswered_questions").update({
        "status": "approved",
        "approved_answer": body.answer,
        "approved_by": admin_username,
        "target": body.target,
        "target_id": str(target_id) if target_id else None,
    }).eq("id", item_id).execute()

    return {
        "success": True,
        "message": f"Answer approved and saved to {body.target.upper()}",
        "target_id": str(target_id) if target_id else None,
    }


@router.post("/{item_id}/reject")
async def reject_question(
    item_id: str,
    admin=Depends(require_admin),
):
    """Mark a question as rejected (won't be shown again)."""
    admin_username = admin.get("profile", {}).get("username", "admin")
    supabase.table("unanswered_questions").update({
        "status": "rejected",
        "approved_by": admin_username,
    }).eq("id", item_id).execute()

    return {"success": True}


@router.delete("/{item_id}")
async def delete_question(
    item_id: str,
    _admin=Depends(require_admin),
):
    """Permanently delete a logged question."""

    supabase.table("unanswered_questions").delete().eq("id", item_id).execute()
    return {"success": True}


@router.get("/stats")
async def get_stats(_admin=Depends(require_admin)):
    """Summary counts by status and source."""

    all_rows = supabase.table("unanswered_questions").select("status,source").execute()
    rows = all_rows.data or []
    from collections import Counter  # noqa: PLC0415
    by_status = Counter(r["status"] for r in rows)
    by_source = Counter(r["source"] for r in rows if r.get("status") == "pending")
    return {
        "total": len(rows),
        "pending": by_status.get("pending", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "pending_by_source": dict(by_source),
    }
