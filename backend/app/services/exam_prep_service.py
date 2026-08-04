"""
exam_prep_service.py — Exam Prep Center business logic
=======================================================
Access rules (backend-enforced):
  - admin: always allowed
  - student Grade 11 / Grade 12: allowed
  - akshita.teststudent: allowed regardless of grade (test rollout)
  - all other students/roles: 403
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from app.services.logger_service import get_logger

_log = get_logger("exam_prep_service")

# ── Access control ─────────────────────────────────────────────────────────────

EXAM_PREP_TEST_USERS: set[str] = {"akshita.teststudent"}
EXAM_PREP_GRADES: set[str] = {"Grade 11", "Grade 12"}

# ── Upgrade discount ──────────────────────────────────────────────────────────
# ₹200 loyalty discount for an existing Premium/Family Premium Grade 11/12
# subscriber upgrading to Exam Prep Center. Scoped literally to "starter" and
# "family_premium" (not the 6-month/annual variants) per product decision.
EXAM_PREP_UPGRADE_DISCOUNT_RUPEES = 200
_DISCOUNT_ELIGIBLE_CURRENT_PLANS: set[str] = {"starter", "family_premium"}


def exam_prep_upgrade_discount_rupees(current_plan_key: str | None, grade: str | None) -> int:
    """
    ₹200 loyalty discount amount for a Grade 11/12 student currently on Premium
    or Family Premium upgrading to Exam Prep Center. Applied on top of any admin
    global discount_percent; the caller is responsible for flooring at 0.
    """
    if current_plan_key in _DISCOUNT_ELIGIBLE_CURRENT_PLANS and grade in EXAM_PREP_GRADES:
        return EXAM_PREP_UPGRADE_DISCOUNT_RUPEES
    return 0


# Streams that are eligible for each entrance exam
JEE_ELIGIBLE_STREAMS: set[str] = {"PCM", "PCMB"}
NEET_ELIGIBLE_STREAMS: set[str] = {"PCB", "PCMB"}


def build_exam_eligibility(stream: str | None) -> dict:
    """
    Return per-exam eligibility based on academic stream.

    JEE Main  → PCM, PCMB (requires Mathematics)
    NEET UG   → PCB, PCMB (requires Biology)
    CUET UG   → all streams (enabled)
    """
    s = (stream or "").strip().upper()
    return {
        "jee_main": {
            "eligible": s in JEE_ELIGIBLE_STREAMS,
            "reason": (
                ""
                if s in JEE_ELIGIBLE_STREAMS
                else "JEE Main requires Mathematics. Available for PCM and PCMB students."
            ),
        },
        "neet_ug": {
            "eligible": s in NEET_ELIGIBLE_STREAMS,
            "reason": (
                ""
                if s in NEET_ELIGIBLE_STREAMS
                else "NEET UG requires Biology. Available for PCB and PCMB students."
            ),
        },
        "cuet_ug": {
            "eligible": True,
            "reason": "",
        },
        # Global standardised tests — eligible for all streams
        "sat": {"eligible": True, "reason": ""},
        "ielts": {"eligible": True, "reason": ""},
        "toefl_ibt": {"eligible": True, "reason": ""},
    }


def check_exam_prep_access(profile: dict) -> None:
    """
    Raise HTTP 403 if the user cannot see the Exam Prep Center page at all.

    This is the GRADE/ROLE gate only — it controls whether the page shell
    renders.  Subscription gating for actual content is in
    check_exam_prep_content_access().
    """
    role = profile.get("role", "")
    username = profile.get("username", "")
    grade = profile.get("grade", "")

    if role == "admin":
        return
    if username in EXAM_PREP_TEST_USERS:
        return
    if role == "student" and grade in EXAM_PREP_GRADES:
        return

    raise HTTPException(
        status_code=403,
        detail=(
            "Exam Prep Center is only available for Grade 11 & 12 students. "
            "Grade 5-10 access is not enabled yet."
        ),
    )


def check_exam_prep_content_access(profile: dict) -> dict:
    """
    Raise HTTP 403 if the user cannot access actual Exam Prep content.

    Content includes: questions, topic priorities, simulated tests,
    answer explanations, AI follow-up.

    Access matrix (canonical, via feature_authorization_service):
      FREE_TIER  → 403 (preview only)
      NANO       → 403 (preview only)
      PREMIUM    → allowed
      FAMILY_*   → allowed
      ADMIN_GRANT → allowed
      admin role  → allowed
      test users  → allowed

    Returns the feature authorization result dict on success.
    """
    # First enforce grade/role gate
    check_exam_prep_access(profile)

    role = profile.get("role", "")
    username = profile.get("username", "")
    if role == "admin" or username in EXAM_PREP_TEST_USERS:
        return {"allowed": True, "limited": False, "canonical_plan_key": "ADMIN_GRANT"}

    # Canonical subscription check via feature authorization service
    from app.services.feature_authorization_service import authorize_feature, Feature  # noqa: PLC0415
    user_id = profile.get("id", "")
    result = authorize_feature(user_id, Feature.EXAM_PREP_CONTENT)

    if not result["allowed"]:
        cpk = result.get("canonical_plan_key", "FREE_TIER")
        is_nano = "NANO" in cpk.upper()
        restriction_type = "nano" if is_nano else "free"
        msg = (
            "Exam Prep Center is available on Premium, Family Premium, or Admin Grant. "
            "Your current Premium Nano plan does not include Exam Prep."
            if is_nano
            else result["restriction_message"]
        )
        raise HTTPException(
            status_code=403,
            detail={
                "feature": "EXAM_PREP_CONTENT",
                "current_plan": result["plan_name"],
                "canonical_plan_key": cpk,
                "restriction_type": restriction_type,
                "message": msg,
                "upgrade_message": result["upgrade_recommendation"],
            },
        )
    return result


# Packs (jee_main / neet_ug / cuet_ug) are a separate, standalone purchase —
# independent of the CBSE subscription tiers (see routes/exam_prep_packs.py).
# A student on Free/Nano who buys a pack must get full Exam Prep Center
# access, exactly like a Premium subscriber — this helper is the single
# source of truth both here (access-check) and in exam_prep_packs.py.
_PACK_EXAM_TYPES = ("jee_main", "neet_ug", "cuet_ug")


def get_active_packs(user_id: str) -> dict:
    """
    Return which of the 3 exam-prep packs (jee_main/neet_ug/cuet_ug) the
    given user currently has active (paid & not expired).

    Returns: {"jee_main": bool, "neet_ug": bool, "cuet_ug": bool}
    """
    result = {et: False for et in _PACK_EXAM_TYPES}
    try:
        db = _get_db()
        now = datetime.now(timezone.utc).isoformat()
        rows = (
            db.table("exam_prep_subscriptions")
            .select("exam_type, status, expires_at")
            .eq("user_id", user_id)
            .execute()
        ).data or []
        for row in rows:
            et = row.get("exam_type")
            if et not in result or row.get("status") != "active":
                continue
            exp = row.get("expires_at")
            if exp and exp < now:
                continue  # expired — treated as not owned
            result[et] = True
    except Exception as exc:
        _log.warning("exam_prep.get_active_packs.failed", error=str(exc))
    return result


def check_exam_content_access_with_packs(profile: dict, exam_type: str) -> dict:
    """
    Raise HTTP 403 if the user cannot access content for a SPECIFIC exam.

    Unlike check_exam_prep_content_access() (subscription-only gate used by
    ask-followup/legacy endpoints), this variant also grants access when the
    student owns an active standalone pack for the given exam_type — so a
    Free/Nano student who purchased e.g. the JEE pack can use
    dashboard/subjects/topics/questions/simulated-tests for jee_main, while
    still being blocked from neet_ug/cuet_ug/sat/ielts/toefl_ibt (which they
    did not pay for) unless they separately hold Premium+.

    Returns the same shape as check_exam_prep_content_access() on success.
    """
    # First enforce grade/role gate
    check_exam_prep_access(profile)

    role = profile.get("role", "")
    username = profile.get("username", "")
    if role == "admin" or username in EXAM_PREP_TEST_USERS:
        return {"allowed": True, "limited": False, "canonical_plan_key": "ADMIN_GRANT"}

    # Canonical subscription check via feature authorization service
    from app.services.feature_authorization_service import authorize_feature, Feature  # noqa: PLC0415
    user_id = profile.get("id", "")
    result = authorize_feature(user_id, Feature.EXAM_PREP_CONTENT)

    if result["allowed"]:
        return result

    # Subscription doesn't grant access — check pack ownership for this exam.
    # Packs only exist for jee_main/neet_ug/cuet_ug; other exams have no pack.
    if exam_type in _PACK_EXAM_TYPES:
        owned = get_active_packs(user_id)
        if owned.get(exam_type):
            return {"allowed": True, "limited": False, "canonical_plan_key": "PACK_ACCESS"}

    cpk = result.get("canonical_plan_key", "FREE_TIER")
    is_nano = "NANO" in cpk.upper()
    restriction_type = "nano" if is_nano else "free"
    msg = (
        "Exam Prep Center is available on Premium, Family Premium, Admin Grant, "
        "or by purchasing a standalone exam pack for this exam. "
        "Your current Premium Nano plan does not include Exam Prep."
        if is_nano
        else result["restriction_message"]
    )
    raise HTTPException(
        status_code=403,
        detail={
            "feature": "EXAM_PREP_CONTENT",
            "exam_type": exam_type,
            "current_plan": result["plan_name"],
            "canonical_plan_key": cpk,
            "restriction_type": restriction_type,
            "message": msg,
            "upgrade_message": result["upgrade_recommendation"],
        },
    )


def get_access_check_response(user_id: str, profile: dict) -> dict:
    """
    Build the canonical access-check response for GET /api/exam-prep/access-check.

    Returns a JSON-safe dict consumed by the frontend to determine whether
    to render the full Exam Prep Center or the locked preview shell.

    NOTE: `owned_packs` is always included so the frontend can show pack
    purchase/ownership status regardless of subscription tier.
    """
    role = profile.get("role", "")
    username = profile.get("username", "")
    grade = profile.get("grade", "")
    stream = profile.get("stream") or profile.get("academic_stream") or None
    owned_packs = get_active_packs(user_id)

    # Admin: full access, no subscription check
    if role == "admin":
        return {
            "grade_eligible": True,
            "has_access": True,
            "preview_only": False,
            "reason": "admin",
            "stream": stream,
            "stream_missing": stream is None,
            "exam_eligibility": build_exam_eligibility(stream),
            "canonical_plan_key": "ADMIN_GRANT",
            "plan_name": "Admin",
            "owned_packs": owned_packs,
        }

    # Test users: full access to all exams regardless of stream
    if username in EXAM_PREP_TEST_USERS:
        return {
            "grade_eligible": True,
            "has_access": True,
            "preview_only": False,
            "reason": "test_user",
            "stream": stream,
            "stream_missing": stream is None,
            "exam_eligibility": {
                "jee_main":   {"eligible": True, "reason": ""},
                "neet_ug":    {"eligible": True, "reason": ""},
                "cuet_ug":    {"eligible": True, "reason": ""},
                "sat":        {"eligible": True, "reason": ""},
                "ielts":      {"eligible": True, "reason": ""},
                "toefl_ibt":  {"eligible": True, "reason": ""},
            },
            "canonical_plan_key": "ADMIN_GRANT",
            "plan_name": "Test Access",
            "owned_packs": owned_packs,
        }

    # Grade ineligible (not Grade 11/12)
    if role != "student" or grade not in EXAM_PREP_GRADES:
        return {
            "grade_eligible": False,
            "has_access": False,
            "preview_only": True,
            "reason": "grade_ineligible",
            "stream": stream,
            "stream_missing": False,
            "exam_eligibility": None,
            "canonical_plan_key": None,
            "plan_name": None,
            "owned_packs": owned_packs,
        }

    # Grade 11/12 student — check subscription via canonical feature auth
    from app.services.feature_authorization_service import authorize_feature, Feature  # noqa: PLC0415
    result = authorize_feature(user_id, Feature.EXAM_PREP_CONTENT)
    cpk = result.get("canonical_plan_key", "FREE_TIER")
    is_nano = "NANO" in cpk.upper()

    if result["allowed"]:
        return {
            "grade_eligible": True,
            "has_access": True,
            "preview_only": False,
            "reason": "full_access",
            "stream": stream,
            "stream_missing": stream is None,
            "exam_eligibility": build_exam_eligibility(stream),
            "canonical_plan_key": cpk,
            "plan_name": result.get("plan_name", "Premium"),
            "owned_packs": owned_packs,
        }

    # Free/Nano tier — normally locked, UNLESS the student owns at least
    # one active exam-prep pack. Pack ownership grants full page access
    # (has_access=True) so the Exam Prep Center renders; the individual
    # exam tabs the student did NOT pay for are separately restricted by
    # the frontend using `owned_packs`, similar to how `exam_eligibility`
    # already restricts JEE/NEET tabs by academic stream.
    has_any_pack = any(owned_packs.values())
    restriction_type = "nano" if is_nano else "free"
    return {
        "grade_eligible": True,
        "has_access": has_any_pack,
        "preview_only": not has_any_pack,
        "reason": "pack_access" if has_any_pack else restriction_type,
        "stream": stream,
        "stream_missing": stream is None,
        "exam_eligibility": build_exam_eligibility(stream),
        "canonical_plan_key": cpk,
        "plan_name": result.get("plan_name", "Free Tier"),
        "upgrade_message": result.get("upgrade_recommendation", ""),
        "owned_packs": owned_packs,
    }


# ── Static syllabus data ───────────────────────────────────────────────────────

JEE_SUBJECTS = {
    "Physics": {
        "icon": "⚛️",
        "color": "#6366f1",
        "chapters": 22,
        "weightage_pct": 33,
        "topics": [
            {
                "name": "Kinematics",
                "priority": "HIGH",
                "subtopics": ["Projectile Motion", "Relative Velocity", "Graphs"],
                "weightage_pct": 8,
                "chapter": "Motion in a Straight Line",
                "ncert_chapter": "NCERT Class 11, Chapter 3",
            },
            {
                "name": "Laws of Motion",
                "priority": "HIGH",
                "subtopics": ["Newton's Laws", "Friction", "Circular Motion"],
                "weightage_pct": 10,
                "chapter": "Laws of Motion",
                "ncert_chapter": "NCERT Class 11, Chapter 5",
            },
            {
                "name": "Work, Energy and Power",
                "priority": "HIGH",
                "subtopics": ["Work-Energy Theorem", "Conservation of Energy", "Power"],
                "weightage_pct": 7,
                "chapter": "Work, Energy and Power",
                "ncert_chapter": "NCERT Class 11, Chapter 6",
            },
            {
                "name": "Electrostatics",
                "priority": "HIGH",
                "subtopics": ["Coulomb's Law", "Electric Field", "Capacitors"],
                "weightage_pct": 9,
                "chapter": "Electric Charges and Fields",
                "ncert_chapter": "NCERT Class 12, Chapter 1",
            },
            {
                "name": "Current Electricity",
                "priority": "HIGH",
                "subtopics": ["Ohm's Law", "Kirchhoff's Laws", "Wheatstone Bridge"],
                "weightage_pct": 8,
                "chapter": "Current Electricity",
                "ncert_chapter": "NCERT Class 12, Chapter 3",
            },
            {
                "name": "Magnetism",
                "priority": "MED",
                "subtopics": ["Biot-Savart Law", "Ampere's Law", "Lorentz Force"],
                "weightage_pct": 6,
                "chapter": "Moving Charges and Magnetism",
                "ncert_chapter": "NCERT Class 12, Chapter 4",
            },
            {
                "name": "Optics",
                "priority": "MED",
                "subtopics": ["Ray Optics", "Wave Optics", "Interference"],
                "weightage_pct": 6,
                "chapter": "Wave Optics",
                "ncert_chapter": "NCERT Class 12, Chapter 10",
            },
            {
                "name": "Modern Physics",
                "priority": "HIGH",
                "subtopics": ["Photoelectric Effect", "Atomic Models", "Radioactivity"],
                "weightage_pct": 9,
                "chapter": "Dual Nature of Radiation",
                "ncert_chapter": "NCERT Class 12, Chapter 11",
            },
            {
                "name": "Thermodynamics",
                "priority": "MED",
                "subtopics": ["Laws of Thermodynamics", "Carnot Engine", "Entropy"],
                "weightage_pct": 6,
                "chapter": "Thermodynamics",
                "ncert_chapter": "NCERT Class 11, Chapter 12",
            },
            {
                "name": "Waves & Oscillations",
                "priority": "MED",
                "subtopics": ["SHM", "Wave Equations", "Standing Waves"],
                "weightage_pct": 5,
                "chapter": "Waves",
                "ncert_chapter": "NCERT Class 11, Chapter 15",
            },
        ],
    },
    "Chemistry": {
        "icon": "🧪",
        "color": "#10b981",
        "chapters": 28,
        "weightage_pct": 33,
        "topics": [
            {
                "name": "Chemical Bonding",
                "priority": "HIGH",
                "subtopics": ["VSEPR Theory", "Hybridisation", "MO Theory"],
                "weightage_pct": 9,
                "chapter": "Chemical Bonding and Molecular Structure",
                "ncert_chapter": "NCERT Class 11, Chapter 4",
            },
            {
                "name": "Electrochemistry",
                "priority": "HIGH",
                "subtopics": ["Electrolytic Cells", "EMF", "Nernst Equation"],
                "weightage_pct": 8,
                "chapter": "Electrochemistry",
                "ncert_chapter": "NCERT Class 12, Chapter 3",
            },
            {
                "name": "Organic Mechanisms",
                "priority": "HIGH",
                "subtopics": ["SN1/SN2", "Elimination", "Addition Reactions"],
                "weightage_pct": 10,
                "chapter": "Haloalkanes and Haloarenes",
                "ncert_chapter": "NCERT Class 12, Chapter 10",
            },
            {
                "name": "Equilibrium",
                "priority": "HIGH",
                "subtopics": ["Le Chatelier", "Kp/Kc", "Ionic Equilibrium"],
                "weightage_pct": 8,
                "chapter": "Equilibrium",
                "ncert_chapter": "NCERT Class 11, Chapter 7",
            },
            {
                "name": "Coordination Compounds",
                "priority": "HIGH",
                "subtopics": ["Werner's Theory", "CFSE", "Isomerism"],
                "weightage_pct": 7,
                "chapter": "Coordination Compounds",
                "ncert_chapter": "NCERT Class 12, Chapter 9",
            },
            {
                "name": "Organic Compounds",
                "priority": "HIGH",
                "subtopics": ["Aldehydes/Ketones", "Carboxylic Acids", "Amines"],
                "weightage_pct": 9,
                "chapter": "Aldehydes, Ketones and Carboxylic Acids",
                "ncert_chapter": "NCERT Class 12, Chapter 12",
            },
            {
                "name": "p-Block Elements",
                "priority": "MED",
                "subtopics": ["Group 15,16,17", "Oxyacids", "Noble Gases"],
                "weightage_pct": 6,
                "chapter": "p-Block Elements",
                "ncert_chapter": "NCERT Class 12, Chapter 7",
            },
        ],
    },
    "Mathematics": {
        "icon": "📐",
        "color": "#f59e0b",
        "chapters": 16,
        "weightage_pct": 34,
        "topics": [
            {
                "name": "Integration",
                "priority": "HIGH",
                "subtopics": ["Definite Integrals", "Area Under Curve", "Integration by Parts"],
                "weightage_pct": 10,
                "chapter": "Integrals",
                "ncert_chapter": "NCERT Class 12, Chapter 7",
            },
            {
                "name": "Coordinate Geometry",
                "priority": "HIGH",
                "subtopics": ["Straight Lines", "Circles", "Parabola/Ellipse"],
                "weightage_pct": 10,
                "chapter": "Conic Sections",
                "ncert_chapter": "NCERT Class 11, Chapter 11",
            },
            {
                "name": "Vectors & 3D Geometry",
                "priority": "HIGH",
                "subtopics": ["Dot/Cross Product", "Lines in 3D", "Planes"],
                "weightage_pct": 9,
                "chapter": "Vector Algebra",
                "ncert_chapter": "NCERT Class 12, Chapter 10",
            },
            {
                "name": "Matrices & Determinants",
                "priority": "HIGH",
                "subtopics": ["Matrix Operations", "Eigenvalues", "Cramer's Rule"],
                "weightage_pct": 8,
                "chapter": "Matrices",
                "ncert_chapter": "NCERT Class 12, Chapter 3",
            },
            {
                "name": "Limits & Continuity",
                "priority": "HIGH",
                "subtopics": ["L'Hopital's Rule", "Sandwich Theorem", "Continuity"],
                "weightage_pct": 8,
                "chapter": "Limits and Derivatives",
                "ncert_chapter": "NCERT Class 11, Chapter 13",
            },
            {
                "name": "Probability",
                "priority": "MED",
                "subtopics": ["Bayes Theorem", "Distributions", "Conditional Probability"],
                "weightage_pct": 7,
                "chapter": "Probability",
                "ncert_chapter": "NCERT Class 12, Chapter 13",
            },
            {
                "name": "Differential Equations",
                "priority": "MED",
                "subtopics": ["Variable Separable", "Linear DE", "Homogeneous"],
                "weightage_pct": 6,
                "chapter": "Differential Equations",
                "ncert_chapter": "NCERT Class 12, Chapter 9",
            },
        ],
    },
}

NEET_BIOLOGY = {
    "icon": "🌿",
    "color": "#22c55e",
    "chapters": 38,
    "weightage_pct": 50,
    "topics": [
        {
            "name": "Cell Biology",
            "priority": "HIGH",
            "subtopics": ["Cell Structure", "Cell Division", "Biomolecules"],
            "weightage_pct": 9,
            "chapter": "Cell: The Unit of Life",
            "ncert_chapter": "NCERT Class 11, Chapter 8",
        },
        {
            "name": "Genetics & Molecular Biology",
            "priority": "HIGH",
            "subtopics": ["Mendelian Genetics", "DNA Replication", "Gene Expression", "Mutations"],
            "weightage_pct": 13,
            "chapter": "Principles of Inheritance and Variation",
            "ncert_chapter": "NCERT Class 12, Chapter 5",
        },
        {
            "name": "Human Physiology",
            "priority": "HIGH",
            "subtopics": ["Digestion", "Respiration", "Circulation", "Excretion", "Nervous System"],
            "weightage_pct": 12,
            "chapter": "Breathing and Exchange of Gases",
            "ncert_chapter": "NCERT Class 11, Chapter 17",
        },
        {
            "name": "Plant Physiology",
            "priority": "HIGH",
            "subtopics": ["Photosynthesis", "Respiration in Plants", "Plant Growth"],
            "weightage_pct": 8,
            "chapter": "Photosynthesis in Higher Plants",
            "ncert_chapter": "NCERT Class 11, Chapter 13",
        },
        {
            "name": "Reproduction",
            "priority": "HIGH",
            "subtopics": ["Sexual Reproduction in Plants", "Human Reproduction", "Reproductive Health"],
            "weightage_pct": 9,
            "chapter": "Human Reproduction",
            "ncert_chapter": "NCERT Class 12, Chapter 3",
        },
        {
            "name": "Ecology & Environment",
            "priority": "HIGH",
            "subtopics": ["Ecosystem", "Biodiversity", "Environmental Issues", "Population"],
            "weightage_pct": 8,
            "chapter": "Ecosystem",
            "ncert_chapter": "NCERT Class 12, Chapter 14",
        },
        {
            "name": "Biotechnology",
            "priority": "MED",
            "subtopics": ["Recombinant DNA", "PCR", "GMOs", "Applications"],
            "weightage_pct": 6,
            "chapter": "Biotechnology: Principles and Processes",
            "ncert_chapter": "NCERT Class 12, Chapter 11",
        },
        {
            "name": "Evolution",
            "priority": "MED",
            "subtopics": ["Origin of Life", "Darwinism", "Human Evolution", "Speciation"],
            "weightage_pct": 5,
            "chapter": "Evolution",
            "ncert_chapter": "NCERT Class 12, Chapter 7",
        },
        {
            "name": "Structural Organisation",
            "priority": "MED",
            "subtopics": ["Tissues", "Morphology of Flowering Plants", "Anatomy"],
            "weightage_pct": 5,
            "chapter": "Morphology of Flowering Plants",
            "ncert_chapter": "NCERT Class 11, Chapter 5",
        },
        {
            "name": "Diversity in Living World",
            "priority": "MED",
            "subtopics": ["Five Kingdom Classification", "Fungi", "Protista", "Monera"],
            "weightage_pct": 4,
            "chapter": "Biological Classification",
            "ncert_chapter": "NCERT Class 11, Chapter 2",
        },
    ],
}

# NEET Physics has same chapters as JEE but different weightage distribution
NEET_PHYSICS = dict(JEE_SUBJECTS["Physics"])
NEET_PHYSICS["weightage_pct"] = 25

NEET_CHEMISTRY = dict(JEE_SUBJECTS["Chemistry"])
NEET_CHEMISTRY["weightage_pct"] = 25

# CUET UG — Common University Entrance Test
# Section IA: Language (mandatory), Section II: Domain Subjects, Section III: General Test
CUET_SUBJECTS = {
    "English": {
        "icon": "📝",
        "color": "#6366f1",
        "chapters": 10,
        "weightage_pct": 20,
        "topics": [
            {
                "name": "Reading Comprehension",
                "priority": "HIGH",
                "subtopics": ["Passage-based Questions", "Inference", "Vocabulary in Context"],
                "weightage_pct": 25,
                "chapter": "Reading Comprehension",
                "ncert_chapter": "NCERT Flamingo / Vistas Class 12",
            },
            {
                "name": "Grammar & Usage",
                "priority": "HIGH",
                "subtopics": ["Tenses", "Voices", "Narration", "Error Spotting"],
                "weightage_pct": 20,
                "chapter": "Grammar",
                "ncert_chapter": "NCERT English Class 11 & 12",
            },
            {
                "name": "Vocabulary",
                "priority": "HIGH",
                "subtopics": ["Synonyms", "Antonyms", "Idioms", "One-word Substitution"],
                "weightage_pct": 15,
                "chapter": "Vocabulary",
                "ncert_chapter": "NCERT English Class 11 & 12",
            },
            {
                "name": "Literature",
                "priority": "MED",
                "subtopics": ["Poetry", "Prose", "Drama", "Short Stories"],
                "weightage_pct": 20,
                "chapter": "Literature",
                "ncert_chapter": "NCERT Flamingo Class 12",
            },
            {
                "name": "Writing Skills",
                "priority": "MED",
                "subtopics": ["Essay Writing", "Letter Writing", "Report Writing", "Notice Writing"],
                "weightage_pct": 10,
                "chapter": "Writing",
                "ncert_chapter": "NCERT English Class 12",
            },
            {
                "name": "Verbal Ability",
                "priority": "MED",
                "subtopics": ["Para Jumbles", "Sentence Completion", "Cloze Test"],
                "weightage_pct": 10,
                "chapter": "Verbal Ability",
                "ncert_chapter": "NCERT English Class 11 & 12",
            },
        ],
    },
    "Hindi": {
        "icon": "अ",
        "color": "#f97316",
        "chapters": 10,
        "weightage_pct": 20,
        "topics": [
            {
                "name": "Gadya — Prose Comprehension",
                "priority": "HIGH",
                "subtopics": ["Factual Inference", "Author's Viewpoint", "Unseen Prose Passages"],
                "weightage_pct": 25,
                "chapter": "Gadya — Prose Comprehension",
                "ncert_chapter": "NCERT Hindi Class 11 & 12 (Aroh/Antra)",
            },
            {
                "name": "Padya — Poetry Comprehension",
                "priority": "HIGH",
                "subtopics": ["Meaning", "Bhav-Arth", "Alankar (Figures of Speech)"],
                "weightage_pct": 20,
                "chapter": "Padya — Poetry Comprehension",
                "ncert_chapter": "NCERT Hindi Class 11 & 12 (Aroh/Antra)",
            },
            {
                "name": "Vyakaran — Grammar",
                "priority": "HIGH",
                "subtopics": ["Sandhi", "Samas", "Vakya-Shuddhi", "Muhavare aur Lokoktiyan"],
                "weightage_pct": 20,
                "chapter": "Vyakaran — Grammar",
                "ncert_chapter": "NCERT Hindi Vyakaran Class 11 & 12",
            },
            {
                "name": "Applied Hindi — Vocabulary and Usage",
                "priority": "MED",
                "subtopics": ["Paryayvachi", "Vilom Shabd", "Anekarthi", "Tatsam-Tadbhav"],
                "weightage_pct": 15,
                "chapter": "Applied Hindi — Vocabulary and Usage",
                "ncert_chapter": "NCERT Hindi Vyakaran Class 11 & 12",
            },
            {
                "name": "Sahitya — Literary Knowledge",
                "priority": "MED",
                "subtopics": ["Kaal Vibhajan", "Major Writers", "Chhayavad", "Pragativad", "Prayogvad"],
                "weightage_pct": 20,
                "chapter": "Sahitya — Literary Knowledge",
                "ncert_chapter": "NCERT Hindi Class 11 & 12 (Antra)",
            },
        ],
    },
    "General Test": {
        "icon": "🧩",
        "color": "#8b5cf6",
        "chapters": 8,
        "weightage_pct": 20,
        "topics": [
            {
                "name": "Quantitative Reasoning",
                "priority": "HIGH",
                "subtopics": ["Number System", "Percentage", "Ratio & Proportion", "Profit & Loss"],
                "weightage_pct": 25,
                "chapter": "Quantitative Aptitude",
                "ncert_chapter": "NCERT Mathematics Class 10",
            },
            {
                "name": "Logical Reasoning",
                "priority": "HIGH",
                "subtopics": ["Series", "Analogy", "Coding-Decoding", "Blood Relations"],
                "weightage_pct": 25,
                "chapter": "Logical Reasoning",
                "ncert_chapter": "General Aptitude",
            },
            {
                "name": "General Knowledge",
                "priority": "HIGH",
                "subtopics": ["Current Affairs", "History", "Geography", "Science & Technology"],
                "weightage_pct": 20,
                "chapter": "General Knowledge",
                "ncert_chapter": "NCERT Social Science",
            },
            {
                "name": "Data Interpretation",
                "priority": "MED",
                "subtopics": ["Tables", "Bar Graphs", "Pie Charts", "Line Graphs"],
                "weightage_pct": 15,
                "chapter": "Data Interpretation",
                "ncert_chapter": "NCERT Statistics",
            },
            {
                "name": "General Mental Ability",
                "priority": "MED",
                "subtopics": ["Direction Sense", "Venn Diagrams", "Syllogisms", "Calendar"],
                "weightage_pct": 15,
                "chapter": "Mental Ability",
                "ncert_chapter": "General Aptitude",
            },
        ],
    },
    "Physics (Domain)": {
        "icon": "⚛️",
        "color": "#6366f1",
        "chapters": 22,
        "weightage_pct": 30,
        "topics": JEE_SUBJECTS["Physics"]["topics"],
    },
    "Chemistry (Domain)": {
        "icon": "🧪",
        "color": "#10b981",
        "chapters": 28,
        "weightage_pct": 30,
        "topics": JEE_SUBJECTS["Chemistry"]["topics"],
    },
    "Mathematics (Domain)": {
        "icon": "📐",
        "color": "#f59e0b",
        "chapters": 16,
        "weightage_pct": 30,
        "topics": JEE_SUBJECTS["Mathematics"]["topics"],
    },
    "Biology (Domain)": {
        "icon": "🌿",
        "color": "#22c55e",
        "chapters": 38,
        "weightage_pct": 30,
        "topics": NEET_BIOLOGY["topics"],
    },

    # ── Humanities / Arts Domain Subjects ────────────────────────────────────
    "History": {
        "icon": "🏺",
        "color": "#b45309",
        "chapters": 16,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Ancient India",
                "priority": "HIGH",
                "subtopics": ["Harappan Civilization", "Vedic Age", "Mauryan Empire", "Gupta Period"],
                "weightage_pct": 20,
                "chapter": "Early Societies",
                "ncert_chapter": "NCERT Themes in World History Class 11, Chapter 1-4",
            },
            {
                "name": "Medieval India",
                "priority": "HIGH",
                "subtopics": ["Delhi Sultanate", "Mughal Empire", "Bhakti & Sufi Movements", "Regional Powers"],
                "weightage_pct": 20,
                "chapter": "Medieval Societies",
                "ncert_chapter": "NCERT Themes in Indian History Class 12, Chapter 5-9",
            },
            {
                "name": "Modern India",
                "priority": "HIGH",
                "subtopics": ["British Colonialism", "1857 Revolt", "National Movement", "Partition & Independence"],
                "weightage_pct": 25,
                "chapter": "Colonialism and the Countryside",
                "ncert_chapter": "NCERT Themes in Indian History Class 12, Chapter 10-15",
            },
            {
                "name": "World History",
                "priority": "MED",
                "subtopics": ["Industrial Revolution", "World Wars", "Cold War", "Decolonization"],
                "weightage_pct": 15,
                "chapter": "Work, Life and Leisure",
                "ncert_chapter": "NCERT Themes in World History Class 11",
            },
            {
                "name": "Sources & Historiography",
                "priority": "MED",
                "subtopics": ["Types of Sources", "Archaeological Evidence", "Inscriptions", "Literary Sources"],
                "weightage_pct": 10,
                "chapter": "Bricks, Beads and Bones",
                "ncert_chapter": "NCERT Themes in Indian History Class 12, Chapter 1",
            },
            {
                "name": "Cultural History",
                "priority": "LOW",
                "subtopics": ["Art & Architecture", "Religion & Philosophy", "Language & Literature"],
                "weightage_pct": 10,
                "chapter": "Bhakti–Sufi Traditions",
                "ncert_chapter": "NCERT Themes in Indian History Class 12, Chapter 6",
            },
        ],
    },
    "Geography": {
        "icon": "🌍",
        "color": "#0891b2",
        "chapters": 14,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Physical Geography",
                "priority": "HIGH",
                "subtopics": ["Interior of Earth", "Rocks & Minerals", "Landforms", "Climate & Weather"],
                "weightage_pct": 20,
                "chapter": "The Origin and Evolution of the Earth",
                "ncert_chapter": "NCERT Fundamentals of Physical Geography Class 11",
            },
            {
                "name": "India's Physical Environment",
                "priority": "HIGH",
                "subtopics": ["Physiographic Divisions", "Drainage System", "Climate", "Natural Vegetation"],
                "weightage_pct": 20,
                "chapter": "India — Location",
                "ncert_chapter": "NCERT India Physical Environment Class 11",
            },
            {
                "name": "Human Geography",
                "priority": "HIGH",
                "subtopics": ["Population", "Migration", "Human Development", "Settlements"],
                "weightage_pct": 20,
                "chapter": "The World Population",
                "ncert_chapter": "NCERT Fundamentals of Human Geography Class 12",
            },
            {
                "name": "India — People and Economy",
                "priority": "HIGH",
                "subtopics": ["Population Distribution", "Agriculture", "Industries", "Transport"],
                "weightage_pct": 20,
                "chapter": "Population — Distribution, Density, Growth",
                "ncert_chapter": "NCERT India People and Economy Class 12",
            },
            {
                "name": "Map Work & Practical",
                "priority": "MED",
                "subtopics": ["Topographical Maps", "Aerial Photos", "Satellite Images", "Graphs"],
                "weightage_pct": 10,
                "chapter": "Practical Work in Geography",
                "ncert_chapter": "NCERT Practical Work in Geography Class 11",
            },
            {
                "name": "Resources",
                "priority": "MED",
                "subtopics": ["Water Resources", "Mineral Resources", "Energy Resources", "Land Resources"],
                "weightage_pct": 10,
                "chapter": "Water Resources",
                "ncert_chapter": "NCERT India People and Economy Class 12",
            },
        ],
    },
    "Political Science": {
        "icon": "🏛️",
        "color": "#7c3aed",
        "chapters": 18,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Indian Constitution",
                "priority": "HIGH",
                "subtopics": ["Preamble", "Fundamental Rights", "DPSP", "Constitutional Amendments"],
                "weightage_pct": 20,
                "chapter": "Constitution — Why and How?",
                "ncert_chapter": "NCERT Political Theory Class 11, Chapter 1",
            },
            {
                "name": "Indian Government",
                "priority": "HIGH",
                "subtopics": ["Parliament", "President", "Prime Minister", "Judiciary"],
                "weightage_pct": 20,
                "chapter": "Legislature",
                "ncert_chapter": "NCERT Indian Constitution at Work Class 11",
            },
            {
                "name": "Electoral Politics & Democracy",
                "priority": "HIGH",
                "subtopics": ["Elections", "Parties", "Federalism", "Local Self-Government"],
                "weightage_pct": 20,
                "chapter": "Electoral Politics",
                "ncert_chapter": "NCERT Politics in India since Independence Class 12",
            },
            {
                "name": "International Relations",
                "priority": "MED",
                "subtopics": ["Cold War Era", "Post-Cold War", "India's Foreign Policy", "UN"],
                "weightage_pct": 15,
                "chapter": "The Cold War Era",
                "ncert_chapter": "NCERT Contemporary World Politics Class 12",
            },
            {
                "name": "Political Theory",
                "priority": "MED",
                "subtopics": ["Freedom", "Equality", "Justice", "Rights", "Nationality & Secularism"],
                "weightage_pct": 15,
                "chapter": "Freedom",
                "ncert_chapter": "NCERT Political Theory Class 11",
            },
            {
                "name": "Globalisation & Security",
                "priority": "LOW",
                "subtopics": ["Globalization", "Security Challenges", "Environment & Politics"],
                "weightage_pct": 10,
                "chapter": "Environment and Natural Resources",
                "ncert_chapter": "NCERT Contemporary World Politics Class 12",
            },
        ],
    },
    "Economics": {
        "icon": "📊",
        "color": "#059669",
        "chapters": 12,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Microeconomics",
                "priority": "HIGH",
                "subtopics": ["Demand & Supply", "Elasticity", "Market Structures", "Consumer Theory"],
                "weightage_pct": 25,
                "chapter": "Introduction to Microeconomics",
                "ncert_chapter": "NCERT Introductory Microeconomics Class 11",
            },
            {
                "name": "Macroeconomics",
                "priority": "HIGH",
                "subtopics": ["National Income", "Money & Banking", "Government Budget", "Balance of Payments"],
                "weightage_pct": 25,
                "chapter": "Introduction to Macroeconomics",
                "ncert_chapter": "NCERT Introductory Macroeconomics Class 12",
            },
            {
                "name": "Indian Economic Development",
                "priority": "HIGH",
                "subtopics": ["Pre-Independence Economy", "Planning", "Liberalisation 1991", "Current Challenges"],
                "weightage_pct": 20,
                "chapter": "Indian Economy on the Eve of Independence",
                "ncert_chapter": "NCERT Indian Economic Development Class 11",
            },
            {
                "name": "Statistics for Economics",
                "priority": "MED",
                "subtopics": ["Collection of Data", "Organisation", "Central Tendency", "Index Numbers"],
                "weightage_pct": 15,
                "chapter": "Collection of Data",
                "ncert_chapter": "NCERT Statistics for Economics Class 11",
            },
            {
                "name": "Development Economics",
                "priority": "MED",
                "subtopics": ["Human Capital", "Rural Development", "Infrastructure", "Environment"],
                "weightage_pct": 15,
                "chapter": "Development Experience of India",
                "ncert_chapter": "NCERT Indian Economic Development Class 11",
            },
        ],
    },
    "Accountancy": {
        "icon": "📒",
        "color": "#1d4ed8",
        "chapters": 15,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Fundamentals of Accounting",
                "priority": "HIGH",
                "subtopics": ["Accounting Equation", "Journal", "Ledger", "Trial Balance"],
                "weightage_pct": 20,
                "chapter": "Introduction to Accounting",
                "ncert_chapter": "NCERT Accountancy Class 11, Chapter 1-4",
            },
            {
                "name": "Financial Statements",
                "priority": "HIGH",
                "subtopics": ["Trading Account", "P&L Account", "Balance Sheet", "Adjustments"],
                "weightage_pct": 20,
                "chapter": "Financial Statements",
                "ncert_chapter": "NCERT Accountancy Class 11, Chapter 9-10",
            },
            {
                "name": "Partnership Accounts",
                "priority": "HIGH",
                "subtopics": ["Partnership Deed", "Admission", "Retirement", "Dissolution"],
                "weightage_pct": 20,
                "chapter": "Accounting for Partnership",
                "ncert_chapter": "NCERT Accountancy Class 12 Part 1",
            },
            {
                "name": "Company Accounts",
                "priority": "HIGH",
                "subtopics": ["Share Capital", "Debentures", "Final Accounts of Companies", "Cash Flow"],
                "weightage_pct": 20,
                "chapter": "Accounting for Share Capital",
                "ncert_chapter": "NCERT Accountancy Class 12 Part 1",
            },
            {
                "name": "Analysis of Financial Statements",
                "priority": "MED",
                "subtopics": ["Comparative Statements", "Common Size", "Ratios", "Cash Flow Statement"],
                "weightage_pct": 20,
                "chapter": "Financial Statements Analysis",
                "ncert_chapter": "NCERT Accountancy Class 12 Part 2",
            },
        ],
    },
    "Business Studies": {
        "icon": "💼",
        "color": "#b91c1c",
        "chapters": 12,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Nature & Forms of Business",
                "priority": "HIGH",
                "subtopics": ["Business Activities", "Sole Proprietorship", "Partnership", "Companies"],
                "weightage_pct": 20,
                "chapter": "Nature and Purpose of Business",
                "ncert_chapter": "NCERT Business Studies Class 11, Chapter 1-2",
            },
            {
                "name": "Management",
                "priority": "HIGH",
                "subtopics": ["Functions of Management", "Planning", "Organising", "Staffing", "Directing"],
                "weightage_pct": 25,
                "chapter": "Nature and Significance of Management",
                "ncert_chapter": "NCERT Business Studies Class 12 Part 1",
            },
            {
                "name": "Finance & Marketing",
                "priority": "HIGH",
                "subtopics": ["Financial Management", "Capital Structure", "Marketing Mix", "Consumer Protection"],
                "weightage_pct": 20,
                "chapter": "Financial Management",
                "ncert_chapter": "NCERT Business Studies Class 12 Part 2",
            },
            {
                "name": "Business Environment",
                "priority": "MED",
                "subtopics": ["Economic Environment", "LPG Reforms", "Government Policy", "GST"],
                "weightage_pct": 15,
                "chapter": "Business Environment",
                "ncert_chapter": "NCERT Business Studies Class 11, Chapter 3",
            },
            {
                "name": "Entrepreneurship",
                "priority": "MED",
                "subtopics": ["Concept", "Startup Ecosystem", "Business Plan", "Social Enterprise"],
                "weightage_pct": 10,
                "chapter": "Entrepreneurship",
                "ncert_chapter": "NCERT Business Studies Class 12",
            },
            {
                "name": "e-Business & Emerging Trends",
                "priority": "LOW",
                "subtopics": ["e-Commerce", "Digital Payments", "Outsourcing", "Green Business"],
                "weightage_pct": 10,
                "chapter": "Emerging Modes of Business",
                "ncert_chapter": "NCERT Business Studies Class 11, Chapter 5",
            },
        ],
    },
    "Sociology": {
        "icon": "👥",
        "color": "#dc2626",
        "chapters": 10,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Introducing Sociology",
                "priority": "HIGH",
                "subtopics": ["Social Structure", "Sociological Perspectives", "Research Methods"],
                "weightage_pct": 20,
                "chapter": "Sociology and Society",
                "ncert_chapter": "NCERT Introducing Sociology Class 11, Chapter 1",
            },
            {
                "name": "Indian Society",
                "priority": "HIGH",
                "subtopics": ["Caste", "Class", "Tribe", "Gender", "Religion & Communalism"],
                "weightage_pct": 20,
                "chapter": "Understanding Society",
                "ncert_chapter": "NCERT Understanding Society Class 11",
            },
            {
                "name": "Social Change & Development",
                "priority": "HIGH",
                "subtopics": ["Modernisation", "Globalisation", "Social Movements", "Urbanisation"],
                "weightage_pct": 20,
                "chapter": "Social Change and Social Order",
                "ncert_chapter": "NCERT Social Change and Development in India Class 12",
            },
            {
                "name": "Demographic Structure",
                "priority": "MED",
                "subtopics": ["Population Size", "Literacy", "Health", "Gender Composition"],
                "weightage_pct": 15,
                "chapter": "Demographic Structure of the Indian Society",
                "ncert_chapter": "NCERT Indian Society Class 12, Chapter 2",
            },
            {
                "name": "Challenges of Nation Building",
                "priority": "MED",
                "subtopics": ["Partition", "Integration of States", "Linguistic Diversity", "Regional Identity"],
                "weightage_pct": 15,
                "chapter": "The Challenges of Cultural Diversity",
                "ncert_chapter": "NCERT Indian Society Class 12, Chapter 6",
            },
            {
                "name": "Rural & Agrarian Society",
                "priority": "LOW",
                "subtopics": ["Land Reforms", "Green Revolution", "Panchayati Raj", "Farmer Movements"],
                "weightage_pct": 10,
                "chapter": "Structural Change",
                "ncert_chapter": "NCERT Social Change and Development in India Class 12, Chapter 3",
            },
        ],
    },
    "Psychology": {
        "icon": "🧠",
        "color": "#9333ea",
        "chapters": 10,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Nature & Scope of Psychology",
                "priority": "HIGH",
                "subtopics": ["Branches", "Research Methods", "Psychological Tests"],
                "weightage_pct": 15,
                "chapter": "What is Psychology?",
                "ncert_chapter": "NCERT Psychology Class 11, Chapter 1",
            },
            {
                "name": "Human Development",
                "priority": "HIGH",
                "subtopics": ["Prenatal Development", "Childhood", "Adolescence", "Old Age"],
                "weightage_pct": 15,
                "chapter": "Human Development",
                "ncert_chapter": "NCERT Psychology Class 11, Chapter 4",
            },
            {
                "name": "Cognition & Intelligence",
                "priority": "HIGH",
                "subtopics": ["Attention & Perception", "Memory", "Thinking", "Intelligence Theories"],
                "weightage_pct": 20,
                "chapter": "Attention and Perception",
                "ncert_chapter": "NCERT Psychology Class 11, Chapter 5-7",
            },
            {
                "name": "Personality & Self",
                "priority": "HIGH",
                "subtopics": ["Theories of Personality", "Self-concept", "Freud", "Humanistic Approach"],
                "weightage_pct": 15,
                "chapter": "Self and Personality",
                "ncert_chapter": "NCERT Psychology Class 12, Chapter 2",
            },
            {
                "name": "Psychological Disorders",
                "priority": "MED",
                "subtopics": ["Anxiety Disorders", "Depression", "Schizophrenia", "Therapy"],
                "weightage_pct": 15,
                "chapter": "Psychological Disorders",
                "ncert_chapter": "NCERT Psychology Class 12, Chapter 4",
            },
            {
                "name": "Social Behaviour",
                "priority": "MED",
                "subtopics": ["Attitudes", "Prejudice", "Group Dynamics", "Leadership"],
                "weightage_pct": 10,
                "chapter": "Attitude and Social Cognition",
                "ncert_chapter": "NCERT Psychology Class 12, Chapter 6",
            },
            {
                "name": "Motivation & Emotion",
                "priority": "LOW",
                "subtopics": ["Maslow's Hierarchy", "Intrinsic vs Extrinsic", "Emotions", "Stress"],
                "weightage_pct": 10,
                "chapter": "Motivation and Emotion",
                "ncert_chapter": "NCERT Psychology Class 11, Chapter 9",
            },
        ],
    },
    "Legal Studies": {
        "icon": "⚖️",
        "color": "#475569",
        "chapters": 10,
        "weightage_pct": 30,
        "topics": [
            {
                "name": "Nature of Law",
                "priority": "HIGH",
                "subtopics": ["Sources of Law", "Constitutional Law", "Statutory Law", "Common Law"],
                "weightage_pct": 20,
                "chapter": "Nature of Law",
                "ncert_chapter": "NCERT Legal Studies Class 11, Chapter 1",
            },
            {
                "name": "Indian Constitution",
                "priority": "HIGH",
                "subtopics": ["Preamble", "Fundamental Rights", "Directive Principles", "Amendments"],
                "weightage_pct": 25,
                "chapter": "Constitution as the Supreme Law",
                "ncert_chapter": "NCERT Legal Studies Class 11, Chapter 2",
            },
            {
                "name": "Judiciary System",
                "priority": "HIGH",
                "subtopics": ["Supreme Court", "High Courts", "District Courts", "Lok Adalat", "PIL"],
                "weightage_pct": 20,
                "chapter": "Judiciary",
                "ncert_chapter": "NCERT Legal Studies Class 12, Chapter 3",
            },
            {
                "name": "Criminal & Civil Law",
                "priority": "MED",
                "subtopics": ["IPC", "CrPC", "CPC", "Evidence Act"],
                "weightage_pct": 20,
                "chapter": "Criminal Justice System",
                "ncert_chapter": "NCERT Legal Studies Class 12",
            },
            {
                "name": "International Law",
                "priority": "LOW",
                "subtopics": ["United Nations", "International Courts", "Human Rights Law", "Treaties"],
                "weightage_pct": 15,
                "chapter": "International Law",
                "ncert_chapter": "NCERT Legal Studies Class 12",
            },
        ],
    },
}  # end CUET_SUBJECTS

# ── SAT (Digital SAT) Subjects ───────────────────────────────────────────────
SAT_SUBJECTS = {
    "Reading & Writing": {
        "chapters": 4,          # 4 domain areas: Information & Ideas, Craft & Structure, Expression of Ideas, Standard English
        "weightage_pct": 50,
        "topics": [
            {"name": "Reading Comprehension", "priority": "high", "ncert_chapter": "Information and Ideas"},
            {"name": "Vocabulary in Context", "priority": "high", "ncert_chapter": "Craft and Structure"},
            {"name": "Standard English Conventions", "priority": "high", "ncert_chapter": "Grammar and Usage"},
            {"name": "Expression of Ideas", "priority": "medium", "ncert_chapter": "Rhetorical Skills"},
            {"name": "Rhetorical Synthesis", "priority": "medium", "ncert_chapter": "Argument and Evidence"},
            {"name": "Text Structure and Purpose", "priority": "medium", "ncert_chapter": "Textual Analysis"},
        ],
    },
    "Mathematics": {
        "chapters": 4,          # 4 domain areas: Algebra, Advanced Math, Data Analysis, Geometry/Trig
        "weightage_pct": 50,
        "topics": [
            {"name": "Algebra", "priority": "high", "ncert_chapter": "Linear equations, inequalities, functions (~35%)"},
            {"name": "Advanced Mathematics", "priority": "high", "ncert_chapter": "Quadratic, exponential, polynomial (~35%)"},
            {"name": "Problem Solving & Data Analysis", "priority": "medium", "ncert_chapter": "Ratios, percentages, statistics (~15%)"},
            {"name": "Geometry & Trigonometry", "priority": "medium", "ncert_chapter": "Coordinate geometry, circles, trig ratios (~15%)"},
        ],
    },
}

# ── IELTS (Academic) Subjects ─────────────────────────────────────────────────
IELTS_SUBJECTS = {
    "Listening": {
        "chapters": 4,   # 4 recording types: social/everyday, training, monologue, academic lecture
        "weightage_pct": 25,
        "topics": [
            {"name": "Everyday Conversation", "priority": "high", "ncert_chapter": "Social and everyday contexts"},
            {"name": "Academic Discussion", "priority": "high", "ncert_chapter": "Academic and professional contexts"},
            {"name": "Lecture Comprehension", "priority": "high", "ncert_chapter": "Monologue — academic topic"},
            {"name": "MCQ & Form Completion", "priority": "medium", "ncert_chapter": "Question types: MCQ, gap-fill"},
        ],
    },
    "Reading": {
        "chapters": 3,   # 3 academic passages per test
        "weightage_pct": 25,
        "topics": [
            {"name": "Matching Headings", "priority": "high", "ncert_chapter": "Academic passages — identifying main ideas"},
            {"name": "True / False / Not Given", "priority": "high", "ncert_chapter": "Factual accuracy identification"},
            {"name": "Sentence Completion", "priority": "high", "ncert_chapter": "Specific facts and details"},
            {"name": "Multiple Choice", "priority": "medium", "ncert_chapter": "Comprehension and inference"},
            {"name": "Summary Completion", "priority": "medium", "ncert_chapter": "Paraphrasing and key ideas"},
        ],
    },
    "Vocabulary & Grammar": {
        "chapters": 3,   # 3 skill areas: vocabulary, grammar, paraphrasing
        "weightage_pct": 50,  # Writing + Speaking combined band
        "topics": [
            {"name": "Academic Vocabulary", "priority": "high", "ncert_chapter": "Word meanings and collocations"},
            {"name": "Grammar in Context", "priority": "medium", "ncert_chapter": "Tense, voice, reported speech"},
            {"name": "Paraphrasing", "priority": "medium", "ncert_chapter": "Synonyms and restatement"},
        ],
    },
}

# ── TOEFL iBT Subjects ────────────────────────────────────────────────────────
TOEFL_SUBJECTS = {
    "Reading": {
        "chapters": 2,   # 2 academic passages per TOEFL iBT Reading section
        "weightage_pct": 30,
        "topics": [
            {"name": "Reading Comprehension", "priority": "high", "ncert_chapter": "Academic passages — 20 questions, 35 min"},
            {"name": "Vocabulary in Context", "priority": "high", "ncert_chapter": "Word choice in academic texts"},
            {"name": "Inference Questions", "priority": "high", "ncert_chapter": "Implied meaning and author purpose"},
            {"name": "Sentence Insertion", "priority": "medium", "ncert_chapter": "Paragraph and text structure"},
            {"name": "Prose Summary", "priority": "medium", "ncert_chapter": "Main ideas and supporting details"},
        ],
    },
    "Listening": {
        "chapters": 5,   # 3 lectures + 2 conversations per TOEFL iBT Listening section
        "weightage_pct": 30,
        "topics": [
            {"name": "Lecture Comprehension", "priority": "high", "ncert_chapter": "Academic lectures — main ideas and details"},
            {"name": "Campus Conversations", "priority": "high", "ncert_chapter": "Service encounters and office hours"},
            {"name": "Purpose and Attitude", "priority": "medium", "ncert_chapter": "Speaker intent and tone"},
            {"name": "Connecting Information", "priority": "medium", "ncert_chapter": "Relationships between ideas"},
        ],
    },
    "Integrated Skills": {
        "chapters": 2,   # 2 writing tasks: Integrated Writing + Academic Discussion
        "weightage_pct": 40,
        "topics": [
            {"name": "Integrated Writing Task", "priority": "high", "ncert_chapter": "Synthesise reading and lecture"},
            {"name": "Academic Discussion Writing", "priority": "high", "ncert_chapter": "Contribute to an online discussion"},
            {"name": "Note-taking Strategy", "priority": "medium", "ncert_chapter": "Key points, supporting details"},
        ],
    },
}

EXAM_SUBJECTS_MAP = {
    "jee_main": JEE_SUBJECTS,
    "neet_ug": {
        "Physics": NEET_PHYSICS,
        "Chemistry": NEET_CHEMISTRY,
        "Biology": NEET_BIOLOGY,
    },
    "cuet_ug": CUET_SUBJECTS,
    "sat":      SAT_SUBJECTS,
    "ielts":    IELTS_SUBJECTS,
    "toefl_ibt": TOEFL_SUBJECTS,
}

# Exam date targets
EXAM_DATES = {
    "jee_main":  (2027, 1, 15),   # JEE Session 1 (approximate)
    "neet_ug":   (2027, 5, 4),    # NEET UG (approximate)
    "cuet_ug":   (2027, 5, 20),   # CUET UG (approximate)
    "sat":       (2027, 3, 8),    # SAT March test date (approximate)
    "ielts":     (2027, 2, 15),   # IELTS — multiple dates, approximate
    "toefl_ibt": (2027, 2, 22),   # TOEFL iBT — multiple dates, approximate
}


# ── Supabase helper ────────────────────────────────────────────────────────────

def _get_db():
    """Return the primary Supabase client — all exam prep tables live there."""
    from app.services.auth_service import admin_client  # noqa: PLC0415
    return admin_client


def _get_exam_attempts(exam_type: str, user_id: str) -> list[dict]:
    """
    Return this user's practice attempts for the given exam only, each
    annotated with its question's subject via the exam_prep_attempts ->
    exam_prep_questions foreign key.

    exam_prep_attempts has no exam_type/subject column of its own (only
    question_id), so without this join, "questions attempted" is either a
    lifetime count across every exam the user has ever practiced (dashboard)
    or unavailable per-subject at all (subject cards) — both were true
    before this fix, which is why e.g. Physics, Chemistry and Maths in the
    Structured Learning tab all showed Phase 3 as "Done" simultaneously as
    soon as the student practiced any ONE of them, in any exam.
    """
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_attempts")
            .select("id, question_id, is_correct, exam_prep_questions!inner(subject, exam_type)")
            .eq("user_id", user_id)
            .eq("exam_prep_questions.exam_type", exam_type)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        _log.warning("exam_prep.attempts_fetch_failed", error=str(exc))
        return []


def _get_seen_question_ids(exam_type: str, user_id: str) -> set[str]:
    """Question IDs this user has already attempted, anywhere, for this exam."""
    if not user_id:
        return set()
    return {a["question_id"] for a in _get_exam_attempts(exam_type, user_id) if a.get("question_id")}


def _pick_questions(rows: list[dict], limit: int, seen_ids: set[str]) -> list[dict]:
    """
    Randomly select up to `limit` rows, preferring ones this user hasn't
    attempted yet. Falls back to the full pool (including seen rows) once
    there aren't enough unseen ones left to fill the request, so a student
    who has exhausted a subject's bank keeps practicing instead of getting a
    short or empty set.
    """
    if not rows:
        return []
    unseen = [r for r in rows if r.get("id") not in seen_ids]
    pool = unseen if len(unseen) >= min(limit, len(rows)) else rows
    pool = list(pool)
    random.shuffle(pool)
    return pool[:limit]


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_dashboard(exam_type: str, user_id: str) -> dict:
    """Return dashboard stats for the given exam."""
    db = _get_db()

    total_questions = 0
    try:
        q_result = (
            db.table("exam_prep_questions")
            .select("id", count="exact")
            .eq("exam_type", exam_type)
            .eq("status", "published")
            .execute()
        )
        total_questions = q_result.count or 0
    except Exception as exc:
        _log.warning("exam_prep.dashboard.q_fetch", error=str(exc))

    # Scoped to this exam only — previously this counted the user's attempts
    # across every exam they'd ever practiced (see _get_exam_attempts docstring).
    attempts = _get_exam_attempts(exam_type, user_id)

    correct_count = sum(1 for a in attempts if a.get("is_correct"))
    accuracy_pct = round(correct_count / len(attempts) * 100) if attempts else 0

    # Weeks to exam (per exam type)
    weeks_to_exam = 28
    try:
        edate = EXAM_DATES.get(exam_type, (2027, 1, 15))
        exam_date = datetime(edate[0], edate[1], edate[2], tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_days = (exam_date - now).days
        weeks_to_exam = max(0, math.ceil(delta_days / 7))
    except Exception:
        pass

    subjects_map = EXAM_SUBJECTS_MAP.get(exam_type, {})
    total_topics = sum(len(s.get("topics", [])) for s in subjects_map.values())

    return {
        "exam_type": exam_type,
        "weeks_to_exam": weeks_to_exam,
        "total_questions": total_questions,
        "questions_attempted": len(attempts),
        "accuracy_pct": accuracy_pct,
        "correct_count": correct_count,
        "total_topics": total_topics,
        "subjects_count": len(subjects_map),
    }


# ── Subjects ────────────────────────────────────────────────────────────────────

def get_subjects(exam_type: str, user_id: str) -> list[dict]:
    """Return subject cards with question counts and progress."""
    db = _get_db()
    subjects_map = EXAM_SUBJECTS_MAP.get(exam_type, {})

    # Fetch per-subject question counts from DB.
    #
    # Keyset-paginated (not a single unpaginated .execute()) — Supabase/
    # PostgREST silently caps an unpaginated select at 1000 rows. CUET UG
    # alone has passed that (1,279 published rows as of writing), which
    # made this undercount every subject whose rows fell past the cutoff —
    # confirmed live: get_subjects() reported far fewer than the true count
    # after a large ingestion batch, while a direct DB count showed the
    # real total. See admin_import_bulk's dedup fetch for the same fix.
    q_by_subject: dict[str, int] = {}
    try:
        last_id = None
        page_size = 1000
        while True:
            query = (
                db.table("exam_prep_questions")
                .select("id, subject")
                .eq("exam_type", exam_type)
                .eq("status", "published")
                .order("id")
                .limit(page_size)
            )
            if last_id is not None:
                query = query.gt("id", last_id)
            page = query.execute().data or []
            if not page:
                break
            for row in page:
                s = row["subject"]
                q_by_subject[s] = q_by_subject.get(s, 0) + 1
            if len(page) < page_size:
                break
            last_id = page[-1]["id"]
    except Exception as exc:
        _log.warning("exam_prep.subjects.q_fetch", error=str(exc))

    # Per-subject attempted count, so the Structured Learning tab's "Practice
    # Questions" phase can be marked done independently for each subject
    # instead of all subjects going "Done" together off one exam-wide count.
    attempted_by_subject: dict[str, int] = {}
    for attempt in _get_exam_attempts(exam_type, user_id):
        s = (attempt.get("exam_prep_questions") or {}).get("subject")
        if s:
            attempted_by_subject[s] = attempted_by_subject.get(s, 0) + 1

    exam_targets = _EXAM_SUBJECT_TARGETS.get(exam_type, {})

    result = []
    for name, data in subjects_map.items():
        target = exam_targets.get(
            name,
            _CUET_DEFAULT_PER_SUBJECT if exam_type == "cuet_ug" else max(10, 90 // max(1, len(subjects_map))),
        )
        result.append({
            "name": name,
            "icon": data.get("icon", "📚"),
            "color": data.get("color", "#6366f1"),
            "chapters": data.get("chapters", 0),
            "weightage_pct": data.get("weightage_pct", 0),
            "topic_count": len(data.get("topics", [])),
            "question_count": q_by_subject.get(name, 0),
            # How many questions a single Practice/Simulated Test session
            # tries to pull for this subject. When question_count is at or
            # below this, the session already shows the entire bank every
            # time — there's no rotation headroom left to fix with more
            # exclusion logic, only with more written questions.
            "target_per_session": target,
            "thin_bank": 0 < q_by_subject.get(name, 0) <= target,
            "no_content": q_by_subject.get(name, 0) == 0,
            "questions_attempted": attempted_by_subject.get(name, 0),
        })
    return result


# ── Topics ──────────────────────────────────────────────────────────────────────

def get_topics(exam_type: str, subject: str) -> list[dict]:
    """Return topic priority cards for a subject."""
    subjects_map = EXAM_SUBJECTS_MAP.get(exam_type, {})
    subject_data = subjects_map.get(subject)
    if not subject_data:
        return []
    return subject_data.get("topics", [])


# ── Questions ───────────────────────────────────────────────────────────────────

def get_questions(
    exam_type: str,
    subject: Optional[str],
    topic: Optional[str],
    limit: int = 20,
    user_id: Optional[str] = None,
) -> list[dict]:
    """
    Return published questions from DB, randomized and excluding ones this
    user has already attempted (falling back to the full pool once every
    matching question has been seen). Without user_id, just shuffles.

    Previously this was a bare `LIMIT N` with no ORDER BY, so the same fixed
    subset was returned in the same order on every single visit — a subject
    with 100+ questions would only ever show the first 20 of them, forever.
    """
    db = _get_db()
    try:
        query = (
            db.table("exam_prep_questions")
            .select(_QUESTION_FIELDS)
            .eq("exam_type", exam_type)
            .eq("status", "published")
        )
        if subject:
            query = query.eq("subject", subject)
        if topic:
            # Use ILIKE for flexible matching — handles case differences and partial matches.
            # e.g. "Reading Comprehension" matches "SAT Reading Comprehension" and vice versa.
            # Falls back to all subject questions if no exact/partial match exists.
            query = query.ilike("topic", f"%{topic}%")
        rows = query.limit(2000).execute().data or []
        seen_ids = _get_seen_question_ids(exam_type, user_id) if user_id else set()
        return _pick_questions(rows, limit, seen_ids)
    except Exception as exc:
        _log.warning("exam_prep.questions.fetch", error=str(exc))
        return []


def get_question_by_id(question_id: str) -> dict:
    """Return a single published question with full details."""
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_questions")
            .select("*")
            .eq("id", question_id)
            .eq("status", "published")
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(404, "Question not found")
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch question") from exc


# ── Submit answer ───────────────────────────────────────────────────────────────

def submit_answer(
    user_id: str,
    question_id: str,
    selected_option: Optional[str],
    time_taken_seconds: int = 0,
) -> dict:
    """Record a practice attempt and return instant feedback."""
    db = _get_db()

    # Get question
    try:
        q_result = (
            db.table("exam_prep_questions")
            .select("correct_option, detailed_explanation, solution_steps_json, formula_used, ncert_reference, marks, negative_marks, subject, topic")
            .eq("id", question_id)
            .single()
            .execute()
        )
        question = q_result.data
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch question for scoring") from exc

    if not question:
        raise HTTPException(404, "Question not found")

    correct_option = question["correct_option"]
    is_correct = selected_option == correct_option if selected_option else False
    marks = float(question.get("marks") or 4)
    negative_marks = float(question.get("negative_marks") or 1)

    if selected_option is None:
        marks_awarded = 0.0
    elif is_correct:
        marks_awarded = marks
    else:
        marks_awarded = -negative_marks

    # Save attempt
    try:
        db.table("exam_prep_attempts").insert({
            "user_id": user_id,
            "question_id": question_id,
            "selected_option": selected_option,
            "is_correct": is_correct,
            "time_taken_seconds": time_taken_seconds,
        }).execute()
    except Exception as exc:
        _log.warning("exam_prep.submit_answer.save_failed", error=str(exc))

    return {
        "is_correct": is_correct,
        "correct_option": correct_option,
        "marks_awarded": marks_awarded,
        "explanation": question.get("detailed_explanation", ""),
        "solution_steps": question.get("solution_steps_json") or [],
        "formula_used": question.get("formula_used", ""),
        "ncert_reference": question.get("ncert_reference", ""),
        # subject/topic — the frontend's "Revise Weak Topics" study-plan phase
        # groups incorrect answers by these to build its topic list. Without
        # them here, that feature silently never had anything to show.
        "subject": question.get("subject", ""),
        "topic": question.get("topic", ""),
    }


# ── Simulated tests ─────────────────────────────────────────────────────────────

# Per-subject question targets for a simulated test, per NTA 2024-2026 official
# patterns. NEET's Biology entry covers Botany+Zoology combined (real DB rows
# are all tagged "Biology" — matching EXAM_SUBJECTS_MAP/get_subjects() above —
# there is no separate Botany/Zoology subject, so this is 2x a single-subject
# share rather than two 45-question subjects).
#   JEE Main: 25/subject x 3 = 75 total
#   NEET UG:  45 + 45 + 90 = 180 total
_EXAM_SUBJECT_TARGETS: dict[str, dict[str, int]] = {
    "jee_main": {"Physics": 25, "Chemistry": 25, "Mathematics": 25},
    "neet_ug": {"Physics": 45, "Chemistry": 45, "Biology": 90},
    "sat": {"Reading & Writing": 49, "Mathematics": 49},
    "ielts": {"Listening": 27, "Reading": 27, "Vocabulary & Grammar": 27},
    "toefl_ibt": {"Reading": 16, "Listening": 16, "Integrated Skills": 16},
}
_CUET_DEFAULT_PER_SUBJECT = 40

_QUESTION_FIELDS = (
    "id, subject, chapter, topic, subtopic, question_text, "
    "options_json, correct_option, difficulty, marks, negative_marks, "
    "estimated_time_seconds, ncert_reference, formula_used, source_type"
)


def start_simulated_test(
    user_id: str,
    exam_type: str,
    grade: str,
    subjects: Optional[list[str]] = None,
) -> dict:
    """
    Start a new simulated test session. Picks published questions from DB,
    randomized and excluding ones this user has already attempted anywhere in
    this exam (falling back to the full pool once exhausted) — previously
    this was a bare per-subject LIMIT with no ORDER BY, so every attempt
    served the identical fixed set of questions.

    Returns the full question objects (not just IDs) so the caller can
    render the test directly from this response instead of re-fetching —
    that re-fetch used to be a *second*, independent, equally-unordered
    query, which only happened to line up with this function's own
    question_ids (used later for scoring) because neither side randomized.
    Randomizing one without the other would have made them diverge and
    broken scoring, so both now go through the same selection here.

    `subjects` lets the caller override the default subject list (used by
    CUET, where the student picks their own subject combination); other
    exams use the fixed per-subject targets in _EXAM_SUBJECT_TARGETS.
    """
    db = _get_db()

    if subjects:
        subject_targets = {s: _CUET_DEFAULT_PER_SUBJECT for s in subjects}
    else:
        subject_targets = _EXAM_SUBJECT_TARGETS.get(exam_type)
        if not subject_targets:
            subjects_map = EXAM_SUBJECTS_MAP.get(exam_type, {})
            per_subject = max(10, 90 // max(1, len(subjects_map)))
            subject_targets = {s: per_subject for s in subjects_map}

    seen_ids = _get_seen_question_ids(exam_type, user_id)
    questions: list[dict] = []
    try:
        for subj, target in subject_targets.items():
            rows = (
                db.table("exam_prep_questions")
                .select(_QUESTION_FIELDS)
                .eq("exam_type", exam_type)
                .eq("subject", subj)
                .eq("status", "published")
                .limit(2000)
                .execute()
            ).data or []
            questions.extend(_pick_questions(rows, target, seen_ids))
    except Exception as exc:
        _log.warning("exam_prep.start_test.q_fetch", error=str(exc))

    question_ids = [q["id"] for q in questions]
    total_questions = len(question_ids)

    # Create test record
    try:
        test_data = {
            "user_id": user_id,
            "exam_type": exam_type,
            "grade": grade,
            "question_ids": question_ids,
            "status": "active",
            "duration_minutes": 180,
            "total_questions": total_questions,
        }
        result = db.table("exam_prep_simulated_tests").insert(test_data).execute()
        test = result.data[0] if result.data else test_data
    except Exception as exc:
        raise HTTPException(500, "Failed to create test session") from exc

    return {
        "test_id": test.get("id", ""),
        "exam_type": exam_type,
        "grade": grade,
        "question_ids": question_ids,
        "questions": questions,
        "total_questions": total_questions,
        "duration_minutes": 180,
        "status": "active",
        "started_at": test.get("started_at", ""),
        "message": (
            "No questions available yet. Admin needs to prewarm the question bank."
            if total_questions == 0
            else f"Test started with {total_questions} questions. Good luck!"
        ),
    }


def submit_simulated_test(
    test_id: str,
    user_id: str,
    answers: list[dict],  # [{question_id, selected_option, time_taken_seconds}]
    time_spent_seconds: int = 0,
) -> dict:
    """
    Score a simulated test and return results.
    Score normalization: score_normalized = min(100, score_pct)
    No result percentage ever exceeds 100.
    """
    db = _get_db()

    # Fetch test
    try:
        t_result = (
            db.table("exam_prep_simulated_tests")
            .select("*")
            .eq("id", test_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        test = t_result.data
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch test") from exc

    if not test:
        raise HTTPException(404, "Test not found")
    if test["status"] != "active":
        raise HTTPException(400, "Test already submitted")

    question_ids = test.get("question_ids", [])
    if not question_ids:
        # No questions — return empty result
        result_data = _build_empty_result(test_id, exam_type=test["exam_type"])
        _save_test_result(db, test_id, result_data, time_spent_seconds)
        return result_data

    # Fetch questions for scoring
    try:
        q_result = (
            db.table("exam_prep_questions")
            .select("id, subject, topic, correct_option, marks, negative_marks")
            .in_("id", question_ids)
            .execute()
        )
        questions = {q["id"]: q for q in (q_result.data or [])}
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch questions for scoring") from exc

    # Build answer map
    answer_map = {a["question_id"]: a for a in answers}

    # Score
    total_marks = 0.0
    max_marks = 0.0
    correct = 0
    wrong = 0
    skipped = 0
    subject_scores: dict[str, dict] = {}
    topic_accuracy: dict[str, list[bool]] = {}
    answer_rows = []

    for qid in question_ids:
        q = questions.get(qid)
        if not q:
            continue
        subj = q.get("subject", "Unknown")
        topic = q.get("topic", "Unknown")
        marks = float(q.get("marks") or 4)
        neg = float(q.get("negative_marks") or 1)
        max_marks += marks

        if subj not in subject_scores:
            subject_scores[subj] = {"correct": 0, "wrong": 0, "skipped": 0, "score": 0.0, "max_score": 0.0}
        subject_scores[subj]["max_score"] += marks

        ans = answer_map.get(qid)
        selected = ans.get("selected_option") if ans else None
        time_taken = ans.get("time_taken_seconds", 0) if ans else 0

        if selected is None:
            skipped += 1
            marks_awarded = 0.0
            is_correct = False
            subject_scores[subj]["skipped"] += 1
        elif selected == q["correct_option"]:
            correct += 1
            marks_awarded = marks
            is_correct = True
            total_marks += marks
            subject_scores[subj]["correct"] += 1
            subject_scores[subj]["score"] += marks
        else:
            wrong += 1
            marks_awarded = -neg
            is_correct = False
            total_marks += marks_awarded
            subject_scores[subj]["wrong"] += 1
            subject_scores[subj]["score"] += marks_awarded

        topic_accuracy.setdefault(topic, []).append(is_correct)
        answer_rows.append({
            "test_id": test_id,
            "question_id": qid,
            "selected_option": selected,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "time_taken_seconds": time_taken,
        })

    # Compute normalized score (0-100, never > 100)
    score_pct = (total_marks / max_marks * 100) if max_marks > 0 else 0
    score_normalized = min(100.0, max(0.0, round(score_pct, 2)))

    # Topic accuracy map
    topic_accuracy_pct = {
        t: round(sum(vals) / len(vals) * 100) if vals else 0
        for t, vals in topic_accuracy.items()
    }

    # Weak topics = accuracy < 50%
    weak_topics = [t for t, acc in topic_accuracy_pct.items() if acc < 50]

    # Save answers
    if answer_rows:
        try:
            db.table("exam_prep_simulated_test_answers").insert(answer_rows).execute()
        except Exception as exc:
            _log.warning("exam_prep.submit_test.save_answers", error=str(exc))

    # Build result
    result_data = {
        "test_id": test_id,
        "exam_type": test["exam_type"],
        "score_raw": round(total_marks, 1),
        "score_normalized": score_normalized,
        "max_marks": round(max_marks, 1),
        "total_questions": len(question_ids),
        "attempted": correct + wrong,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "time_spent_seconds": time_spent_seconds,
        "subject_scores": subject_scores,
        "topic_accuracy": topic_accuracy_pct,
        "weak_topics": weak_topics,
        "ai_recommendations": _build_recommendations(weak_topics, score_normalized),
    }
    _save_test_result(db, test_id, result_data, time_spent_seconds)
    return result_data


def _build_empty_result(test_id: str, exam_type: str) -> dict:
    return {
        "test_id": test_id,
        "exam_type": exam_type,
        "score_raw": 0,
        "score_normalized": 0.0,
        "max_marks": 0,
        "total_questions": 0,
        "attempted": 0,
        "correct": 0,
        "wrong": 0,
        "skipped": 0,
        "time_spent_seconds": 0,
        "subject_scores": {},
        "topic_accuracy": {},
        "weak_topics": [],
        "ai_recommendations": ["Prewarm the question bank to generate practice questions."],
    }


def _build_recommendations(weak_topics: list[str], score_pct: float) -> list[str]:
    recs = []
    if score_pct < 40:
        recs.append("Focus on fundamentals — revise NCERT concepts before attempting more tests.")
    elif score_pct < 60:
        recs.append("Good effort! Work through solved examples to strengthen your weak areas.")
    else:
        recs.append("Strong performance! Focus on speed and accuracy for harder questions.")
    for t in weak_topics[:3]:
        recs.append(f"Revise '{t}' — your accuracy is below 50% in this topic.")
    return recs


def _save_test_result(db, test_id: str, result: dict, time_spent_seconds: int) -> None:
    # score_raw column is int — must cast Python float to int to avoid PostgREST type rejection
    raw_score = result.get("score_raw")
    safe_score_raw = int(round(raw_score)) if raw_score is not None else None

    try:
        db.table("exam_prep_simulated_tests").update({
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "score_raw": safe_score_raw,
            "score_normalized": float(result.get("score_normalized") or 0),
            "subject_scores": result.get("subject_scores"),
            "topic_accuracy": result.get("topic_accuracy"),
            "weak_topics": result.get("weak_topics", []),
            "time_spent_seconds": int(time_spent_seconds or 0),
            "attempted": int(result.get("attempted") or 0),
            "correct": int(result.get("correct") or 0),
            "wrong": int(result.get("wrong") or 0),
            "ai_recommendations": result.get("ai_recommendations"),
        }).eq("id", test_id).execute()
        _log.info("exam_prep.save_test_result.ok", test_id=test_id,
                  score_raw=safe_score_raw, status="submitted")
    except Exception as exc:
        _log.warning("exam_prep.save_test_result.failed", test_id=test_id, error=str(exc))


def get_test_result(test_id: str, user_id: str) -> dict:
    """Return a completed test result."""
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_simulated_tests")
            .select("*")
            .eq("id", test_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(404, "Test not found")
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch test result") from exc


def get_sim_test_history(user_id: str, exam_type: str, limit: int = 10) -> list:
    """Return the last N completed simulated tests for a user + exam.

    Each entry includes:
      id, exam_type, score_raw, score_normalized, correct, wrong,
      total_questions, time_spent_seconds, submitted_at

    Ordered newest first. Only returns status='submitted' rows.
    """
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_simulated_tests")
            .select(
                "id, exam_type, score_raw, score_normalized, correct, wrong, "
                "total_questions, attempted, time_spent_seconds, submitted_at"
            )
            .eq("user_id", user_id)
            .eq("exam_type", exam_type)
            .eq("status", "submitted")
            .order("submitted_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = result.data or []
        # Normalise: ensure numeric types
        for row in rows:
            row["score_normalized"] = float(row["score_normalized"] or 0)
            row["score_raw"] = row["score_raw"]  # may be None for old rows
            row["correct"] = row.get("correct") or 0
            row["wrong"] = row.get("wrong") or 0
            row["total_questions"] = row.get("total_questions") or 0
        return rows
    except Exception as exc:
        _log.warning("exam_prep.sim_history.failed", error=str(exc))
        return []


# ── Admin: Prewarm jobs ─────────────────────────────────────────────────────────

def get_question_bank_status(exam_type: Optional[str] = None) -> dict:
    """Return question bank stats for admin dashboard."""
    db = _get_db()
    rows: list[dict] = []
    try:
        # Keyset-paginated — see get_subjects() for why an unpaginated
        # .execute() silently caps at 1000 rows on Supabase/PostgREST,
        # which the whole-table case here (exam_type=None) hits easily.
        last_id = None
        page_size = 1000
        while True:
            query = (
                db.table("exam_prep_questions")
                .select("id, exam_type, subject, status")
                .order("id")
                .limit(page_size)
            )
            if exam_type:
                query = query.eq("exam_type", exam_type)
            if last_id is not None:
                query = query.gt("id", last_id)
            page = query.execute().data or []
            if not page:
                break
            rows.extend(page)
            if len(page) < page_size:
                break
            last_id = page[-1]["id"]
    except Exception as exc:
        _log.warning("exam_prep.qb_status.failed", error=str(exc))
        rows = []

    stats: dict = {}
    for row in rows:
        et = row["exam_type"]
        subj = row["subject"]
        status = row["status"]
        if et not in stats:
            stats[et] = {}
        if subj not in stats[et]:
            stats[et][subj] = {"total": 0, "published": 0, "draft": 0, "archived": 0}
        stats[et][subj]["total"] += 1
        stats[et][subj][status] = stats[et][subj].get(status, 0) + 1

    try:
        jobs = (
            db.table("exam_prep_prewarm_jobs")
            .select("id, status, exam_type, subject, questions_generated, created_at")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        recent_jobs = jobs.data or []
    except Exception:
        recent_jobs = []

    return {"stats": stats, "recent_jobs": recent_jobs}


def create_prewarm_job(
    triggered_by: str,
    exam_type: str,
    grade: str,
    subject: Optional[str],
    chapter: Optional[str],
    topic: Optional[str],
    difficulty_mix: Optional[dict],
    question_count: int,
    publish_mode: str,
) -> dict:
    """Create a prewarm job record (admin only). Actual generation runs async."""
    db = _get_db()

    if question_count < 1 or question_count > 100:
        raise HTTPException(400, "question_count must be between 1 and 100")
    if publish_mode not in ("draft", "auto_publish"):
        raise HTTPException(400, "publish_mode must be 'draft' or 'auto_publish'")

    # Mapping-integrity check: `subject` must be a key the app actually reads
    # (EXAM_SUBJECTS_MAP[exam_type]) or generated questions are silently
    # unreachable to students regardless of how valid the content itself is.
    if subject:
        valid_subjects = set(EXAM_SUBJECTS_MAP.get(exam_type, {}).keys())
        if valid_subjects and subject not in valid_subjects:
            raise HTTPException(
                400,
                f"Unknown subject '{subject}' for exam_type '{exam_type}'. "
                f"Must be one of: {sorted(valid_subjects)}",
            )

    job_data = {
        "triggered_by": triggered_by,
        "exam_type": exam_type,
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "difficulty_mix": difficulty_mix or {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        "question_count": question_count,
        "publish_mode": publish_mode,
        "status": "pending",
    }
    try:
        result = db.table("exam_prep_prewarm_jobs").insert(job_data).execute()
        job = result.data[0] if result.data else job_data
    except Exception as exc:
        raise HTTPException(500, "Failed to create prewarm job") from exc

    return job


def get_prewarm_job(job_id: str) -> dict:
    """Get prewarm job status."""
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_prewarm_jobs")
            .select("*")
            .eq("id", job_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(404, "Job not found")
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch job") from exc


def run_prewarm_job(job_id: str) -> dict:
    """
    Execute a prewarm job synchronously using the configured LLM.
    Generates MCQ questions with validation.
    Draft only by default; auto_publish only if strict validation passes.
    """
    db = _get_db()

    # Mark running
    try:
        db.table("exam_prep_prewarm_jobs").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()
        job_result = db.table("exam_prep_prewarm_jobs").select("*").eq("id", job_id).single().execute()
        job = job_result.data
    except Exception as exc:
        raise HTTPException(500, "Failed to start prewarm job") from exc

    if not job:
        raise HTTPException(404, "Job not found")

    from app.services.openai_service import ask_llm, get_effective_settings  # noqa: PLC0415

    exam_type = job["exam_type"]
    grade = job["grade"]
    subject = job.get("subject", "Physics")
    chapter = job.get("chapter", "")
    topic = job.get("topic", "")
    question_count = job.get("question_count", 10)
    publish_mode = job.get("publish_mode", "draft")
    diff_mix = job.get("difficulty_mix") or {"easy": 0.3, "medium": 0.5, "hard": 0.2}

    exam_label = {"jee_main": "JEE Main", "neet_ug": "NEET UG", "cuet_ug": "CUET UG"}.get(exam_type, exam_type)
    chapter_str = chapter or topic or subject
    topic_str = topic or ""
    easy_pct = round(diff_mix.get("easy", 0.3) * 100)
    med_pct = round(diff_mix.get("medium", 0.5) * 100)
    hard_pct = round(diff_mix.get("hard", 0.2) * 100)

    # Build difficulty distribution string
    diff_parts = []
    if easy_pct > 0:
        diff_parts.append(f"{easy_pct}% Easy")
    if med_pct > 0:
        diff_parts.append(f"{med_pct}% Moderate")
    if hard_pct > 0:
        diff_parts.append(f"{hard_pct}% Difficult")
    diff_distribution = ", ".join(diff_parts)

    system_prompt = f"""You are an expert assessment designer and senior question setter for Indian competitive examinations.

Your responsibility is to generate ORIGINAL, HIGH-QUALITY, COMPLETE multiple-choice questions.

═══ ABSOLUTE REQUIREMENTS ═══

A. EVERY QUESTION MUST HAVE ALL 4 OPTIONS (A, B, C, D)
   - If you omit ANY option, the question is INVALID and will be REJECTED.
   - All 4 options must be populated with meaningful content.
   - Options must be distinct — no two options can be the same value.

B. EVERY QUESTION MUST HAVE A COMPLETE EXPLANATION
   - Explain WHY the correct answer is correct (show the full working).
   - Explain WHY each wrong option is incorrect.

C. NO DUPLICATE CONCEPTS
   - Each question in the batch MUST test a DIFFERENT concept/formula/idea.
   - Do NOT ask two questions that test the same formula with different numbers.
   - Variety is mandatory: mix different sub-topics within {subject}.

D. DIFFICULTY CALIBRATION for {exam_label}:
   - Easy: Direct single-concept, one formula, answer in ≤2 steps.
   - Moderate: Two-step reasoning, one small calculation, conceptual application.
   - Hard: Multi-concept integration, non-obvious approach, requires analysis.
   - A "hard" question is NOT just a calculation with big numbers — it requires genuine analytical thinking.

E. EXAM STANDARD for {exam_label}:
   {"- Each question solvable in 60–90 seconds. - Moderate calculation, no excessive arithmetic. - Tests conceptual understanding + application." if "JEE Main" in exam_label else "- NCERT-centric. - Biology: exact NCERT terminology. - Physics/Chemistry: conceptual clarity over tricks." if "NEET" in exam_label else "- Conceptual focus. - NCERT-based. - Minimal lengthy calculations."}

F. OPTION QUALITY:
   - 3 plausible distractors — wrong answers that arise from common mistakes.
   - Randomize which letter (A/B/C/D) is correct across the batch.
   - No "All of the above" / "None of the above".

G. SELF-CHECK before outputting each question:
   ✓ Does it have exactly 4 non-empty options?
   ✓ Is the correct answer definitely correct?
   ✓ Is the explanation complete?
   ✓ Is the concept unique in this batch?
   ✓ Are units correct?
   ✓ Is all numerical data consistent (no contradictions)?
   If any ✓ is NO → rewrite before outputting.

Difficulty distribution: {diff_distribution}"""

    user_prompt = f"""Generate {question_count} original, high-quality, COMPLETE MCQ questions for:

Target Exam: {exam_label}
Subject: {subject}
Chapter/Area: {chapter_str}
Topic: {topic_str or subject}
Grade: {grade}
Difficulty Mix: {diff_distribution}

CRITICAL: Each question MUST include all 4 answer options. Questions without all 4 options are invalid.
CRITICAL: No two questions should test the same concept or formula. Test different sub-topics.

EXAMPLE of correct output format (follow this EXACTLY):
[
  {{
    "question_text": "A particle moves in a circle of radius 0.5 m. If it completes 2 revolutions per second, its centripetal acceleration is:",
    "options": {{"A": "4π² m/s²", "B": "2π² m/s²", "C": "8π² m/s²", "D": "π² m/s²"}},
    "correct_option": "C",
    "detailed_explanation": "Centripetal acceleration a = ω²r. Angular velocity ω = 2πn = 2π×2 = 4π rad/s. Therefore a = (4π)² × 0.5 = 16π² × 0.5 = 8π² m/s².",
    "why_others_wrong": "A: Uses ω = 2π instead of 4π. B: Arithmetic error — halved without justification. D: Forgot to square ω.",
    "solution_steps": ["ω = 2πn = 4π rad/s", "a = ω²r = (4π)² × 0.5", "a = 16π² × 0.5 = 8π² m/s²"],
    "formula_used": "a = ω²r, ω = 2πn",
    "ncert_reference": "NCERT Class 11, Chapter 5 — Laws of Motion",
    "difficulty": "medium",
    "topic": "Circular Motion",
    "subtopic": "Centripetal Acceleration",
    "bloom_level": "Apply",
    "concept_tested": "Centripetal acceleration from angular frequency",
    "estimated_time_seconds": 75,
    "common_mistake": "Students forget to square ω or use frequency instead of angular velocity.",
    "quality_score": 94
  }}
]

Now generate {question_count} questions following the EXACT same format. Each must test a DIFFERENT concept.
Return ONLY the JSON array, nothing else."""

    settings = get_effective_settings()
    generated_count = 0
    validated_count = 0
    published_count = 0
    errors = []

    import json as _json  # noqa: PLC0415

    # ── Batch generation to avoid LLM timeouts ─────────────────────────────────
    # The expert prompt is complex — limit to 5 questions per API call.
    # For larger counts, make multiple calls and merge results.
    BATCH_SIZE = 5
    remaining = question_count
    batch_num = 0

    while remaining > 0:
        batch_count = min(BATCH_SIZE, remaining)
        remaining -= batch_count
        batch_num += 1

        # Adjust user prompt for this batch
        batch_user_prompt = user_prompt.replace(
            f"Generate {question_count} original",
            f"Generate {batch_count} original",
        ).replace(
            f"Generate {question_count} high-quality",
            f"Generate {batch_count} high-quality",
        )
        # Replace the JSON count in the prompt too
        batch_system = system_prompt.replace(
            "generate ORIGINAL, HIGH-QUALITY multiple-choice questions",
            "generate ORIGINAL, HIGH-QUALITY multiple-choice questions",
        )

        try:
            raw = ask_llm(
                system_prompt=batch_system,
                user_prompt=batch_user_prompt.replace(
                    f"Generate {question_count} original",
                    f"Generate {batch_count} original",
                ),
                username=job.get("triggered_by", "admin"),
                feature="exam_prep_prewarm",
            )

            # ── Robust JSON extraction ────────────────────────────────────────
            # Strip markdown code fences
            raw = raw.strip()
            if "```" in raw:
                # Extract content between first ``` and last ```
                parts = raw.split("```")
                # parts[1] is the code block content (may start with "json\n")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            # Extract just the JSON array — find first [ and last ]
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                raw = raw[start : end + 1]

            # Attempt parse with fallback cleanup
            try:
                batch_questions = _json.loads(raw)
            except _json.JSONDecodeError as je:
                # Log the exact position to aid debugging
                _log.warning(
                    "exam_prep.prewarm.json_parse_error",
                    batch=batch_num,
                    error=str(je),
                    snippet=raw[max(0, je.pos - 50): je.pos + 50] if hasattr(je, "pos") else "",
                )
                # Try stripping control characters and retry
                import re as _re  # noqa: PLC0415
                raw_clean = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
                batch_questions = _json.loads(raw_clean)

            if not isinstance(batch_questions, list):
                _log.warning("exam_prep.prewarm.batch_not_list", batch=batch_num)
                continue

            generated_count += len(batch_questions)

            # Validate and insert each question
            for q in batch_questions:
                validation_errors = _validate_question(q)
                validation_score = max(0.0, 1.0 - len(validation_errors) * 0.2)
                is_valid = len(validation_errors) == 0

                opts = q.get("options", {})
                options_list = [{"key": k, "text": v} for k, v in opts.items() if k in ("A", "B", "C", "D")]

                status = "draft"
                if publish_mode == "auto_publish" and is_valid:
                    status = "published"

                row = {
                    "exam_type": exam_type,
                    "grade": grade,
                    "subject": subject,
                    "chapter": chapter or q.get("topic", topic),
                    "topic": q.get("topic", topic),
                    "subtopic": q.get("subtopic", ""),
                    "question_text": q.get("question_text", ""),
                    "options_json": options_list,
                    "correct_option": q.get("correct_option", ""),
                    "detailed_explanation": q.get("detailed_explanation", ""),
                    "solution_steps_json": q.get("solution_steps") or [],
                    "formula_used": q.get("formula_used", ""),
                    "ncert_reference": q.get("ncert_reference", ""),
                    "difficulty": q.get("difficulty", "medium"),
                    "source_type": "llm_generated",
                    "status": status,
                    "validation_score": round(validation_score, 2),
                    "validation_errors": validation_errors,
                    "prewarm_job_id": job_id,
                }

                if is_valid:
                    validated_count += 1

                try:
                    db.table("exam_prep_questions").insert(row).execute()
                    if status == "published":
                        published_count += 1
                except Exception as insert_exc:
                    errors.append(str(insert_exc)[:100])

        except Exception as exc:
            err_str = str(exc)
            _log.warning(
                "exam_prep.prewarm.batch_failed",
                batch=batch_num,
                error=err_str[:200],
            )
            errors.append(f"Batch {batch_num}: {err_str[:100]}")
            # Continue with next batch rather than failing the whole job
            continue

    # If no questions were generated at all, mark as failed
    if generated_count == 0 and errors:
        error_msg = "; ".join(errors[:3])
        db.table("exam_prep_prewarm_jobs").update({
            "status": "failed",
            "error_message": error_msg,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "questions_generated": 0,
            "questions_validated": 0,
        }).eq("id", job_id).execute()
        raise HTTPException(500, f"Prewarm failed: {error_msg}")

    # Mark completed
    db.table("exam_prep_prewarm_jobs").update({
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "questions_generated": generated_count,
        "questions_validated": validated_count,
        "questions_published": published_count,
        "provider": settings.get("provider", "openai"),
        "model": settings.get("groq_model") or settings.get("gemini_model") or "gpt-4.1-nano",
    }).eq("id", job_id).execute()

    return {
        "job_id": job_id,
        "status": "completed",
        "questions_generated": generated_count,
        "questions_validated": validated_count,
        "questions_published": published_count,
        "errors": errors[:5],
    }


# ── Admin: question management ─────────────────────────────────────────────────

def get_admin_questions(
    exam_type: Optional[str] = None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Return questions for admin review (all statuses)."""
    db = _get_db()
    try:
        query = db.table("exam_prep_questions").select(
            "id, exam_type, grade, subject, chapter, topic, question_text, "
            "correct_option, difficulty, status, validation_score, validation_errors, "
            "source_type, created_at"
        )
        if exam_type:
            query = query.eq("exam_type", exam_type)
        if subject:
            query = query.eq("subject", subject)
        if status:
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as exc:
        _log.warning("exam_prep.admin_questions.fetch", error=str(exc))
        return []


def update_question(question_id: str, updates: dict) -> dict:
    """Update a question (admin only)."""
    db = _get_db()
    allowed = {
        "question_text", "options_json", "correct_option", "detailed_explanation",
        "solution_steps_json", "formula_used", "ncert_reference", "difficulty",
        "topic", "subtopic", "chapter", "status",
    }
    safe_updates = {k: v for k, v in updates.items() if k in allowed}
    if not safe_updates:
        raise HTTPException(400, "No valid fields to update")
    safe_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        result = db.table("exam_prep_questions").update(safe_updates).eq("id", question_id).execute()
        return result.data[0] if result.data else {"id": question_id, **safe_updates}
    except Exception as exc:
        raise HTTPException(500, "Failed to update question") from exc


def publish_question(question_id: str) -> dict:
    """Publish a draft question (admin only)."""
    return update_question(question_id, {"status": "published"})


def archive_question(question_id: str) -> dict:
    """Archive a question (admin only)."""
    return update_question(question_id, {"status": "archived"})


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate_question(q: dict) -> list[str]:
    """Validate a generated question. Returns list of error strings."""
    errors = []
    opts = q.get("options", {})
    keys = set(opts.keys()) if isinstance(opts, dict) else set()

    if not q.get("question_text", "").strip():
        errors.append("Empty question text")
    if len(keys) != 4 or keys != {"A", "B", "C", "D"}:
        errors.append("Must have exactly 4 options: A, B, C, D")
    if q.get("correct_option") not in ("A", "B", "C", "D"):
        errors.append("correct_option must be A, B, C, or D")
    if not q.get("detailed_explanation", "").strip():
        errors.append("Missing detailed explanation")
    if q.get("difficulty") not in ("easy", "medium", "hard"):
        errors.append("difficulty must be easy, medium, or hard")
    if not q.get("topic", "").strip():
        errors.append("Missing topic")

    # Check for duplicate options
    if isinstance(opts, dict):
        values = [v.strip().lower() for v in opts.values() if v]
        if len(values) != len(set(values)):
            errors.append("Duplicate option values detected")

    # Check answer not leaked in question text
    qt = q.get("question_text", "").lower()
    correct_key = q.get("correct_option", "")
    correct_val = opts.get(correct_key, "").lower() if isinstance(opts, dict) else ""
    if correct_val and len(correct_val) > 5 and correct_val in qt:
        errors.append("Correct answer may be leaked in question text")

    return errors
