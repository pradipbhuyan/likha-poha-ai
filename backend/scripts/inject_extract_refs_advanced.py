#!/usr/bin/env python3
"""
Inject Extract-Ref Citation Popups into Grade 9 Advanced Maths/Science Lessons
================================================================================
Backfills the platform's existing ```extract-ref``` citation-popup
mechanism (ExtractPopupBlock.jsx) onto already-ingested Advanced
Maths/Science lesson content, so bare citations like "Example 15(iv)",
"Activity 9.1", or "Quick Check 3" have an actual clickable popup showing
the real source text, instead of a dangling reference with nothing to
look up.

Usage:
    cd backend
    python3 scripts/inject_extract_refs_advanced.py --subject Science
    python3 scripts/inject_extract_refs_advanced.py --subject Maths
    python3 scripts/inject_extract_refs_advanced.py --subject Science --chapter "Advanced - Structure of Atom"
    python3 scripts/inject_extract_refs_advanced.py --subject Science --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prepare_gpt55_prompts_advanced import SUBJECT_CONFIG, extract_text_pages, GRADE  # noqa: E402
from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

BOARD = "CBSE"
MODE = "CBSE"
REQUIRED_LESSON_STEPS = [
    "Concept introduction", "Core explanation", "Worked examples",
    "Exam-style problems", "Revision and recap",
]


def _clean_block(text, max_chars=1400):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " ..."
    return text


def parse_maths_citations(pdf_text):
    """Extract 'Example N' blocks and 'Exercise N.N, Question M' items
    from the Maths source PDF text."""
    citations = {}
    example_re = re.compile(
        r"Example\s+(\d+)\s*[:.]?\s*(.*?)(?=\n?\s*Example\s+\d+\s*[:.]|\n?\s*EXERCISE\s+\d+\.\d+|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in example_re.finditer(pdf_text):
        num = m.group(1)
        body = _clean_block(m.group(2))
        if len(body) > 20:
            citations["Example " + num] = body

    exercise_section_re = re.compile(
        r"EXERCISE\s+(\d+\.\d+)([\s\S]*?)(?=EXERCISE\s+\d+\.\d+|\Z)",
        re.IGNORECASE,
    )
    for sec_m in exercise_section_re.finditer(pdf_text):
        section_num = sec_m.group(1)
        for q_num, q_text in _extract_numbered_items(sec_m.group(2)):
            label = "Exercise " + section_num + ", Question " + q_num
            citations[label] = q_text

    return citations


def _extract_numbered_items(section_text, max_items=30):
    """Split a 'Quick Check' or 'Check Your Understanding' section's body
    into its numbered items. Different chapters use different numbering
    punctuation: '1. text', '1) text', or '1.text' (no space) all occur
    across the source PDFs, so both '.' and ')' terminators are accepted."""
    items = []
    item_re = re.compile(r"(?:^|\n)\s*(\d{1,2})[.)]\s*(.*?)(?=\n\s*\d{1,2}[.)]\s|\Z)", re.DOTALL)
    for m in item_re.finditer(section_text):
        num = m.group(1)
        text = _clean_block(m.group(2), max_chars=500)
        if len(text) > 5:
            items.append((num, text))
        if len(items) >= max_items:
            break
    return items


def parse_science_citations(pdf_text):
    """Extract 'Activity N.N' blocks, 'Quick Check' numbered items, and
    'Check Your Understanding' numbered items from the Science source
    PDF text. Quick Check / Check Your Understanding sections repeat
    per-chapter-section without their own section numbers, so their
    items are labelled sequentially per occurrence: the first "Quick
    Check" section's items become "Quick Check 1", "Quick Check 2", ...;
    the SECOND "Quick Check" section restarts at "Quick Check 1" again
    (matching how the generated lesson text cites them, e.g. "Quick
    Check 3 in Section 3.1" always resets per section)."""
    citations = {}

    activity_re = re.compile(
        r"Activity\s+(\d+\.\d+)\s*[:.]?\s*(.*?)(?=\n?\s*Activity\s+\d+\.\d+|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in activity_re.finditer(pdf_text):
        num = m.group(1)
        body = _clean_block(m.group(2))
        if len(body) > 20:
            citations["Activity " + num] = body

    quick_check_re = re.compile(
        r"Quick Check\s*[:.]?\s*(.*?)(?=\n\s*(?:Quick Check|Check Your Understanding|\d+\.\d+\s+[A-Z]|\Z))",
        re.IGNORECASE | re.DOTALL,
    )
    for m in quick_check_re.finditer(pdf_text):
        for num, text in _extract_numbered_items(m.group(1)):
            label = "Quick Check " + num
            if label not in citations:
                citations[label] = text

    cyu_re = re.compile(
        r"Check Your Understanding\s*[:.]?\s*(.*?)(?=\n\s*(?:Quick Check|Check Your Understanding|\Z))",
        re.IGNORECASE | re.DOTALL,
    )
    for m in cyu_re.finditer(pdf_text):
        for num, text in _extract_numbered_items(m.group(1)):
            label = "Check Your Understanding Q" + num
            if label not in citations:
                citations[label] = text
            alt_label = "Check Your Understanding " + num
            if alt_label not in citations:
                citations[alt_label] = text

    return citations


def parse_citations_for_subject(subject_key, pdf_text):
    if subject_key == "Maths":
        return parse_maths_citations(pdf_text)
    return parse_science_citations(pdf_text)


def find_citation_for_line(line, citations):
    """Return (label, text) of the first citation dict entry whose label
    text appears (case-insensitively, allowing minor punctuation
    differences) inside the given line, else None."""
    low = line.lower()
    for label in citations:
        if label.lower() in low:
            return label, citations[label]
    return None


EXTRACT_FENCE_TEMPLATE = "```extract-ref\n{payload}\n```"


def build_extract_fence(citation, extract_text, note=""):
    payload = json.dumps(
        {"citation": citation, "extract_text": extract_text, "note": note},
        ensure_ascii=False,
    )
    return EXTRACT_FENCE_TEMPLATE.format(payload=payload)


def _skip_existing_fence(lines, start_index):
    """Given the index right after a 'Question:' line, if the next
    non-blank line(s) form an existing ```extract-ref ... ``` fence,
    return the index just past that fence (so it can be dropped/replaced
    by the caller); otherwise return start_index unchanged."""
    i = start_index
    # skip a single blank line, if present, before the fence
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and lines[i].strip().startswith("```extract-ref"):
        fence_start = i
        i += 1
        while i < len(lines) and lines[i].strip() != "```":
            i += 1
        if i < len(lines):
            i += 1  # consume the closing ```
        return fence_start, i
    return None, start_index


def inject_into_content(content, citations, chapter_name):
    """Scan 'Question:' lines inside the markdown content; for each one
    that mentions a known citation label, insert (or REPLACE, if a stale
    one already exists) a matching ```extract-ref``` fence right after
    it. Replacing rather than skipping matters when the underlying PDF
    text extraction was fixed after the first injection pass (e.g. the
    Symbol-font-glyph fix), since old fences would otherwise keep their
    garbled text forever. Returns (new_content, inserted_count)."""
    lines = content.split("\n")
    out = []
    inserted = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        is_question_line = line.strip().lower().startswith("question:")
        if is_question_line:
            fence_start, resume_index = _skip_existing_fence(lines, i + 1)
            found = find_citation_for_line(line, citations)
            if found:
                label, text = found
                fence = build_extract_fence(label, text, note=chapter_name)
                out.append("")
                out.append(fence)
                inserted += 1
                i = resume_index
                continue
            elif fence_start is not None:
                # No valid citation for this line under the corrected
                # citation set, but a fence exists from a previous run —
                # this fence is now known-stale (e.g. it pointed to the
                # wrong chapter's content due to a since-fixed page-range
                # spillover bug). Drop it entirely rather than leaving
                # incorrect information visible to students.
                i = resume_index
                continue
        i += 1
    return "\n".join(out), inserted


def _trim_leading_spillover(pdf_text, chapter_name):
    """The page-range slices used for each chapter sometimes start a few
    lines into the PREVIOUS chapter's trailing content (e.g. its final
    'Check Your Understanding' section spills onto the first page of the
    next chapter). Citation parsing must not pick up that leftover
    content and mislabel it as belonging to THIS chapter. This trims
    everything before the first strong match of the chapter's own title
    words, so only text that is actually part of this chapter is
    searched for citations. Falls back to the untrimmed text if no
    confident title match is found (better to risk one false positive
    than to silently return zero chapter text)."""
    # Derive a short, distinctive title fragment from the chapter name
    # (drop the "Advanced - " prefix and any parenthetical/colon suffix).
    core = re.sub(r"^Advanced\s*-\s*", "", chapter_name, flags=re.IGNORECASE)
    core = re.split(r"[:(]", core)[0].strip()
    if not core:
        return pdf_text
    # Build a tolerant regex: exact phrase, case-insensitive, allowing
    # normal PDF line-wrap whitespace between words.
    words = re.escape(core).replace(r"\ ", r"\s+")
    title_re = re.compile(words, re.IGNORECASE)
    matches = list(title_re.finditer(pdf_text))
    if not matches:
        return pdf_text
    # Use the LAST match in the first quarter of the text (titles usually
    # appear near the top of a chapter's own pages; picking the last
    # such match skips over any early false-positive substring hits).
    cutoff = max(1, len(pdf_text) // 4)
    candidates = [m for m in matches if m.start() <= cutoff]
    chosen = candidates[-1] if candidates else matches[0]
    return pdf_text[chosen.start():]


def process_chapter(subject_key, chapter_name, start, end, dry_run, force):
    cfg = SUBJECT_CONFIG[subject_key]
    pdf_path = cfg["pdf_path"]
    subject_name = cfg["subject_name"]

    print("\n  Chapter: " + chapter_name)
    try:
        pdf_text = extract_text_pages(pdf_path, start, end)
    except Exception as e:
        print("    [error] could not extract PDF text: " + str(e))
        return

    pdf_text = _trim_leading_spillover(pdf_text, chapter_name)
    citations = parse_citations_for_subject(subject_key, pdf_text)
    print("    Parsed " + str(len(citations)) + " citation(s) from source PDF.")
    if not citations:
        print("    [skip] No citations parsed; nothing to inject.")
        return

    total_inserted = 0
    for step_title in REQUIRED_LESSON_STEPS:
        cache_key = make_lesson_cache_key(
            board=BOARD, grade=GRADE, subject=subject_name, chapter=chapter_name,
            mode=MODE, step_title=step_title, teacher_persona="",
        )
        row = get_cached_lesson(cache_key, grade=GRADE)
        if not row:
            print("    [warn] no cached row for step: " + step_title)
            continue
        content = row.get("lesson_content") if isinstance(row, dict) else None
        if not content:
            print("    [warn] empty content for step: " + step_title)
            continue

        new_content, inserted = inject_into_content(content, citations, chapter_name)
        content_changed = new_content != content
        if inserted == 0 and not content_changed:
            print("    [" + step_title + "] no new citations found to link.")
            continue

        total_inserted += inserted
        if inserted > 0:
            print("    [" + step_title + "] inserted " + str(inserted) + " extract-ref popup(s).")
        else:
            print("    [" + step_title + "] removed stale/invalid extract-ref popup(s).")

        if dry_run:
            continue

        store_lesson_cache(
            cache_key=cache_key,
            lesson_content=new_content,
            source_type="MANUAL",
            board=BOARD, grade=GRADE, subject=subject_name, chapter=chapter_name,
            mode=MODE, step_title=step_title, teacher_persona="",
            practice_questions=[],
        )

    print("    Total popups inserted: " + str(total_inserted))

    if not dry_run and total_inserted > 0:
        try:
            from app.services.grade_db_router import get_content_db  # noqa: PLC0415
            db = get_content_db(GRADE)
            db.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
                "subject", subject_name
            ).eq("chapter", chapter_name).execute()
            print("    Invalidated stale lesson_chapter_doc for this chapter.")
        except Exception as e:
            print("    [warn] could not invalidate chapter doc cache: " + str(e))


def main():
    parser = argparse.ArgumentParser(description="Inject extract-ref citation popups into Advanced chapters")
    parser.add_argument("--subject", required=True, choices=["Maths", "Science"])
    parser.add_argument("--chapter", default=None, help="Only process this exact chapter name")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cfg = SUBJECT_CONFIG[args.subject]
    chapters = cfg["chapters"]

    print("\n  Inject Extract-Ref Popups: Grade 9 / " + cfg["subject_name"])
    print("  Mode: " + ("DRY RUN" if args.dry_run else "LIVE WRITE"))

    for chapter_name, start, end in chapters:
        if args.chapter and chapter_name != args.chapter:
            continue
        process_chapter(args.subject, chapter_name, start, end, args.dry_run, args.force)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
