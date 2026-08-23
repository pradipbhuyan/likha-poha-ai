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
    ExploreMoreBlock,
    FreeTextQABlock,
    HookBlock,
    KeyTerm,
    Milestone,
    QuickCheckBlock,
    RecapBlock,
    StudentsAskBlock,
    SuggestedImage,
    TextbookImageBlock,
    VisualBlock,
    VocabBlock,
    WatchoutBlock,
)
from app.services.grade_db_router import get_content_db
from app.services.lesson_kb_service import _get_lesson_steps as get_lesson_steps
from app.services.logger_service import get_logger

_log = get_logger("services.chapter_doc")

# Steps whose cached rows may exist under a legacy title (pre-rename prewarm).
# Maps a CANONICAL step title (from get_lesson_steps()/_get_lesson_steps())
# to an alternate lesson_cache.step_title to try if the exact canonical
# title has no row. Needed because Grade 4/5's canonical curriculum uses
# a simplified 3-step structure (What We Learn / Worked Examples / Recap
# — see lesson_kb_service._get_lesson_steps()), but the standard GPT-5.5
# chapter-authoring pipeline (prepare_gpt55_prompts.py) always generates
# the full 5-step structure (Concept introduction / Core explanation /
# Worked examples / Exam-style problems / Revision and recap) for EVERY
# grade, including Grade 4/5. Without this mapping, freshly-ingested
# Grade 4/5 GPT-5.5 content is silently invisible to students — only 2 of
# 5 generated steps ("What We Learn"->none, "Worked Examples"->none,
# "Recap"->none) would exact-match, confirmed live for Grade 5 English
# "1. Papa's Spectacles" (10-chapter GPT-5.5 batch on 2026-07-29): only
# very old pre-GPT-5.5 rows under the literal "What We Learn"/"Recap"
# titles were being served, and "Worked Examples" (capital E, the
# canonical title) never matched the stored "Worked examples" (lowercase
# e) title at all. This intentionally leaves 2 of the 5 generated steps
# ("Core explanation", "Exam-style problems") unused for Grade 4/5 —
# consistent with that grade band's deliberately simpler 3-step design,
# not a bug; the content still exists in lesson_cache/manifests for any
# future curriculum change, just not rendered to young learners today.
_LEGACY_STEP_TITLES = {
    "Exam-style problems": "Practice questions",
    "What We Learn": "Concept introduction",
    "Worked Examples": "Worked examples",
    "Recap": "Revision and recap",
}


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
    """Map a section title to a block category — port of getSectionType().

    Hindi patterns mirror the frontend's LessonSections.jsx getSectionType()
    (see scripts/prepare_gpt55_prompts.py HEADING_SETS["hi"]:
    आप क्या सीखेंगे, सरल व्याख्या, चरण-दर-चरण विवरण, हल किया गया उदाहरण,
    सामान्य भूल, शीघ्र जाँच प्रश्न, सारांश). Without these, every Hindi
    "check" section (शीघ्र जाँच प्रश्न) fell through to the generic
    "concept" classification, which meant parse_freetext_qa() never ran
    for Hindi Quick check questions — the whole "Question: ... Answer:
    ... Explanation: ..." text rendered as one unbroken sentence instead
    of parsing into a proper FreeTextQABlock with each part on its own
    line. Confirmed live for every Grade 10 Hindi chapter (user-reported
    screenshot)."""
    title = title or ""
    t = title.lower()
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
    # Hindi patterns (checked against the ORIGINAL-case title — Devanagari
    # has no case folding, so this uses `title`, not the lowercased `t`).
    if "आप क्या सीखेंगे" in title or "परिचय" in title:
        return "intro"
    if "सरल व्याख्या" in title or "मुख्य व्याख्या" in title or "विवरण" in title:
        return "concept"
    if "हल किया गया उदाहरण" in title or "उदाहरण" in title:
        return "example"
    if "सामान्य भूल" in title or "भूल" in title or "चेतावनी" in title:
        return "warning"
    if "जाँच प्रश्न" in title or "अभ्यास प्रश्न" in title or "प्रश्न" in title:
        return "check"
    if "सारांश" in title or "पुनरावलोकन" in title:
        return "summary"
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
# Free-text Q&A parsing — "Question: ... Answer: ... Explanation: ..." that
# does NOT follow the lettered-options MCQ format (parse_mcq() above).
# ─────────────────────────────────────────────────────────────────────────────

_FREETEXT_QA_RE = re.compile(
    r"question\s*:\s*(?P<question>.+?)\s*"
    r"answer\s*:\s*(?P<answer>.+?)\s*"
    r"(?:explanation\s*:\s*(?P<explanation>.+))?$",
    re.IGNORECASE | re.DOTALL,
)


def parse_freetext_qa(text: str) -> FreeTextQABlock | None:
    """Parse a "Question: ... Answer: ... Explanation: ..." triple that does
    NOT have lettered A)/B)/C)/D) options (i.e. parse_mcq() already failed
    on it). This is the common shape for open-ended Quick check questions
    in storybook/poem chapters and other humanities/language content —
    confirmed live for every Grade 5 English chapter's "Quick check
    question" section. Returns None if the text doesn't contain a
    recognisable Question:/Answer: pair at all, in which case the caller
    falls back to a plain ConceptBlock (unchanged prior behaviour)."""
    if not text:
        return None
    work = re.sub(r"^#{1,3}\s*", "", text.strip(), flags=re.MULTILINE)
    m = _FREETEXT_QA_RE.search(work)
    if not m:
        return None
    question = (m.group("question") or "").strip().replace("**", "")
    answer = (m.group("answer") or "").strip().replace("**", "")
    explanation = (m.group("explanation") or "").strip().replace("**", "")
    if not question or not answer:
        return None
    try:
        return FreeTextQABlock(question=question, answer=answer, explanation=explanation)
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


# Matches frontend/src/components/journey/chapterGlance.js's FENCE_RE — kept
# in sync deliberately, since both must agree on which block carries the
# chapter-infographic poster (that file finds it for nav-entry purposes, this
# one for insertion-order purposes).
_CHAPTER_INFOGRAPHIC_FENCE_RE = re.compile(r"```+\s*chapter-infographic", re.IGNORECASE)


def _chapter_infographic_index(blocks: list) -> int | None:
    """Index of the ConceptBlock carrying the chapter-infographic poster, if any.

    The poster must always be the last thing rendered in a milestone (it sits
    just above "Wrap-up" in both renderers). Anything appended to a
    milestone's blocks after this point — LKB chips, textbook page images —
    must be spliced in BEFORE this index, not appended past it, or those
    blocks would render below the poster instead of above it.
    """
    for i, block in enumerate(blocks):
        if getattr(block, "type", None) == "concept" and _CHAPTER_INFOGRAPHIC_FENCE_RE.search(
            getattr(block, "body_md", "") or ""
        ):
            return i
    return None


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
            if mcq:
                return [mcq]
            freetext_qa = parse_freetext_qa(content)
            if freetext_qa:
                return [freetext_qa]
            # Unparseable check → keep the content visible as a concept
            return [ConceptBlock(title=title, body_md=content)]
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


_CHAPTER_SOURCE_PREFIX_RE = re.compile(
    r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
    r"History|Geography|Political Science|Economics)\s*[-:]\s*",
    re.IGNORECASE,
)
_CHAPTER_PART_PREFIX_RE = re.compile(r"^\s*part\s*\d+\s*[-:]\s*", re.IGNORECASE)


def _strip_display_prefixes(chapter: str) -> str:
    """Strip display-only 'Part N - ' / 'Text Book - ' style prefixes that
    the student-facing dropdown adds (see app/routes/syllabus.py's
    create_part_display_label/create_source_display_label) but which are
    NOT part of the actual chapter key used in lesson_cache/rag_documents/
    rag_visual_assets for most GPT-5.5-authored chapters. Confirmed live:
    Grade 10 English's dropdown sends "Text Book - Chapter 1: A Letter to
    God" while the July 2026 GPT-5.5 content + backfilled textbook images
    are stored under the bare "Chapter 1: A Letter to God" key — without
    this fallback, the exact-match lookup below silently found only an
    older, stale, English-Text-Book-prefixed lesson_cache row from July 5
    with zero images, even though correct fresh content existed."""
    result = (chapter or "").strip()
    for _ in range(3):
        stripped = _CHAPTER_SOURCE_PREFIX_RE.sub("", _CHAPTER_PART_PREFIX_RE.sub("", result)).strip()
        if stripped == result:
            break
        result = stripped
    return result


def _fetch_step_rows(db, grade, subject, chapter, mode) -> dict[str, str]:
    """Return {step_title: lesson_content} for all active cached steps.

    Tries BOTH the display-prefix-stripped ("bare") chapter key and the
    exact chapter string as sent by the dropdown, then keeps whichever
    result set has the most recently-created row. This handles a
    confirmed-live scenario where BOTH keys have real data for the same
    chapter — e.g. Grade 10 English "A Letter to God" has old (2026-07-05)
    rows stored under the prefixed "Text Book - Chapter 1: A Letter to
    God" key AND fresh GPT-5.5 rows (2026-07-28) stored under the bare
    "Chapter 1: A Letter to God" key. A simple "exact match first, bare
    key only as a fallback-on-empty" strategy silently keeps serving the
    stale prefixed-key rows forever, since they're never empty. Preferring
    whichever key has the newest content ensures the latest ingested
    version always wins regardless of which key it happens to be under.
    """
    def _query(chapter_value: str):
        try:
            result = (
                db.table("lesson_cache")
                .select("step_title, lesson_content, source_type, created_at")
                .eq("grade", grade)
                .eq("subject", subject)
                .eq("chapter", chapter_value)
                .eq("mode", mode)
                .eq("status", "active")
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception:
            return []

    def _query_suffix(bare_value: str):
        """Fallback for the recurring 'dropdown sends bare title, but the
        GPT-5.5 batch-ingest pipeline stores lesson_cache.chapter as the
        "Chapter N: <title>" prefixed form' mismatch (confirmed live for
        Grade 11 Mathematics/Biology on 2026-07-31: chapters ingested in
        that session with NO pre-existing legacy bare-form row -- e.g.
        Chapter 10-13 Maths, most Grade 11 Biology chapters -- rendered
        "This chapter isn't available yet" because _strip_display_prefixes
        only strips 'Text Book -'/'Part N -' style labels, never a
        "Chapter N: " numeric prefix, so the exact-match candidates above
        never include the stored prefixed key at all). Uses an ilike
        suffix match (chapter LIKE '%: <bare>') so this works for any
        chapter number without having to know N in advance.
        """
        if not bare_value:
            return []
        try:
            result = (
                db.table("lesson_cache")
                .select("step_title, lesson_content, source_type, created_at")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", f"%: {bare_value}")
                .eq("mode", mode)
                .eq("status", "active")
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception:
            return []

    def _latest_created_at(rows: list[dict]) -> str:
        values = [r.get("created_at") or "" for r in rows]
        return max(values) if values else ""

    bare = _strip_display_prefixes(chapter)
    candidates = list(dict.fromkeys([bare, chapter])) if bare and bare != chapter else [chapter]

    data: list[dict] = []
    best_created_at = ""
    for candidate in candidates:
        candidate_data = _query(candidate)
        if not candidate_data:
            continue
        candidate_latest = _latest_created_at(candidate_data)
        if not data or candidate_latest > best_created_at:
            data = candidate_data
            best_created_at = candidate_latest

    if not data:
        # No exact match under any candidate key at all -- try the
        # "Chapter N: <bare>" suffix-match fallback before giving up.
        data = _query_suffix(bare or chapter)

    if not data:
        # LAST RESORT: case-insensitive exact match. Confirmed live for
        # Grade 11 English "The Ailing Planet: the Green Movement's
        # Role" and "Discovering Tut: the Saga Continues" — the
        # student-facing chapter dropdown sends these two titles with a
        # capitalised mid-title "The" (e.g. "...: The Green Movement's
        # Role"), but the chapter was ingested and stored with NCERT's
        # own printed lowercase "the" ("...: the Green Movement's
        # Role"). Every other Grade 11 English chapter title has no
        # capitalisable word after its colon, so this exact-casing
        # mismatch invisibly affected only these two specific titles —
        # both rendered a fully blank "Lessons" page (no content, no
        # error) because convert_chapter() silently returned None when
        # _fetch_step_rows() found zero rows under any case-sensitive
        # candidate key. ilike with no wildcard characters performs an
        # exact, case-INsensitive match in PostgREST, so this safely
        # recovers the correct row without ever matching a genuinely
        # different chapter title.
        for candidate in candidates:
            try:
                result = (
                    db.table("lesson_cache")
                    .select("step_title, lesson_content, source_type, created_at")
                    .eq("grade", grade)
                    .eq("subject", subject)
                    .ilike("chapter", candidate)
                    .eq("mode", mode)
                    .eq("status", "active")
                    .order("created_at", desc=True)
                    .execute()
                )
                if result.data:
                    data = result.data
                    break
            except Exception:
                continue

    rows: dict[str, str] = {}
    for row in data:
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


def _fetch_approved_visuals(board, grade, subject, chapter) -> list[dict]:
    """Return admin-approved (status="active") textbook page images for this
    chapter, ordered by page number. Never AI-generated — always real
    NCERT textbook pages extracted via rag_visual_service.backfill.

    Tries an exact chapter-string match first, then falls back to a
    suffix match (ilike '%<chapter>') — this handles the recurring
    "Chapter N: <title>" vs bare "<title>" naming mismatch between
    rag_visual_assets.chapter (usually prefixed) and lesson_cache.chapter
    (often unprefixed for GPT-5.5-authored chapters), documented in
    §4i/§4m of docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md.
    """
    try:
        from app.services.rag_visual_service import list_active_visual_assets_for_context  # noqa: PLC0415
        exact = list_active_visual_assets_for_context(
            board=board, grade=grade, subject=subject, chapter=chapter, limit=25,
        )
        if exact:
            return exact
        # Retry with the display-prefix stripped (see _strip_display_prefixes
        # docstring) — a dropdown-decorated chapter string like "Text Book -
        # Chapter 1: A Letter to God" won't exact-match rag_visual_assets rows
        # stored under the bare "Chapter 1: A Letter to God" key.
        bare = _strip_display_prefixes(chapter)
        if bare and bare != chapter:
            exact = list_active_visual_assets_for_context(
                board=board, grade=grade, subject=subject, chapter=bare, limit=25,
            )
            if exact:
                return exact
    except Exception:
        pass

    # Fallback: suffix-match on chapter string (handles "Chapter N: " prefix
    # mismatches) using the same live DB the exact lookup would have used.
    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        for candidate in dict.fromkeys([chapter, _strip_display_prefixes(chapter)]):
            if not candidate:
                continue
            result = (
                db.table("rag_visual_assets")
                .select(
                    "id,document_id,board,grade,subject,chapter,title,page_number,"
                    "asset_url,caption,nearby_text,status"
                )
                .eq("status", "active")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", f"%{candidate}")
                .order("page_number")
                .limit(25)
                .execute()
            )
            if result.data:
                return result.data
        return []
    except Exception:
        return []


_IMAGE_MATCH_STOPWORDS = {
    "the", "and", "for", "from", "this", "that", "with", "about", "chapter",
    "page", "figure", "fig", "of", "in", "on", "to", "a", "an", "is", "are",
}


def _match_visuals_to_milestone(
    visuals: list[dict],
    milestone_title: str,
    milestone_text: str,
    used_ids: set[str],
    max_per_milestone: int = 2,
) -> list[TextbookImageBlock]:
    """Score unused approved visuals by caption/nearby-text keyword overlap
    with this milestone's title+content, attach the best matches, and mark
    them used so the same image never appears in two milestones."""
    if not visuals:
        return []

    # NOTE: [a-z0-9]+ alone only matches Latin letters/digits — for
    # Devanagari-script chapters (Hindi, Sanskrit) this returned an
    # almost-empty haystack (occasional stray digits like page numbers),
    # making keyword-overlap matching effectively non-functional and
    # causing most Grade 9 Hindi milestones to get zero textbook images
    # even though dozens of admin-approved page images existed for the
    # chapter (user-reported: visuals appeared "removed" from Hindi
    # lessons). \u0900-\u097F covers the Devanagari block (used by Hindi,
    # Sanskrit, Marathi, Nepali) so both scripts are now tokenized.
    _WORD_RE = re.compile(r"[a-z0-9\u0900-\u097F]+")
    haystack_terms = {
        t for t in _WORD_RE.findall(f"{milestone_title} {milestone_text}".lower())
        if len(t) > 2 and t not in _IMAGE_MATCH_STOPWORDS
    }
    if not haystack_terms:
        return []

    scored = []
    for visual in visuals:
        vid = visual.get("id")
        if not vid or vid in used_ids:
            continue
        visual_terms = {
            t for t in _WORD_RE.findall(
                f"{visual.get('caption', '')} {visual.get('nearby_text', '')}".lower(),
            )
            if len(t) > 2 and t not in _IMAGE_MATCH_STOPWORDS
        }
        score = len(haystack_terms & visual_terms)
        if score > 0:
            scored.append((score, visual))

    scored.sort(key=lambda item: (-item[0], item[1].get("page_number") or 0))

    blocks: list[TextbookImageBlock] = []
    for score, visual in scored[:max_per_milestone]:
        try:
            blocks.append(TextbookImageBlock(
                asset_url=visual["asset_url"],
                caption=visual.get("caption") or "",
                page_number=visual.get("page_number"),
            ))
            used_ids.add(visual["id"])
        except Exception:
            continue
    return blocks


import json as _json_module
import re as _re_module
from pathlib import Path as _Path


def _slugify_for_manifest(text: str) -> str:
    text = _re_module.sub(r"[^\w\s-]", "", (text or "").lower())
    text = _re_module.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


_MANIFEST_ROOT = _Path(__file__).resolve().parents[1] / "data" / "chapter_manifests"


def _load_explore_more(grade: str, subject: str, chapter: str) -> ExploreMoreBlock | None:
    """Load the optional "supplementary_enrichment" object from this
    chapter's manifest file on disk (see scripts/ingest_gpt55_chapter_output.py),
    and convert it into an ExploreMoreBlock. Returns None if no manifest
    exists or it has no enrichment data — this is an optional, additive
    section and its absence never blocks chapter rendering."""
    try:
        manifest_path = (
            _MANIFEST_ROOT
            / _slugify_for_manifest(grade)
            / _slugify_for_manifest(subject)
            / f"{_slugify_for_manifest(chapter)}.json"
        )
        if not manifest_path.exists():
            return None
        manifest = _json_module.loads(manifest_path.read_text(encoding="utf-8"))
        enrichment = manifest.get("supplementary_enrichment")
        if not enrichment:
            return None
        notes = enrichment.get("beyond_the_textbook") or []
        images_raw = enrichment.get("suggested_web_images") or []
        images = [SuggestedImage(**img) for img in images_raw if isinstance(img, dict)]
        if not notes and not images:
            return None
        return ExploreMoreBlock(beyond_the_textbook=notes, suggested_web_images=images)
    except Exception as exc:
        _log.warning(
            "chapter_doc.explore_more_load_failed",
            grade=grade, subject=subject, chapter=chapter[:60], error=str(exc),
        )
        return None


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

    # Admin-approved NCERT textbook page images for this chapter (never
    # AI-generated). Fetched once per chapter, matched per-milestone below,
    # and tracked in used_visual_ids so no page appears in two milestones.
    approved_visuals = _fetch_approved_visuals(board, grade, subject, chapter)
    used_visual_ids: set[str] = set()

    steps = get_lesson_steps(grade)
    for index, step_title in enumerate(steps):
        lkb_step_title = step_title
        content = None
        # Prefer the mapped alternate title FIRST (e.g. Grade 4/5's
        # canonical "Worked Examples" maps to the GPT-5.5 pipeline's
        # standard "Worked examples") — this is deliberately checked
        # BEFORE the literal canonical title, because a chapter can have
        # BOTH an old pre-GPT-5.5 row stored under the literal canonical
        # title (e.g. "What We Learn", "Recap" from an earlier prewarm
        # pass) AND fresh GPT-5.5 content stored under the mapped title
        # (e.g. "Concept introduction", "Revision and recap"). Checking
        # the literal title first would silently keep serving that old
        # stale content forever, exactly as confirmed live for Grade 5
        # English "1. Papa's Spectacles" and its sibling chapters on
        # 2026-07-29 — only 1 of 3 canonical steps ("Worked Examples")
        # actually had zero pre-existing legacy row, so it alone updated
        # correctly on the first version of this fallback; "What We
        # Learn" and "Recap" kept resolving to old July-10 rows because
        # those literal titles matched directly before the mapped
        # alternate was ever tried.
        if step_title in _LEGACY_STEP_TITLES:
            mapped = _LEGACY_STEP_TITLES[step_title]
            content = step_rows.get(mapped)
            if content is not None:
                lkb_step_title = mapped
        if content is None:
            content = step_rows.get(step_title)
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
        new_chip_blocks = []
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
            new_chip_blocks.append(StudentsAskBlock(question=question, answer_md=answer))

        # ── Textbook images: attach best-matching approved page(s) for this
        # milestone's topic, placed right after the concept/example content ──
        image_blocks = []
        if approved_visuals:
            milestone_text = " ".join(
                getattr(b, "body_md", "") or getattr(b, "text", "") or ""
                for b in blocks
            )
            image_blocks = _match_visuals_to_milestone(
                approved_visuals, step_title, milestone_text, used_visual_ids,
            )

        # The chapter-at-a-glance poster must always be the last thing in a
        # milestone (it sits just above "Wrap-up"). Splice new chips/images in
        # BEFORE it rather than appending past it, so any other lesson images
        # move above the poster instead of rendering below it.
        poster_index = _chapter_infographic_index(blocks)
        insert_at = poster_index if poster_index is not None else len(blocks)
        blocks[insert_at:insert_at] = new_chip_blocks + image_blocks

        if blocks:
            milestones.append(Milestone(title=step_title, blocks=blocks))

    # Fallback: if this chapter has genuine admin-approved textbook page
    # images but keyword-overlap matching (_match_visuals_to_milestone)
    # attached zero of them to ANY milestone, distribute the images
    # round-robin across milestones instead of silently showing 0 images.
    # This happens for source PDFs that use a legacy, non-Unicode
    # glyph-mapped font (confirmed for several older NCERT Hindi "Vitan"
    # series books) — rag_visual_assets.nearby_text extracts as gibberish
    # Latin-lookalike characters rather than real Devanagari, so the
    # Devanagari-aware keyword-overlap scorer in _match_visuals_to_milestone
    # can never find any term overlap even though real, useful page images
    # exist and were already verified live in rag_visual_assets.
    if approved_visuals and not used_visual_ids and milestones:
        per_milestone = 2
        vis_iter = iter(approved_visuals)
        for milestone in milestones:
            poster_index = _chapter_infographic_index(milestone.blocks)
            for _ in range(per_milestone):
                visual = next(vis_iter, None)
                if visual is None:
                    break
                try:
                    image_block = TextbookImageBlock(
                        asset_url=visual["asset_url"],
                        caption=visual.get("caption") or "",
                        page_number=visual.get("page_number"),
                    )
                    # Keep the poster last in the milestone (see
                    # _chapter_infographic_index) — insert before it rather
                    # than appending past it, tracking the shift as each
                    # image is added.
                    if poster_index is not None:
                        milestone.blocks.insert(poster_index, image_block)
                        poster_index += 1
                    else:
                        milestone.blocks.append(image_block)
                except Exception:
                    continue

    if not milestones:
        return None

    explore_more = _load_explore_more(grade, subject, chapter)

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
            explore_more=explore_more,
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
            # Case-insensitive fallback -- see the matching note in
            # _fetch_step_rows() above for the confirmed-live scenario
            # (Grade 11 English titles with a capitalisable word after a
            # colon) this recovers.
            result = (
                db.table("lesson_chapter_doc")
                .select("id, doc, version, access_count")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", chapter)
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


def invalidate_stored_chapter_doc(grade, subject, chapter, mode="CBSE") -> int:
    """Delete any stored lesson_chapter_doc row(s) for this exact chapter.

    Used by the student-facing "Refresh lesson" button (and by the
    ingestion scripts) so a stale converted document is never served
    indefinitely — see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4i/§4o
    for why this reconversion step is otherwise easy to silently miss.
    Returns the number of rows deleted (0 if none existed).
    """
    db = get_content_db(grade)
    try:
        result = (
            db.table("lesson_chapter_doc")
            .delete()
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .eq("mode", mode)
            .execute()
        )
        return len(result.data or [])
    except Exception as exc:
        _log.warning(
            "chapter_doc.invalidate_failed",
            grade=grade, chapter=chapter[:60], error=str(exc),
        )
        return 0


def invalidate_stored_chapter_doc_variants(grade, subject, chapter, mode="CBSE") -> int:
    """Delete the exact-match row AND every other stored row that resolves to
    the same bare chapter (see Trap 9 in docs/CHAPTER_INFOGRAPHIC_FEATURE.md).

    For a split-part grade, `/api/syllabus` sends students a "Part N - "
    (or "Text Book - ") prefixed chapter string, which caches to a SEPARATE
    lesson_chapter_doc row from whatever bare/differently-prefixed string an
    authoring script refreshes with `invalidate_stored_chapter_doc()`. A row
    keyed on one variant can go stale independently of a row keyed on
    another, even though both resolve to the same underlying lesson_cache
    content via `_strip_display_prefixes()`. Confirmed live 2026-08-21: Grade
    7 Social Science Part 1 Chapters 1-2 had a freshly-refreshed bare-keyed
    doc with the poster fence, but a stale prefixed-keyed doc with no fence
    at all, served to students via the syllabus dropdown.

    This deletes every row for this grade/subject/mode whose chapter string
    shares the same bare form, so each reconverts fresh (fence included) on
    its own next request — no per-variant refresh call needed. Returns the
    total number of rows deleted.
    """
    bare = _strip_display_prefixes(chapter)
    db = get_content_db(grade)
    try:
        result = (
            db.table("lesson_chapter_doc")
            .select("chapter")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("mode", mode)
            .execute()
        )
    except Exception as exc:
        _log.warning(
            "chapter_doc.invalidate_variants_lookup_failed",
            grade=grade, chapter=chapter[:60], error=str(exc),
        )
        return invalidate_stored_chapter_doc(grade, subject, chapter, mode=mode)

    variants = {
        row["chapter"] for row in (result.data or [])
        if _strip_display_prefixes(row["chapter"]) == bare
    }
    variants.add(chapter)

    deleted = 0
    for variant in variants:
        deleted += invalidate_stored_chapter_doc(grade, subject, variant, mode=mode)
    return deleted


def get_or_convert_chapter_doc(
    board, grade, subject, chapter, mode="CBSE", force_refresh: bool = False,
) -> dict | None:
    """
    Serving entry point: stored doc if present, else convert-and-store from
    lesson_cache. Never calls the LLM; returns None when nothing is cached.

    force_refresh=True skips the stored doc and always reconverts fresh
    from the current lesson_cache content, overwriting whatever was
    stored before — this is what the "Refresh lesson" button uses so a
    student can self-serve a fix without needing an admin script run.
    """
    if force_refresh:
        invalidate_stored_chapter_doc(grade, subject, chapter, mode)
    else:
        stored = get_stored_chapter_doc(board, grade, subject, chapter, mode)
        if stored:
            return stored

    doc = convert_chapter(board, grade, subject, chapter, mode)
    if doc is None:
        return None
    store_chapter_doc(doc)
    return doc.model_dump()
