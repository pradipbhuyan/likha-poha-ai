"""
Lesson Knowledge Base Service (LKB)
=====================================
Pre-warmed Q&A chips for lesson follow-up suggestion buttons.

Design goals
------------
- 5 chip questions per lesson step per chapter, grounded in NCERT content.
- Answers are 6-10 concise bullet points sourced from the chapter's RAG content.
- Chips are served instantly (zero LLM cost after pre-warm).
- Admin triggers pre-warm via Cache & Question Bank Management panel.
- Tracks hit counts for analytics.

Table: lesson_kb
Run backend/sql/add_lesson_kb.sql in Supabase before enabling.
Pre-warm via: POST /api/admin/cache/build-lkb/{grade-slug}
"""

from __future__ import annotations

import logging
import re

from app.services.grade_db_router import get_content_db
from app.services.openai_service import ask_llm, PREWARM_TEXT_MODEL

logger = logging.getLogger("likhapoha.lesson_kb")

# Number of chips per step
CHIPS_PER_STEP = 5

# Default lesson steps by grade group
def _get_lesson_steps(grade: str) -> list[str]:
    g = (grade or "").lower()
    if g in ("grade 1", "grade 2", "grade 3"):
        return ["Introduction", "Let's Practice", "Quick Review"]
    if g in ("grade 4", "grade 5"):
        return ["What We Learn", "Worked Examples", "Recap"]
    if g in ("grade 6", "grade 7", "grade 8"):
        return ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"]
    if g in ("grade 10", "grade 11", "grade 12"):
        return ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"]
    # Grade 9 + fallback
    return ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap"]


# ---------------------------------------------------------------------------
# Fetch chips for student lesson page
# ---------------------------------------------------------------------------

def get_lkb_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    limit: int = CHIPS_PER_STEP,
) -> list[dict]:
    """
    Return pre-warmed LKB chips for the current lesson step.
    Returns list of {"question": str, "answer": str} ordered by hit_count desc.
    Returns [] if no chips exist (student falls back to DKB or strategy tips).
    """
    supabase = _get_db(grade)
    try:
        result = (
            supabase.table("lesson_kb")
            .select("id, question, answer, hit_count")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .eq("step_title", step_title)
            .eq("status", "active")
            .order("hit_count", desc=True)
            .limit(limit)
            .execute()
        )
        rows = result.data or []
        return [{"id": r["id"], "question": r["question"], "answer": r["answer"]} for r in rows]
    except Exception as exc:
        logger.warning("LKB fetch failed for %s/%s/%s/%s: %s", grade, subject, chapter, step_title, exc)
        return []


def record_lkb_hit(chip_id: str, grade: str) -> None:
    """Increment hit count for analytics (fire-and-forget)."""
    try:
        supabase = _get_db(grade)
        supabase.table("lesson_kb").update({
            "hit_count": supabase.table("lesson_kb").select("hit_count").eq("id", chip_id).execute().data[0]["hit_count"] + 1
        }).eq("id", chip_id).execute()
    except Exception:
        pass  # Non-critical


# ---------------------------------------------------------------------------
# Admin: count LKB entries per grade
# ---------------------------------------------------------------------------

def count_lkb_chips(grade: str) -> int:
    """Return total active LKB chips for a grade."""
    try:
        supabase = _get_db(grade)
        r = supabase.table("lesson_kb").select("id", count="exact").eq("grade", grade).eq("status", "active").execute()
        return r.count or 0
    except Exception:
        return 0


def count_expected_lkb_chips(grade: str) -> int:
    """Total expected LKB chips = chapters × steps × 5 chips."""
    try:
        from app.services.prewarm_service import get_syllabus_for_grade  # noqa: PLC0415
        syllabus = get_syllabus_for_grade(grade)
        cbse_data = syllabus.get("CBSE", {})
        steps = _get_lesson_steps(grade)
        total = 0
        for chapters in cbse_data.values():
            total += len(chapters) * len(steps) * CHIPS_PER_STEP
        return total
    except Exception:
        return 0


def get_lkb_chapter_status(grade: str) -> list[dict]:
    """
    For admin panel: list all chapters with chip counts.
    Returns [{"subject": str, "chapter": str, "chips": int, "expected": int}]
    """
    try:
        from app.services.prewarm_service import get_syllabus_for_grade  # noqa: PLC0415
        syllabus = get_syllabus_for_grade(grade)
        cbse_data = syllabus.get("CBSE", {})
        steps = _get_lesson_steps(grade)
        expected_per_chapter = len(steps) * CHIPS_PER_STEP

        supabase = _get_db(grade)
        # Fetch all active chips for this grade
        r = supabase.table("lesson_kb").select("subject, chapter, id").eq("grade", grade).eq("status", "active").execute()
        rows = r.data or []

        # Build count map
        count_map: dict[tuple, int] = {}
        for row in rows:
            key = (row["subject"], row["chapter"])
            count_map[key] = count_map.get(key, 0) + 1

        result = []
        for subject, chapters in cbse_data.items():
            for chapter in chapters:
                chips = count_map.get((subject, chapter), 0)
                result.append({
                    "subject": subject,
                    "chapter": chapter,
                    "chips": chips,
                    "expected": expected_per_chapter,
                    "complete": chips >= expected_per_chapter,
                })
        return result
    except Exception as exc:
        logger.warning("LKB chapter status failed for %s: %s", grade, exc)
        return []


# ---------------------------------------------------------------------------
# Admin: pre-warm LKB for a grade
# ---------------------------------------------------------------------------

def build_lkb_for_grade(grade: str, mode: str = "CBSE") -> dict:
    """
    Generate LKB chips for all chapters in a grade.
    Called as a background task from the admin cache management panel.
    Returns summary {"built": int, "skipped": int, "errors": int}.
    """
    from app.services.prewarm_service import get_syllabus_for_grade  # noqa: PLC0415

    logger.info("LKB build started for %s", grade)
    syllabus = get_syllabus_for_grade(grade)
    cbse_data = syllabus.get("CBSE", {})
    steps = _get_lesson_steps(grade)

    built = skipped = errors = 0

    for subject, chapters in cbse_data.items():
        for chapter in chapters:
            for step_title in steps:
                try:
                    # Skip if already fully pre-warmed
                    existing = _count_existing(grade, subject, chapter, step_title)
                    if existing >= CHIPS_PER_STEP:
                        skipped += CHIPS_PER_STEP
                        continue

                    # Generate chips using LLM with RAG context
                    chips = _generate_chips(grade, subject, chapter, step_title, mode)
                    if chips:
                        _store_chips(grade, subject, chapter, step_title, chips)
                        built += len(chips)
                    else:
                        errors += 1
                except Exception as exc:
                    logger.warning("LKB build failed %s/%s/%s: %s", subject, chapter, step_title, exc)
                    errors += 1

    logger.info("LKB build done for %s: built=%d skipped=%d errors=%d", grade, built, skipped, errors)
    return {"built": built, "skipped": skipped, "errors": errors}


def build_lkb_for_chapter(grade: str, subject: str, chapter: str, mode: str = "CBSE") -> dict:
    """Build LKB chips for a single chapter (all steps)."""
    steps = _get_lesson_steps(grade)
    built = skipped = errors = 0

    for step_title in steps:
        try:
            existing = _count_existing(grade, subject, chapter, step_title)
            if existing >= CHIPS_PER_STEP:
                skipped += CHIPS_PER_STEP
                continue

            chips = _generate_chips(grade, subject, chapter, step_title, mode)
            if chips:
                _store_chips(grade, subject, chapter, step_title, chips)
                built += len(chips)
            else:
                errors += 1
        except Exception as exc:
            logger.warning("LKB build failed %s/%s/%s: %s", subject, chapter, step_title, exc)
            errors += 1

    return {"built": built, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_db(grade: str):
    return get_content_db(grade)


def _count_existing(grade: str, subject: str, chapter: str, step_title: str) -> int:
    try:
        supabase = _get_db(grade)
        r = supabase.table("lesson_kb").select("id", count="exact").eq("grade", grade).eq("subject", subject).eq("chapter", chapter).eq("step_title", step_title).eq("status", "active").execute()
        return r.count or 0
    except Exception:
        return 0


def _get_rag_context(grade: str, subject: str, chapter: str, step_title: str) -> str:
    """Fetch relevant RAG content for the chapter to ground answers in NCERT."""
    try:
        from app.services.rag_service import search_rag  # noqa: PLC0415
        query = f"{step_title} {chapter} {subject}"
        results = search_rag(query=query, grade=grade, subject=subject, chapter=chapter, limit=5)
        if not results:
            return ""
        return "\n\n".join(r.get("content", "") for r in results if r.get("content"))
    except Exception as exc:
        logger.debug("RAG context fetch failed: %s", exc)
        return ""


def _generate_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    mode: str = "CBSE",
) -> list[dict]:
    """
    Call LLM to generate 5 chip Q&A pairs for this lesson step.
    Answers are 6-10 bullet points grounded in NCERT content.
    Returns list of {"question": str, "answer": str}.
    """
    try:
        rag_context = _get_rag_context(grade, subject, chapter, step_title)
        context_section = f"\n\nNCERT CONTENT FOR REFERENCE:\n{rag_context}" if rag_context else ""

        system_prompt = (
            f"You are a CBSE {grade} {subject} subject-matter expert. "
            "Generate lesson chip Q&A pairs grounded strictly in NCERT textbook content. "
            "Return valid JSON only — no markdown, no preamble."
        )

        user_prompt = f"""Chapter: "{chapter}" | Lesson step: "{step_title}"{context_section}

Generate exactly 5 question-answer pairs a student needs after reading this lesson step.
Each answer = 6 to 10 bullet points (start each with "•") from the NCERT chapter only.

RULES:
• Questions must be specific to THIS chapter — not generic study tips.
• Every bullet point must state a factual point from the chapter.
• Do NOT reference diagrams, figures, or visualisations.
• Keep each bullet to one clear sentence.

Respond ONLY with JSON array:
[
  {{
    "question": "Specific chapter question",
    "answer": "• Fact 1\\n• Fact 2\\n• Fact 3\\n• Fact 4\\n• Fact 5\\n• Fact 6"
  }}
]"""

        response = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=PREWARM_TEXT_MODEL,
            feature="lkb_build",
        )
        if not response:
            return []

        # Parse JSON
        raw = response.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            return []

        import json  # noqa: PLC0415
        chips = json.loads(raw[start:end + 1])

        # Validate
        validated = []
        for chip in chips:
            q = (chip.get("question") or "").strip()
            a = (chip.get("answer") or "").strip()
            if q and a and "•" in a:
                validated.append({"question": q, "answer": a})

        return validated[:CHIPS_PER_STEP]

    except Exception as exc:
        logger.warning("LKB chip generation failed for %s/%s/%s: %s", subject, chapter, step_title, exc)
        return []


def _store_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    chips: list[dict],
) -> None:
    """Store generated chips in lesson_kb table."""
    supabase = _get_db(grade)
    rows = [
        {
            "grade": grade,
            "subject": subject,
            "chapter": chapter,
            "step_title": step_title,
            "question": chip["question"],
            "answer": chip["answer"],
            "source": "prewarmed",
            "hit_count": 0,
            "status": "active",
        }
        for chip in chips
    ]
    try:
        supabase.table("lesson_kb").insert(rows).execute()
    except Exception as exc:
        logger.warning("LKB store failed: %s", exc)
