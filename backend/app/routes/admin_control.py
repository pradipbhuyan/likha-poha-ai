import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.data.subscription_plans import (
    get_default_subscription_plans,
    subscription_plan_order,
)
from app.services.model_routing_service import normalize_model_preference
from app.services.auth_service import require_admin, create_auth_user, invite_parent_by_email, admin_client
from app.services.board_service import normalize_board
from app.services.subject_access_service import clean_subject_access_list
from app.services.usage_service import normalize_token_limit
from app.config import settings

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


class CreateOfferCodeRequest(BaseModel):
    description: str = ""
    valid_until: str  # ISO datetime string e.g. "2026-12-31T23:59:59"
    max_uses: int = 100
    valid_from: str | None = None  # defaults to now if omitted
    # Influencer tracking fields
    influencer_name: str = ""
    influencer_email: str = ""
    code_type: str = "free_trial"   # "free_trial" or "discount"
    discount_percent: int = 0        # 0 for free_trial; 5-10 for discount
    incentive_inr: int = 0           # INR per confirmed redemption to pay influencer


class CreateTeacherRequest(BaseModel):
    email: str
    password: str
    username: str
    teacher_type: str = "independent"
    school_name: str = ""
    subjects: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    status: str = "active"


class AssignTeacherStudentRequest(BaseModel):
    teacher_id: str
    student_id: str
    grade: str = "Grade 9"
    subject: str = ""
    section: str = ""


class UpdateAccessRequest(BaseModel):
    access_cbse: bool
    access_sof_science: bool
    access_sof_maths: bool
    access_sof_english: bool
    cbse_subjects: list[str] = Field(default_factory=list)
    subscription_plan: str = "free"
    account_status: str = "active"
    grade: str = "Grade 9"
    board: str = "CBSE"
    ai_model_preference: str = "default"


class UpdateLimitsRequest(BaseModel):
    daily_token_limit: int = Field(default=0, ge=0)
    monthly_token_limit: int = Field(default=0, ge=0)


class SubscriptionPlanSettings(BaseModel):
    key: str
    label: str
    short_label: str
    price: int
    billing_label: str
    audience: str
    badge: str = ""
    recommended: bool = False
    discount_percent: int = 0
    discount_label: str = ""
    is_public: bool = True
    display_order: int = 999
    access_cbse: bool = True
    access_sof_science: bool = False
    access_sof_maths: bool = False
    access_sof_english: bool = False
    daily_token_limit: int = 0
    monthly_token_limit: int = 0
    included: list[str] = []
    not_included: list[str] = []
    comparison: dict = {}


class UpdateSubscriptionPlanSettingsRequest(BaseModel):
    plans: list[SubscriptionPlanSettings]


class SubscriptionContactSettings(BaseModel):
    email: str = "lilhapohaai@gmail.com"
    phone: str = ""
    whatsapp: str = ""
    availability: str = "We usually respond within one business day."
    message: str = (
        "Need help choosing a plan or activating access? Contact us and we will guide you."
    )


DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS = {
    "email": "lilhapohaai@gmail.com",
    "phone": "",
    "whatsapp": "",
    "availability": "We usually respond within one business day.",
    "message": (
        "Need help choosing a plan or activating access? Contact us and we will guide you."
    ),
}


def summarize_student_activity(username: str, logs: list[dict]):
    """Summarize raw AI usage logs into the admin child activity card."""
    now = datetime.now(timezone.utc)
    today_start = now.date().isoformat()
    month_start = now.replace(day=1).date().isoformat()

    today_prefix = f"{today_start}T"
    month_prefix = f"{month_start[:7]}-"

    today_logs = [
        item for item in logs
        if str(item.get("created_at", "")).startswith(today_prefix)
    ]

    month_logs = [
        item for item in logs
        if str(item.get("created_at", "")).startswith(month_prefix)
    ]

    def feature_count(feature_name: str):
        """Count how many logged AI requests used one feature name."""
        return len([
            item for item in logs
            if item.get("feature") == feature_name
        ])

    return {
        "username": username,
        "lessons_generated": feature_count("lesson"),
        "doubts_asked": feature_count("doubt"),
        "mock_tests_generated": feature_count("mock_test"),
        "requests_total": len(logs),
        "tokens_today": sum(int(item.get("total_tokens") or 0) for item in today_logs),
        "tokens_this_month": sum(int(item.get("total_tokens") or 0) for item in month_logs),
        "tokens_total": sum(int(item.get("total_tokens") or 0) for item in logs),
        "cost_total": sum(float(item.get("estimated_cost") or 0) for item in logs),
        "last_activity": logs[0].get("created_at") if logs else None,
    }


def build_student_activity(username: str):
    """Load and summarize AI usage for one student username."""
    usage_response = (
        admin_client
        .table("ai_usage_logs")
        .select("*")
        .eq("username", username)
        .execute()
    )

    return summarize_student_activity(username, usage_response.data or [])


def build_activity_by_username(usernames: list[str]):
    """
    Batch-load usage logs and summarize activity for many students at once.

    This avoids one Supabase query per child on the admin family list.
    """
    if not usernames:
        return {}

    usage_response = (
        admin_client
        .table("ai_usage_logs")
        .select("*")
        .in_("username", usernames)
        .execute()
    )

    logs_by_username = {username: [] for username in usernames}

    for log in usage_response.data or []:
        username = log.get("username")

        if username in logs_by_username:
            logs_by_username[username].append(log)

    return {
        username: summarize_student_activity(username, logs)
        for username, logs in logs_by_username.items()
    }


def list_teacher_profiles_by_id():
    """Return teacher metadata rows keyed by profile_id for admin display."""
    try:
        response = (
            admin_client
            .table("teacher_profiles")
            .select("*")
            .execute()
        )
    except Exception:
        return {}

    return {
        item.get("profile_id"): item
        for item in response.data or []
        if item.get("profile_id")
    }


def list_teacher_assignments():
    """Return all teacher-student links for the admin assignment panel."""
    try:
        response = (
            admin_client
            .table("teacher_student_assignments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        return []

    return response.data or []


def normalize_subscription_plan_row(row: dict):
    """
    Normalize a database subscription-plan row into API-safe field types.

    Supabase JSON/nullable fields are converted to predictable booleans, ints,
    lists, and dicts before merging with defaults or sending to the frontend.
    """
    return {
        "key": row.get("key"),
        "label": row.get("label") or "",
        "short_label": row.get("short_label") or row.get("label") or "",
        "price": int(row.get("price") or 0),
        "billing_label": row.get("billing_label") or "month",
        "audience": row.get("audience") or "",
        "badge": row.get("badge") or "",
        "recommended": bool(row.get("recommended")),
        "discount_percent": int(row.get("discount_percent") or 0),
        "discount_label": row.get("discount_label") or "",
        "is_public": row.get("is_public") is not False,
        "display_order": int(row.get("display_order") or 999),
        "access_cbse": bool(row.get("access_cbse")),
        "access_sof_science": bool(row.get("access_sof_science")),
        "access_sof_maths": bool(row.get("access_sof_maths")),
        "access_sof_english": bool(row.get("access_sof_english")),
        "daily_token_limit": int(row.get("daily_token_limit") or 0),
        "monthly_token_limit": int(row.get("monthly_token_limit") or 0),
        "included": row.get("included") or [],
        "not_included": row.get("not_included") or [],
        "comparison": row.get("comparison") or {},
    }


def list_subscription_plan_settings():
    """
    Load subscription plans from Supabase with built-in defaults as fallback.

    The admin and parent subscription pages both call this path so discounts,
    prices, visibility, and feature lists stay aligned.
    """
    plans = get_default_subscription_plans()
    persisted = False
    load_error = None

    try:
        response = (
            admin_client
            .table("subscription_plan_settings")
            .select("*")
            .execute()
        )

        for row in response.data or []:
            normalized = normalize_subscription_plan_row(row)
            if normalized["key"] in plans:
                plans[normalized["key"]] = {
                    **plans[normalized["key"]],
                    **normalized,
                }

        persisted = bool(response.data)
    except Exception as exc:
        persisted = False
        load_error = str(exc)

    order = subscription_plan_order(plans)

    return {
        "success": True,
        "persisted": persisted,
        "source": "database" if persisted else "defaults",
        "load_error": load_error,
        "plans": plans,
        "plan_order": order,
    }


def normalize_subscription_contact_row(row: dict | None):
    """Normalize subscription support/contact settings for admin and parent UIs."""
    row = row or {}

    return {
        **DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS,
        "email": row.get("email") or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["email"],
        "phone": row.get("phone") or "",
        "whatsapp": row.get("whatsapp") or "",
        "availability": (
            row.get("availability")
            or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["availability"]
        ),
        "message": row.get("message") or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["message"],
    }


def list_subscription_contact_settings():
    """Load subscription contact settings with a safe default fallback."""
    persisted = False
    load_error = None
    contact = normalize_subscription_contact_row(None)

    try:
        response = (
            admin_client
            .table("subscription_contact_settings")
            .select("*")
            .eq("key", "default")
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]

        if row:
            persisted = True
            contact = normalize_subscription_contact_row(row)
    except Exception as exc:
        persisted = False
        load_error = str(exc)

    return {
        "success": True,
        "persisted": persisted,
        "source": "database" if persisted else "defaults",
        "load_error": load_error,
        "contact": contact,
    }


@router.get("/families")
def get_all_families(admin=Depends(require_admin)):
    """
    Return all profiles grouped by family for the admin control page.

    Student rows are enriched with activity summaries so admins can review usage
    and plan limits without opening separate reports.
    """
    profiles_response = (
        admin_client
        .table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    profiles = profiles_response.data or []
    student_usernames = [
        profile.get("username") or ""
        for profile in profiles
        if profile.get("role") == "student"
    ]
    activity_by_username = build_activity_by_username(student_usernames)

    teacher_profiles_by_id = list_teacher_profiles_by_id()
    teacher_assignments = list_teacher_assignments()
    assignments_by_teacher = {}

    for assignment in teacher_assignments:
        teacher_id = assignment.get("teacher_id")
        if teacher_id:
            assignments_by_teacher.setdefault(teacher_id, []).append(assignment)

    families = {}

    for profile in profiles:
        family_id = profile.get("family_id") or "no-family"

        if family_id not in families:
            families[family_id] = {
                "family_id": family_id,
                "parents": [],
                "children": [],
                "admins": [],
                "teachers": [],
            }

        if profile.get("role") == "parent":
            families[family_id]["parents"].append(profile)
        elif profile.get("role") == "student":
            username = profile.get("username") or ""
            profile["activity"] = activity_by_username.get(
                username,
                summarize_student_activity(username, []),
            )
            families[family_id]["children"].append(profile)
        elif profile.get("role") == "admin":
            families[family_id]["admins"].append(profile)
        elif profile.get("role") == "teacher":
            profile["teacher_profile"] = teacher_profiles_by_id.get(
                profile.get("id"),
                {},
            )
            profile["assignments"] = assignments_by_teacher.get(
                profile.get("id"),
                [],
            )
            families[family_id]["teachers"].append(profile)

    return {
        "success": True,
        "families": list(families.values()),
    }


@router.get("/subscription-plans")
def get_subscription_plans(admin=Depends(require_admin)):
    """Return editable subscription plan settings for admins."""
    return list_subscription_plan_settings()


@router.put("/subscription-plans")
def update_subscription_plans(
    data: UpdateSubscriptionPlanSettingsRequest,
    admin=Depends(require_admin),
):
    """
    Persist admin-edited subscription prices, discounts, access, and inclusions.

    Discount percent is clamped to 0-100 before upsert so invalid UI/input state
    cannot produce negative or above-free pricing.
    """
    rows = []

    for index, plan in enumerate(data.plans, start=1):
        row = plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()
        row["display_order"] = int(row.get("display_order") or index)
        row["discount_percent"] = max(
            0,
            min(100, int(row.get("discount_percent") or 0)),
        )
        rows.append(row)

    try:
        response = (
            admin_client
            .table("subscription_plan_settings")
            .upsert(rows, on_conflict="key")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save subscription plan settings. Make sure the "
                "subscription_plan_settings table exists. "
                f"Original error: {str(exc)}"
            ),
        )

    saved_settings = list_subscription_plan_settings()

    if saved_settings.get("load_error"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Subscription plan settings were saved, but the saved values "
                "could not be read back from Supabase. "
                f"Original error: {saved_settings['load_error']}"
            ),
        )

    if not saved_settings.get("persisted"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Subscription plan settings were saved, but no rows were read "
                "back from subscription_plan_settings."
            ),
        )

    return saved_settings


@router.get("/subscription-contact")
def get_subscription_contact(admin=Depends(require_admin)):
    """Return editable subscription contact settings for admins."""
    return list_subscription_contact_settings()


@router.put("/subscription-contact")
def update_subscription_contact(
    data: SubscriptionContactSettings,
    admin=Depends(require_admin),
):
    """Persist the support contact details shown on the parent Subscription page."""
    row = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    row["key"] = "default"
    row["email"] = (
        row.get("email")
        or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["email"]
    ).strip()
    row["phone"] = (row.get("phone") or "").strip()
    row["whatsapp"] = (row.get("whatsapp") or "").strip()
    row["availability"] = (
        row.get("availability")
        or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["availability"]
    ).strip()
    row["message"] = (
        row.get("message")
        or DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS["message"]
    ).strip()
    row["updated_by"] = admin["profile"]["id"]

    try:
        admin_client.table("subscription_contact_settings").upsert(
            row,
            on_conflict="key",
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save subscription contact settings. Make sure the "
                "subscription_contact_settings table exists. "
                f"Original error: {str(exc)}"
            ),
        )

    saved_settings = list_subscription_contact_settings()

    if saved_settings.get("load_error"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Subscription contact settings were saved, but could not be "
                "read back from Supabase. "
                f"Original error: {saved_settings['load_error']}"
            ),
        )

    return saved_settings


@router.post("/parents")
def create_parent(data: CreateParentRequest, admin=Depends(require_admin)):
    """
    Create a parent auth account/profile, creating a family when needed.

    Admin-created parents default to the free plan with CBSE enabled and SOF
    disabled until plan/access is updated.
    """
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
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
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
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
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


# ---------------------------------------------------------------------------
# Offer Code routes
# ---------------------------------------------------------------------------

def _generate_offer_code() -> str:
    """Generate a unique 8-character alphanumeric offer code (uppercase)."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=8))
        # Ensure no existing code collision
        existing = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", code)
            .execute()
        )
        if not existing.data:
            return code


@router.get("/offer-codes")
def list_offer_codes(admin=Depends(require_admin)):
    """Return all offer codes with usage stats for the admin panel."""
    try:
        result = (
            admin_client
            .table("offer_codes")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "offer_codes": result.data or []}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Offer codes table not found. Run backend/scripts/migration_offer_codes.sql "
                f"in Supabase first. Error: {str(exc)}"
            ),
        )


@router.post("/offer-codes")
def create_offer_code(data: CreateOfferCodeRequest, admin=Depends(require_admin)):
    """
    Create a new offer code.

    The 8-char alphanumeric code is auto-generated and guaranteed unique.
    The admin provides description, validity window, and max redemptions.
    """
    code = _generate_offer_code()
    admin_id = admin["profile"]["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "code": code,
        "description": (data.description or "").strip(),
        "valid_from": data.valid_from or now_iso,
        "valid_until": data.valid_until,
        "max_uses": max(1, data.max_uses),
        "uses_count": 0,
        "created_by": admin_id,
        "is_active": True,
        # Influencer tracking fields
        "influencer_name": (data.influencer_name or "").strip(),
        "influencer_email": (data.influencer_email or "").strip(),
        "code_type": data.code_type if data.code_type in ("free_trial", "discount") else "free_trial",
        "discount_percent": max(0, min(100, int(data.discount_percent or 0))),
        "incentive_inr": max(0, int(data.incentive_inr or 0)),
        "incentive_paid": False,
    }

    try:
        result = admin_client.table("offer_codes").insert(row).execute()
        saved = result.data[0] if result.data else row
        return {"success": True, "offer_code": saved}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create offer code. Run migration_offer_codes.sql and "
                "migration_offer_codes_influencer.sql in Supabase. "
                f"Error: {str(exc)}"
            ),
        )


@router.get("/offer-codes/influencer-summary")
def get_influencer_summary(admin=Depends(require_admin)):
    """
    Return per-influencer redemption stats for the admin tracking dashboard.

    Aggregates all codes with non-empty influencer_name, counts redemptions
    from offer_redemptions, and calculates total incentive payable.
    """
    try:
        codes = (
            admin_client
            .table("offer_codes")
            .select("*")
            .neq("influencer_name", "")
            .execute()
        ).data or []
    except Exception:
        return {"success": True, "influencers": []}

    if not codes:
        return {"success": True, "influencers": []}

    # Get redemption counts per code
    code_ids = [c["id"] for c in codes]
    try:
        redemptions = (
            admin_client
            .table("offer_redemptions")
            .select("code_id, user_id")
            .in_("code_id", code_ids)
            .execute()
        ).data or []
    except Exception:
        redemptions = []

    redemptions_by_code: dict = {}
    for r in redemptions:
        cid = r["code_id"]
        redemptions_by_code[cid] = redemptions_by_code.get(cid, 0) + 1

    # Aggregate by influencer name (one influencer may have multiple codes)
    by_influencer: dict = {}
    for code in codes:
        name = code.get("influencer_name") or "Unknown"
        if name not in by_influencer:
            by_influencer[name] = {
                "influencer_name": name,
                "influencer_email": code.get("influencer_email") or "",
                "codes": [],
                "total_redemptions": 0,
                "total_incentive_payable": 0,
                "incentive_paid": True,  # False if any code unpaid
            }
        redemption_count = redemptions_by_code.get(code["id"], 0)
        incentive = int(code.get("incentive_inr") or 0) * redemption_count
        paid = bool(code.get("incentive_paid"))
        by_influencer[name]["codes"].append({
            **code,
            "redemption_count": redemption_count,
            "incentive_due": incentive,
        })
        by_influencer[name]["total_redemptions"] += redemption_count
        by_influencer[name]["total_incentive_payable"] += incentive
        if not paid:
            by_influencer[name]["incentive_paid"] = False

    return {
        "success": True,
        "influencers": list(by_influencer.values()),
        "total_payable": sum(i["total_incentive_payable"] for i in by_influencer.values() if not i["incentive_paid"]),
    }


@router.get("/offer-codes/enrollments")
def get_offer_code_enrollments(admin=Depends(require_admin)):
    """
    Return all student enrollments grouped by offer code.

    For each active offer code, returns:
    - Code details (code, influencer, valid_until, uses_count)
    - List of enrolled students (username, email, grade, enrolled_at)

    Joins offer_redemptions + offer_codes + profiles in Python
    (Supabase free tier has no cross-table joins via REST).
    """
    try:
        # Load all offer codes
        codes_result = admin_client.table("offer_codes").select("*").order("created_at", desc=True).execute()
        codes = {c["id"]: c for c in (codes_result.data or [])}
    except Exception:
        return {"success": True, "codes": []}

    if not codes:
        return {"success": True, "codes": []}

    # Load all redemptions
    try:
        redemptions_result = admin_client.table("offer_redemptions").select("*").order("redeemed_at", desc=True).execute()
        redemptions = redemptions_result.data or []
    except Exception:
        redemptions = []

    # Load profiles for all redeemed user_ids
    user_ids = list({r["user_id"] for r in redemptions})
    profiles_by_id: dict = {}
    if user_ids:
        try:
            batch = admin_client.table("profiles").select("id,username,email,grade,board,created_at").in_("id", user_ids).execute()
            profiles_by_id = {p["id"]: p for p in (batch.data or [])}
        except Exception:
            pass

    # Group redemptions by code
    enrollments_by_code: dict = {}
    for r in redemptions:
        cid = r["code_id"]
        if cid not in enrollments_by_code:
            enrollments_by_code[cid] = []
        profile = profiles_by_id.get(r["user_id"], {})
        enrollments_by_code[cid].append({
            "user_id": r["user_id"],
            "username": profile.get("username") or "—",
            "email": profile.get("email") or "—",
            "grade": profile.get("grade") or "—",
            "board": profile.get("board") or "CBSE",
            "enrolled_at": r.get("redeemed_at", "")[:19],
            "access_until": r.get("valid_until", "")[:10],
        })

    # Build response: all codes with their enrollments
    result = []
    for code in codes.values():
        result.append({
            "id": code["id"],
            "code": code["code"],
            "description": code.get("description") or "",
            "influencer_name": code.get("influencer_name") or "",
            "influencer_email": code.get("influencer_email") or "",
            "code_type": code.get("code_type") or "free_trial",
            "valid_until": (code.get("valid_until") or "")[:10],
            "is_active": code.get("is_active", False),
            "max_uses": code.get("max_uses", 0),
            "uses_count": code.get("uses_count", 0),
            "incentive_inr": code.get("incentive_inr", 0),
            "enrollments": enrollments_by_code.get(code["id"], []),
            "enrollment_count": len(enrollments_by_code.get(code["id"], [])),
        })

    return {
        "success": True,
        "codes": result,
        "total_enrollments": sum(c["enrollment_count"] for c in result),
    }


@router.patch("/offer-codes/{code_id}/mark-incentive-paid")
def mark_influencer_incentive_paid(code_id: str, admin=Depends(require_admin)):
    """Mark a specific offer code's influencer incentive as paid."""
    result = (
        admin_client
        .table("offer_codes")
        .update({
            "incentive_paid": True,
            "incentive_paid_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", code_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")
    return {"success": True, "offer_code": result.data[0]}


@router.post("/offer-codes/regenerate-promo-images")
def regenerate_promo_images(payload: dict, admin=Depends(require_admin)):
    """
    Regenerate all WhatsApp promo images with a new offer code banner and
    re-upload them to the sales-collaterals/whatsapp/ Supabase bucket.

    Payload: { "offer_code": "L3YT1HAD", "valid_until": "30 June 2026" }
    """
    import subprocess
    import sys
    import pathlib

    offer_code = (payload.get("offer_code") or "").strip().upper()
    valid_until = (payload.get("valid_until") or "").strip()

    if not offer_code:
        raise HTTPException(status_code=400, detail="offer_code is required.")

    script = pathlib.Path(
        "/Users/a0247716/Pradips_Project/LikhaPohaAI-ReelBot/"
        "likha-poha-reel-factory/tools/create_whatsapp_promos.py"
    )
    if not script.exists():
        raise HTTPException(status_code=500, detail="Promo generation script not found.")

    # Step 1 — generate images
    cmd = [sys.executable, str(script), "--offer-code", offer_code]
    if valid_until:
        cmd += ["--valid-until", valid_until]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Image generation timed out.")

    # Step 2 — upload to Supabase
    promo_dir = pathlib.Path(
        "/Users/a0247716/Pradips_Project/LikhaPohaAI-ReelBot/"
        "likha-poha-reel-factory/output/whatsapp-promos"
    )
    bucket = "sales-collaterals"
    folder = "whatsapp"
    uploaded = []
    errors = []

    for img_path in sorted(promo_dir.glob("*.png")):
        fname = img_path.name
        dest = f"{folder}/{fname}"
        with open(img_path, "rb") as f:
            data = f.read()
        try:
            try:
                admin_client.storage.from_(bucket).update(dest, data, {"content-type": "image/png", "upsert": "true"})
            except Exception:
                admin_client.storage.from_(bucket).upload(dest, data, {"content-type": "image/png"})
            pub = admin_client.storage.from_(bucket).get_public_url(dest)
            uploaded.append({"file": fname, "url": pub})
        except Exception as exc:
            errors.append({"file": fname, "error": str(exc)})

    return {
        "success": True,
        "offer_code": offer_code,
        "valid_until": valid_until,
        "uploaded": len(uploaded),
        "errors": errors,
        "files": uploaded,
    }


@router.patch("/offer-codes/{code_id}/deactivate")
def deactivate_offer_code(code_id: str, admin=Depends(require_admin)):
    """Deactivate an offer code so it can no longer be redeemed."""
    result = (
        admin_client
        .table("offer_codes")
        .update({"is_active": False})
        .eq("id", code_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer code not found.")
    return {"success": True, "offer_code": result.data[0]}


@router.post("/redeem-offer-code")
def redeem_offer_code(
    payload: dict,
    current_user=Depends(require_admin),
):
    """
    Placeholder — actual redemption is handled by /api/offer/redeem (no admin required).
    This route exists for admin-initiated redemption testing only.
    """
    return {"success": False, "message": "Use /api/offer/redeem for student redemptions."}


@router.post("/teachers")
def create_teacher(data: CreateTeacherRequest, admin=Depends(require_admin)):
    """
    Create a teacher auth/profile pair from the admin panel only.

    Teachers can represent either school accounts or independent tutors. Their
    metadata is stored separately so teacher access can evolve without changing
    parent/student signup.
    """
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
        "access_sof_science": True,
        "access_sof_maths": True,
        "access_sof_english": True,
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


@router.post("/teacher-assignments")
def assign_teacher_student(
    data: AssignTeacherStudentRequest,
    admin=Depends(require_admin),
):
    """Assign one student to one teacher for a subject/section context."""
    response = (
        admin_client
        .table("teacher_student_assignments")
        .upsert(
            {
                "teacher_id": data.teacher_id,
                "student_id": data.student_id,
                "grade": data.grade or "Grade 9",
                "subject": data.subject or "",
                "section": data.section or "",
            },
            on_conflict="teacher_id,student_id,subject",
        )
        .execute()
    )

    return {
        "success": True,
        "assignment": response.data[0] if response.data else {
            "teacher_id": data.teacher_id,
            "student_id": data.student_id,
            "grade": data.grade or "Grade 9",
            "subject": data.subject or "",
            "section": data.section or "",
        },
    }


@router.delete("/teacher-assignments/{assignment_id}")
def delete_teacher_assignment(
    assignment_id: str,
    admin=Depends(require_admin),
):
    """Remove one teacher-student assignment from the admin panel."""
    admin_client.table("teacher_student_assignments").delete().eq(
        "id",
        assignment_id,
    ).execute()

    return {
        "success": True,
        "message": "Teacher assignment removed.",
    }


@router.patch("/access/{child_id}")
def update_child_access(
    child_id: str,
    data: UpdateAccessRequest,
    admin=Depends(require_admin),
):
    """Update a student's subscription plan, status, and subject access flags."""
    response = (
        admin_client
        .table("profiles")
        .update({
            "access_cbse": data.access_cbse,
            "access_sof_science": data.access_sof_science,
            "access_sof_maths": data.access_sof_maths,
            "access_sof_english": data.access_sof_english,
            "cbse_subjects": clean_subject_access_list(data.cbse_subjects),
            "subscription_plan": data.subscription_plan,
            "account_status": data.account_status,
            "grade": data.grade or "Grade 9",
            "board": normalize_board(data.board),
            "ai_model_preference": normalize_model_preference(
                data.ai_model_preference,
            ),
        })
        .eq("id", child_id)
        .eq("role", "student")
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return {
        "success": True,
        "profile": response.data[0],
    }


@router.patch("/limits/{child_id}")
def update_child_limits(
    child_id: str,
    data: UpdateLimitsRequest,
    admin=Depends(require_admin),
):
    """Update a student's daily and monthly AI token limits."""
    response = (
        admin_client
        .table("profiles")
        .update({
            "daily_token_limit": normalize_token_limit(data.daily_token_limit),
            "monthly_token_limit": normalize_token_limit(data.monthly_token_limit),
        })
        .eq("id", child_id)
        .eq("role", "student")
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return {
        "success": True,
        "profile": response.data[0],
    }


# ---------------------------------------------------------------------------
# AI Settings — master switch + API key management
# ---------------------------------------------------------------------------

class UpdateAiSettingsRequest(BaseModel):
    api_enabled: bool
    openai_api_key: str | None = None


def _load_ai_settings_row() -> dict | None:
    """Read the ai_settings row from admin_settings. Returns value dict or None."""
    try:
        response = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", "ai_settings")
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["value"]
    except Exception:
        pass
    return None


@router.get("/ai-settings")
def get_ai_settings(admin=Depends(require_admin)):
    """
    Return current AI settings for the admin console.

    The full API key is never returned — only the first 8 characters so the
    admin can confirm which key is active without exposing the secret.
    """
    row = _load_ai_settings_row()

    if row:
        stored_key = (row.get("openai_api_key") or "").strip()
        effective_key = stored_key if stored_key else (settings.OPENAI_API_KEY or "")
        return {
            "success": True,
            "api_enabled": row.get("api_enabled", True),
            "api_key_prefix": effective_key[:12] if effective_key else "",
            "key_source": "database" if stored_key else "environment",
        }

    # Table exists but no row yet — fall back to env key
    env_key = settings.OPENAI_API_KEY or ""
    return {
        "success": True,
        "api_enabled": True,
        "api_key_prefix": env_key[:12] if env_key else "",
        "key_source": "environment",
    }


@router.put("/ai-settings")
def update_ai_settings(
    data: UpdateAiSettingsRequest,
    admin=Depends(require_admin),
):
    """
    Persist the master API switch and (optionally) a new OpenAI API key.

    When openai_api_key is omitted or blank the existing stored key is kept.
    After saving, the in-memory settings cache is force-expired so the next
    LLM call picks up the change without a server restart.
    """
    # Preserve existing key when the admin only toggles the switch
    existing_key = ""
    row = _load_ai_settings_row()
    if row:
        existing_key = (row.get("openai_api_key") or "").strip()

    new_key = (data.openai_api_key or "").strip()
    effective_key = new_key if new_key else existing_key

    value = {
        "api_enabled": data.api_enabled,
        "openai_api_key": effective_key,
    }

    try:
        admin_client.table("admin_settings").upsert(
            {
                "key": "ai_settings",
                "value": value,
                "updated_at": "now()",
            },
            on_conflict="key",
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save AI settings. Run backend/sql/add_admin_settings.sql "
                f"in Supabase first. Original error: {str(exc)}"
            ),
        )

    # Immediately expire the in-memory cache in this process
    from app.services.openai_service import force_refresh_settings
    force_refresh_settings()

    display_key = effective_key if effective_key else (settings.OPENAI_API_KEY or "")
    return {
        "success": True,
        "api_enabled": data.api_enabled,
        "api_key_prefix": display_key[:12] if display_key else "",
        "key_source": "database" if effective_key else "environment",
        "message": "AI settings saved successfully.",
    }


@router.get("/payment-logs")
def get_payment_logs(admin=Depends(require_admin)):
    """
    Return all payment records for the admin Payment Logs page.

    Joins subscription_payments with profiles to add username, email, grade.
    Also computes summary stats: monthly revenue, active paid users, plan breakdown,
    and a 12-month revenue/user trend for charts.
    """
    from datetime import datetime, timezone  # noqa: PLC0415
    import calendar  # noqa: PLC0415

    # Load all payment records
    try:
        pay_result = (
            admin_client
            .table("subscription_payments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        payments = pay_result.data or []
    except Exception:
        return {"success": True, "payments": [], "summary": {}, "trends": []}

    # Load profiles for all parent_ids
    user_ids = list({p.get("parent_id") for p in payments if p.get("parent_id")})
    profiles_by_id: dict = {}
    if user_ids:
        try:
            batch = (
                admin_client
                .table("profiles")
                .select("id,username,email,grade,board")
                .in_("id", user_ids)
                .execute()
            )
            profiles_by_id = {p["id"]: p for p in (batch.data or [])}
        except Exception:
            pass

    # Enrich payments with profile data
    enriched = []
    for p in payments:
        profile = profiles_by_id.get(p.get("parent_id") or "") or {}
        meta = p.get("metadata") or {}
        enriched.append({
            "id": p.get("id"),
            "order_id": p.get("razorpay_order_id"),
            "payment_id": p.get("razorpay_payment_id"),
            "status": p.get("status", "unknown"),
            "plan_key": p.get("plan_key"),
            "amount": p.get("amount", 0),
            "currency": p.get("currency", "INR"),
            "username": profile.get("username") or meta.get("signup_role", "—"),
            "email": profile.get("email") or meta.get("signup_email", "—"),
            "grade": profile.get("grade") or "—",
            "created_at": (p.get("created_at") or "")[:19],
            "verified_at": (p.get("verified_at") or "")[:19],
            "failure_reason": meta.get("failure_reason") or meta.get("error") or "",
        })

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Summary stats
    paid = [p for p in enriched if p["status"] == "paid"]
    this_month_paid = [p for p in paid if (p["created_at"] or "").startswith(this_month)]
    monthly_revenue = sum(p["amount"] for p in this_month_paid)
    total_revenue = sum(p["amount"] for p in paid)
    active_paid_users = len({p["email"] for p in paid if p["email"] != "—"})

    # Plan distribution
    plan_counts: dict = {}
    for p in paid:
        k = p["plan_key"] or "unknown"
        plan_counts[k] = plan_counts.get(k, 0) + 1

    # 12-month trend
    trends = []
    for months_ago in range(11, -1, -1):
        m = (now.month - months_ago - 1) % 12 + 1
        y = now.year - (months_ago // 12) - (1 if (now.month - months_ago - 1) < 0 else 0)
        label = f"{y}-{m:02d}"
        month_paid = [p for p in paid if (p["created_at"] or "").startswith(label)]
        trends.append({
            "month": label,
            "label": f"{calendar.month_abbr[m]} {str(y)[-2:]}",
            "revenue": sum(p["amount"] for p in month_paid),
            "users": len({p["email"] for p in month_paid if p["email"] != "—"}),
        })

    return {
        "success": True,
        "payments": enriched,
        "summary": {
            "monthly_revenue": monthly_revenue,
            "total_revenue": total_revenue,
            "active_paid_users": active_paid_users,
            "total_transactions": len(paid),
            "failed_transactions": len([p for p in enriched if p["status"] == "failed"]),
            "plan_distribution": plan_counts,
        },
        "trends": trends,
    }


@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin=Depends(require_admin)):
    """
    Delete a user from Supabase auth and then remove their profile row.

    Auth deletion happens first so a profile is not removed while the login
    account remains active.
    """
    profile_response = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if not profile_response.data:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        admin_client.auth.admin.delete_user(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to delete auth user: {str(exc)}",
        )

    admin_client.table("profiles").delete().eq("id", user_id).execute()

    return {
        "success": True,
        "message": "User deleted successfully.",
    }


# ── Offer-gate test harness (admin only) ─────────────────────────────────────

@router.post("/offer-gate-test")
def offer_gate_test(
    payload: dict,
    admin=Depends(require_admin),
):
    """
    Admin-only endpoint to toggle offer-gate mode on any user without touching
    Supabase directly.

    Actions:
      enable  — strip paid access flags, insert a 30-day test offer redemption.
      disable — restore access_cbse=True, delete all test offer redemptions.
      status  — return current gate state without changing anything.

    Payload: {"username": "akshita.teststudent", "action": "enable|disable|status"}
    """
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415

    username = str(payload.get("username") or "").strip().casefold()
    action = str(payload.get("action") or "status").strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="username is required.")

    if action not in ("enable", "disable", "status"):
        raise HTTPException(status_code=400, detail="action must be enable, disable, or status.")

    # Resolve user profile
    profile_resp = (
        admin_client
        .table("profiles")
        .select("id, username, role, access_cbse, access_sof_science, access_sof_maths, access_sof_english")
        .ilike("username", username)
        .limit(1)
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    profile = profile_resp.data[0]
    user_id = profile["id"]

    # Determine current state
    has_paid_access = bool(
        profile.get("access_cbse")
        or profile.get("access_sof_science")
        or profile.get("access_sof_maths")
        or profile.get("access_sof_english")
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    redemption_resp = (
        admin_client
        .table("offer_redemptions")
        .select("id, valid_until, code_id")
        .eq("user_id", user_id)
        .gte("valid_until", now_iso)
        .limit(1)
        .execute()
    )
    is_currently_gated = not has_paid_access and bool(redemption_resp.data)

    if action == "status":
        return {
            "success": True,
            "username": profile.get("username"),
            "is_offer_gated": is_currently_gated,
            "has_paid_access": has_paid_access,
            "active_redemptions": len(redemption_resp.data or []),
        }

    if action == "enable":
        # 1. Strip all paid access flags
        admin_client.table("profiles").update({
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
        }).eq("id", user_id).execute()

        # 2. Ensure a test offer code exists
        test_code_label = "ADMTST01"
        existing_code = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", test_code_label)
            .limit(1)
            .execute()
        )
        if existing_code.data:
            code_id = existing_code.data[0]["id"]
        else:
            valid_until_far = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            new_code = admin_client.table("offer_codes").insert({
                "code": test_code_label,
                "label": "Admin Offer-Gate Test Code",
                "is_active": True,
                "valid_from": datetime.now(timezone.utc).isoformat(),
                "valid_until": valid_until_far,
                "max_uses": 9999,
                "uses_count": 0,
            }).execute()
            code_id = new_code.data[0]["id"]

        # 3. Upsert a 30-day test redemption for this user
        valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        # Remove any existing redemptions for this code+user first to avoid duplicates
        admin_client.table("offer_redemptions").delete().eq("user_id", user_id).eq("code_id", code_id).execute()
        admin_client.table("offer_redemptions").insert({
            "user_id": user_id,
            "code_id": code_id,
            "valid_until": valid_until,
        }).execute()

        return {
            "success": True,
            "action": "enabled",
            "username": profile.get("username"),
            "message": f"Offer gate ENABLED for {profile.get('username')}. "
                       f"access_cbse=False, test redemption valid until {valid_until[:10]}. "
                       "Ask Doubt and Lesson follow-up are now DKB-only.",
        }

    if action == "disable":
        # 1. Restore paid access
        admin_client.table("profiles").update({
            "access_cbse": True,
        }).eq("id", user_id).execute()

        # 2. Delete the test redemption for ADMTST01 if it exists
        test_code = (
            admin_client
            .table("offer_codes")
            .select("id")
            .eq("code", "ADMTST01")
            .limit(1)
            .execute()
        )
        if test_code.data:
            admin_client.table("offer_redemptions").delete().eq("user_id", user_id).eq("code_id", test_code.data[0]["id"]).execute()

        return {
            "success": True,
            "action": "disabled",
            "username": profile.get("username"),
            "message": f"Offer gate DISABLED for {profile.get('username')}. "
                       "access_cbse restored to True. Full LLM access is back.",
        }
