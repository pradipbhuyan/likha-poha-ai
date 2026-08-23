"""
weekly_digest_service.py
─────────────────────────────────────────────────────────────────────────────
Weekly parent email digest: summarizes each linked child's last 7 days
(mock tests, weak areas, AI activity, plan status) and emails every opted-in
parent who has at least one linked child.

Design:
  - Reuses canonical helpers — never re-derives plan display, score
    normalization, or subscription resolution logic.
  - Batch-fetches activity/test/weak-area data for ALL children in one run
    (same pattern as get_parent_dashboard_summary) — no N+1 across parents.
  - Sends synchronously (blocking=True) — this job's process exits right
    after run_weekly_digest_job() returns, so email_service's normal
    fire-and-forget daemon thread would be killed before it could send.
  - Never raises — logs and counts errors, returns a summary dict.

Can be triggered:
  - via a cron/scheduler (GitHub Actions weekly-parent-digest.yml)
  - via CLI: python -m app.services.weekly_digest_service
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.auth_service import admin_client
from app.services.audit_log_service import write_audit_event
from app.services.subscription_resolver_service import resolve_user_subscription
from app.services.email_service import send_weekly_digest_email
from app.routes.parent_dashboard import _normalize_score_pct, _plan_display

logger = logging.getLogger(__name__)

_BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")


def _unsubscribe_url(parent_id: str) -> str:
    base = _BACKEND_URL or "https://api.likhapoha.in"
    return f"{base}/api/parent/digest/unsubscribe?parent_id={parent_id}"


def _child_week_stats(
    child: dict,
    test_rows: list[dict],
    activity_rows: list[dict],
    weak_rows: list[dict],
) -> dict[str, Any]:
    """Pure helper: compute one child's weekly digest block from pre-fetched rows."""
    scores = [
        s for s in (
            _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score"))
            for r in test_rows
        ) if s is not None
    ]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    weak_areas = [
        f"{r.get('subject','')} — {r.get('chapter','')}".strip(" —")
        for r in weak_rows[:3] if r.get("subject") or r.get("chapter")
    ]
    if not weak_areas:
        # Fallback: subjects averaging below 50% this week from test_history itself
        subj_scores: dict = {}
        for r in test_rows:
            subj = r.get("subject") or "Unknown"
            pct = _normalize_score_pct(r.get("percentage"), r.get("raw_score"), r.get("max_score"))
            if pct is not None:
                subj_scores.setdefault(subj, []).append(pct)
        weak_areas = [
            subj for subj, vals in subj_scores.items()
            if (sum(vals) / len(vals)) < 50
        ][:3]

    child_sub = resolve_user_subscription(child["id"])
    plan = _plan_display(
        child_sub.get("canonical_plan_key", "FREE_TIER"),
        child_sub.get("plan_name", "Free Tier"),
        child_sub.get("has_full_access", False),
        child_sub.get("valid_until"),
        child_sub.get("days_remaining"),
    )

    return {
        "name": child.get("username", "Child"),
        "grade": child.get("grade", ""),
        "mock_tests_count": len(test_rows),
        "avg_score": avg_score,
        "weak_areas": weak_areas,
        "activity_count": len(activity_rows),
        "plan_name": plan["plan_name"],
        "plan_status_label": plan["status_label"],
        "has_full_access": plan["has_full_access"],
    }


def _group_by_profile_id(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        profile_id = r.get("profile_id")
        if profile_id:
            grouped.setdefault(profile_id, []).append(r)
    return grouped


def run_weekly_digest_job() -> dict[str, Any]:
    """
    Email every opted-in parent with ≥1 linked child a weekly progress digest.

    Returns a summary dict with counts of parents processed / emails sent /
    skipped / failed.
    """
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    result: dict[str, Any] = {
        "ran_at": now.isoformat(),
        "parents_processed": 0,
        "emails_sent": 0,
        "emails_failed": 0,
        "parents_skipped_no_children": 0,
        "parents_skipped_opted_out_or_no_email": 0,
        "errors": 0,
    }

    try:
        children_resp = (
            admin_client.table("profiles")
            .select("id, username, grade, parent_id, family_id")
            .eq("role", "student")
            .execute()
        )
        parents_resp = (
            admin_client.table("profiles")
            .select("id, email, username, family_id")
            .eq("role", "parent")
            .eq("account_status", "active")
            .eq("email_digest_opt_out", False)
            .execute()
        )
    except Exception as exc:
        logger.error("weekly_digest.query_failed error=%s", exc)
        result["errors"] += 1
        return result

    children = children_resp.data or []
    parents = [p for p in (parents_resp.data or []) if p.get("email")]

    children_by_family: dict[str, list[dict]] = {}
    children_by_parent: dict[str, list[dict]] = {}
    for c in children:
        if c.get("family_id"):
            children_by_family.setdefault(c["family_id"], []).append(c)
        if c.get("parent_id"):
            children_by_parent.setdefault(c["parent_id"], []).append(c)

    child_ids = [c["id"] for c in children if c.get("id")]

    test_all: list[dict] = []
    activity_all: list[dict] = []
    weak_all: list[dict] = []
    if child_ids:
        try:
            test_all = (
                admin_client.table("test_history")
                .select("profile_id, username, percentage, raw_score, max_score, subject, chapter, created_at")
                .in_("profile_id", child_ids)
                .gte("created_at", week_ago)
                .execute()
            ).data or []
            activity_all = (
                admin_client.table("ai_usage_logs")
                .select("profile_id, username, created_at, feature")
                .in_("profile_id", child_ids)
                .gte("created_at", week_ago)
                .execute()
            ).data or []
            weak_all = (
                admin_client.table("weak_area_alerts")
                .select("profile_id, username, subject, chapter, best_score, created_at")
                .in_("profile_id", child_ids)
                .gte("created_at", week_ago)
                .execute()
            ).data or []
        except Exception as exc:
            logger.warning("weekly_digest.activity_query_failed error=%s", exc)

    test_by_user = _group_by_profile_id(test_all)
    activity_by_user = _group_by_profile_id(activity_all)
    weak_by_user = _group_by_profile_id(weak_all)

    for parent in parents:
        result["parents_processed"] += 1
        parent_id = parent["id"]

        family_id = parent.get("family_id")
        own_children = (
            children_by_family.get(family_id, []) if family_id
            else children_by_parent.get(parent_id, [])
        )
        if not own_children:
            result["parents_skipped_no_children"] += 1
            continue

        try:
            digest_children = [
                _child_week_stats(
                    child,
                    test_by_user.get(child["id"], []),
                    activity_by_user.get(child["id"], []),
                    weak_by_user.get(child["id"], []),
                )
                for child in own_children
            ]

            sent = send_weekly_digest_email(
                to=parent["email"],
                parent_name=parent.get("username", "there"),
                children=digest_children,
                unsubscribe_url=_unsubscribe_url(parent_id),
                blocking=True,
            )
            if sent:
                result["emails_sent"] += 1
            else:
                result["emails_failed"] += 1

        except Exception as exc:
            result["errors"] += 1
            logger.error("weekly_digest.parent_error parent=%s error=%s", parent_id, exc)

    write_audit_event(event_type="weekly_digest.ran", metadata={**result})
    logger.info(
        "weekly_digest.completed processed=%d sent=%d failed=%d errors=%d",
        result["parents_processed"], result["emails_sent"],
        result["emails_failed"], result["errors"],
    )
    return result


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    summary = run_weekly_digest_job()
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["errors"] == 0 and summary["emails_failed"] == 0 else 1)
