"""
formula_sheets.py  —  GET /api/student/formula-sheets
─────────────────────────────────────────────────────────────────────────────
Chapter-wise formula reference with freemium access control.

Freemium model:
  FREE_TIER — full syllabus structure visible; first FREE_PREVIEW_PER_CHAPTER
              formulas per chapter unlocked; rest locked (name+expression only).
              Premium fields (solution_steps, memory_tip) always locked for free.
  PAID — full access to all formulas including solved examples, memory tips.

Feature key: Feature.FORMULA_SHEET_PREMIUM controls premium sections.
The page itself is always accessible — only premium fields are gated.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.services.auth_service import require_student, admin_client
from app.services.feature_authorization_service import Feature, get_feature_summary
from app.routes.parent_dashboard_v2 import _safe_query

router = APIRouter()
_log = logging.getLogger("likhapoha.formula_sheets")

TABLE = "formula_sheets"
FREE_PREVIEW_PER_CHAPTER = 3   # Number of formulas unlocked per chapter for Free Tier


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_chapters(rows: list[dict], has_premium: bool) -> list[dict]:
    """
    Group formula rows into chapter → topic → formulas structure.
    Apply freemium locking: first FREE_PREVIEW_PER_CHAPTER per chapter are previews.
    """
    chapter_map: dict[str, dict] = {}  # chapter_name → {"order", "topics": {topic → [rows]}}

    for row in rows:
        ch = row.get("chapter") or "General"
        ch_order = row.get("chapter_order") or 0
        topic = row.get("topic") or row.get("section_title") or "General"

        if ch not in chapter_map:
            chapter_map[ch] = {"order": ch_order, "topics": {}}
        if topic not in chapter_map[ch]["topics"]:
            chapter_map[ch]["topics"][topic] = []
        chapter_map[ch]["topics"][topic].append(row)

    result = []
    for ch_name, ch_data in sorted(chapter_map.items(), key=lambda x: x[1]["order"]):
        ch_formulas_count = sum(len(v) for v in ch_data["topics"].values())
        topics_out = []
        chapter_preview_used = 0

        for topic_name, topic_rows in ch_data["topics"].items():
            formulas_out = []
            for row in sorted(topic_rows, key=lambda r: r.get("display_order", 0)):
                is_preview = chapter_preview_used < FREE_PREVIEW_PER_CHAPTER
                is_locked = not has_premium and not is_preview

                formula = {
                    "id":          str(row.get("id", "")),
                    "name":        row.get("formula_name", ""),
                    "expression":  row.get("expression", ""),
                    "description": row.get("explanation") or "",
                    "variables":   row.get("variables") or "",
                    "chapter":     ch_name,
                    "topic":       topic_name,
                    "difficulty":  row.get("difficulty") or "medium",
                    "tags":        row.get("tags") or [],
                    "locked":      is_locked,
                    "preview_allowed": is_preview or has_premium,
                    # Premium fields — only visible with premium access
                    "example":         row.get("example") if has_premium else None,
                    "solution_steps":  row.get("solution_steps") if has_premium else None,
                    "memory_tip":      row.get("memory_tip") if has_premium else None,
                    # Locked section labels for free users
                    "premium_sections": [] if has_premium else (
                        ["solved_example", "solution_steps", "memory_tip"] if is_preview
                        else ["all"]
                    ),
                }
                formulas_out.append(formula)
                if is_preview:
                    chapter_preview_used += 1

            topics_out.append({"topic_name": topic_name, "formulas": formulas_out})

        result.append({
            "chapter_id":    ch_name.lower().replace(" ", "_"),
            "chapter_name":  ch_name,
            "chapter_order": ch_data["order"],
            "total_formulas": ch_formulas_count,
            "unlocked_count": min(FREE_PREVIEW_PER_CHAPTER, ch_formulas_count) if not has_premium else ch_formulas_count,
            "locked":        not has_premium and ch_formulas_count > FREE_PREVIEW_PER_CHAPTER,
            "topics":        topics_out,
        })

    return result


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/formula-sheets")
def get_formula_sheets(
    grade:   Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    student=Depends(require_student),
):
    """
    Return CBSE formula reference grouped by chapter.
    Freemium: Free Tier gets preview formulas per chapter, premium sections locked.
    """
    profile  = student["profile"]
    uid = profile["id"]
    eff_grade = (grade or profile.get("grade", "Grade 9")).strip()

    # Validate grade
    valid_grades = {f"Grade {i}" for i in range(5, 13)}
    if eff_grade not in valid_grades:
        return {
            "success": False,
            "available": False,
            "message": f"Invalid grade '{eff_grade}'. Supported: Grade 5 to Grade 12.",
            "chapters": [],
        }

    # Feature access
    feat = get_feature_summary(uid)
    has_premium = feat.get("features", {}).get(Feature.FORMULA_SHEET_PREMIUM, {}).get("allowed", False)

    # Fetch formulas
    def _query():
        q = (
            admin_client.table(TABLE)
            .select("id, formula_name, expression, explanation, variables, example, solution_steps, memory_tip, chapter, topic, section_title, display_order, chapter_order, difficulty, tags, active")
            .eq("grade", eff_grade)
            .eq("active", True)
            .order("chapter_order", desc=False)
            .order("display_order", desc=False)
        )
        if subject:
            q = q.eq("subject", subject.strip())
        if chapter:
            q = q.eq("chapter", chapter.strip())
        return q.execute()

    rows, err = _safe_query(_query)

    # Graceful fallback if table doesn't exist yet
    if err and "schema cache" in str(err).lower():
        return {
            "success": True,
            "available": False,
            "grade": eff_grade,
            "subject": subject,
            "message": "Formula sheet database is being set up. Please check back soon.",
            "chapters": [],
            "subjects": [],
            "unlocked_count": 0,
            "total_count": 0,
            "premium_required": False,
        }

    if not rows:
        return {
            "success": True,
            "available": False,
            "grade": eff_grade,
            "subject": subject,
            "message": f"Formula sheet is not available for {eff_grade} yet.",
            "chapters": [],
            "subjects": [],
            "unlocked_count": 0,
            "total_count": 0,
            "premium_required": False,
        }

    # Available subjects for this grade
    subj_rows, _ = _safe_query(
        lambda: admin_client.table(TABLE)
        .select("subject")
        .eq("grade", eff_grade)
        .eq("active", True)
        .execute()
    )
    subjects = sorted(set(r["subject"] for r in subj_rows if r.get("subject")))

    # Build chapters with freemium logic
    chapters = _build_chapters(rows, has_premium)
    total_count = len(rows)
    unlocked_count = total_count if has_premium else sum(
        min(FREE_PREVIEW_PER_CHAPTER, ch["total_formulas"]) for ch in chapters
    )

    return {
        "success":        True,
        "available":      True,
        "grade":          eff_grade,
        "subject":        subject,
        "subjects":       subjects,
        "has_premium":    has_premium,
        "premium_required": not has_premium,
        "unlocked_count": unlocked_count,
        "total_count":    total_count,
        "chapters":       chapters,
        "upgrade_message": None if has_premium else "Upgrade to unlock solved examples, memory tips and the full formula library.",
    }
