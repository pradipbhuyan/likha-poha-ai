"""
admin_platform_settings.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Lesson card style, platform logging configuration, and the Grade 11/12
egress/capacity health monitor.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client

router = APIRouter()


# ── Logging settings ──────────────────────────────────────────────────────────

def _load_logging_settings() -> dict:
    """Load logging_settings from admin_settings table. Returns defaults if absent."""
    try:
        row = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", "logging_settings")
            .limit(1)
            .execute()
        )
        if row.data:
            return row.data[0]["value"] or {}
    except Exception:
        pass
    return {}


# ── Lesson Card Style Settings ────────────────────────────────────────────────

LESSON_CARD_DEFAULTS = {
    "card_style": "default",   # "default" | "A" | "B" | "C"
    "card_theme": "brand",     # "brand" | "forest"
}


def _load_lesson_card_settings() -> dict:
    """Read lesson_card_settings from admin_settings. Returns defaults if absent."""
    try:
        row = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", "lesson_card_settings")
            .limit(1)
            .execute()
        )
        if row.data:
            return {**LESSON_CARD_DEFAULTS, **(row.data[0]["value"] or {})}
    except Exception:
        pass
    return dict(LESSON_CARD_DEFAULTS)


@router.get("/lesson-card-settings")
def get_lesson_card_settings(admin=Depends(require_admin)):
    """Return current lesson section card style and colour theme."""
    return {"success": True, **_load_lesson_card_settings()}


class LessonCardSettingsRequest(BaseModel):
    card_style: str = "default"   # "default" | "A" | "B" | "C"
    card_theme: str = "brand"     # "brand" | "forest"


@router.put("/lesson-card-settings")
def update_lesson_card_settings(
    data: LessonCardSettingsRequest,
    admin=Depends(require_admin),
):
    """Persist the active lesson section card style and colour theme."""
    valid_styles = {"default", "A", "B", "C"}
    valid_themes = {"brand", "forest"}
    card_style = data.card_style if data.card_style in valid_styles else "default"
    card_theme = data.card_theme if data.card_theme in valid_themes else "brand"

    value = {"card_style": card_style, "card_theme": card_theme}

    try:
        admin_client.table("admin_settings").upsert(
            {"key": "lesson_card_settings", "value": value, "updated_at": "now()"},
            on_conflict="key",
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save lesson card settings. Make sure "
                "backend/sql/add_admin_settings.sql has been run. "
                f"Original error: {str(exc)}"
            ),
        )

    return {"success": True, **value, "message": "Lesson card settings saved."}


@router.get("/logging-settings")
def get_logging_settings(admin=Depends(require_admin)):
    """Return current logging configuration."""
    settings = _load_logging_settings()
    return {
        "success": True,
        "logging_enabled": settings.get("logging_enabled", True),
        "log_level": settings.get("log_level", "INFO"),
    }


class LoggingSettingsRequest(BaseModel):
    logging_enabled: bool
    log_level: str = "INFO"   # DEBUG | INFO | WARN | ERROR


@router.post("/logging-settings")
def update_logging_settings(data: LoggingSettingsRequest, admin=Depends(require_admin)):
    """Enable or disable platform logging and set the log level."""
    import logging as _logging  # noqa: PLC0415
    from app.services.logger_service import _root  # noqa: PLC0415

    valid_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
    log_level = data.log_level.upper()
    if log_level not in valid_levels:
        log_level = "INFO"

    # Persist to DB
    admin_client.table("admin_settings").upsert(
        {
            "key": "logging_settings",
            "value": {
                "logging_enabled": data.logging_enabled,
                "log_level": log_level,
            },
        },
        on_conflict="key",
    ).execute()

    # Apply immediately to the running process
    if data.logging_enabled:
        _root.setLevel(getattr(_logging, log_level, _logging.INFO))
        _root.disabled = False
    else:
        _root.disabled = True

    admin_profile = admin.get("profile", {})
    return {
        "success": True,
        "logging_enabled": data.logging_enabled,
        "log_level": log_level,
        "message": f"Logging {'enabled' if data.logging_enabled else 'disabled'} at {log_level} level.",
        "changed_by": admin_profile.get("username", "admin"),
    }


# ── Supabase Egress Health Monitor ──────────────────────────────────────────
# Estimates Supabase DB egress from ai_usage_logs.
# Each RAG-triggering call generates ~762 KB egress (N+1 query pattern).
# Non-RAG calls generate ~5 KB.
# Thresholds (Supabase Free = 5 GB/month):
#   GREEN:  < 2 GB estimated  → safe
#   YELLOW: 2–4 GB estimated  → approaching limit
#   RED:    > 4 GB estimated  → action required

_RAG_FEATURES = {
    "lkb_build", "doubt_kb_prewarm", "question_bank_build",
    "lesson", "doubt", "lesson_followup",
    "prewarm_questions", "answer_evaluation",
}
_EGRESS_PER_RAG_CALL_KB = 762  # 1 RPC (42KB) + 60 N+1 rag_documents queries (720KB)
_EGRESS_PER_SMALL_CALL_KB = 5   # auth, non-RAG responses
_SUPABASE_FREE_LIMIT_GB = 5.0

# ── Grade 11/12 second-project capacity snapshot ────────────────────────────
# ai_usage_logs above lives only on the primary project and isn't tagged with
# grade, so it can't be split to estimate the Grade 11/12 project's egress.
# Supabase free-tier limits are row/storage-based as much as egress-based, so
# a direct row-count snapshot of the second project's content tables is a more
# useful early-warning signal than trying to force the egress estimate to
# cover it. See docs/product-specs/07_ARCHITECTURE_ASSESSMENT.md §3.3 — this
# whole second project exists to stay on Supabase free tier until there are
# paying subscribers, so knowing when it's approaching that cap matters.
_GRADE_1112_CONTENT_TABLES = ["rag_documents", "lesson_cache", "doubt_kb", "question_bank"]


def _grade_1112_capacity_snapshot() -> dict:
    """Row-count snapshot for the Grade 11/12 Supabase project's content tables."""
    from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415

    if grade_1112_client is None:
        return {
            "configured": False,
            "note": (
                "SUPABASE_GRADE_1112_URL / SUPABASE_GRADE_1112_SERVICE_KEY not set — "
                "Grade 11/12 project capacity cannot be checked."
            ),
        }

    table_row_counts: dict[str, int | None] = {}
    errors: dict[str, str] = {}
    for table in _GRADE_1112_CONTENT_TABLES:
        try:
            r = grade_1112_client.table(table).select("id", count="exact").limit(1).execute()
            table_row_counts[table] = r.count or 0
        except Exception as exc:
            table_row_counts[table] = None
            errors[table] = str(exc)[:150]

    return {
        "configured": True,
        "table_row_counts": table_row_counts,
        "errors": errors,
    }


@router.get("/egress-health")
def get_egress_health(admin=Depends(require_admin)):
    """
    Estimate Supabase DB egress from ai_usage_logs for the last 30 days.
    Returns a traffic-light status (green/yellow/red) and per-feature breakdown.
    """
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    try:
        resp = admin_client.table("ai_usage_logs") \
            .select("feature, created_at") \
            .gte("created_at", cutoff) \
            .execute()
        logs = resp.data or []
    except Exception:
        return {"status": "unknown", "error": "Could not fetch usage logs"}

    # Count calls per feature
    feature_counts: dict[str, int] = {}
    for log in logs:
        feat = log.get("feature", "unknown")
        feature_counts[feat] = feature_counts.get(feat, 0) + 1

    # Estimate egress
    total_kb = 0.0
    breakdown = []
    for feat, count in sorted(feature_counts.items(), key=lambda x: -x[1]):
        kb_per_call = _EGRESS_PER_RAG_CALL_KB if feat in _RAG_FEATURES else _EGRESS_PER_SMALL_CALL_KB
        feat_kb = count * kb_per_call
        total_kb += feat_kb
        breakdown.append({
            "feature": feat,
            "calls": count,
            "estimated_mb": round(feat_kb / 1024, 1),
        })

    total_gb = round(total_kb / 1024 / 1024, 2)
    pct = round(total_gb / _SUPABASE_FREE_LIMIT_GB * 100, 1)

    if total_gb < 2.0:
        status = "green"
        message = f"Estimated egress {total_gb} GB — well within free tier ({pct}% of 5 GB)"
    elif total_gb < 4.0:
        status = "yellow"
        message = f"Estimated egress {total_gb} GB — approaching limit ({pct}% of 5 GB). Reduce prewarm operations."
    else:
        status = "red"
        message = f"Estimated egress {total_gb} GB — OVER/NEAR limit ({pct}% of 5 GB). Apply N+1 fix urgently."

    return {
        "status": status,
        "message": message,
        "estimated_gb": total_gb,
        "pct_of_free_limit": pct,
        "free_limit_gb": _SUPABASE_FREE_LIMIT_GB,
        "top_features": breakdown[:8],
        "total_calls_30d": len(logs),
        "note": "Estimate uses N+1 formula (762KB/RAG call). After applying the N+1 fix, multiply by 0.06 for actual post-fix egress.",
        "grade_1112_capacity": _grade_1112_capacity_snapshot(),
    }
