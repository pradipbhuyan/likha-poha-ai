"""
Lesson Knowledge Base Service (LKB)
=====================================
Pre-warmed Q&A chips for lesson follow-up suggestion buttons.

Design goals
------------
- Up to 5 chip questions per lesson step per chapter, grounded in NCERT content
  (fewer for thin chapters/matches — see _target_chip_count — rather than
  padding with repetitive or ungrounded filler to force a fixed count).
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


def get_or_generate_lkb_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
) -> tuple[list[dict], bool]:
    """
    Return LKB chips for the current lesson step, generating them on-demand if missing.

    Flow:
    1. DB lookup (instant if pre-warmed).
    2. On miss → generate 5 chips via LLM with NCERT RAG context.
    3. Store generated chips in lesson_kb so all future requests are instant.
    4. Return chips + generated flag.

    Returns (chips: list[dict], was_generated: bool).
    """
    # ── Fast path: DB hit ──────────────────────────────────────────────────────
    chips = get_lkb_chips(grade, subject, chapter, step_title)
    if chips:
        return chips, False

    # ── Slow path: generate + store ────────────────────────────────────────────
    logger.info(
        "LKB miss — generating chips for %s / %s / %s / %s",
        grade, subject, chapter, step_title,
    )
    try:
        new_chips = _generate_chips(grade, subject, chapter, step_title)
        if new_chips:
            _store_chips(grade, subject, chapter, step_title, new_chips)
            # Re-fetch from DB so IDs are included
            stored = get_lkb_chips(grade, subject, chapter, step_title)
            return stored if stored else new_chips, True
    except Exception as exc:
        logger.warning("LKB on-demand generation failed: %s", exc)

    return [], True


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
                    # Skip if this step already has any active chips. Not
                    # ">= CHIPS_PER_STEP" — a thin chapter can legitimately
                    # settle on fewer than 5 chips (see _target_chip_count),
                    # and comparing against the old fixed target would mean
                    # a properly-processed thin step never counts as "done"
                    # and gets re-sent to the LLM on every future prewarm run.
                    existing = _count_existing(grade, subject, chapter, step_title)
                    if existing >= 1:
                        skipped += existing
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
            # See build_lkb_for_grade for why this is ">= 1", not ">= CHIPS_PER_STEP".
            existing = _count_existing(grade, subject, chapter, step_title)
            if existing >= 1:
                skipped += existing
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
    """
    Fetch relevant RAG content for the chapter to ground LKB answers in NCERT text.

    Uses search_textbook_content (the correct function name in rag_service).
    Returns all retrieved chunk_text joined so the LLM has real textbook content.

    Bug fixed: previous version imported non-existent 'search_rag', which raised
    ImportError caught silently, returning empty string — causing ALL LKB chips
    to be generated purely from LLM training data with no textbook grounding.
    """
    try:
        from app.services.rag_service import search_textbook_content  # noqa: PLC0415
        # Use a broad query to pull all relevant chunks for this chapter
        query = f"{chapter} {subject} {step_title} key concepts definitions examples"
        results = search_textbook_content(
            query=query,
            grade=grade,
            subject=subject,
            chapter=chapter,
            match_count=12,  # increased from 5 to get more textbook coverage
        )
        if not results:
            # Fallback: broaden to subject-level (handles chapter name mismatches)
            results = search_textbook_content(
                query=query,
                grade=grade,
                subject=subject,
                chapter=None,
                match_count=8,
            )
        if not results:
            logger.warning(
                "LKB: No RAG context found for %s/%s/%s — chips will be generated "
                "from LLM knowledge only, not textbook content.",
                grade, subject, chapter,
            )
            return ""
        # Return the actual textbook text chunks (chunk_text key, not content)
        chunks = [r.get("chunk_text", "") or r.get("content", "") for r in results]
        return "\n\n---\n\n".join(c for c in chunks if c.strip())
    except Exception as exc:
        logger.warning("RAG context fetch failed for LKB: %s", exc)
        return ""


# Word-count thresholds mapping RAG richness to how many chips are worth
# asking for. A short chapter (or a narrow match) only has enough distinct
# content for a couple of well-grounded questions — asking for 5 regardless
# just pressures the model to pad with repetitive or weakly-grounded filler.
_CHIP_COUNT_THRESHOLDS = [
    (80, 1),
    (180, 2),
    (320, 3),
    (500, 4),
]


def _target_chip_count(rag_context: str) -> int:
    """Map available RAG word count to a chip target between 1 and CHIPS_PER_STEP."""
    word_count = len(rag_context.split())
    for threshold, count in _CHIP_COUNT_THRESHOLDS:
        if word_count < threshold:
            return count
    return CHIPS_PER_STEP


def _generate_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    mode: str = "CBSE",
) -> list[dict]:
    """
    Call LLM to generate up to CHIPS_PER_STEP chip Q&A pairs for this lesson step
    (fewer for thin RAG content — see _target_chip_count).
    Answers are 6-10 bullet points grounded in NCERT content.
    Returns list of {"question": str, "answer": str}.
    """
    try:
        rag_context = _get_rag_context(grade, subject, chapter, step_title)
        has_rag = bool(rag_context.strip())

        # Anti-hallucination guard — applies to EVERY subject, not just
        # language/literature ones. Originally this only fired for
        # STORY_DEPENDENT_SUBJECTS (mirroring tutor_service.generate_step_lesson),
        # because a language chapter with no RAG match reliably produced
        # confidently wrong content — e.g. "Grade 11 English / The Frog" (a
        # Norman Gale poem) returned fabricated Class 11 Biology questions
        # about real frogs, because the LLM defaulted to its strongest prior
        # for "grade 11" + "frog" once nothing grounded it.
        #
        # Widened after an audit found ALL 21k+ existing LKB chips were
        # generated during a period when RAG lookup was silently broken
        # (search_rag didn't exist — see _get_rag_context's docstring), so
        # every chip, in every subject, was "generate generic questions
        # anyway" output with zero textbook grounding. Math/Science chapters
        # with a genuine RAG coverage gap have the exact same failure mode as
        # a story chapter with no match: nothing to ground the answer in, so
        # the model guesses from training-data priors instead of the actual
        # NCERT text. Refusing to guess (empty chips) is strictly better than
        # serving plausible-sounding but ungrounded content.
        if not has_rag:
            logger.warning(
                "LKB: skipping chip generation for %s/%s/%s — no RAG grounding "
                "found, refusing to guess rather than generate ungrounded content.",
                grade, subject, chapter,
            )
            return []

        # Scale the requested chip count to how much textbook content actually
        # came back, instead of always demanding 5. A short chapter (or a
        # narrow RAG match) genuinely only supports a couple of distinct,
        # well-grounded questions — forcing 5 out of thin content just
        # reintroduces padding/repetition/ungrounded filler by another route.
        target_count = _target_chip_count(rag_context)

        context_section = f"\n\nNCERT CONTENT FOR REFERENCE:\n{rag_context}"

        system_prompt = (
            f"You are a CBSE {grade} {subject} subject-matter expert. "
            "Generate lesson chip Q&A pairs grounded STRICTLY in the NCERT textbook content "
            "provided below. NEVER use general knowledge or outside sources. "
            "Every question and every answer bullet MUST be directly answerable from "
            "the textbook text provided. "
            "Return valid JSON only — no markdown, no preamble."
        )

        grounding_instruction = (
            "CRITICAL GROUNDING RULES:\n"
            "- Read the NCERT CONTENT FOR REFERENCE above carefully.\n"
            "- Every question MUST be about something explicitly mentioned in that content.\n"
            "- Every answer bullet MUST be a fact that appears in that content.\n"
            "- Do NOT use general subject knowledge not present in the retrieved text.\n"
            "- Do NOT invent examples, characters, or facts not in the textbook chunks.\n"
            "- If the retrieved content covers only some topics, generate questions only for those topics.\n"
        )

        user_prompt = f"""Chapter: "{chapter}" | Lesson step: "{step_title}" | Grade: {grade}{context_section}

{grounding_instruction}
Generate UP TO {target_count} question-answer pair(s) a student needs after reading this lesson step.
Each answer = 6 to 10 bullet points (each on its own line, starting with "- ") sourced ONLY from the NCERT content above.

ADDITIONAL RULES:
- Questions must name specific things from THIS chapter (characters, concepts, events, processes).
- Do NOT ask "What did you learn?" or generic meta-questions.
- Do NOT reference diagrams, figures, or visualisations.
- Keep each bullet to one clear, complete sentence from the textbook.
- Use "- " (hyphen space) for each bullet, one bullet per line.
- If the content above only supports fewer than {target_count} distinct, well-grounded
  questions, return FEWER — never pad with repetitive, generic, or weakly-grounded questions
  just to reach {target_count}.

Respond ONLY with JSON array:
[
  {{
    "question": "Specific chapter question referencing actual content",
    "answer": "- Textbook fact 1\\n- Textbook fact 2\\n- Textbook fact 3\\n- Textbook fact 4\\n- Textbook fact 5\\n- Textbook fact 6"
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
        import re as _re  # noqa: PLC0415
        # Sanitise: replace literal newlines inside JSON string values with \n escape
        # (some LLMs like Llama/SambaNova emit raw newlines inside JSON strings)
        json_text = raw[start:end + 1]
        # Replace unescaped control characters inside JSON strings
        def _fix_ctrl(m):
            return m.group(0).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        # Only fix inside quoted strings (between " delimiters)
        json_text = _re.sub(r'"(?:[^"\\]|\\.)*"', _fix_ctrl, json_text, flags=_re.DOTALL)
        chips = json.loads(json_text)

        # Validate — accept both • and - bullet formats
        validated = []
        for chip in chips:
            q = (chip.get("question") or "").strip()
            a = (chip.get("answer") or "").strip()
            if q and a and ("•" in a or "- " in a):
                validated.append({"question": q, "answer": a})

        return validated[:target_count]

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
