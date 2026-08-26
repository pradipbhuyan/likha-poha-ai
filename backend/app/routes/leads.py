"""
leads.py — Instagram bio-link lead capture
─────────────────────────────────────────────────────────────────────────────
Public, unauthenticated endpoint. The "Learn More" questionnaire linked from
the Instagram bio (github.io/likha-poha-promo-assets/interest/) posts here.

  POST /api/leads   — save a lead + notify the team inbox

No auth: this is hit directly from a static page served off a different
origin (GitHub Pages), by people who aren't logged in and may never create
an account. Rate-limited per IP since it's open to the internet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from ..services.auth_service import admin_client
from ..services.email_service import send_instagram_lead_notification
from ..services.rate_limit_service import LEAD_CAPTURE_LIMITER, rate_limit_dependency

router = APIRouter()


def _clean(text: str | None, max_len: int) -> str:
    return (text or "").strip()[:max_len]


class LeadIn(BaseModel):
    role: str
    name: str
    phone: str
    grade: str = ""
    count: str = ""
    source: str = "instagram_bio_link"

    @field_validator("role")
    @classmethod
    def _role_valid(cls, v: str) -> str:
        if v not in ("student", "parent", "teacher"):
            raise ValueError("role must be student, parent, or teacher")
        return v

    @field_validator("name", "phone")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("required")
        return v.strip()


@router.post("")
def submit_lead(body: LeadIn, _rl=Depends(rate_limit_dependency(LEAD_CAPTURE_LIMITER))):
    row = {
        "role": body.role,
        "name": _clean(body.name, 200),
        "phone": _clean(body.phone, 20),
        "grade": _clean(body.grade, 50),
        "student_count": _clean(body.count, 20),
        "source": _clean(body.source, 100) or "instagram_bio_link",
    }

    r = admin_client.table("instagram_leads").insert(row).execute()
    if not r.data:
        raise HTTPException(500, "Failed to save lead.")

    send_instagram_lead_notification(
        role=row["role"],
        name=row["name"],
        phone=row["phone"],
        grade=row["grade"],
        student_count=row["student_count"],
    )

    return {"success": True, "id": r.data[0]["id"]}
