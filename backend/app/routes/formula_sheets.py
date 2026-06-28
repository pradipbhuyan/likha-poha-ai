"""
formula_sheets.py  —  GET /api/student/formula-sheets
─────────────────────────────────────────────────────────────────────────────
Returns CBSE formula reference content for a given grade and optional subject.
Content is stored in the formula_sheets table (seeded via seed_formula_sheets.py).

If the table does not exist yet, returns available=false gracefully.
Feature access: formula sheets are available to all tiers (Free + Paid).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.services.auth_service import require_student, admin_client
from app.routes.parent_dashboard_v2 import _safe_query

router = APIRouter()
_log = logging.getLogger("likhapoha.formula_sheets")

TABLE = "formula_sheets"


def _build_sections(rows: list[dict]) -> list[dict]:
    """Group formula rows into sections keyed by section_title."""
    sections: dict[str, list[dict]] = {}
    for row in rows:
        key = row.get("section_title", "General")
        sections.setdefault(key, []).append({
            "name":        row.get("formula_name", ""),
            "expression":  row.get("expression", ""),
            "explanation": row.get("explanation"),
            "example":     row.get("example"),
            "chapter":     row.get("chapter"),
        })
    return [{"title": k, "formulas": v} for k, v in sections.items()]


@router.get("/formula-sheets")
def get_formula_sheets(
    grade:   Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    student=Depends(require_student),
):
    """
    Return formula reference content for the student's grade.
    grade defaults to the student's own grade if not provided.
    """
    profile  = student["profile"]
    eff_grade = (grade or profile.get("grade", "Grade 9")).strip()

    def _query():
        q = (
            admin_client.table(TABLE)
            .select("section_title, formula_name, expression, explanation, example, chapter, display_order")
            .eq("grade", eff_grade)
            .eq("active", True)
            .order("display_order", desc=False)
        )
        if subject:
            q = q.eq("subject", subject.strip())
        if chapter:
            q = q.eq("chapter", chapter.strip())
        return q.execute()

    rows, err = _safe_query(_query)

    if err and "schema cache" in str(err).lower():
        return {
            "success":      True,
            "available":    False,
            "grade":        eff_grade,
            "subject":      subject,
            "message":      "Formula sheet database is being set up. Please check back soon.",
            "sections":     [],
            "subjects":     [],
        }

    if not rows:
        return {
            "success":   True,
            "available": False,
            "grade":     eff_grade,
            "subject":   subject,
            "message":   f"Formula sheet is not available for {eff_grade} yet.",
            "sections":  [],
            "subjects":  [],
        }

    # Build subject list for filter UI
    subj_rows, _ = _safe_query(
        lambda: admin_client.table(TABLE)
        .select("subject")
        .eq("grade", eff_grade)
        .eq("active", True)
        .execute()
    )
    subjects = sorted(set(r["subject"] for r in subj_rows if r.get("subject")))

    # Build chapter list for selected subject
    chapters: list[str] = []
    if subject:
        ch_rows, _ = _safe_query(
            lambda: admin_client.table(TABLE)
            .select("chapter")
            .eq("grade", eff_grade)
            .eq("subject", subject.strip())
            .eq("active", True)
            .execute()
        )
        chapters = sorted(set(r["chapter"] for r in ch_rows if r.get("chapter")))

    return {
        "success":  True,
        "available": True,
        "grade":    eff_grade,
        "subject":  subject,
        "chapter":  chapter,
        "subjects": subjects,
        "chapters": chapters,
        "sections": _build_sections(rows),
        "total":    len(rows),
    }
