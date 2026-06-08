from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.data.subscription_plans import (
    get_default_subscription_plans,
    subscription_plan_order,
)
from app.services.model_routing_service import normalize_model_preference
from app.services.auth_service import require_admin, create_auth_user, admin_client
from app.services.board_service import normalize_board
from app.services.subject_access_service import clean_subject_access_list
from app.services.usage_service import normalize_token_limit

router = APIRouter()


class CreateParentRequest(BaseModel):
    email: str
    password: str
    username: str
    family_id: str | None = None


class CreateChildRequest(BaseModel):
    email: str
    password: str
    username: str
    parent_id: str
    family_id: str
    grade: str = "Grade 9"
    board: str = "CBSE"


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

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
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
    """Create a student auth account/profile under an existing parent/family."""
    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    child_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "student",
        "parent_id": data.parent_id,
        "family_id": data.family_id,
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
