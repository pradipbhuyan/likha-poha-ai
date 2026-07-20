"""
subscription_settings_service.py
─────────────────────────────────────────────────────────────────────────────
Subscription plan and contact settings — DB-driven with built-in defaults as
fallback, loaded/normalized here so admin and parent-facing pages stay aligned.

Extracted from app/routes/admin_control.py, where it originally lived as
route-file-local logic despite being imported by 5 other files (auth.py,
parent_dashboard.py, payments.py, exam_prep_packs.py,
feature_authorization_service.py) — moved to a service module so those
callers depend on a service, not on another route file's internals.
"""
from __future__ import annotations

import json as _json

from pydantic import BaseModel

from app.data.subscription_plans import (
    get_default_subscription_plans,
    subscription_plan_order,
)
from app.services.auth_service import admin_client


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
    daily_token_limit: int = 0
    monthly_token_limit: int = 0
    included: list[str] = []
    not_included: list[str] = []
    comparison: dict = {}
    # ── Centralized feature flags (DB-driven) ────────────────────────────────
    duration_days: int | None = None    # exact expiry days (overrides billing_label lookup)
    access_exam_prep: bool = True       # include Exam Prep Center (JEE/NEET/CUET)
    access_exemplar: bool = True        # include Exemplar Research & Lessons


class SubscriptionContactSettings(BaseModel):
    email: str = "likhapohaai@gmail.com"
    phone: str = ""
    whatsapp: str = ""
    availability: str = "We usually respond within one business day."
    message: str = (
        "Need help choosing a plan or activating access? Contact us and we will guide you."
    )


DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS = {
    "email": "likhapohaai@gmail.com",
    "phone": "",
    "whatsapp": "",
    "availability": "We usually respond within one business day.",
    "message": (
        "Need help choosing a plan or activating access? Contact us and we will guide you."
    ),
}


def _to_list(value) -> list:
    """
    Safely coerce a DB value to a Python list.
    Handles: list, JSON-encoded string '["a","b"]', None/empty.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                parsed = _json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except Exception:
                pass
        # Fallback: newline-separated
        return [line.strip() for line in stripped.splitlines() if line.strip()]
    return []


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
        "daily_token_limit": int(row.get("daily_token_limit") or 0),
        "monthly_token_limit": int(row.get("monthly_token_limit") or 0),
        "included": _to_list(row.get("included")),
        "not_included": _to_list(row.get("not_included")),
        "comparison": row.get("comparison") or {},
        # ── Centralized feature flags (DB-driven) ────────────────────────────
        # duration_days: explicit expiry days — overrides billing_label→days lookup in payments.py
        "duration_days": int(row["duration_days"]) if row.get("duration_days") is not None else None,
        # access_exam_prep: whether this plan includes the Exam Prep Center (JEE/NEET/CUET)
        "access_exam_prep": bool(row.get("access_exam_prep", True)),  # default True for paid plans
        # access_exemplar: whether this plan includes Exemplar Research & Lessons
        "access_exemplar": bool(row.get("access_exemplar", True)),    # default True for paid plans
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
