"""
lesson_lab_service.py — Admin Lesson Experience Lab
─────────────────────────────────────────────────────────────────────────────
Provides read-only lesson data for the admin Lesson Experience Lab.

Safety rules:
  - NEVER writes to lesson_cache or any student data table
  - NEVER auto-publishes any content
  - NEVER exposes admin-only assets to non-admins
  - All LLM operations require explicit admin toggle, output is preview-only

Reuses existing logic from:
  - step_sequence_service  — formula/MCQ extraction, similarity scoring
  - lesson_repair_service  — section validation
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

_log = logging.getLogger("likhapoha.lesson_lab")

# ── Reuse extraction helpers from step_sequence_service ───────────────────────
from app.services.step_sequence_service import (
    _extract_formulas,
    _extract_mcqs,
    _word_count,
    audit_lesson_steps,
)

# ── Canonical section keys (mirrors lesson_repair_service) ───────────────────
CANONICAL_SECTIONS = [
    "introduction",
    "what you will learn",
    "simple explanation",
    "step-by-step breakdown",
    "worked example",
    "common mistake",
    "quick check question",
    "summary",
]

# Reading speed: words per minute (average for educational content)
_WPM = 180


def _estimate_minutes(text: str) -> int:
    wc = _word_count(text)
    return max(1, round(wc / _WPM))


def _extract_sections(raw_content: str) -> dict[str, str]:
    """
    Parse a lesson's raw markdown content into named sections.
    Heuristic: ## or ### headings split content into sections.
    Returns a dict mapping lowercased section name → content text.
    """
    sections: dict[str, str] = {}
    current_key = "introduction"
    current_lines: list[str] = []

    for line in raw_content.splitlines():
        heading_match = re.match(r"^#{1,3}\s+(.+)", line)
        if heading_match:
            # Save previous section
            if current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = heading_match.group(1).strip().lower()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _section_completeness(sections: dict[str, str]) -> int:
    """Score 0–100 based on how many canonical sections are present and non-empty."""
    if not sections:
        return 0
    hits = sum(
        1 for key in CANONICAL_SECTIONS
        if any(key in k for k in sections.keys()) and
           any(sections[k].strip() for k in sections if key in k)
    )
    return round((hits / len(CANONICAL_SECTIONS)) * 100)


def _extract_examples(text: str) -> list[str]:
    """Extract example paragraphs (lines containing 'for example', 'e.g.', 'consider')."""
    examples = []
    for line in text.splitlines():
        l = line.strip()
        if re.search(r"\bfor example\b|\be\.g\.\b|\bconsider\b|\bsuppose\b|\blet us\b", l, re.I):
            if len(l) > 20:
                examples.append(l[:200])
    return examples[:5]


def _normalize_step(
    step_index: int,
    step_title: str,
    raw_content: str,
    all_step_texts: list[str],
) -> dict[str, Any]:
    """
    Normalize a single lesson step into a rich structured dict.
    Reuses step_sequence_service functions — no duplication.
    """
    sections   = _extract_sections(raw_content)
    formulas   = _extract_formulas(raw_content)
    mcqs       = _extract_mcqs(raw_content)
    examples   = _extract_examples(raw_content)
    wc         = _word_count(raw_content)
    minutes    = _estimate_minutes(raw_content)
    completeness = _section_completeness(sections)

    # Per-step scores from audit engine
    from app.services.step_sequence_service import score_step  # noqa: PLC0415
    step_scores = score_step(step_index, raw_content, all_step_texts)

    # Extract summary text (last section that looks like a summary)
    summary_text = ""
    for key, val in sections.items():
        if "summary" in key or "recap" in key or "key" in key:
            summary_text = val[:500]
            break

    return {
        "step_number": step_index + 1,
        "step_title": step_title,
        "raw_content": raw_content,
        "normalized_sections": sections,
        "formulas": formulas[:10],
        "examples": examples,
        "mcqs": mcqs[:5],
        "summary": summary_text,
        "word_count": wc,
        "estimated_minutes": minutes,
        "completeness_score": completeness,
        "uniqueness_score": step_scores["step_uniqueness_score"],
        "depth_progression_score": step_scores["depth_progression_score"],
        "cross_step_repetition_score": step_scores["cross_step_repetition_score"],
        "overall_step_score": step_scores["overall_step_score"],
        "status": step_scores["status"],
        "issues": step_scores["issues"],
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_lesson_list(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return lesson metadata (no content) for the lab selector.

    Queries lesson_cache read-only.
    Returns deduplicated grades, subjects, chapters, and lesson stubs.
    """
    try:
        from app.services.grade_db_router import get_content_db, is_grade_1112  # noqa: PLC0415

        # All grades on the primary shard (Grades 5–10)
        PRIMARY_GRADES = [
            "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
        ]
        SECONDARY_GRADES = ["Grade 11", "Grade 12"]

        def _query_one_grade(db, g):
            """Query a single grade with subject/chapter filters — avoids row-limit truncation."""
            q = (db.table("lesson_cache")
                 .select("id, grade, subject, chapter, step_title, status")
                 .eq("status", "active")
                 .eq("grade", g))
            if subject:
                q = q.ilike("subject", f"%{subject}%")
            if chapter:
                q = q.ilike("chapter", f"%{chapter}%")
            r = q.order("subject").order("chapter").order("step_title").limit(500).execute()
            return r.data or []

        if grade:
            # Specific grade requested — single targeted query
            rows = _query_one_grade(get_content_db(grade), grade)
        else:
            # No grade filter — query every known grade individually to avoid
            # Supabase's 1000-row default limit truncating results
            rows = []
            primary_db = get_content_db("Grade 9")
            for g in PRIMARY_GRADES:
                try:
                    rows.extend(_query_one_grade(primary_db, g))
                except Exception:
                    pass
            # Grade 11/12 shard (separate DB if configured)
            try:
                secondary_db = get_content_db("Grade 11")
                for g in SECONDARY_GRADES:
                    rows.extend(_query_one_grade(secondary_db, g))
            except Exception:
                pass  # secondary shard not configured — silently skip

    except Exception as e:
        _log.warning("lesson_lab: DB unavailable — %s", e)
        rows = []

    # Aggregate metadata
    grades   = sorted(set(r["grade"]   for r in rows if r.get("grade")))
    subjects = sorted(set(r["subject"] for r in rows if r.get("subject")))
    chapters = sorted(set(r["chapter"] for r in rows if r.get("chapter")))

    # Group into lessons (grade + subject + chapter)
    lesson_map: dict[str, dict] = {}
    for row in rows:
        key = f"{row.get('grade')}|{row.get('subject')}|{row.get('chapter')}"
        if key not in lesson_map:
            lesson_map[key] = {
                "lesson_id": key,
                "grade": row.get("grade", ""),
                "subject": row.get("subject", ""),
                "chapter": row.get("chapter", ""),
                "steps": [],
            }
        lesson_map[key]["steps"].append({
            "db_id": row.get("id"),
            "step_title": row.get("step_title", ""),
        })

    return {
        "grades": grades,
        "subjects": subjects,
        "chapters": chapters,
        "lessons": list(lesson_map.values()),
        "total_lessons": len(lesson_map),
        "total_steps": len(rows),
    }


def get_lesson_detail(
    lesson_id: str,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return full normalized lesson data for a lesson_id.

    lesson_id is either a DB uuid or "Grade|Subject|Chapter" composite key.
    Read-only — never writes.
    """
    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415

        # If lesson_id contains "|" it is a composite key — skip UUID lookup
        # entirely to avoid Supabase "invalid input syntax for type uuid" errors.
        is_composite = "|" in lesson_id
        rows = []

        if not is_composite:
            db = get_content_db(grade or "Grade 9")
            resp = (db.table("lesson_cache")
                    .select("id, grade, subject, chapter, step_title, lesson_content, status")
                    .eq("id", lesson_id)
                    .execute())
            rows = resp.data or []

        if not rows:
            # Composite key "Grade|Subject|Chapter"
            parts = lesson_id.split("|")
            if len(parts) >= 3:
                g, s, c = parts[0], parts[1], "|".join(parts[2:])
                db2 = get_content_db(g)

                # ── Use the same cache_key logic as the live lesson page ──────
                # The live student lesson uses make_lesson_cache_key(board, grade,
                # subject, chapter, mode, step_title, teacher_persona="") to look
                # up the canonical active row. We replicate this exactly so the
                # Lab shows the same content the student sees.
                # Load canonical step order for sorting
                try:
                    from app.services.prewarm_service import get_lesson_steps_for_grade as _get_steps  # noqa: PLC0415
                    canonical_steps = _get_steps(g)
                except Exception:
                    canonical_steps = []

                def _step_sort_key(row):
                    """Sort by canonical step order; unknown steps go to the end."""
                    st = row.get("step_title", "")
                    try:
                        return canonical_steps.index(st)
                    except ValueError:
                        return 999

                try:
                    from app.services.lesson_cache_service import (  # noqa: PLC0415
                        get_cached_lesson,
                        make_lesson_cache_key,
                    )

                    board = "CBSE"
                    mode = "CBSE"

                    rows = []
                    for st in (canonical_steps or []):
                        cache_key = make_lesson_cache_key(
                            board=board, grade=g, subject=s,
                            chapter=c, mode=mode, step_title=st,
                            teacher_persona="",
                        )
                        cached = get_cached_lesson(cache_key, grade=g)
                        if cached and cached.get("lesson_content"):
                            rows.append({
                                "id": None,
                                "grade": g,
                                "subject": s,
                                "chapter": c,
                                "step_title": st,
                                "lesson_content": cached["lesson_content"],
                                "status": "active",
                            })
                except Exception as ck_err:
                    _log.warning("lesson_lab: cache_key lookup failed (%s), falling back to DB scan", ck_err)
                    rows = []

                # Fallback: direct DB scan if cache_key path failed or returned nothing
                if not rows:
                    def _db_scan(chapter_filter):
                        return (db2.table("lesson_cache")
                                .select("id, grade, subject, chapter, step_title, lesson_content, status, access_count")
                                .eq("grade", g).ilike("subject", f"%{s}%").ilike("chapter", chapter_filter)
                                .eq("status", "active")
                                .limit(500)
                                .execute()).data or []

                    # 1. Try EXACT chapter match first (avoids mixing Exemplar content)
                    raw_rows = _db_scan(c)

                    # 2. If no exact match, try fuzzy (strips "Chapter N:" prefix)
                    if not raw_rows:
                        core_chapter = re.sub(r"^chapter\s+\d+[:\s]+", "", c, flags=re.I).strip()
                        raw_rows = _db_scan(f"%{core_chapter}%")

                    def _content_quality(content: str) -> tuple:
                        heading_count = len(re.findall(r"^#{1,3}\s+", content, re.M))
                        word_count = len(content.split())
                        return (heading_count, word_count)

                    # Group by step_title, pick best-quality row per step
                    step_groups: dict[str, list] = {}
                    for row in raw_rows:
                        st = row.get("step_title", "")
                        step_groups.setdefault(st, []).append(row)

                    rows = []
                    for st, candidates in step_groups.items():
                        best = max(candidates, key=lambda r: _content_quality(r.get("lesson_content", "")))
                        rows.append(best)

                # Sort by canonical step order (not alphabetically)
                rows.sort(key=_step_sort_key)

    except Exception as e:
        _log.warning("lesson_lab: DB error fetching lesson — %s", e)
        return {"error": f"Could not fetch lesson: {str(e)[:200]}"}

    if not rows:
        return {"error": "Lesson not found."}

    # Resolve grade/subject/chapter from data
    g = grade or rows[0].get("grade", "")
    s = subject or rows[0].get("subject", "")
    c = chapter or rows[0].get("chapter", "")

    # All step texts for cross-step scoring
    all_texts = [r.get("lesson_content", "") for r in rows]

    # Normalize each step
    steps = []
    total_minutes = 0
    for i, row in enumerate(rows):
        step = _normalize_step(
            step_index=i,
            step_title=row.get("step_title", f"Step {i + 1}"),
            raw_content=row.get("lesson_content", ""),
            all_step_texts=all_texts,
        )
        step["db_id"] = row.get("id")
        steps.append(step)
        total_minutes += step["estimated_minutes"]

    # Run full sequence audit for cross-step analysis
    audit_steps_input = [
        {"step_number": i + 1, "step_title": r.get("step_title", f"Step {i+1}"),
         "content": r.get("lesson_content", "")}
        for i, r in enumerate(rows)
    ]
    try:
        audit = audit_lesson_steps(g, s, c, audit_steps_input, lesson_id=lesson_id)
    except Exception:
        audit = None

    return {
        "lesson_id": lesson_id,
        "grade": g,
        "subject": s,
        "chapter": c,
        "title": f"{s} — {c}",
        "total_steps": len(steps),
        "total_estimated_minutes": total_minutes,
        "steps": steps,
        "audit_summary": audit.get("summary") if audit else None,
        "similarity_matrix": audit.get("similarity_matrix") if audit else None,
    }


def preview_transform(
    lesson_id: str,
    mode: str = "structure_only",
    use_llm: bool = False,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate a preview transformation of a lesson.

    NEVER saves or publishes output.
    LLM is only called when use_llm=True and admin explicitly enables it.
    """
    detail = get_lesson_detail(lesson_id, grade=grade, subject=subject, chapter=chapter)
    if "error" in detail:
        return detail

    if mode == "structure_only":
        # Return section structure without full content
        steps_preview = []
        for step in detail.get("steps", []):
            steps_preview.append({
                "step_number": step["step_number"],
                "step_title": step["step_title"],
                "sections": list(step["normalized_sections"].keys()),
                "formula_count": len(step["formulas"]),
                "mcq_count": len(step["mcqs"]),
                "example_count": len(step["examples"]),
                "completeness_score": step["completeness_score"],
                "estimated_minutes": step["estimated_minutes"],
                "issues": step["issues"],
            })
        return {
            "preview_mode": "structure_only",
            "lesson_id": lesson_id,
            "grade": detail["grade"],
            "subject": detail["subject"],
            "chapter": detail["chapter"],
            "steps": steps_preview,
            "use_llm": False,
            "note": "Deterministic structure only — no LLM used.",
        }

    if mode == "summary_only":
        summaries = []
        for step in detail.get("steps", []):
            summaries.append({
                "step_number": step["step_number"],
                "step_title": step["step_title"],
                "summary": step["summary"] or step["raw_content"][:300],
                "key_formulas": step["formulas"][:3],
                "key_mcqs": step["mcqs"][:2],
            })
        return {
            "preview_mode": "summary_only",
            "lesson_id": lesson_id,
            "steps": summaries,
            "use_llm": False,
        }

    if mode in ("student_friendly", "sectioned"):
        # Return full normalized content without LLM transformation
        if not use_llm:
            return {
                "preview_mode": mode,
                "lesson_id": lesson_id,
                "grade": detail["grade"],
                "subject": detail["subject"],
                "chapter": detail["chapter"],
                "steps": detail["steps"],
                "use_llm": False,
                "note": "Deterministic sectioned preview. Enable LLM for AI-enhanced version.",
            }

        # LLM path — admin-explicitly enabled, preview only
        _log.info("lesson_lab: LLM preview requested for %s mode=%s", lesson_id, mode)
        return {
            "preview_mode": mode,
            "lesson_id": lesson_id,
            "use_llm": True,
            "note": "LLM preview generation is not implemented in v1. Use structure_only or sectioned without LLM.",
            "steps": detail["steps"],
        }

    return {"error": f"Unknown preview mode: {mode}"}


def get_visuals(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    lesson_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return available textbook visuals for a lesson context.

    Only returns existing uploaded/approved visuals from lesson_cache_visuals
    (or equivalent asset table). NEVER generates visuals.
    NEVER exposes assets publicly — admin-only endpoint.
    """
    visuals: list[dict] = []
    available = False

    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415

        db = get_content_db(grade or "Grade 9")
        q = (db.table("lesson_cache_visuals")
             .select("id, title, asset_url, source, matched_topic, caption, page_number, chapter, subject, grade")
             .eq("is_active", True))

        if grade:
            q = q.eq("grade", grade)
        if subject:
            q = q.ilike("subject", f"%{subject}%")
        if chapter:
            q = q.ilike("chapter", f"%{chapter}%")

        resp = q.order("page_number").limit(20).execute()
        rows = resp.data or []

        for row in rows:
            visuals.append({
                "id": row.get("id"),
                "title": row.get("title") or f"Page {row.get('page_number', '?')}",
                "image_url_or_asset_ref": row.get("asset_url", ""),
                "source": row.get("source", "textbook"),
                "matched_topic": row.get("matched_topic") or row.get("chapter", ""),
                "caption": row.get("caption") or "",
                "explanation": "",
                "confidence": 0.8 if row.get("matched_topic") else 0.5,
            })
        available = len(visuals) > 0

    except Exception as e:
        _log.debug("lesson_lab: visuals table unavailable — %s", e)
        available = False

    return {
        "available": available,
        "grade": grade or "",
        "subject": subject or "",
        "chapter": chapter or "",
        "lesson_id": lesson_id or "",
        "visuals": visuals,
        "empty_state": "No textbook visuals linked yet." if not available else None,
    }
