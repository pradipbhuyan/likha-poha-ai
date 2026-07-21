"""
Chapter-Doc Prewarm v2 (Phase 3)
================================
Generates chapter documents NATIVELY as typed blocks — no markdown middle step,
no client parsing, no conversion. Admin/prewarm-time only; students never
trigger this path.

Pipeline (per chapter):
  1. RAG fetch — textbook chunks for grounding (same guardrails as v1:
     story-dependent subjects with zero RAG are refused, never guessed).
  2. Outline pass  — one LLM call → 3-8 milestone titles from the textbook.
  3. Blocks pass   — one LLM call per milestone → typed blocks (JSON).
  4. Recap + exam  — one LLM call → recap block, plus exam_qa for Grades 9-12.
  5. Pydantic validation gates every pass; one retry on invalid JSON, then the
     chapter is reported failed (nothing partial is ever stored).

Token profile: ~(2 + milestones) calls per chapter on the prewarm model.
Serving stays zero-token — docs go into lesson_chapter_doc like converted ones.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.models.lesson_blocks import (
    ChapterDoc,
    ExamQABlock,
    Milestone,
    RecapBlock,
)
from app.services.logger_service import get_logger
from app.services.openai_service import PREWARM_TEXT_MODEL, ask_llm
from app.services.rag_service import search_textbook_content
from app.services.tutor_service import STORY_DEPENDENT_SUBJECTS

_log = get_logger("services.chapter_doc_prewarm")

JUNIOR_GRADES = {"Grade 5", "Grade 6", "Grade 7", "Grade 8"}

_JSON_SYSTEM = (
    "You are a CBSE curriculum content generator. You output ONLY valid JSON — "
    "no markdown fences, no commentary, no trailing text. Every fact must come "
    "from the textbook context provided; never invent story details, data, or "
    "questions about content not present in the context."
)

_BLOCK_RULES = """
Block types you may use (JSON objects with a "type" field):
- {"type":"concept","title":"...","body_md":"...","key_terms":[{"term":"...","meaning":"..."}]}
  One idea per concept. body_md is markdown; wrap ALL math in $...$ (inline) or $$...$$ (display).
- {"type":"example","question":"<complete self-contained problem>","body_md":"Step 1: ...\\nStep 2: ...\\nAnswer: ..."}
  The question must include all data needed. NEVER ask the student to draw or sketch.
- {"type":"quickcheck","format":"mcq","question":"...","options":["...","...","...","..."],"answer_index":0,"explanation":"..."}
  Self-contained MCQ (or format "truefalse" with exactly ["True","False"]).
  answer_index is 0-based and MUST point at the correct option.
- {"type":"watchout","body_md":"<common mistake and how to avoid it>"}
- {"type":"vocab","words":[{"term":"...","meaning":"<as used in THIS text>"}]}
  Only for language chapters, only words that appear in the textbook context.
"""


def _parse_json(raw: str):
    """Parse LLM output as JSON, tolerating accidental code fences and the
    literal control characters (raw newlines/tabs inside string values) that
    smaller/open models frequently emit despite being told to escape them."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Repair common ways smaller/open models mangle JSON string bodies —
        # applied ONLY inside quoted strings; a blanket replace would corrupt
        # the JSON structure itself.
        # \b and \f are technically valid JSON escapes (backspace/form-feed)
        # but generated lesson content never intends those — they only show
        # up as the start of LaTeX like \frac or \forall, so they're treated
        # as invalid here and doubled like any other stray backslash.
        _VALID_ESCAPE_RE = re.compile(r'\\(?!["\\/nrtu])')

        def _repair_string(match: "re.Match[str]") -> str:
            body = match.group(0)
            # 1. Literal control characters (raw newlines/tabs) → escaped.
            body = body.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            # 2. Backslashes that don't start a valid JSON escape (e.g. LaTeX
            #    like \frac{...} or \sqrt{...}) → doubled so they read as a
            #    literal backslash instead of breaking the parser.
            body = _VALID_ESCAPE_RE.sub(r"\\\\", body)
            return body

        repaired = re.sub(r'"(?:[^"\\]|\\.)*"', _repair_string, text, flags=re.DOTALL)
        return json.loads(repaired)


def _fetch_rag_context(board, grade, subject, chapter, match_count=12) -> str:
    results = search_textbook_content(
        query=f"{grade} {subject} {chapter} explanation definitions examples",
        board=board, grade=grade, subject=subject, chapter=chapter,
        match_count=match_count,
    )
    if not results:
        results = search_textbook_content(
            query=f"{grade} {subject} {chapter}",
            board=board, grade=grade, subject=subject, chapter=None,
            match_count=match_count,
        )
    return "\n\n".join(r.get("chunk_text", "") for r in (results or []))


def _ask_json(prompt: str, username: str, feature: str, model: str):
    """One LLM call → parsed JSON, with a single retry on parse failure.

    Uses ask_llm() — honours whatever provider is active in Admin AI Studio
    (currently ollama_cloud). The `model` argument is only applied when the
    active provider is OpenAI; other providers use their own admin-configured
    model. Use openai_service.ask_openai_direct() instead when a SPECIFIC
    OpenAI model must run regardless of the active admin provider.
    """
    for attempt in (1, 2):
        raw = ask_llm(_JSON_SYSTEM, prompt, username=username, feature=feature, model=model)
        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            if attempt == 2:
                raise
            prompt = (
                "Your previous output was not valid JSON. Output ONLY the JSON, "
                "nothing else.\n\n" + prompt
            )
    return None  # unreachable


def generate_outline(grade, subject, chapter, context, username, model) -> list[str]:
    prompt = f"""Textbook context for {grade} {subject} — {chapter}:
{context[:9000]}

From this textbook content, list the real subtopics a student should learn,
in teaching order. Output JSON only:
{{"milestones": ["<subtopic title>", "..."]}}

Rules:
- 3 to 8 milestones, each a short student-friendly title (max 60 chars).
- Titles must come from the actual textbook content above, not a generic template.
- Order must follow the textbook's own progression."""
    data = _ask_json(prompt, username, "chapter_doc_outline", model)
    titles = [str(t).strip() for t in (data.get("milestones") or []) if str(t).strip()]
    if not (3 <= len(titles) <= 8):
        raise ValueError(f"outline returned {len(titles)} milestones (need 3-8)")
    return titles


def generate_milestone_blocks(
    grade, subject, chapter, milestone_title, context, junior, username, model,
) -> Milestone:
    tone = (
        "Grade 5-8 student: short sentences, concrete everyday examples, a warm "
        "curious tone. Include 1 quickcheck. Start with ONE 'hook' block: "
        '{"type":"hook","text":"<one surprising, curiosity-raising fact from the textbook>"}'
        if junior else
        "Grade 9-12 student: precise textbook terminology, exam-oriented depth, "
        "reasoning for every claim. Include 1 quickcheck. Do NOT use hook blocks."
    )
    prompt = f"""Textbook context for {grade} {subject} — {chapter}:
{context[:9000]}

Write the lesson blocks for ONE milestone: "{milestone_title}".
Audience: {tone}

{_BLOCK_RULES}

Output JSON only:
{{"blocks": [ <2 to 6 block objects for this milestone> ]}}

Rules:
- Cover ONLY "{milestone_title}" — other milestones are taught separately.
- No introduction or summary blocks — the chapter has a single recap elsewhere.
- Ground every fact in the textbook context above."""
    data = _ask_json(prompt, username, "chapter_doc_blocks", model)
    milestone = Milestone.model_validate({"title": milestone_title, "blocks": data.get("blocks") or []})
    if not milestone.blocks:
        raise ValueError(f"no blocks generated for milestone '{milestone_title}'")
    return milestone


def generate_recap_and_exam(
    grade, subject, chapter, milestone_titles, context, senior, username, model,
) -> tuple[RecapBlock, list[ExamQABlock]]:
    exam_part = (
        """Also produce "exam": 3 to 5 CBSE board-style questions covering the chapter:
[{"type":"exam_qa","marks":<1-5>,"year":"","question":"...","model_answer_md":"<mark-scheme style answer>"}]
Mix marks (1, 2/3, and one 5-mark). Questions must be answerable in text only."""
        if senior else 'Set "exam" to an empty list [].'
    )
    prompt = f"""Textbook context for {grade} {subject} — {chapter}:
{context[:9000]}

The chapter was taught through these milestones: {json.dumps(milestone_titles)}

Produce the single chapter recap: 4-8 bullet points (markdown) of what to
remember, ending with a next-step instruction (not a question).
{exam_part}

Output JSON only:
{{"recap": {{"type":"recap","body_md":"..."}}, "exam": [...]}}"""
    data = _ask_json(prompt, username, "chapter_doc_recap", model)
    recap = RecapBlock.model_validate(data.get("recap") or {})
    exam = [ExamQABlock.model_validate(item) for item in (data.get("exam") or [])]
    return recap, exam


def generate_chapter_doc_v2(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    mode: str = "CBSE",
    username: str = "prewarm_admin",
    model: str = PREWARM_TEXT_MODEL,
) -> ChapterDoc | None:
    """
    Generate one complete, validated ChapterDoc natively as typed blocks.
    Returns None (with a log line) when generation is refused or fails —
    nothing partial is ever returned.
    """
    context = _fetch_rag_context(board, grade, subject, chapter)

    # Anti-hallucination guard — same policy as v1 lesson generation.
    if not context and any(s in (subject or "").lower() for s in STORY_DEPENDENT_SUBJECTS):
        _log.warning(
            "chapter_doc_v2.refused_no_rag",
            grade=grade, subject=subject, chapter=chapter[:60],
        )
        return None

    junior = grade in JUNIOR_GRADES
    try:
        titles = generate_outline(grade, subject, chapter, context, username, model)
        milestones = [
            generate_milestone_blocks(
                grade, subject, chapter, title, context, junior, username, model,
            )
            for title in titles
        ]
        recap, exam = generate_recap_and_exam(
            grade, subject, chapter, titles, context, senior=not junior,
            username=username, model=model,
        )
        return ChapterDoc(
            board=board, grade=grade, subject=subject, chapter=chapter, mode=mode,
            source="prewarm_v2", milestones=milestones, recap=recap, exam=exam,
        )
    except (ValidationError, ValueError, json.JSONDecodeError, KeyError) as exc:
        _log.error(
            "chapter_doc_v2.generation_failed",
            grade=grade, subject=subject, chapter=chapter[:60], error=str(exc),
        )
        return None
