"""
parent_dashboard.py
─────────────────────────────────────────────────────────────────────────────
Parent Experience Platform — consolidated (formerly split across
parent_dashboard.py / parent_dashboard_v2.py / parent_dashboard_p2.py).

Two routers are exposed, matching the two URL prefixes already in production:

  router          @ /api/parent-dashboard  — family/children CRUD (original)
  router_parent   @ /api/parent            — dashboard summary, child detail,
                                              analytics, insights, progress
                                              report, notifications (former
                                              "Phase 1" + "Phase 2")

Safety rules (apply to router_parent endpoints):
- Parent can only see own linked children (parent_id / family_id match).
- parentId NEVER implies paid access.
- feature authorization uses canonical feature_authorization_service.
- teacher-private notes NEVER exposed.
- admin audit metadata NEVER exposed.
- Missing data sources return graceful empty/null (never crash).
- create-student child limit enforced from subscription resolver, not hardcoded.
- Notification metadata is sanitized (no secrets/tokens).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.auth_service import require_parent, get_current_user, create_auth_user, invite_parent_by_email, admin_client
from app.services.supabase_retry import call_with_retry
from app.services.parent_dashboard_service import (
    get_children,
    get_child_by_id,
    get_family_members,
)
from app.services.subscription_resolver_service import resolve_user_subscription
from app.services.feature_authorization_service import (
    get_feature_summary,
    Feature,
    FREE_MOCK_TEST_DAILY_LIMIT,
)
from app.services.subscription_settings_service import (
    list_subscription_contact_settings,
    list_subscription_plan_settings,
)
from app.services.board_service import normalize_board
from app.services.audit_log_service import write_audit_event

_log = logging.getLogger("likhapoha.parent")

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CHILD_EMAIL_DOMAIN = "child.likhapoha.in"


def _resolve_child_auth_email(requested_email: str | None, username: str) -> str:
    """
    Return the email used for Supabase auth + profile lookup.

    - If the parent provided a real email, use it.
    - Otherwise generate a synthetic email so Supabase auth (which always
      requires an email) succeeds and the lookup-email login flow works.
    """
    raw = (requested_email or "").strip()
    if raw and _EMAIL_RE.match(raw):
        return raw
    # Sanitise username to a safe local-part
    safe = re.sub(r"[^a-zA-Z0-9._-]", "", username) or "child"
    return f"{safe}@{_CHILD_EMAIL_DOMAIN}"


class CreateStudentRequest(BaseModel):
    email: Optional[str] = None   # optional for children — real or synthetic
    password: str
    username: str
    board: str = "CBSE"
    grade: str = "Grade 9"   # required from the parent form — defaults kept for API compat
    stream: Optional[str] = None  # required for Grade 11/12: PCM|PCB|PCMB|Commerce|Humanities
    avatar: Optional[str] = None  # emoji key (e.g. 'boy1') or data: URL
    cbse_subjects: Optional[list] = None


class InviteParentRequest(BaseModel):
    email: str
    username: str
    # password is NOT accepted here — Supabase sends an invite email and the
    # parent sets their own password when they click the confirmation link.
    # This enforces real email ownership verification before first login.


@router.get("/family")
def get_family(parent=Depends(require_parent)):
    """Return all parents and children in the signed-in parent's family."""
    parent_profile = parent["profile"]
    family = get_family_members(parent_profile["id"])

    return {
        "success": True,
        "family_id": family["family_id"],
        "parents": family["parents"],
        "children": family["children"],
    }


@router.get("/children")
def get_parent_children(parent=Depends(require_parent)):
    """Return only the children that belong to the signed-in parent's family."""
    parent_profile = parent["profile"]

    return {
        "success": True,
        "children": get_children(parent_profile["id"]),
    }


@router.get("/subscription-plans")
def get_parent_subscription_plans(user=Depends(get_current_user)):
    """Return public subscription plans for the subscription page.

    Accessible by any authenticated user (parent, student, child, teacher)
    — this endpoint only returns public pricing data, not personal information.
    """
    settings = list_subscription_plan_settings()
    plans = {
        key: plan
        for key, plan in settings["plans"].items()
        if plan.get("is_public") is not False
    }
    plan_order = [
        key for key in settings["plan_order"]
        if key in plans
    ]

    return {
        "success": True,
        "persisted": settings.get("persisted", False),
        "source": settings.get("source", "defaults"),
        "load_error": settings.get("load_error"),
        "plans": plans,
        "plan_order": plan_order,
        "contact": list_subscription_contact_settings().get("contact", {}),
    }


@router.get("/children/{child_id}")
def get_single_child(child_id: str, parent=Depends(require_parent)):
    """Return one child profile after parent-scoped ownership validation."""
    parent_profile = parent["profile"]

    child = get_child_by_id(parent_profile["id"], child_id)

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    return {
        "success": True,
        "child": child,
    }

@router.get("/children/{child_id}/weak-area-alerts")
def get_child_weak_area_alerts(child_id: str, parent=Depends(require_parent)):
    """Return weak-area alerts for one child owned by the signed-in parent."""
    parent_profile = parent["profile"]

    child = get_child_by_id(parent_profile["id"], child_id)

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    response = (
        admin_client
        .table("weak_area_alerts")
        .select("*")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "success": True,
        "alerts": response.data or [],
    }


@router.post("/create-student")
def create_student(data: CreateStudentRequest, parent=Depends(require_parent)):
    """
    Create a student auth account and profile inside the parent's family.

    Families are capped at two children here to keep the paid-plan/family-plan
    assumptions consistent.
    """
    parent_profile = parent["profile"]

    children = get_children(parent_profile["id"])

    # Child limit from canonical subscription resolver (not hardcoded).
    # FREE/NANO/PREMIUM = 1 child. FAMILY_PREMIUM = 2. ADMIN_GRANT = None (no limit).
    parent_sub = resolve_user_subscription(parent_profile["id"])
    child_limit = parent_sub.get("child_limit")  # None means no limit (admin)
    if child_limit is None:
        cpk = parent_sub.get("canonical_plan_key", "FREE_TIER")
        child_limit = 2 if cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL") else 1
    if len(children) >= child_limit:
        plan_name = parent_sub.get("plan_name", "your plan")
        raise HTTPException(
            status_code=400,
            detail=f"Child limit reached for {plan_name}. Maximum {child_limit} child{'ren' if child_limit > 1 else ''} allowed.",
        )

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    # A username collision here isn't just cosmetic: get_child_analytics and
    # get_parent_dashboard_summary below both filter test_history/
    # student_progress/weak_area_alerts by the username STRING, so a new
    # child sharing a name with an existing profile inherits that profile's
    # mock test scores and progress. See docs/sql/2026-08-16_check_username_uniqueness.sql
    # (this collided for real: two "likha" profiles, 2026-08-20).
    from app.routes.auth import _reject_reserved_username, _reject_taken_username  # noqa: PLC0415
    _reject_reserved_username(data.username)
    _reject_taken_username(data.username, client=admin_client)

    auth_email = _resolve_child_auth_email(data.email, data.username)

    auth_user = create_auth_user(
        email=auth_email,
        password=data.password,
    )

    from app.data.product_catalogue import ALL_GRADES  # noqa: PLC0415
    grade = data.grade if data.grade in ALL_GRADES else "Grade 9"

    child_profile = {
        "id": auth_user.id,
        # Store the resolved email (real or synthetic) so the username→email
        # lookup-email login flow returns a usable address for signInWithPassword.
        "email": auth_email,
        "username": data.username,
        "role": "student",
        "parent_id": parent_profile["id"],
        "family_id": parent_profile["family_id"],
        "board": normalize_board(data.board),
        "grade": grade,
        "subscription_plan": parent_profile.get("subscription_plan", "free"),
        "account_status": "active",
        "access_cbse": parent_profile.get("access_cbse", False),
        "cbse_subjects": data.cbse_subjects or [],
        "daily_token_limit": parent_profile.get("daily_token_limit", 50000),
        "monthly_token_limit": parent_profile.get("monthly_token_limit", 1000000),
        "ai_model_preference": "default",
    }

    # Grade 11/12: stream is required and cbse_subjects is derived server-side
    # from it — mirrors the same rule enforced in auth.py's signup_free route,
    # so a parent-created child gets the same subject access as a self-signup.
    if grade in ("Grade 11", "Grade 12"):
        valid_streams = {"PCM", "PCB", "PCMB", "Commerce", "Humanities"}
        stream = (data.stream or "").strip()
        if stream not in valid_streams:
            raise HTTPException(
                status_code=400,
                detail=f"Stream is required for {grade} students. "
                       f"Choose one of: PCM, PCB, PCMB, Commerce, Humanities",
            )
        stream_subjects = {
            "PCM":        ["Physics", "Chemistry", "Mathematics", "English", "Hindi"],
            "PCB":        ["Physics", "Chemistry", "Biology", "English", "Hindi"],
            "PCMB":       ["Physics", "Chemistry", "Mathematics", "Biology", "English", "Hindi"],
            "Commerce":   ["Mathematics", "Business Studies", "Accountancy", "Economics", "English", "Hindi"],
            "Humanities": ["History", "Geography", "Political Science", "Sociology", "English", "Hindi"],
        }
        child_profile["stream"] = stream
        child_profile["cbse_subjects"] = stream_subjects.get(stream, [])

    # Save avatar if provided (emoji key or data: URL)
    if data.avatar:
        child_profile["avatar"] = data.avatar[:400000]  # cap at ~300KB

    response = (
        admin_client
        .table("profiles")
        .insert(child_profile)
        .execute()
    )

    # Detect silent insert failure (RLS or constraint violation with empty data)
    if not response.data:
        # Profile insert silently returned nothing — attempt to rollback auth user
        try:
            admin_client.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Child account created but profile could not be saved. Please try again.",
        )

    created_profile = response.data[0]

    # login_id: what the child types to log in (their username in the lookup-email flow)
    # The lookup-email endpoint resolves username → email → Supabase signIn
    login_id = data.username  # display name is the login identifier

    return {
        "success": True,
        "child": created_profile,
        "login_id": login_id,
        "login_email": auth_email,  # actual Supabase auth email (synthetic or real)
        "login_note": (
            "Child logs in with their display name as username. "
            f"Login ID: {login_id}"
        ),
    }


class UpdateAvatarRequest(BaseModel):
    avatar: str  # emoji key or data: URL


@router.post("/update-avatar")
def update_avatar(data: UpdateAvatarRequest, parent=Depends(require_parent)):
    """Parent updates their own avatar."""
    parent_profile = parent["profile"]
    admin_client.table("profiles").update(
        {"avatar": data.avatar[:400000]}
    ).eq("id", parent_profile["id"]).execute()
    return {"success": True}


@router.post("/invite-parent")
def invite_parent(data: InviteParentRequest, parent=Depends(require_parent)):
    """
    Invite another parent to join the same family.

    Email confirmation is always enforced for parent-initiated invites so the
    invited parent must verify their email address before they can log in.
    Only admin-created accounts bypass this check.
    """
    parent_profile = parent["profile"]

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    # Use invite_user_by_email so Supabase sends a real invitation email.
    # The invited parent must click the link to confirm their email and set
    # their password before they can log in. This is the only Supabase admin
    # API method that actually sends an email upon account creation.
    auth_user = invite_parent_by_email(
        email=data.email,
        username=data.username,
    )

    invited_parent = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "parent",
        "family_id": parent_profile["family_id"],
        "parent_id": None,
    }

    response = (
        admin_client
        .table("profiles")
        .insert(invited_parent)
        .execute()
    )

    return {
        "success": True,
        "parent": response.data[0] if response.data else invited_parent,
    }


# ═════════════════════════════════════════════════════════════════════════════
# router_parent  @ /api/parent  (formerly parent_dashboard_v2.py "Phase 1")
# ═════════════════════════════════════════════════════════════════════════════

router_parent = APIRouter()


def _safe_query(fn):
    """Execute a Supabase query; return (data_list, error_str) — never crash.

    Wrapped with call_with_retry so transient HTTP/2 connection drops
    (Render free tier occasionally terminates the connection pool
    mid-request — see supabase_retry.py) are retried instead of
    immediately surfacing as a query failure / empty result."""
    try:
        r = call_with_retry(fn)
        return (r.data or [], None)
    except Exception as exc:
        _log.warning("parent_dashboard query failed: %s", exc)
        return ([], str(exc)[:120])


_SAFE_Q = lambda fn: _safe_query(fn)  # noqa: E731


def _safe_one(fn):
    """Execute a Supabase query; return (first_row | None, error_str)."""
    rows, err = _safe_query(fn)
    return (rows[0] if rows else None, err)

def _normalize_score_pct(percentage=None, raw_score=None, max_score=None) -> float | None:
    """
    Canonical score normalizer for parent dashboard display.

    Rules:
    - If percentage is provided and 0 <= percentage <= 100 → use directly.
    - If percentage > 100 → treat as invalid, try raw_score/max_score calculation.
    - If raw_score and max_score both > 0 → (raw_score / max_score) * 100.
    - If ambiguous or no valid data → return None (show "Score not available").
    - Never multiply an already-percent value by 100.
    """
    # Preferred: percentage column (already 0-100)
    if percentage is not None:
        pct = float(percentage)
        if 0.0 <= pct <= 100.0:
            return round(pct, 1)
        # pct > 100: invalid, fall through to raw calculation

    # Fallback: raw_score / max_score
    if raw_score is not None and max_score and float(max_score) > 0:
        pct = (float(raw_score) / float(max_score)) * 100.0
        if 0.0 <= pct <= 100.0:
            return round(pct, 1)

    return None  # Cannot determine a valid percentage



def _plan_display(cpk: str, plan_name: str, has_full: bool, expires_at, days_remaining) -> dict:
    """Build a human-friendly plan summary for parent UI."""
    expiry_warning = False
    if expires_at and days_remaining is not None:
        expiry_warning = days_remaining <= 3

    if cpk == "FREE_TIER":
        status_label = "Free Tier — Restricted"
        status_color = "restricted"
        description = "This child is on Free Tier with limited access."
    elif cpk == "NANO":
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for 8 days.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk in ("PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL"):
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for one child, 30 days.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL"):
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for up to two children.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk == "ADMIN_GRANT":
        status_label = "Admin Override / Full Access"
        status_color = "admin"
        description = "Full access granted by admin."
    else:
        status_label = "Free Tier — Restricted" if not has_full else "Full Access"
        status_color = "restricted" if not has_full else "paid"
        description = ""

    return {
        "canonical_plan_key": cpk,
        "plan_name": plan_name,
        "has_full_access": has_full,
        "status_label": status_label,
        "status_color": status_color,  # "restricted" | "paid" | "admin"
        "description": description,
        "expires_at": expires_at,
        "days_remaining": days_remaining,
        "expiry_warning": expiry_warning,
    }


def _build_feature_badges(features: dict) -> list:
    """Build UI-ready feature badge list from get_feature_summary output."""
    badge_map = [
        (Feature.LESSONS,           "Lessons",           "📖"),
        (Feature.MOCK_TEST,         "Mock Tests",        "📝"),
        (Feature.EXEMPLAR,          "Exemplar",          "🔬"),
        (Feature.EXEMPLAR_RESEARCH, "Exemplar Research", "🧪"),
        (Feature.ASK_DOUBTS,        "Ask Doubts",        "❓"),
        (Feature.AI_ASSISTANT,      "AI Assistant",      "🤖"),
    ]
    badges = []
    for feat_key, label, icon in badge_map:
        feat = features.get(feat_key, {})
        allowed = feat.get("allowed", False)
        limited = feat.get("limited", False)
        if allowed and not limited:
            state = "full"
        elif allowed and limited:
            state = "limited"
        else:
            state = "locked"
        badges.append({
            "feature": feat_key,
            "label": label,
            "icon": icon,
            "state": state,  # "full" | "limited" | "locked"
        })
    return badges


def _build_recommendations(child_username: str, sub: dict, features: dict,
                            mock_count: int, last_active: str | None) -> list:
    """Rule-based recommendations from available data. No external AI."""
    recs = []
    cpk = sub.get("canonical_plan_key", "FREE_TIER")
    has_full = sub.get("has_full_access", False)

    # Inactivity check
    if not last_active:
        recs.append({
            "type": "inactive",
            "title": "Encourage your child to log in",
            "body": "No recent activity recorded. Regular practice improves results.",
            "action": "view_progress",
            "priority": "medium",
        })
    else:
        try:
            la_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            if la_dt.tzinfo is None:
                la_dt = la_dt.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - la_dt).days
            if days_ago >= 7:
                recs.append({
                    "type": "inactive",
                    "title": f"Your child hasn't logged in for {days_ago} days",
                    "body": "Regular daily study leads to better exam results.",
                    "action": "view_progress",
                    "priority": "high" if days_ago >= 14 else "medium",
                })
        except Exception:
            pass

    # Free Tier upgrade nudge
    if cpk == "FREE_TIER":
        recs.append({
            "type": "upgrade",
            "title": "Unlock full platform access",
            "body": "Your child is on Free Tier with limited lessons, mock tests, and no Exemplar access. Upgrade to Premium for full CBSE coverage.",
            "action": "upgrade",
            "priority": "high",
        })

    # No mock tests
    if mock_count == 0:
        recs.append({
            "type": "mock_test",
            "title": "Try the first mock test",
            "body": "Mock tests help identify weak areas early. Attempt the first test today.",
            "action": "mock_tests",
            "priority": "medium",
        })

    # Exemplar locked
    if not features.get(Feature.EXEMPLAR, {}).get("allowed", False):
        recs.append({
            "type": "exemplar",
            "title": "Unlock NCERT Exemplar practice",
            "body": "Exemplar problems are key for scoring above 90% in CBSE. Upgrade to access them.",
            "action": "upgrade",
            "priority": "low",
        })

    # Expiry warning
    if sub.get("expiry_warning"):
        days = sub.get("days_remaining", 0)
        recs.append({
            "type": "expiry",
            "title": f"Plan expires in {days} day{'s' if days != 1 else ''}",
            "body": "Renew your subscription to maintain full access without interruption.",
            "action": "upgrade",
            "priority": "high",
        })

    return recs


def _build_notifications(child_name: str, sub: dict, mock_count: int,
                          last_active: str | None, avg_score: float | None) -> list:
    """Build parent notification list from available data."""
    notes = []
    cpk = sub.get("canonical_plan_key", "FREE_TIER")

    if sub.get("expiry_warning"):
        days = sub.get("days_remaining", 0)
        notes.append({
            "type": "expiry_warning",
            "icon": "⚠️",
            "title": f"{child_name}: Plan expires in {days} day{'s' if days != 1 else ''}",
            "body": "Renew now to avoid access interruption.",
            "priority": "high",
        })

    if not last_active:
        notes.append({
            "type": "inactive",
            "icon": "😴",
            "title": f"{child_name} hasn't logged in yet",
            "body": "Encourage daily study for best results.",
            "priority": "medium",
        })

    if avg_score is not None and avg_score < 40:
        notes.append({
            "type": "low_score",
            "icon": "📉",
            "title": f"{child_name} needs attention",
            "body": f"Average mock test score is {avg_score}%. Help identify weak chapters.",
            "priority": "high",
        })

    if cpk == "FREE_TIER":
        notes.append({
            "type": "upgrade",
            "icon": "🔒",
            "title": f"{child_name} is on Free Tier",
            "body": "Upgrade to unlock Exemplar, unlimited mock tests, and full AI lessons.",
            "priority": "low",
        })

    return notes


def _verify_child_ownership(parent_profile: dict, child_id: str) -> dict | None:
    """
    Return the child profile if it's visible to this parent, else None.

    Mirrors get_parent_dashboard_summary's visibility rule: when the parent
    belongs to a family, any student in that family_id is visible (so both
    parents on a Family Premium account see the same children — a second
    parent invited via /invite-parent has parent_id=None on their own profile
    and would otherwise be locked out of every child added by the first
    parent). Falls back to a strict parent_id match only for parents with no
    family_id.
    """
    family_id = parent_profile.get("family_id")
    query = (
        admin_client.table("profiles")
        .select("id, username, grade, email, parent_id, family_id, account_status, subscription_plan, access_cbse, subscription_expires_at")
        .eq("id", child_id)
        .eq("role", "student")
    )
    if family_id:
        query = query.eq("family_id", family_id)
    else:
        query = query.eq("parent_id", parent_profile["id"])
    child, _ = _safe_one(lambda: query.limit(1).execute())
    return child


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/dashboard/summary
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/dashboard/summary")
def get_parent_dashboard_summary(parent=Depends(require_parent)):
    """
    Canonical parent dashboard summary.

    Returns:
    - parent profile
    - children[] with subscription, feature summary, activity, recommendations, notifications
    - child_limit from subscription resolver
    - upgrade_eligible flag
    """
    parent_profile = parent["profile"]
    parent_id = parent_profile["id"]

    # Resolve parent's own subscription to determine child limit.
    # child_limit from resolver:
    #   FREE_TIER  → None (no explicit limit in resolver, defaults to 1 below)
    #   NANO       → 1
    #   PREMIUM    → 1
    #   FAMILY_PREMIUM → 2
    #   ADMIN_GRANT → None (unlimited — do NOT convert to 1)
    parent_sub = resolve_user_subscription(parent_id)
    parent_cpk = parent_sub.get("canonical_plan_key", "FREE_TIER")
    raw_child_limit = parent_sub.get("child_limit")  # may be None
    if raw_child_limit is not None:
        child_limit = raw_child_limit  # explicit value from resolver (1 or 2)
    elif parent_cpk == "ADMIN_GRANT":
        child_limit = None  # unlimited — admin can add any number of children
    elif parent_cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL"):
        child_limit = 2
    else:
        child_limit = 1  # FREE_TIER, NANO, PREMIUM, expired = 1 child

    # Load children — use family_id if available (family plan: both parents see same children)
    # Fall back to parent_id for single-parent accounts
    _family_id = parent_profile.get("family_id")
    _child_filter = (
        admin_client.table("profiles")
        .select("id, username, grade, email, parent_id, family_id, account_status, subscription_plan, access_cbse, subscription_expires_at")
    )
    if _family_id:
        _child_filter = _child_filter.eq("family_id", _family_id).neq("role", "parent")
    else:
        _child_filter = _child_filter.eq("parent_id", parent_id)
    children_rows, children_err = _safe_query(lambda: _child_filter.execute())

    data_warnings = []
    if children_err:
        data_warnings.append("Some family data could not be loaded. Pull to refresh, or try again shortly.")

    # Batch-fetch activity + mock-test rows for ALL children up front (2 queries
    # total) instead of issuing 2 extra queries per child in the loop below —
    # avoids an N+1 pattern once families can have more than 1-2 children.
    child_ids = [c.get("id") for c in children_rows if c.get("id")]
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    activity_all, test_all = [], []
    if child_ids:
        activity_all, activity_err = _safe_query(
            lambda: admin_client.table("ai_usage_logs")
            .select("profile_id, username, created_at, feature")
            .in_("profile_id", child_ids)
            .gte("created_at", thirty_days_ago)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        if activity_err:
            data_warnings.append("Recent activity data could not be loaded.")

        test_all, test_err = _safe_query(
            lambda: admin_client.table("test_history")
            .select("profile_id, username, percentage, raw_score, max_score, subject, chapter, created_at")
            .in_("profile_id", child_ids)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        if test_err:
            data_warnings.append("Mock test data could not be loaded.")

    activity_by_user: dict = {}
    for r in activity_all:
        activity_by_user.setdefault(r.get("profile_id"), []).append(r)
    test_by_user: dict = {}
    for r in test_all:
        test_by_user.setdefault(r.get("profile_id"), []).append(r)

    children_summary = []
    all_notifications = []

    for child in children_rows:
        child_id = child["id"]
        child_username = child.get("username", "")

        # Canonical subscription from child's OWN profile
        child_sub = resolve_user_subscription(child_id)
        child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
        child_plan_name = child_sub.get("plan_name", "Free Tier")
        child_has_full = child_sub.get("has_full_access", False)
        child_expires = child_sub.get("valid_until")
        child_days_remaining = child_sub.get("days_remaining")
        child_expiry_warning = child_sub.get("expiring_soon", False)

        # Feature summary from canonical service
        feat_summary = get_feature_summary(child_id)
        features = feat_summary.get("features", {})
        feature_badges = _build_feature_badges(features)

        # Last active from ai_usage_logs (already batch-fetched above)
        activity_rows = activity_by_user.get(child_id, [])[:5]
        last_active = activity_rows[0]["created_at"] if activity_rows else None
        recent_activity = [{"feature": r.get("feature"), "at": r.get("created_at")} for r in activity_rows[:3]]

        # Mock test summary from test_history (already batch-fetched above)
        test_rows = test_by_user.get(child_id, [])[:10]
        mock_count = len(test_rows)
        scores = [s for s in (_normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")) for r in test_rows) if s is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Plan display
        plan_display = _plan_display(
            child_cpk, child_plan_name, child_has_full,
            child_expires, child_days_remaining
        )
        plan_display["expiry_warning"] = child_expiry_warning

        # Recommendations
        recs = _build_recommendations(
            child_username, {**child_sub, "expiry_warning": child_expiry_warning},
            features, mock_count, last_active
        )

        # Notifications
        child_notes = _build_notifications(
            child.get("username", "Child"), child_sub,
            mock_count, last_active, avg_score
        )
        all_notifications.extend(child_notes)

        children_summary.append({
            "id": child_id,
            "name": child.get("username", ""),
            "grade": child.get("grade", "—"),
            "account_status": child.get("account_status", "active"),
            "plan": plan_display,
            "subscription": child_sub,
            "features": features,
            "feature_badges": feature_badges,
            "mock_test_summary": {
                "count": mock_count,
                "average_score": avg_score,
                "recent": [
                    {"subject": r.get("subject"), "chapter": r.get("chapter"), "score": _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")), "max_score": r.get("max_score"), "at": r.get("created_at")}
                    for r in test_rows[:5]
                ],
                "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT if child_cpk == "FREE_TIER" else None,
            },
            "activity_summary": {
                "last_active": last_active,
                "recent": recent_activity,
            },
            "recommendations": recs,
            "notifications": child_notes,
        })

    # Sort notifications by priority
    prio_order = {"high": 0, "medium": 1, "low": 2}
    all_notifications.sort(key=lambda n: prio_order.get(n.get("priority", "low"), 3))

    # Parent plan display
    parent_plan = _plan_display(
        parent_cpk, parent_sub.get("plan_name", "Free Tier"),
        parent_sub.get("has_full_access", False),
        parent_sub.get("valid_until"), parent_sub.get("days_remaining"),
    )

    return {
        "success": True,
        "parent": {
            "id": parent_id,
            "username": parent_profile.get("username"),
            "email": parent_profile.get("email"),
            "family_id": parent_profile.get("family_id"),
        },
        "parent_plan": parent_plan,
        "parent_canonical_plan_key": parent_cpk,
        "child_limit": child_limit,
        "children_count": len(children_summary),
        "can_add_child": len(children_summary) < (child_limit if child_limit is not None else 999),
        "children": children_summary,
        "notifications": all_notifications,
        "data_warnings": data_warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/detail
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/children/{child_id}/detail")
def get_child_detail(child_id: str, parent=Depends(require_parent)):
    """
    Enriched child detail for the parent's child detail view.
    Includes subscription, all feature access, progress, mock tests, doubts, recommendations.
    Teacher-private notes are NEVER included.
    """
    parent_profile = parent["profile"]

    child = _verify_child_ownership(parent_profile, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    child_username = child.get("username", "")

    # Canonical subscription
    child_sub = resolve_user_subscription(child_id)
    child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
    child_expiry_warning = child_sub.get("expiring_soon", False)

    # Feature summary
    feat_summary = get_feature_summary(child_id)
    features = feat_summary.get("features", {})
    feature_badges = _build_feature_badges(features)

    # Plan display
    plan_display = _plan_display(
        child_cpk, child_sub.get("plan_name", "Free Tier"),
        child_sub.get("has_full_access", False),
        child_sub.get("valid_until"), child_sub.get("days_remaining"),
    )
    plan_display["expiry_warning"] = child_expiry_warning

    # Track real query failures separately from "no data yet" — a failed
    # _safe_query silently returns [] just like an empty table would, so we
    # collect the actual error strings here and surface them as data_warnings
    # instead of letting them look identical to a legitimately empty section.
    data_warnings = []

    # Activity
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    activity_rows, activity_err = _safe_query(
        lambda: admin_client.table("ai_usage_logs")
        .select("created_at, feature")
        .eq("profile_id", child_id)
        .gte("created_at", thirty_days_ago)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    if activity_err:
        data_warnings.append("Recent activity data could not be loaded.")
    last_active = activity_rows[0]["created_at"] if activity_rows else None
    feature_counts: dict = {}
    for r in activity_rows:
        f = r.get("feature", "other")
        feature_counts[f] = feature_counts.get(f, 0) + 1

    # Mock tests
    test_rows, test_err = _safe_query(
        lambda: admin_client.table("test_history")
        .select("percentage, raw_score, max_score, subject, chapter, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    if test_err:
        data_warnings.append("Mock test data could not be loaded.")
    mock_count = len(test_rows)
    scores = [s for s in (_normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")) for r in test_rows) if s is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Progress (chapter completions)
    progress_rows, progress_err = _safe_query(
        lambda: admin_client.table("student_progress")
        .select("subject, chapter, completed, current_step_index, updated_at")
        .eq("profile_id", child_id)
        .execute()
    )
    if progress_err:
        data_warnings.append("Progress data could not be loaded.")
    completed_chapters = [r for r in progress_rows if r.get("completed")]
    in_progress = [r for r in progress_rows if not r.get("completed") and (r.get("current_step_index") or 0) > 0]

    # Weak area alerts
    weak_rows, weak_err = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, step_title, best_score, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    if weak_err:
        data_warnings.append("Weak-area alerts could not be loaded.")

    # Recommendations
    recs = _build_recommendations(
        child_username,
        {**child_sub, "expiry_warning": child_expiry_warning},
        features, mock_count, last_active,
    )

    # Notifications
    notifications = _build_notifications(
        child.get("username", "Child"), child_sub,
        mock_count, last_active, avg_score,
    )

    return {
        "success": True,
        "child": {
            "id": child_id,
            "name": child_username,
            "grade": child.get("grade", "—"),
            "account_status": child.get("account_status", "active"),
        },
        "plan": plan_display,
        "subscription": child_sub,
        "features": features,
        "feature_badges": feature_badges,
        "progress": {
            "available": len(progress_rows) > 0,
            "completed_chapters": len(completed_chapters),
            "in_progress_chapters": len(in_progress),
            "weak_topics": [
                {"subject": r.get("subject"), "chapter": r.get("chapter"), "score": r.get("best_score")}
                for r in weak_rows
            ],
        },
        "mock_tests": {
            "available": mock_count > 0,
            "count": mock_count,
            "average_score": avg_score,
            "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT if child_cpk == "FREE_TIER" else None,
            "recent": [
                {"subject": r.get("subject"), "chapter": r.get("chapter"), "score": r.get("percentage"),
                 "total": r.get("max_score"), "at": r.get("created_at")}
                for r in test_rows[:5]
            ],
        },
        "ai_activity": {
            "available": len(activity_rows) > 0,
            "last_active": last_active,
            "feature_counts": feature_counts,
            "is_limited": child_cpk == "FREE_TIER",
        },
        "recommendations": recs,
        "notifications": notifications,
        "data_warnings": data_warnings,
    }


# ═════════════════════════════════════════════════════════════════════════════
# router_parent continued  @ /api/parent  (formerly parent_dashboard_p2.py "Phase 2")
# ═════════════════════════════════════════════════════════════════════════════

# ── Structured metric helper ──────────────────────────────────────────────────
def _metric(label: str, value, available: bool = True, explanation: str = "") -> dict:
    return {"label": label, "value": value, "available": available, "explanation": explanation}


def _unavailable(label: str, explanation: str = "Not available yet.") -> dict:
    return {"label": label, "value": None, "available": False, "explanation": explanation}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/analytics
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/children/{child_id}/analytics")
def get_child_analytics(child_id: str, parent=Depends(require_parent)):
    """
    Richer progress analytics for a parent's child.
    Parent ownership enforced. Missing data returns available=false.
    Teacher-private notes and admin audit data NEVER exposed.
    """
    child = _verify_child_ownership(parent["profile"], child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")

    # ── Mock test analytics ───────────────────────────────────────────────────
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("percentage, raw_score, max_score, subject, chapter, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    mock_count = len(test_rows)
    pct_scores = [s for s in (_normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")) for r in test_rows) if s is not None]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Subject averages
    subj_scores: dict = {}
    for r in test_rows:
        subj = r.get("subject") or "Unknown"
        pct = _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score"))
        if pct is not None:
            subj_scores.setdefault(subj, []).append(pct)
    subject_avgs = {s: round(sum(v)/len(v), 1) for s, v in subj_scores.items()}

    # Mock test trend (last 10)
    trend = []
    for i, r in enumerate(reversed(test_rows[:10])):
        pct = round(r.get("percentage") or 0, 1)
        trend.append({"index": i + 1, "subject": r.get("subject", ""), "score": pct, "at": r.get("created_at")})

    # ── Chapter progress analytics ────────────────────────────────────────────
    prog_rows, _ = _safe_query(
        lambda: admin_client.table("student_progress")
        .select("subject, chapter, completed, current_step_index, updated_at")
        .eq("profile_id", child_id)
        .execute()
    )
    completed_ch = [r for r in prog_rows if r.get("completed")]
    in_progress_ch = [r for r in prog_rows if not r.get("completed") and (r.get("current_step_index") or 0) > 0]
    not_started = len(prog_rows) - len(completed_ch) - len(in_progress_ch)

    # Subject-wise progress
    subj_progress: dict = {}
    for r in prog_rows:
        subj = r.get("subject") or "Unknown"
        entry = subj_progress.setdefault(subj, {"total": 0, "completed": 0, "in_progress": 0})
        entry["total"] += 1
        if r.get("completed"):
            entry["completed"] += 1
        elif (r.get("current_step_index") or 0) > 0:
            entry["in_progress"] += 1

    # ── Weak areas ────────────────────────────────────────────────────────────
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, step_title, best_score, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # ── AI/doubt activity (90d window to capture historical data) ─────────────
    ninety_days_ago = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    act_rows, act_err = _safe_query(
        lambda: admin_client.table("ai_usage_logs")
        .select("created_at, feature")
        .eq("profile_id", child_id)
        .gte("created_at", ninety_days_ago)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    last_active = act_rows[0]["created_at"] if act_rows else None
    feature_counts: dict = {}
    for r in act_rows:
        f = r.get("feature", "other")
        feature_counts[f] = feature_counts.get(f, 0) + 1
    lessons_count = feature_counts.get("lesson", 0)
    doubts_count = feature_counts.get("doubt", 0)

    # ── Strengths (subjects with avg score ≥ 70%) ────────────────────────────
    strong_subjects = [s for s, avg in subject_avgs.items() if avg >= 70]
    weak_subjects = [s for s, avg in subject_avgs.items() if avg < 50]

    # ── Data availability flags ───────────────────────────────────────────────
    # Distinguish: table_missing (error) vs zero_rows (no_activity) vs has_data
    mock_table_ok   = True   # test_history always exists
    prog_table_ok   = True   # student_progress always exists
    act_table_ok    = act_err is None  # ai_usage_logs exists if no error

    has_mock_data      = mock_count > 0
    has_progress_data  = len(prog_rows) > 0
    has_activity_data  = len(act_rows) > 0
    has_weak_data      = len(weak_rows) > 0

    return {
        "success": True,
        "child_id": child_id,
        "child_name": username,

        "progress": {
            "available": prog_table_ok,
            "has_data": has_progress_data,
            "status": "data" if has_progress_data else ("no_activity" if prog_table_ok else "unavailable"),
            "total_chapters_tracked": _metric("Chapters Tracked", len(prog_rows), prog_table_ok),
            "completed_chapters": _metric("Completed", len(completed_ch), prog_table_ok),
            "in_progress_chapters": _metric("In Progress", len(in_progress_ch), prog_table_ok),
            "not_started": _metric("Not Started", not_started, prog_table_ok),
            "subject_wise": subj_progress,
        },

        "mock_tests": {
            "available": mock_table_ok,
            "has_data": has_mock_data,
            "status": "data" if has_mock_data else "no_activity",
            "total_tests": _metric("Tests Taken", mock_count, mock_table_ok),
            "average_score": _metric("Average Score", f"{avg_score}%" if avg_score else None, mock_table_ok,
                                     "Based on all mock tests taken"),
            "subject_averages": subject_avgs,
            "trend": trend,
            "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT,
        },

        "strengths": {
            "available": has_mock_data and len(strong_subjects) > 0,
            "strong_subjects": strong_subjects,
            "completed_topics": [
                {"subject": r.get("subject"), "chapter": r.get("chapter")}
                for r in completed_ch[:5]
            ],
        },

        "weaknesses": {
            "available": has_weak_data or (has_mock_data and len(weak_subjects) > 0),
            "weak_subjects": weak_subjects,
            "weak_topics": [
                {
                    "subject": r.get("subject"),
                    "chapter": r.get("chapter"),
                    "score": r.get("best_score"),
                    "explanation": "Scored below average on this topic",
                }
                for r in weak_rows
            ],
        },

        "activity": {
            "available": act_table_ok,
            "has_data": has_activity_data,
            "status": "data" if has_activity_data else ("no_activity" if act_table_ok else "unavailable"),
            "last_active": last_active,
            "lessons_this_month": _metric("Lessons Generated", lessons_count, act_table_ok),
            "doubts_this_month": _metric("Doubts Asked", doubts_count, act_table_ok),
            "active_days": _metric(
                "Active Days (90d)",
                len({r["created_at"][:10] for r in act_rows if r.get("created_at")}),
                act_table_ok,
            ),
        },

        "ai_usage": {
            "available": act_table_ok,
            "has_data": has_activity_data,
            "feature_breakdown": feature_counts,
            "total_ai_requests": len(act_rows),
            "is_limited": resolve_user_subscription(child_id).get("canonical_plan_key") == "FREE_TIER",
        },

        "data_availability": {
            "progress": prog_table_ok,
            "progress_has_data": has_progress_data,
            "mock_tests": mock_table_ok,
            "mock_tests_has_data": has_mock_data,
            "activity": act_table_ok,
            "activity_has_data": has_activity_data,
            "weak_areas": has_weak_data,
            "homework": False,
            "exams": False,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/academic-insights
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/children/{child_id}/academic-insights")
def get_academic_insights(child_id: str, parent=Depends(require_parent)):
    """
    Homework and exam insights for a parent's child.
    Homework/exam tables do not exist yet — returns available=false gracefully.
    Mock test recommendations returned if data exists.
    """
    child = _verify_child_ownership(parent["profile"], child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")

    # Mock test data for recommendations
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("percentage, raw_score, max_score, subject, chapter, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    mock_count = len(test_rows)
    pct_scores = [s for s in (_normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")) for r in test_rows) if s is not None]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Weak areas for revision suggestions
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, best_score")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # Mock test recommendations
    mock_recommendations = []
    if mock_count == 0:
        mock_recommendations.append({
            "type": "start_mock_test",
            "title": "Start your first mock test",
            "description": "Mock tests help identify weak areas early. Try a chapter-wise test today.",
            "priority": "high",
        })
    elif avg_score is not None and avg_score < 50:
        mock_recommendations.append({
            "type": "improve_score",
            "title": "Focus on revision",
            "description": f"Average mock test score is {avg_score}%. Review weak topics before the next test.",
            "priority": "high",
        })
        for w in weak_rows[:3]:
            mock_recommendations.append({
                "type": "revise_topic",
                "title": f"Revise: {w.get('chapter', 'Unknown')}",
                "description": f"Subject: {w.get('subject', '')}. Practice more questions on this topic.",
                "priority": "medium",
            })
    elif avg_score is not None and avg_score >= 70:
        mock_recommendations.append({
            "type": "maintain_progress",
            "title": "Great progress — keep the streak going",
            "description": f"Average score is {avg_score}%. Maintain consistent practice to keep improving.",
            "priority": "low",
        })

    return {
        "success": True,
        "child_id": child_id,

        "homework": {
            "available": False,
            "message": "Homework tracking is not enabled yet. Homework assignments will appear here when available.",
            "upcoming": [],
            "overdue": [],
            "completed": [],
        },

        "exams": {
            "available": False,
            "message": "Exam schedule is not available yet. Upcoming exams will appear here when scheduled.",
            "upcoming": [],
        },

        "mock_test_recommendations": {
            "available": True,
            "recommendations": mock_recommendations,
            "total_tests": mock_count,
            "average_score": avg_score,
        },

        "revision_suggestions": {
            "available": len(weak_rows) > 0,
            "topics": [
                {
                    "subject": r.get("subject"),
                    "chapter": r.get("chapter"),
                    "description": "Review and practice this topic again.",
                }
                for r in weak_rows[:5]
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/progress-report
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/children/{child_id}/progress-report")
def get_progress_report(child_id: str, parent=Depends(require_parent)):
    """
    Print-friendly progress report for a parent's child.
    Excludes teacher-private notes and admin audit data entirely.
    """
    child = _verify_child_ownership(parent["profile"], child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")
    child_sub = resolve_user_subscription(child_id)
    child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
    feat_summary = get_feature_summary(child_id)
    features = feat_summary.get("features", {})

    plan = _plan_display(
        child_cpk, child_sub.get("plan_name", "Free Tier"),
        child_sub.get("has_full_access", False),
        child_sub.get("valid_until"), child_sub.get("days_remaining"),
    )

    # Progress
    prog_rows, _ = _safe_query(
        lambda: admin_client.table("student_progress")
        .select("subject, chapter, completed, current_step_index, updated_at")
        .eq("profile_id", child_id)
        .execute()
    )
    completed_ch = [r for r in prog_rows if r.get("completed")]

    # Mock tests
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("percentage, raw_score, max_score, subject, chapter, created_at")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    pct_scores = [s for s in (_normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")) for r in test_rows) if s is not None]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Weak areas
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, best_score")
        .eq("profile_id", child_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # Strengths/weaknesses from subject averages
    subj_scores: dict = {}
    for r in test_rows:
        subj = r.get("subject") or "Unknown"
        pct = _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score"))
        if pct is not None:
            subj_scores.setdefault(subj, []).append(pct)
    subject_avgs = {s: round(sum(v)/len(v), 1) for s, v in subj_scores.items()}

    # Recommendations (no teacher notes, no audit data)
    recs = _build_recommendations(
        username,
        {**child_sub, "expiry_warning": child_sub.get("expiring_soon", False)},
        features, len(test_rows), None,
    )

    return {
        "success": True,
        "report_type": "parent_progress_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "child": {
            "id": child_id,
            "name": username,
            "grade": child.get("grade", "—"),
            "board": child.get("board", "CBSE"),
        },

        "access_summary": {
            "plan": plan,
            "feature_highlights": [
                {"feature": k, "state": "full" if v.get("allowed") and not v.get("limited") else ("limited" if v.get("allowed") else "locked")}
                for k, v in features.items()
                if k in ("LESSONS", "MOCK_TEST", "EXEMPLAR", "ASK_DOUBTS")
            ],
        },

        "progress_summary": {
            "available": len(prog_rows) > 0,
            "completed_chapters": len(completed_ch),
            "total_tracked": len(prog_rows),
            "recent_completions": [
                {"subject": r.get("subject"), "chapter": r.get("chapter")}
                for r in completed_ch[:5]
            ],
        },

        "mock_test_summary": {
            "available": len(test_rows) > 0,
            "tests_taken": len(test_rows),
            "average_score": avg_score,
            "subject_averages": subject_avgs,
            "recent_tests": [
                {
                    "subject": r.get("subject"),
                    "score": _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score")),
                    "date": (r.get("created_at") or "")[:10],
                }
                for r in test_rows[:5]
            ],
        },

        "strengths": [s for s, avg in subject_avgs.items() if avg >= 70],
        "areas_for_improvement": [
            {"subject": r.get("subject"), "chapter": r.get("chapter")}
            for r in weak_rows
        ],

        "recommendations": recs[:5],

        "disclaimer": "Teacher-private notes and internal audit data are not included in this report.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Notification helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_rule_based_notifications(parent_id: str, children_rows: list) -> list:
    """
    Generate rule-based notifications when parent_notifications table is empty/unavailable.
    Never exposes secrets, raw audit data, or teacher-private notes.
    """
    notifs = []
    now_iso = datetime.now(timezone.utc).isoformat()
    fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    for child in children_rows:
        child_id = child.get("id")
        child_name = child.get("username", "Child")
        username = child.get("username", "")

        # Resolve child subscription
        sub = resolve_user_subscription(child_id)
        cpk = sub.get("canonical_plan_key", "FREE_TIER")

        # Plan expiring soon
        if sub.get("expiring_soon") and sub.get("days_remaining") is not None:
            days = sub["days_remaining"]
            notifs.append({
                "id": f"rule-expiry-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "plan_expiring",
                "title": f"{child_name}: Plan expires in {days} day{'s' if days != 1 else ''}",
                "message": "Renew your subscription to maintain full access without interruption.",
                "severity": "warning",
                "status": "unread",
                "created_at": now_iso,
                "action": "upgrade",
            })

        # Free Tier restriction
        if cpk == "FREE_TIER":
            notifs.append({
                "id": f"rule-free-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "feature_locked",
                "title": f"{child_name} is on Free Tier",
                "message": "Exemplar lessons, unlimited mock tests, and full AI access are locked. Upgrade for full CBSE coverage.",
                "severity": "info",
                "status": "unread",
                "created_at": now_iso,
                "action": "upgrade",
            })

        # Inactivity check
        act_rows, _ = _safe_query(
            lambda: admin_client.table("ai_usage_logs")
            .select("created_at")
            .eq("profile_id", child_id)
            .gte("created_at", fourteen_days_ago)
            .limit(1)
            .execute()
        )
        if len(act_rows) == 0:
            notifs.append({
                "id": f"rule-inactive-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "child_inactive",
                "title": f"{child_name} hasn't logged in recently",
                "message": "No activity recorded in the last 14 days. Encourage a 15-minute revision session.",
                "severity": "warning",
                "status": "unread",
                "created_at": now_iso,
                "action": "view_child",
            })

        # Low mock score
        test_rows, _ = _safe_query(
            lambda: admin_client.table("test_history")
            .select("percentage")
            .eq("profile_id", child_id)
            .limit(10)
            .execute()
        )
        pct_scores = [
            (r.get("percentage") or 0)
            for r in test_rows if r.get("percentage") is not None
        ]
        if pct_scores:
            avg = sum(pct_scores) / len(pct_scores)
            if avg < 40:
                notifs.append({
                    "id": f"rule-lowscore-{child_id}",
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "child_name": child_name,
                    "type": "low_mock_score",
                    "title": f"{child_name} needs help with mock tests",
                    "message": f"Average mock test score is {round(avg, 1)}%. Review weak topics together.",
                    "severity": "warning",
                    "status": "unread",
                    "created_at": now_iso,
                    "action": "view_analytics",
                })
            elif avg >= 70:
                notifs.append({
                    "id": f"rule-goodscore-{child_id}",
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "child_name": child_name,
                    "type": "strong_improvement",
                    "title": f"Great progress — {child_name}!",
                    "message": f"Average mock test score is {round(avg, 1)}%. Keep the momentum going!",
                    "severity": "success",
                    "status": "unread",
                    "created_at": now_iso,
                    "action": "view_analytics",
                })

    return notifs


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/notifications
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.get("/notifications")
def get_notifications(
    status: str = "all",
    notif_type: str = "all",
    limit: int = 50,
    offset: int = 0,
    parent=Depends(require_parent),
):
    """
    Parent notification center.
    Tries persistent table first; falls back to rule-based generation.
    Parent can only access own notifications.
    """
    parent_id = parent["profile"]["id"]
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Existence check (unfiltered) — lets us tell "this parent has no persisted
    # notifications yet / table unavailable" (→ rule-based fallback) apart from
    # "the requested filter legitimately matched zero rows" (→ honest empty list).
    existence_rows, existence_err = _safe_query(
        lambda: admin_client.table("parent_notifications")
        .select("id")
        .eq("parent_id", parent_id)
        .limit(1)
        .execute()
    )

    if existence_err or len(existence_rows) == 0:
        # Table doesn't exist or no persisted notifications — generate rule-based
        children_rows, _ = _safe_query(
            lambda: admin_client.table("profiles")
            .select("id, username, grade")
            .eq("parent_id", parent_id)
            .execute()
        )
        all_notifs = _generate_rule_based_notifications(parent_id, children_rows)

        # Apply filters
        if status != "all":
            all_notifs = [n for n in all_notifs if n.get("status") == status]
        if notif_type != "all":
            all_notifs = [n for n in all_notifs if n.get("type") == notif_type]

        unread_count = sum(1 for n in all_notifs if n.get("status") == "unread")
        total = len(all_notifs)
        page = all_notifs[offset:offset + limit]
        return {
            "success": True,
            "source": "rule_based",
            "unread_count": unread_count,
            "total": total,
            "limit": limit,
            "offset": offset,
            "notifications": page,
        }

    # Parent has persisted notifications — apply the real (possibly filtered,
    # possibly empty) query and return honest results, not a rule-based fallback.
    query = (
        admin_client.table("parent_notifications")
        .select("*")
        .eq("parent_id", parent_id)
        .order("created_at", desc=True)
    )
    if status != "all":
        query = query.eq("status", status)
    if notif_type != "all":
        query = query.eq("type", notif_type)
    query = query.range(offset, offset + limit - 1)

    db_notifs, db_err = _safe_query(lambda: query.execute())
    if db_err:
        raise HTTPException(status_code=503, detail="Could not load notifications right now. Please try again.")

    # Total count matching the same filters (for pagination), and unread count
    # across ALL of this parent's notifications (not just this page/filter).
    count_query = (
        admin_client.table("parent_notifications")
        .select("id")
        .eq("parent_id", parent_id)
    )
    if status != "all":
        count_query = count_query.eq("status", status)
    if notif_type != "all":
        count_query = count_query.eq("type", notif_type)
    count_rows, _ = _safe_query(lambda: count_query.execute())
    total = len(count_rows)

    unread_rows, _ = _safe_query(
        lambda: admin_client.table("parent_notifications")
        .select("id")
        .eq("parent_id", parent_id)
        .eq("status", "unread")
        .execute()
    )
    unread_count = len(unread_rows)

    # Sanitize: strip raw metadata keys that could contain secrets
    safe_notifs = []
    for n in db_notifs:
        safe_meta = {k: v for k, v in (n.get("metadata") or {}).items()
                     if k not in ("token", "secret", "key", "password", "audit_detail")}
        safe_notifs.append({**n, "metadata": safe_meta})

    return {
        "success": True,
        "source": "database",
        "unread_count": unread_count,
        "total": total,
        "limit": limit,
        "offset": offset,
        "notifications": safe_notifs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/parent/notifications/{notification_id}/read
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, parent=Depends(require_parent)):
    """Mark a single notification as read. Parent can only update own notifications."""
    parent_id = parent["profile"]["id"]

    # Verify ownership before updating
    existing, err = _safe_one(
        lambda: admin_client.table("parent_notifications")
        .select("id, parent_id")
        .eq("id", notification_id)
        .eq("parent_id", parent_id)
        .limit(1)
        .execute()
    )
    if err or not existing:
        # Rule-based notification IDs start with "rule-" — they're stateless
        # Just acknowledge without DB write
        return {"success": True, "id": notification_id, "status": "read", "note": "Stateless notification acknowledged."}

    try:
        admin_client.table("parent_notifications").update({
            "status": "read",
            "read_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", notification_id).eq("parent_id", parent_id).execute()
    except Exception as exc:
        _log.warning("mark_notification_read failed: %s", exc)
        return {"success": False, "error": "Could not update notification."}

    return {"success": True, "id": notification_id, "status": "read"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/parent/notifications/read-all
# ─────────────────────────────────────────────────────────────────────────────

@router_parent.post("/notifications/read-all")
def mark_all_notifications_read(parent=Depends(require_parent)):
    """Mark all notifications for this parent as read. Only affects own notifications."""
    parent_id = parent["profile"]["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    rows, err = _safe_query(
        lambda: admin_client.table("parent_notifications")
        .select("id")
        .eq("parent_id", parent_id)
        .eq("status", "unread")
        .execute()
    )

    if err:
        # Table unavailable — rule-based notifications are stateless, nothing to update
        return {"success": True, "updated": 0, "note": "Stateless notifications acknowledged."}

    if not rows:
        return {"success": True, "updated": 0}

    try:
        admin_client.table("parent_notifications").update({
            "status": "read",
            "read_at": now_iso,
        }).eq("parent_id", parent_id).eq("status", "unread").execute()
    except Exception as exc:
        _log.warning("mark_all_notifications_read failed: %s", exc)
        return {"success": False, "error": "Could not update notifications."}

    return {"success": True, "updated": len(rows)}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/digest/unsubscribe
# ─────────────────────────────────────────────────────────────────────────────

_UNSUBSCRIBE_HTML = """<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
text-align:center;padding:60px 20px;color:#1e293b">
<h2>You're unsubscribed</h2>
<p style="color:#64748b">You will no longer receive the weekly progress digest email.
You can still see your child's progress any time by signing in to your dashboard.</p>
</body></html>"""


@router_parent.get("/digest/unsubscribe", response_class=HTMLResponse)
def unsubscribe_email_digest(parent_id: str):
    """
    Unauthenticated by design — this is a one-click link opened from an email,
    where the parent may not have an active session. The parent's UUID doubles
    as the token (unguessable, and misuse only toggles a notification
    preference — not a data exposure). Always returns the same confirmation
    regardless of whether parent_id matched a row, so the response itself
    can't be used to probe which ids exist.
    """
    try:
        admin_client.table("profiles").update(
            {"email_digest_opt_out": True}
        ).eq("id", parent_id).eq("role", "parent").execute()
        write_audit_event(event_type="parent.email_digest_opt_out", target_user_id=parent_id)
    except Exception as exc:
        _log.warning("digest_unsubscribe_failed parent_id=%s error=%s", parent_id, exc)

    return _UNSUBSCRIBE_HTML
