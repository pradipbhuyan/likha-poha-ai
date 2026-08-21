"""
admin_onboarding.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Admin-initiated account creation for parents, children, and teachers.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_service import require_admin, create_auth_user, invite_parent_by_email, admin_client
from app.services.board_service import normalize_board

router = APIRouter()


class CreateParentRequest(BaseModel):
    email: str
    password: str | None = None
    username: str
    family_id: str | None = None
    skip_email_confirmation: bool = False
    """
    By default all parent accounts require email confirmation before login.
    Supabase sends a real invite email via invite_user_by_email.
    The parent clicks the link to confirm and set their own password.

    Set skip_email_confirmation=True for in-person onboarding where the admin
    hands credentials directly to the parent. In this case a password is
    required and the account is immediately active.
    """


class CreateChildRequest(BaseModel):
    email: str
    password: str | None = None
    username: str
    parent_id: str | None = None
    family_id: str | None = None
    grade: str = "Grade 9"
    board: str = "CBSE"
    skip_email_confirmation: bool = True  # admin-created students get immediate access by default
    """
    Admin-created standalone students bypass email verification by default.
    Set skip_email_confirmation=False to send an invite email instead.
    A password is required when skip_email_confirmation=True.
    Parent/family linking is optional — students can exist independently.
    """


class CreateTeacherRequest(BaseModel):
    email: str
    password: str
    username: str
    teacher_type: str = "independent"
    school_name: str = ""
    subjects: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    status: str = "active"


@router.post("/parents")
def create_parent(data: CreateParentRequest, admin=Depends(require_admin)):
    """
    Create a parent auth account/profile, creating a family when needed.

    Admin-created parents default to the free plan until plan/access is updated.
    """
    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(data.username)
    _reject_taken_username(data.username, client=admin_client)

    family_id = data.family_id

    if not family_id:
        family_response = (
            admin_client
            .table("families")
            .insert({
                "family_name": f"{data.username}'s Family",
            })
            .execute()
        )

        if not family_response.data:
            raise HTTPException(
                status_code=400,
                detail="Unable to create family.",
            )

        family_id = family_response.data[0]["id"]

    if data.skip_email_confirmation:
        # In-person onboarding: admin hands credentials directly to the parent.
        # A password is required; account is immediately active.
        if not data.password:
            raise HTTPException(
                status_code=400,
                detail="A password is required when skip_email_confirmation is True.",
            )
        auth_user = create_auth_user(
            email=data.email,
            password=data.password,
            email_confirm=True,
        )
    else:
        # Default: Supabase sends a real invite email.
        # The parent must click the link to confirm their email and set their
        # own password. No password should be submitted in this flow.
        auth_user = invite_parent_by_email(
            email=data.email,
            username=data.username,
        )

    parent_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "parent",
        "parent_id": None,
        "family_id": family_id,
        "account_status": "active",
        "subscription_plan": "free",
        "access_cbse": True,
    }

    response = (
        admin_client
        .table("profiles")
        .insert(parent_profile)
        .execute()
    )

    return {
        "success": True,
        "parent": response.data[0] if response.data else parent_profile,
    }


@router.post("/children")
def create_child(data: CreateChildRequest, admin=Depends(require_admin)):
    """
    Create a standalone student auth account/profile from the admin panel.

    Students can be created without a parent/family (standalone) or linked to
    an existing parent later. Admin-created students bypass email verification
    by default (skip_email_confirmation=True) for in-person onboarding.
    """
    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(data.username)
    _reject_taken_username(data.username, client=admin_client)

    if data.skip_email_confirmation:
        if not data.password:
            raise HTTPException(
                status_code=400,
                detail="A password is required when skip_email_confirmation is True.",
            )
        auth_user = create_auth_user(
            email=data.email,
            password=data.password,
            email_confirm=True,
        )
    else:
        # Send invite email — student sets their own password via the link
        auth_user = invite_parent_by_email(
            email=data.email,
            username=data.username,
        )

    child_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "student",
        "parent_id": data.parent_id or None,
        "family_id": data.family_id or None,
        "grade": data.grade or "Grade 9",
        "board": normalize_board(data.board),
        "account_status": "active",
        "subscription_plan": "free",
        "access_cbse": True,
        "cbse_subjects": [],
        "daily_token_limit": 50000,
        "monthly_token_limit": 1000000,
        "ai_model_preference": "default",
    }

    response = (
        admin_client
        .table("profiles")
        .insert(child_profile)
        .execute()
    )

    return {
        "success": True,
        "child": response.data[0] if response.data else child_profile,
    }


@router.post("/teachers")
def create_teacher(data: CreateTeacherRequest, admin=Depends(require_admin)):
    """
    Create a teacher auth/profile pair from the admin panel only.

    Teachers can represent either school accounts or independent tutors. Their
    metadata is stored separately so teacher access can evolve without changing
    parent/student signup.
    """
    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(data.username)
    _reject_taken_username(data.username, client=admin_client)

    teacher_type = data.teacher_type
    if teacher_type not in {"school", "independent"}:
        teacher_type = "independent"

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    teacher_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "teacher",
        "parent_id": None,
        "family_id": None,
        "account_status": data.status or "active",
        "subscription_plan": "teacher",
        "access_cbse": True,
    }

    metadata = {
        "profile_id": auth_user.id,
        "teacher_type": teacher_type,
        "school_name": data.school_name or "",
        "subjects": data.subjects or [],
        "grades": data.grades or [],
        "status": data.status or "active",
    }

    try:
        profile_response = (
            admin_client
            .table("profiles")
            .insert(teacher_profile)
            .execute()
        )

        metadata_response = (
            admin_client
            .table("teacher_profiles")
            .insert(metadata)
            .execute()
        )
    except Exception as exc:
        try:
            admin_client.table("profiles").delete().eq("id", auth_user.id).execute()
            admin_client.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to create teacher profile. Make sure "
                "backend/sql/add_teacher_dashboard.sql has been executed in "
                f"Supabase. Original error: {str(exc)}"
            ),
        )

    saved_profile = profile_response.data[0] if profile_response.data else teacher_profile
    saved_profile["teacher_profile"] = (
        metadata_response.data[0] if metadata_response.data else metadata
    )
    saved_profile["assignments"] = []

    return {
        "success": True,
        "teacher": saved_profile,
    }
