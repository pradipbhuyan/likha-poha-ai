"""
school_service.py
─────────────────────────────────────────────────────────────────────────────
Shared helpers for the principal portal: school-code generation and the
paid-student incentive tier ladder.

Deliberately has NO dependency on payments.py or the subscription resolver —
tier is computed by counting already-linked students who are not on the Free
Tier (via offer_access_service.is_free_tier_user), read-only, on demand. This
keeps the whole feature additive: nothing here hooks into the payment webhook
path that every other paid feature depends on.
"""
from __future__ import annotations

import random
import string

from app.services.auth_service import admin_client

_CODE_ALPHABET = string.ascii_uppercase + string.digits


# ── Tier ladder ──────────────────────────────────────────────────────────────
# Ordered lowest → highest. Rewards are institutional (school-facing), not a
# personal payout — see docs discussion: a principal earning cash per paid
# student is a real conflict-of-interest / inducement risk in a school
# setting, so every reward below benefits the school as a whole.
SCHOOL_TIERS = ["bronze", "silver", "gold", "platinum"]

SCHOOL_TIER_THRESHOLDS = {
    "bronze": 0,
    "silver": 100,
    "gold": 300,
    "platinum": 600,
}

SCHOOL_REWARD_CATALOG = {
    "bronze": [
        {
            "key": "bronze_support",
            "label": "Standard support line",
            "description": "Email support with a 2-business-day response time.",
        },
    ],
    "silver": [
        {
            "key": "silver_teacher_seats",
            "label": "2 redeemable Premium codes for teachers / month",
            "description": (
                "Send any 2 teachers a redeemable code — nothing changes on "
                "their account until they redeem it themselves."
            ),
        },
        {
            "key": "silver_priority_support",
            "label": "Priority support line",
            "description": "Direct WhatsApp line to the LikhaPohai school success team.",
        },
        {
            "key": "silver_monthly_report",
            "label": "Monthly school performance report",
            "description": "Auto-generated PDF — grade-wise scores vs. CBSE board average.",
        },
    ],
    "gold": [
        {
            "key": "gold_workbooks",
            "label": "Printed workbook sets, Grades 10-12",
            "description": "Physical CBSE workbook sets shipped to school, at no charge.",
        },
        {
            "key": "gold_badge",
            "label": '"Top School" digital badge',
            "description": "For your website, prospectus, and admission material.",
        },
    ],
    "platinum": [
        {
            "key": "platinum_dev_grant",
            "label": "Annual school development grant",
            "description": "Credit toward library, lab, or digital classroom upgrades.",
        },
        {
            "key": "platinum_leaderboard",
            "label": "Statewide leaderboard spotlight",
            "description": "Featured placement on the LikhaPohai Top Schools page.",
        },
    ],
}


def compute_school_tier(paid_student_count: int) -> str:
    """Return the highest tier this school qualifies for by paid-student count."""
    current = SCHOOL_TIERS[0]
    for tier in SCHOOL_TIERS:
        if paid_student_count >= SCHOOL_TIER_THRESHOLDS[tier]:
            current = tier
    return current


def next_tier_progress(paid_student_count: int) -> dict | None:
    """
    Return progress toward the next tier, or None if already at the top tier.

    Shape: {"tier": "gold", "threshold": 300, "remaining": 12}
    """
    current = compute_school_tier(paid_student_count)
    idx = SCHOOL_TIERS.index(current)
    if idx == len(SCHOOL_TIERS) - 1:
        return None

    next_tier = SCHOOL_TIERS[idx + 1]
    threshold = SCHOOL_TIER_THRESHOLDS[next_tier]
    return {
        "tier": next_tier,
        "threshold": threshold,
        "remaining": max(0, threshold - paid_student_count),
    }


def rewards_unlocked_through(tier: str) -> list[dict]:
    """Flatten the catalog for every tier up to and including `tier`."""
    idx = SCHOOL_TIERS.index(tier) if tier in SCHOOL_TIERS else 0
    unlocked = []
    for t in SCHOOL_TIERS[: idx + 1]:
        unlocked.extend(SCHOOL_REWARD_CATALOG.get(t, []))
    return unlocked


# ── School code generation ──────────────────────────────────────────────────
def _random_suffix(length: int = 5) -> str:
    return "".join(random.choices(_CODE_ALPHABET, k=length))


def generate_unique_school_code(name: str, client=None) -> str:
    """
    Generate a short, human-shareable join code like "SPS-7F3K2".

    Retries on collision (checked against the schools table) — vanishingly
    unlikely to matter in practice, but cheap to guard against.
    """
    db = client or admin_client
    letters = "".join(ch for ch in (name or "").upper() if ch.isalpha())
    prefix = (letters[:3] or "SCH")

    for _ in range(20):
        candidate = f"{prefix}-{_random_suffix(5)}"
        existing = (
            db.table("schools")
            .select("id")
            .eq("school_code", candidate)
            .limit(1)
            .execute()
        )
        if not existing.data:
            return candidate

    # Exhausted retries (should never happen) — fall back to a longer suffix.
    return f"{prefix}-{_random_suffix(8)}"
