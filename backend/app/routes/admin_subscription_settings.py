"""
admin_subscription_settings.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Admin-editable subscription plan pricing/features and support contact details.

Extracted from app/routes/admin_control.py. The underlying data-loading logic
lives in app/services/subscription_settings_service.py (shared by 5 other
files), this module only owns the HTTP routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client
from app.services.subscription_settings_service import (
    DEFAULT_SUBSCRIPTION_CONTACT_SETTINGS,
    SubscriptionContactSettings,
    SubscriptionPlanSettings,
    list_subscription_contact_settings,
    list_subscription_plan_settings,
)

router = APIRouter()


class UpdateSubscriptionPlanSettingsRequest(BaseModel):
    plans: list[SubscriptionPlanSettings]


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

    # New fields added in migration 20260708_subscription_plan_feature_flags.sql.
    # If the migration hasn't been run yet, strip new columns and retry gracefully.
    NEW_FEATURE_COLUMNS = {"duration_days", "access_exam_prep", "access_exemplar"}

    def _try_upsert(row_list: list, strip_new_cols: bool = False):
        if strip_new_cols:
            row_list = [{k: v for k, v in r.items() if k not in NEW_FEATURE_COLUMNS} for r in row_list]
        return (
            admin_client
            .table("subscription_plan_settings")
            .upsert(row_list, on_conflict="key")
            .execute()
        )

    try:
        _try_upsert(rows, strip_new_cols=False)
    except Exception as exc:
        err_str = str(exc).lower()
        # If error is about missing column, retry without the new columns
        if any(col in err_str for col in ("duration_days", "access_exam_prep", "access_exemplar", "column")):
            try:
                _try_upsert(rows, strip_new_cols=True)
            except Exception as exc2:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Unable to save subscription plan settings. Make sure the "
                        "subscription_plan_settings table exists. "
                        f"Original error: {str(exc2)}"
                    ),
                )
        else:
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
