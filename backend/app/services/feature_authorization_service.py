"""
feature_authorization_service.py
─────────────────────────────────────────────────────────────────────────────
CANONICAL Feature Authorization Service — single source of truth for ALL
feature access decisions on the backend.

Usage (in any route):
    from app.services.feature_authorization_service import (
        authorize_feature, Feature, require_feature
    )

    # Raises HTTP 403 automatically if denied:
    require_feature(user_id, Feature.EXEMPLAR)

    # Returns a dict if you want to inspect:
    result = authorize_feature(user_id, Feature.MOCK_TEST_UNLIMITED)
    if not result["allowed"]:
        return {"error": result["restriction_message"]}

Feature Matrix (canonical, single source of truth):
─────────────────────────────────────────────────────────────────────────────────────
Feature                  FREE_TIER  NANO   PREMIUM  FAMILY  ADMIN_GRANT  EXAM_PREP_CENTER
─────────────────────────────────────────────────────────────────────────────────────
LESSONS                  Limited    Full   Full     Full    Full         Full (Gr 11-12)
LESSON_DOWNLOAD          No         Yes    Yes      Yes     Yes          Yes
EXEMPLAR                 No         Yes    Yes      Yes     Yes          Yes
EXEMPLAR_RESEARCH        No         Yes    Yes      Yes     Yes          Yes
MOCK_TEST                Limited    Full   Full     Full    Full         Full (Gr 11-12)
MOCK_TEST_UNLIMITED      No         Yes    Yes      Yes     Yes          Yes
ASK_DOUBTS               Limited    Full   Full     Full    Full         Full (Gr 11-12)
AI_ASSISTANT             Limited    Full   Full     Full    Full         Full
AI_CHAT                  Limited    Full   Full     Full    Full         Full
QUESTION_BANK            Limited    Full   Full     Full    Full         Full
FORMULA_SHEET_PREMIUM    No         Yes    Yes      Yes     Yes          Yes
EXAM_PREP_CONTENT        No         No     No       No      Yes          Yes
PARENT_DASHBOARD         Yes        Yes    Yes      Yes     Yes          Yes
TEACHER_DASHBOARD        TeacherOnly (checked separately)
ADMIN_PANEL              AdminOnly
─────────────────────────────────────────────────────────────────────────────────────

"Limited" = DKB-only, no LLM call.
"Full"    = DKB + LLM, unrestricted.
"No"      = 403 with upgrade message.

Plan split (per "This term's plans" notebook spec — strictly followed):
- PREMIUM / FAMILY_PREMIUM: full CBSE (all grades) + Exemplar + Formula Sheet +
  Board Papers. Do NOT get Exam Prep Center content (JEE/NEET/CUET/SAT/IELTS/TOEFL)
  — that is EXAM_PREP_CENTER's exclusive content, not a Premium perk.
- EXAM_PREP_CENTER (₹1,999/yr, Grade 11-12 only): full CBSE for Grade 11-12
  (lessons/doubts/mock tests/question bank) + Exemplar + Formula Sheet + Board
  Papers + all six exams. Effectively "Premium scoped to Gr 11-12" plus the
  exam bundle, not a narrow exam-only add-on.

Security principles:
- Backend NEVER trusts frontend claims about subscription.
- ALWAYS re-resolves from DB on each request.
- `access_cbse` alone is NOT sufficient — subscription expiry is checked.
- `parentId` alone NEVER grants feature access.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.services.subscription_resolver_service import (
    resolve_user_subscription,
    Tier,
)

logger = logging.getLogger("likhapoha.feature_auth")


# ── DB-driven plan feature flag lookup ────────────────────────────────────────
# For features that are now admin-configurable (exam_prep, exemplar), we look up
# the current plan's DB settings to allow admin override without code deployment.
# This is cached per-request via the plan_settings loader (no extra DB round-trip
# when already called by the payment/subscription flow in the same request).

def _get_plan_feature_flag(db_plan_key: str | None, flag_name: str, default: bool = True) -> bool:
    """
    Return a DB-stored feature flag for a given plan key.

    Falls back to `default` if the plan is not found or the flag is not set.
    Uses list_subscription_plan_settings() which merges DB + code defaults.
    """
    if not db_plan_key:
        return default
    try:
        from app.services.subscription_settings_service import list_subscription_plan_settings  # noqa: PLC0415
        settings_payload = list_subscription_plan_settings()
        plan = (settings_payload.get("plans") or {}).get(db_plan_key)
        if plan is None:
            return default
        flag = plan.get(flag_name)
        if flag is None:
            return default
        return bool(flag)
    except Exception as _e:
        logger.warning("_get_plan_feature_flag: error reading %s for plan %s: %s", flag_name, db_plan_key, _e)
        return default


# Map canonical plan keys → DB plan keys (raw subscription_plan column values)
_CANONICAL_TO_DB_PLAN_KEY: dict[str, str] = {
    "NANO":             "free",
    "PREMIUM":          "starter",
    "PREMIUM_6MONTH":   "standard_6month",
    "PREMIUM_ANNUAL":   "standard_annual",
    "FAMILY_PREMIUM":   "family_premium",
    "FAMILY_ANNUAL":    "family_annual",
    "FREE_TIER":        "free_tier",
    "ADMIN_GRANT":      "starter",  # admin grants use premium defaults
    "EXAM_PREP_CENTER": "exam_prep_center",
}


# ── Feature identifiers ───────────────────────────────────────────────────────
class Feature:
    LESSONS              = "LESSONS"
    LESSON_DOWNLOAD      = "LESSON_DOWNLOAD"
    EXEMPLAR             = "EXEMPLAR"
    EXEMPLAR_RESEARCH    = "EXEMPLAR_RESEARCH"
    MOCK_TEST            = "MOCK_TEST"
    MOCK_TEST_UNLIMITED  = "MOCK_TEST_UNLIMITED"
    ASK_DOUBTS           = "ASK_DOUBTS"
    AI_ASSISTANT         = "AI_ASSISTANT"
    AI_CHAT              = "AI_CHAT"
    AI_SOLUTIONS         = "AI_SOLUTIONS"
    QUESTION_BANK        = "QUESTION_BANK"
    PROGRESS_ANALYTICS   = "PROGRESS_ANALYTICS"
    PARENT_DASHBOARD     = "PARENT_DASHBOARD"
    TEACHER_DASHBOARD    = "TEACHER_DASHBOARD"
    ADMIN_PANEL          = "ADMIN_PANEL"
    FORMULA_SHEET_PREMIUM= "FORMULA_SHEET_PREMIUM"
    # Grade 11/12 Exam Prep features
    EXAM_PREP_CENTER     = "EXAM_PREP_CENTER"    # page shell visible to Grade 11/12 (all tiers)
    EXAM_PREP_CONTENT    = "EXAM_PREP_CONTENT"   # actual content: questions, tests, AI — Premium+ only


# Features that support DB-driven admin override via plan settings
# Placed AFTER Feature class so string constants are available.
_DB_DRIVEN_FEATURES: dict[str, str] = {
    Feature.EXAM_PREP_CONTENT:  "access_exam_prep",
    # Gates Exemplar chapters inside Lessons (chapter names starting
    # "Exemplar:"), which are paid. EXEMPLAR_RESEARCH — the separate topic-card
    # page — used to share this flag, so one admin toggle intended for these
    # chapters silently moved both. It no longer does; see its matrix entry.
    Feature.EXEMPLAR:           "access_exemplar",
}


# ── Feature Matrix ────────────────────────────────────────────────────────────
# For each feature: which canonical plan keys are allowed (None = all), and
# whether restricted access is "limited" (True) or fully denied (False).
#
# Structure: Feature → { "allowed_plans": set | None, "limited_on": set | None }
# "allowed_plans = None" means available to all authenticated users.
# "limited_on" = set of plan keys where access is allowed but in a limited form
#   (the route handles the actual limitation; we just signal it).
_FEATURE_MATRIX: dict[str, dict] = {
    Feature.LESSONS: {
        "allowed_plans": None,   # all plans may access lessons
        "limited_on": {"FREE_TIER"},  # DKB-only for free
        # EXAM_PREP_CENTER (₹1,999/yr bundle) includes full CBSE lessons for
        # Grade 11-12 — the grade gate (not this matrix) keeps it out of Gr 5-10.
        "upgrade_message": "Upgrade to access unlimited AI-powered lessons.",
    },
    Feature.LESSON_DOWNLOAD: {
        "allowed_plans": {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                          "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT"},
        "limited_on": set(),
        "upgrade_message": "Upgrade to download lessons.",
    },
    Feature.EXEMPLAR: {
        "allowed_plans": {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                          "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT",
                          "EXAM_PREP_CENTER"},
        "limited_on": set(),
        "upgrade_message": "Exemplar access is available with a paid subscription.",
    },
    Feature.EXEMPLAR_RESEARCH: {
        # Available on every plan, because plan is not what gates this feature
        # — role is. POST /api/teacher/exemplar-research/explain serves any
        # authenticated user and 403s only free-tier TEACHERS, which is what
        # SubscriptionPlansPage.jsx advertises (the "Exemplar Research" row
        # lives in teacherGroups, rendered only when role === "teacher"). It
        # was never sold to students as a paid feature.
        #
        # This entry previously excluded FREE_TIER, which nothing enforced.
        # The only place it surfaced was _build_feature_badges() in
        # parent_dashboard.py: a free-tier parent was shown "Exemplar
        # Research — locked" for a child who could open the page and use all
        # 132 authored cards. The badge was wrong, not the access.
        #
        # Note this is deliberately NOT in _DB_DRIVEN_FEATURES. It used to
        # share the access_exemplar flag with Feature.EXEMPLAR, which gates
        # Exemplar *chapters inside Lessons* — a genuinely paid feature. One
        # admin toggle meant for those chapters would silently have changed
        # this one too.
        "allowed_plans": None,
        "limited_on": set(),
        # Reached only via the role check at the route, never through the
        # plan matrix.
        "upgrade_message": "Exemplar Research requires the Paid Teacher plan.",
    },
    Feature.MOCK_TEST: {
        "allowed_plans": None,   # all plans may take mock tests
        "limited_on": {"FREE_TIER"},  # limited to 5/day for free
        "upgrade_message": "Upgrade for unlimited mock tests.",
    },
    Feature.MOCK_TEST_UNLIMITED: {
        "allowed_plans": {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                          "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT"},
        "limited_on": set(),
        "upgrade_message": "Upgrade for unlimited mock tests.",
    },
    Feature.ASK_DOUBTS: {
        "allowed_plans": None,   # all plans may ask doubts
        "limited_on": {"FREE_TIER"},  # DKB-only for free
        "upgrade_message": "Upgrade for unlimited AI doubt solving.",
    },
    Feature.AI_ASSISTANT: {
        "allowed_plans": None,
        "limited_on": {"FREE_TIER"},
        "upgrade_message": "Upgrade for full AI assistant access.",
    },
    Feature.AI_CHAT: {
        "allowed_plans": None,
        "limited_on": {"FREE_TIER"},
        "upgrade_message": "Upgrade for full AI chat access.",
    },
    Feature.AI_SOLUTIONS: {
        "allowed_plans": None,
        "limited_on": {"FREE_TIER"},
        "upgrade_message": "Upgrade for AI-powered solutions.",
    },
    Feature.FORMULA_SHEET_PREMIUM: {
        "allowed_plans": {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                          "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT",
                          "EXAM_PREP_CENTER"},
        "limited_on": set(),
        "upgrade_message": "Upgrade to unlock solved examples, memory tips and full formula library.",
    },
    # ── Grade 11/12 Exam Prep ────────────────────────────────────────────────
    Feature.EXAM_PREP_CENTER: {
        # Page shell and preview available to all Grade 11/12 students.
        # FREE_TIER and NANO see upgrade CTA; actual content locked.
        "allowed_plans": None,          # page accessible to all tiers
        "limited_on": {"FREE_TIER", "NANO"},   # FREE/NANO: preview only, no real content
        "upgrade_message": (
            "Purchase Exam Prep Center to unlock JEE Main, NEET UG, CUET UG, "
            "SAT, IELTS & TOEFL iBT practice questions, simulated tests, "
            "and AI explanations."
        ),
    },
    Feature.EXAM_PREP_CONTENT: {
        # Actual content: questions, topic details, simulated tests, AI follow-up
        # for the six exams (JEE/NEET/CUET/SAT/IELTS/TOEFL). This is EXAM_PREP_
        # CENTER's exclusive content, NOT a Premium/Family Premium perk — per the
        # "This term's plans" spec, Premium/Family are false across this entire
        # group. Only purchasing Exam Prep Center (or an admin grant) unlocks it.
        "allowed_plans": {"ADMIN_GRANT", "EXAM_PREP_CENTER"},
        "limited_on": set(),
        "upgrade_message": (
            "Purchase the Exam Prep Center plan to access JEE/NEET/CUET/SAT/"
            "IELTS/TOEFL practice questions, simulated tests, and AI "
            "explanations — this isn't included in Premium or Family Premium."
        ),
    },
    Feature.QUESTION_BANK: {
        "allowed_plans": None,
        "limited_on": {"FREE_TIER"},
        "upgrade_message": "Upgrade for full question bank access.",
    },
    Feature.PROGRESS_ANALYTICS: {
        "allowed_plans": None,   # basic available to all
        "limited_on": {"FREE_TIER"},
        "upgrade_message": "Upgrade for detailed progress analytics.",
    },
    Feature.PARENT_DASHBOARD: {
        "allowed_plans": None,   # available to all parents
        "limited_on": set(),
        "upgrade_message": "",
    },
    Feature.TEACHER_DASHBOARD: {
        "allowed_plans": None,   # teacher role check is separate
        "limited_on": set(),
        "upgrade_message": "",
    },
    Feature.ADMIN_PANEL: {
        "allowed_plans": None,   # admin role check is separate
        "limited_on": set(),
        "upgrade_message": "",
    },
}


# ── Free-tier mock test daily limit ──────────────────────────────────────────
FREE_MOCK_TEST_DAILY_LIMIT = 5  # canonical limit — matches frontend constant


def authorize_feature(
    user_id: str,
    feature: str,
    user_role: Optional[str] = None,
) -> dict:
    """
    Determine whether a user can access a given feature.

    Parameters
    ----------
    user_id  : str  — Supabase auth UUID
    feature  : str  — one of the Feature.* constants
    user_role: str  — optional role hint (avoids extra DB lookup in some paths)

    Returns
    -------
    dict with keys:
        allowed        : bool
        limited        : bool  — True when access is in limited/degraded mode
        feature        : str
        canonical_plan_key : str
        plan_name      : str
        restriction_message: str  — human-readable reason if denied/limited
        upgrade_recommendation: str
        required_plan  : str  — "any paid plan" or specific plan name
    """
    if not user_id:
        return _denied(feature, "FREE_TIER", "Free Tier",
                       "Authentication required.", _get_upgrade_msg(feature))

    # Resolve canonical subscription from DB (never trust caller's claim)
    sub = resolve_user_subscription(user_id)
    cpk = sub.get("canonical_plan_key", "FREE_TIER")
    plan_name = sub.get("plan_name", "Free Tier")
    restrictions = sub.get("restrictions", [])

    matrix = _FEATURE_MATRIX.get(feature)
    if not matrix:
        # Unknown feature → deny by default (fail-safe)
        logger.warning("authorize_feature: unknown feature '%s' — denying", feature)
        return _denied(feature, cpk, plan_name, f"Feature '{feature}' is not recognised.", "")

    allowed_plans = matrix["allowed_plans"]
    limited_on    = matrix["limited_on"]
    denied_plans  = matrix.get("denied_plans") or set()
    upgrade_msg   = matrix["upgrade_message"]

    # Explicit denial takes precedence even for "available to all" features.
    # Used by plans that intentionally exclude certain feature groups — e.g.
    # Premium/Family Premium are denied EXAM_PREP_CONTENT via allowed_plans
    # (not denied_plans) since that plan's exams are EXAM_PREP_CENTER-exclusive.
    if cpk in denied_plans:
        return _denied(
            feature, cpk, plan_name,
            f"{_feature_display_name(feature)} is not included in your current plan.",
            upgrade_msg,
        )

    # Feature available to ALL plans → check if this plan is in limited_on
    if allowed_plans is None:
        is_limited = cpk in limited_on
        return {
            "allowed": True,
            "limited": is_limited,
            "feature": feature,
            "canonical_plan_key": cpk,
            "plan_name": plan_name,
            "restriction_message": upgrade_msg if is_limited else "",
            "upgrade_recommendation": upgrade_msg if is_limited else "",
            "required_plan": "Any paid plan" if is_limited else "",
        }

    # Feature restricted to specific plans
    if cpk in allowed_plans:
        # ── DB-driven override check ─────────────────────────────────────────
        # For features that are admin-configurable, check the plan's DB flag.
        # If the admin disabled this feature for this plan, deny even if the
        # canonical matrix says allowed.
        db_flag_name = _DB_DRIVEN_FEATURES.get(feature)
        if db_flag_name:
            db_plan_key = _CANONICAL_TO_DB_PLAN_KEY.get(cpk)
            flag_value = _get_plan_feature_flag(db_plan_key, db_flag_name, default=True)
            if not flag_value:
                return _denied(
                    feature, cpk, plan_name,
                    f"{_feature_display_name(feature)} is not included in your current plan. "
                    "Please contact support or upgrade to a plan that includes this feature.",
                    upgrade_msg,
                )
        return {
            "allowed": True,
            "limited": False,
            "feature": feature,
            "canonical_plan_key": cpk,
            "plan_name": plan_name,
            "restriction_message": "",
            "upgrade_recommendation": "",
            "required_plan": "",
        }

    # ── DB-driven access grant for normally-denied plans ─────────────────────
    # If the canonical matrix denies this plan, but the admin has enabled the
    # feature flag in DB for this plan, grant access.
    # Exception: NANO is explicitly excluded from EXAM_PREP_CONTENT regardless
    # of DB flags — the spec says Nano users get preview only, not content.
    db_flag_name = _DB_DRIVEN_FEATURES.get(feature)
    if db_flag_name:
        db_plan_key = _CANONICAL_TO_DB_PLAN_KEY.get(cpk)
        # NANO is permanently excluded from EXAM_PREP_CONTENT — cannot be overridden by admin
        if feature == Feature.EXAM_PREP_CONTENT and cpk == "NANO":
            db_plan_key = None
        if db_plan_key:
            flag_value = _get_plan_feature_flag(db_plan_key, db_flag_name, default=False)
            if flag_value:
                logger.info(
                    "authorize_feature: DB override grants %s to %s (plan=%s)",
                    feature, user_id[:8], cpk,
                )
                return {
                    "allowed": True,
                    "limited": False,
                    "feature": feature,
                    "canonical_plan_key": cpk,
                    "plan_name": plan_name,
                    "restriction_message": "",
                    "upgrade_recommendation": "",
                    "required_plan": "",
                }

    # Denied
    return _denied(feature, cpk, plan_name,
                   f"{_feature_display_name(feature)} requires a paid subscription.",
                   upgrade_msg)


def require_feature(
    user_id: str,
    feature: str,
    user_role: Optional[str] = None,
) -> dict:
    """
    Like `authorize_feature` but raises HTTP 403 if access is denied.

    Use in route handlers:
        result = require_feature(user.id, Feature.EXEMPLAR)
        # result["limited"] is True → route should use degraded mode

    Raises
    ------
    HTTPException(403) with structured JSON detail if feature is denied.
    """
    result = authorize_feature(user_id, feature, user_role)
    if not result["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "feature": feature,
                "current_plan": result["plan_name"],
                "canonical_plan_key": result["canonical_plan_key"],
                "required_plan": result.get("required_plan", "Paid subscription"),
                "message": result["restriction_message"],
                "upgrade_message": result["upgrade_recommendation"],
            },
        )
    return result


def get_feature_summary(user_id: str) -> dict:
    """
    Return a summary dict of all features and their access state for a user.
    Used by /api/subscription/features endpoint.
    """
    sub = resolve_user_subscription(user_id)
    cpk = sub.get("canonical_plan_key", "FREE_TIER")

    summary = {}
    for feat, matrix in _FEATURE_MATRIX.items():
        allowed_plans = matrix["allowed_plans"]
        limited_on    = matrix["limited_on"]
        if allowed_plans is None:
            summary[feat] = {
                "allowed": True,
                "limited": cpk in limited_on,
            }
        else:
            summary[feat] = {
                "allowed": cpk in allowed_plans,
                "limited": False,
            }
    return {
        "user_id": user_id,
        "canonical_plan_key": cpk,
        "plan_name": sub.get("plan_name", "Free Tier"),
        "has_full_access": sub.get("has_full_access", False),
        "features": summary,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _denied(feature, cpk, plan_name, message, upgrade_msg) -> dict:
    return {
        "allowed": False,
        "limited": False,
        "feature": feature,
        "canonical_plan_key": cpk,
        "plan_name": plan_name,
        "restriction_message": message,
        "upgrade_recommendation": upgrade_msg,
        "required_plan": "Any paid plan",
    }


def _get_upgrade_msg(feature: str) -> str:
    m = _FEATURE_MATRIX.get(feature)
    return m["upgrade_message"] if m else "Upgrade to access this feature."


def _feature_display_name(feature: str) -> str:
    names = {
        Feature.LESSONS:             "CBSE Lessons",
        Feature.LESSON_DOWNLOAD:     "Lesson Download",
        Feature.EXEMPLAR:            "Exemplar",
        Feature.EXEMPLAR_RESEARCH:   "Exemplar Research",
        Feature.MOCK_TEST:           "Mock Tests",
        Feature.MOCK_TEST_UNLIMITED: "Unlimited Mock Tests",
        Feature.ASK_DOUBTS:          "AI Doubt Solving",
        Feature.AI_ASSISTANT:        "AI Assistant",
        Feature.AI_CHAT:             "AI Chat",
        Feature.AI_SOLUTIONS:        "AI Solutions",
        Feature.FORMULA_SHEET_PREMIUM: "Formula Sheet Premium",
        Feature.QUESTION_BANK:       "Question Bank",
        Feature.PROGRESS_ANALYTICS:  "Progress Analytics",
        Feature.PARENT_DASHBOARD:    "Parent Dashboard",
        Feature.TEACHER_DASHBOARD:   "Teacher Dashboard",
        Feature.ADMIN_PANEL:         "Admin Panel",
        Feature.EXAM_PREP_CENTER:    "Exam Prep Center",
        Feature.EXAM_PREP_CONTENT:   "Exam Prep Content",
    }
    return names.get(feature, feature)
