"""
Chapter Doc Service (Phase 1 of the Chapter Journey redesign)
=============================================================
Builds, stores, and serves typed-block chapter documents.

Converter: merges a chapter's per-step markdown blobs from lesson_cache into
ONE validated ChapterDoc — deterministically (no LLM). The section heuristics
are a Python port of the frontend's parseSections/parseMcqQuestion, which the
cached content was generated to satisfy. Chapters whose cache rows fail to
parse are simply reported unavailable; the caller falls back to the old flow.

Design rules:
- Serving NEVER calls the LLM. A missing doc is a fallback, not a generation.
- Exactly one recap per chapter (last step's summary wins).
- LKB chips attach per milestone, deduped against quickcheck questions.
- All DB failures degrade to None/[] so the old lesson flow is never blocked.
"""

from __future__ import annotations

import re

from pydantic import ValidationError

from app.models.lesson_blocks import (
    ChapterDoc,
    ConceptBlock,
    ExampleBlock,
    HookBlock,
    KeyTerm,
    Milestone,
    QuickCheckBlock,
    RecapBlock,
    StudentsAskBlock,
    VisualBlock,
    VocabBlock,
    WatchoutBlock,
)
from app.services.grade_db_router import get_content_db
from app.services.lesson_kb_service import _get_lesson_steps as get_lesson_steps
from app.services.logger_service import get_logger

_log = get_logger("services.chapter_doc")

# Steps whose cached rows may exist under a legacy title (pre-rename prewarm).
_LEGACY_STEP_TITLES = {"Exam-style problems": "Practice questions"}


# ─────────────────────────────────────────────────────────────────────────────
# Section parsing — Python port of frontend parseSections()
# ─────────────────────────────────────────────────────────────────────────────

_NUMBERED_HEADING_RE = re.compile(r"^#{0,3}\s*\**\s*(\d+\.\s+.+?)\**\s*$")
_HASH_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$")
_LABEL_HEADING_RE = re.compile(
    r"^(Step\s+\d+|Question|Summary|Introduction|Conclusion|Common\s+Mistake|"
    r"Quick\s+Check|What\s+You\s+Will\s+Learn|Worked\s+Example|Overview)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_BOLD_HEADING_RE = re.compile(r"^\*\*(.+?)\*\*:?\s*$")


def _detect_heading(line: str) -> str | None:
    """Return the heading title if this line is a section heading, else None."""
    m = _NUMBERED_HEADING_RE.match(line)
    if m:
        captured = re.sub(r"^\d+\.\s*", "", m.group(1)).strip()
        if len(captured) <= 65 and not re.search(r"[.?!]$", captured):
            return captured

    m = _HASH_HEADING_RE.match(line)
    if m:
        title = m.group(1).replace("**", "").strip()
        if len(title) >= 3:
            return title

    m = _LABEL_HEADING_RE.match(line)
    if m:
        label = m.group(1).strip()
        rest = (m.group(2) or "").strip()
        combined = f"{label}: {rest}" if rest else label
        # "Step N:" is only a heading when the rest reads like a title
        # ("Step 2: Worked Examples"), not a solution line
        # ("Step 1: speed = distance/time").
        step_is_solution_line = bool(
            re.match(r"^step\s+\d+$", label, re.IGNORECASE)
            and rest
            and ("=" in rest or re.match(r"^[a-z]", rest))
        )
        if (
            not step_is_solution_line
            and 3 <= len(combined) <= 70
            and not re.search(r"[.?!]$", combined)
        ):
            return combined

    m = _BOLD_HEADING_RE.match(line)
    if m:
        title = m.group(1).strip()
        if 4 <= len(title) <= 80 and not re.match(r"^[a-z]", title):
            return title

    return None


def parse_sections(markdown: str) -> list[dict]:
    """Split lesson markdown into [{"title", "content"}] — port of parseSections."""
    sections: list[dict] = []
    current_title: str | None = None
    current: list[str] = []

    for line in (markdown or "").split("\n"):
        title = _detect_heading(line)
        if title is not None:
            if "\n".join(current).strip():
                sections.append({
                    "title": (current_title or "Introduction").replace("**", "").replace("#", "").strip(),
                    "content": "\n".join(current).strip(),
                })
            current_title = title
            current = []
        else:
            current.append(line)

    if "\n".join(current).strip():
        sections.append({
            "title": (current_title or "Introduction").replace("**", "").replace("#", "").strip(),
            "content": "\n".join(current).strip(),
        })

    return sections


def classify_section(title: str) -> str:
    """Map a section title to a block category — port of getSectionType."""
    t = (title or "").lower()
    if "new words" in t or "vocabulary" in t:
        return "vocab"
    if any(k in t for k in ("what you will learn", "introduction", "overview", "context", "what we learn")):
        return "intro"
    if any(k in t for k in ("common mistake", "warning", "avoid", "do not")):
        return "warning"
    if any(k in t for k in ("quick check", "check question", "self check")):
        return "check"
    if any(k in t for k in ("worked example", "example", "step-by-step", "step by step")):
        return "example"
    if any(k in t for k in ("summary", "recap", "revision", "review", "key points")):
        return "summary"
    if any(k in t for k in ("simple explanation", "core explanation", "concept", "explanation", "breakdown")):
        return "concept"
    if "question" in t or "practice" in t:
        return "check"
    return "concept"


# ─────────────────────────────────────────────────────────────────────────────
# MCQ parsing — Python port of frontend parseMcqQuestion()
# ─────────────────────────────────────────────────────────────────────────────

def parse_mcq(text: str) -> QuickCheckBlock | None:
    """Parse the enforced MCQ/True-False format into a QuickCheckBlock."""
    if not text:
        return None
    work = text.strip()

    explanation = ""
    m = re.search(r"\bExplanation\s*:\s*([\s\S]*)$", work, re.IGNORECASE)
    if m:
        explanation = m.group(1).strip()
        work = work[: m.start()].strip()

    m = re.search(r"\bAnswer\s*:\s*([A-D])\b", work, re.IGNORECASE)
    if not m:
        return None
    answer_key = m.group(1).upper()
    work = work[: m.start()].strip()

    options: list[tuple[str, str]] = []
    for om in re.finditer(r"\b([A-D])\)\s*([\s\S]*?)(?=\s*\b[A-D]\)|$)", work):
        opt_text = om.group(2).strip()
        if opt_text:
            options.append((om.group(1).upper(), opt_text))
    if len(options) < 2:
        return None

    first_opt = re.search(r"\b[A-D]\)", work)
    question = work[: first_opt.start()].strip() if first_opt and first_opt.start() > 0 else ""
    # Strip markdown heading/bold wrappers from the question line
    question = re.sub(r"^#{1,3}\s*", "", question).replace("**", "").strip()
    if not question:
        return None

    keys = [k for k, _ in options]
    if answer_key not in keys:
        return None

    is_tf = len(options) == 2 and {o[1].strip().lower() for o in options} == {"true", "false"}
    try:
        return QuickCheckBlock(
            format="truefalse" if is_tf else "mcq",
            question=question,
            options=[o[1] for o in options],
            answer_index=keys.index(answer_key),
            explanation=explanation,
        )
    except ValidationError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Vocab parsing — "**word** — meaning" lines from the New Words section
# ─────────────────────────────────────────────────────────────────────────────

_VOCAB_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?\*\*(.+?)\*\*\s*[—–:-]\s*(.+)$")


def parse_vocab(content: str) -> VocabBlock | None:
    words = []
    for line in (content or "").split("\n"):
        m = _VOCAB_LINE_RE.match(line)
        if m:
            words.append(KeyTerm(term=m.group(1).strip(), meaning=m.group(2).strip()))
    return VocabBlock(words=words) if words else None


# ─────────────────────────────────────────────────────────────────────────────
# Example parsing — "Question: ..." then stepped solution
# ─────────────────────────────────────────────────────────────────────────────

def parse_example(content: str) -> ExampleBlock | None:
    m = re.search(r"question\s*:\s*", content, re.IGNORECASE)
    if not m:
        return None
    after = content[m.end():]
    # Solution starts at "Step 1:" / "Answer:" / "Solution:"
    sol = re.search(r"(?:^|\n)\s*(?:\*\*)?(?:step\s*1|answer|solution)\s*(?:\*\*)?\s*:", after, re.IGNORECASE)
    if not sol:
        return None
    question = after[: sol.start()].strip().replace("**", "")
    body = after[sol.start():].strip()
    if not question or not body:
        return None
    return ExampleBlock(question=question, body_md=body)


# ─────────────────────────────────────────────────────────────────────────────
# Visual extraction — visual-json fences become typed VisualBlocks
# ─────────────────────────────────────────────────────────────────────────────
# Raw JSON must never reach a student. Fences (and unfenced "visual-json"
# stragglers from prompts that stripped backticks) are pulled out of section
# content; parseable+valid ones become VisualBlocks, everything else is
# silently dropped from the text.

import json as _json

_FENCED_VISUAL_RE = re.compile(r"```+\s*visual-json\s*\n?([\s\S]*?)```+", re.IGNORECASE)
# "visual-json" (fence markers lost) followed by a JSON object — either on the
# next line, or trailing on the same line (some model outputs drop the
# newline entirely, e.g. 'visual-json {"type": ...}').
_LOOSE_VISUAL_RE = re.compile(
    r"(?:^|\n)[ \t]*visual-json[ \t]*(?:\n[ \t]*)?(\{.*?\})[ \t]*(?=\n|$)",
    re.IGNORECASE,
)


def extract_visuals(content: str) -> tuple[str, list[VisualBlock]]:
    """Strip visual-json payloads from content; return (clean_text, blocks)."""
    visuals: list[VisualBlock] = []

    def _try_parse(payload: str):
        try:
            data = _json.loads(payload.strip())
            visuals.append(VisualBlock(visual=data))
        except Exception:
            pass  # unparseable/invalid — drop from text, never show raw
        return ""

    cleaned = _FENCED_VISUAL_RE.sub(lambda m: _try_parse(m.group(1)), content or "")
    cleaned = _LOOSE_VISUAL_RE.sub(lambda m: "\n" + _try_parse(m.group(1)), cleaned)
    # Drop leftover bare "visual-json" label lines with no payload
    cleaned = re.sub(r"(?:^|\n)[ \t]*visual-json[ \t]*(?=\n|$)", "\n", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(), visuals


# ─────────────────────────────────────────────────────────────────────────────
# Question-text dedupe (LKB chips vs in-lesson quickchecks)
# ─────────────────────────────────────────────────────────────────────────────

_QUESTION_STOPWORDS = {
    "the", "its", "his", "her", "our", "your", "their", "a", "an", "of",
    "is", "are", "was", "were", "to", "in", "on", "for", "then", "than",
    "do", "does", "did", "and", "but", "not", "with", "that", "this",
}


def _normalize_question(q: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9ऀ-ॿ]+", (q or "").lower())
    return {t for t in tokens if len(t) > 2 and t not in _QUESTION_STOPWORDS}


def is_duplicate_question(a: str, b: str, threshold: float = 0.7) -> bool:
    """Token-Jaccard similarity gate — drops chips that repeat quickchecks."""
    ta, tb = _normalize_question(a), _normalize_question(b)
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / len(ta | tb)
    return overlap >= threshold


# ─────────────────────────────────────────────────────────────────────────────
# Converter: cached step markdown → ChapterDoc
# ─────────────────────────────────────────────────────────────────────────────

def _sections_to_blocks(sections: list[dict], is_first_step: bool) -> tuple[list, RecapBlock | None]:
    """Convert one step's parsed sections into blocks + optional recap candidate."""
    blocks: list = []
    recap_candidate: RecapBlock | None = None

    def _build(kind: str, title: str, content: str, first_section: bool) -> list:
        nonlocal recap_candidate
        if kind == "intro":
            if is_first_step and first_section:
                # First paragraph becomes the hook; the rest stays a concept.
                paras = [p for p in content.split("\n\n") if p.strip()]
                out = []
                if paras:
                    out.append(HookBlock(text=paras[0].strip()))
                rest = "\n\n".join(paras[1:]).strip()
                if rest:
                    out.append(ConceptBlock(title=title, body_md=rest))
                return out
            # Later-step intros restate context — keep as concept only if
            # they carry real content beyond a sentence.
            if len(content) > 240:
                return [ConceptBlock(title=title, body_md=content)]
            return []
        if kind == "summary":
            recap_candidate = RecapBlock(body_md=content)
            return []
        if kind == "warning":
            return [WatchoutBlock(body_md=content)]
        if kind == "check":
            mcq = parse_mcq(content)
            # Unparseable check → keep the content visible as a concept
            return [mcq] if mcq else [ConceptBlock(title=title, body_md=content)]
        if kind == "example":
            example = parse_example(content)
            return [example] if example else [ConceptBlock(title=title, body_md=content)]
        if kind == "vocab":
            vocab = parse_vocab(content)
            return [vocab] if vocab else [ConceptBlock(title=title, body_md=content)]
        return [ConceptBlock(title=title, body_md=content)]

    for i, section in enumerate(sections):
        # Step-navigation glue ("Next Step:", "What's Next") makes no sense in
        # a single-scroll chapter — drop it entirely.
        if re.match(r"^\s*(next step|what'?s next|next lesson)\b", section["title"], re.IGNORECASE):
            continue
        kind = classify_section(section["title"])
        # Visual-json payloads become typed VisualBlocks — raw JSON never
        # stays in body_md. A section that was ONLY a visual (e.g. a
        # "Visual Aid (Optional)" heading) yields just the visual block.
        content, visual_blocks = extract_visuals(section["content"])
        if content:
            blocks.extend(_build(kind, section["title"], content, first_section=i == 0))
        blocks.extend(visual_blocks)

    return blocks, recap_candidate


def _fetch_step_rows(db, grade, subject, chapter, mode) -> dict[str, str]:
    """Return {step_title: lesson_content} for all active cached steps."""
    try:
        result = (
            db.table("lesson_cache")
            .select("step_title, lesson_content, source_type, created_at")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .eq("mode", mode)
            .eq("status", "active")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        return {}
    rows: dict[str, str] = {}
    for row in result.data or []:
        title = row.get("step_title") or ""
        content = row.get("lesson_content") or ""
        if row.get("source_type") == "NO_CONTENT" or not content.strip():
            continue
        rows.setdefault(title, content)  # newest first — keep first seen
    return rows


def _fetch_lkb_chips(grade, subject, chapter, step_title, limit=2) -> list[dict]:
    try:
        from app.services.lesson_kb_service import get_lkb_chips  # noqa: PLC0415
        return get_lkb_chips(grade, subject, chapter, step_title, limit=limit)
    except Exception:
        return []


def convert_chapter(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    mode: str = "CBSE",
) -> ChapterDoc | None:
    """
    Build a ChapterDoc from existing lesson_cache rows. Deterministic, no LLM.
    Returns None when the chapter has no usable cached steps.
    """
    db = get_content_db(grade)
    step_rows = _fetch_step_rows(db, grade, subject, chapter, mode)
    if not step_rows:
        return None

    milestones: list[Milestone] = []
    final_recap: RecapBlock | None = None
    quickcheck_questions: list[str] = []
    # Chapter-wide list of already-attached chip questions — the same LKB
    # question must never appear as a card twice in one chapter (short poem
    # chapters share top chips across steps; fewer cards is fine, repeats are not).
    attached_ask_questions: list[str] = []

    steps = get_lesson_steps(grade)
    for index, step_title in enumerate(steps):
        content = step_rows.get(step_title)
        lkb_step_title = step_title
        if content is None and step_title in _LEGACY_STEP_TITLES:
            legacy = _LEGACY_STEP_TITLES[step_title]
            content = step_rows.get(legacy)
            if content is not None:
                lkb_step_title = legacy
        if content is None:
            continue

        sections = parse_sections(content)
        if not sections:
            continue

        blocks, recap_candidate = _sections_to_blocks(sections, is_first_step=index == 0)
        if recap_candidate:
            final_recap = recap_candidate  # last step's summary wins

        quickcheck_questions.extend(
            b.question for b in blocks if isinstance(b, QuickCheckBlock)
        )

        # ── LKB chips: attach top 2, deduped against in-lesson quickchecks
        # AND against every chip already attached anywhere in this chapter ──
        for chip in _fetch_lkb_chips(grade, subject, chapter, lkb_step_title):
            question = (chip.get("question") or "").strip()
            answer = (chip.get("answer") or "").strip()
            if not question or not answer:
                continue
            if any(is_duplicate_question(question, qq) for qq in quickcheck_questions):
                continue
            if any(is_duplicate_question(question, aq) for aq in attached_ask_questions):
                continue
            attached_ask_questions.append(question)
            blocks.append(StudentsAskBlock(question=question, answer_md=answer))

        if blocks:
            milestones.append(Milestone(title=step_title, blocks=blocks))

    if not milestones:
        return None

    try:
        return ChapterDoc(
            board=board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=mode,
            source="converted",
            milestones=milestones,
            recap=final_recap,
        )
    except ValidationError as exc:
        _log.warning(
            "chapter_doc.validation_failed",
            grade=grade, subject=subject, chapter=chapter[:60], error=str(exc),
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Storage + serving
# ─────────────────────────────────────────────────────────────────────────────

def get_stored_chapter_doc(board, grade, subject, chapter, mode="CBSE") -> dict | None:
    db = get_content_db(grade)
    try:
        result = (
            db.table("lesson_chapter_doc")
            .select("id, doc, version, access_count")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .eq("mode", mode)
            .eq("status", "active")
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        try:
            db.table("lesson_chapter_doc").update(
                {"access_count": (row.get("access_count") or 0) + 1}
            ).eq("id", row["id"]).execute()
        except Exception:
            pass
        return row["doc"]
    except Exception:
        return None  # table may not exist yet — caller falls back


def store_chapter_doc(doc: ChapterDoc) -> bool:
    db = get_content_db(doc.grade)
    try:
        payload = {
            "board": doc.board,
            "grade": doc.grade,
            "subject": doc.subject,
            "chapter": doc.chapter,
            "mode": doc.mode,
            "version": doc.version,
            "source": doc.source,
            "doc": doc.model_dump(),
            "status": "active",
        }
        existing = (
            db.table("lesson_chapter_doc")
            .select("id")
            .eq("grade", doc.grade)
            .eq("subject", doc.subject)
            .eq("chapter", doc.chapter)
            .eq("mode", doc.mode)
            .limit(1)
            .execute()
        )
        if existing.data:
            db.table("lesson_chapter_doc").update(payload).eq("id", existing.data[0]["id"]).execute()
        else:
            db.table("lesson_chapter_doc").insert(payload).execute()
        return True
    except Exception as exc:
        _log.warning("chapter_doc.store_failed", grade=doc.grade, chapter=doc.chapter[:60], error=str(exc))
        return False


def get_or_convert_chapter_doc(board, grade, subject, chapter, mode="CBSE") -> dict | None:
    """
    Serving entry point: stored doc if present, else convert-and-store from
    lesson_cache. Never calls the LLM; returns None when nothing is cached.
    """
    stored = get_stored_chapter_doc(board, grade, subject, chapter, mode)
    if stored:
        return stored

    doc = convert_chapter(board, grade, subject, chapter, mode)
    if doc is None:
        return None
    store_chapter_doc(doc)
    return doc.model_dump()
