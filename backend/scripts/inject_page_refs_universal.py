#!/usr/bin/env python3
"""
Universal Page-Image Citation Linker (ALL grades / ALL subjects)
====================================================================
Generalises the Grade-10-Science-only `inject_extract_refs_grade10_
science.py` into a single, database-driven script that works for ANY
chapter in ANY grade/subject, with no dependency on local PDF files.

Why this works without touching local PDFs at all:
  Every PDF ever uploaded via the RAG pipeline already has EVERY page
  pre-rendered as a full-page image and stored in Supabase Storage,
  recorded in `rag_visual_assets` (columns: document_id, page_number,
  asset_url, nearby_text) -- regardless of curation status
  (active/needs_review). `nearby_text` contains the actual OCR/extracted
  text for that page, so we can locate any citation string (e.g.
  "Activity 2.1", "Exercise 12.2", "Example 3") entirely from the
  database, without opening a single local PDF.

What this script does, for every (grade, subject, chapter) that has at
least one active `lesson_cache` row:
  1. Scans the chapter's 5 lesson_cache steps for citation-like strings
     using a broad multi-pattern regex (Activity/Exercise/Example/
     Case Study/Figure + number, standalone "Example N", "Q<N>", etc.)
  2. For each unique citation found, searches `rag_visual_assets.
     nearby_text` for the matching document to find which page number
     contains it (normalizing decorative repeated-character headings
     the same way the Grade-10-Science version did).
  3. If found, replaces/inserts an ```extract-ref``` fence immediately
     after EVERY line that mentions that citation (not just lines
     starting with "Question:" -- bare narrative mentions like "In
     Activity 2.1, a student places..." are just as important to link).
  4. Writes the updated content back to lesson_cache and invalidates
     the chapter's cached Chapter Journey doc.

Usage:
    cd backend
    # Dry run across EVERYTHING (just reports counts, writes nothing):
    python3 scripts/inject_page_refs_universal.py --dry-run

    # Live run across everything:
    python3 scripts/inject_page_refs_universal.py

    # Scope to one grade and/or subject:
    python3 scripts/inject_page_refs_universal.py --grade "Grade 9" --subject "Science"
    python3 scripts/inject_page_refs_universal.py --grade "Grade 9" --subject "Science" --chapter "Chapter 2: Cell: The Building Block of Life"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

REQUIRED_LESSON_STEPS = [
    "Concept introduction", "Core explanation", "Worked examples",
    "Exam-style problems", "Revision and recap",
]

# Decorative-heading normalizer (same rationale as the Grade 10 Science
# version): some NCERT PDFs render headings with each character
# repeated ~5 times for a bold/decorative effect. Collapsing repeats
# lets both the heading form and inline mentions match consistently.
_REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")


def normalize_decorative_headings(text: str) -> str:
    return _REPEATED_CHAR_RE.sub(r"\1", text)


# Broad citation patterns covering every NCERT citation style seen
# across subjects so far: "Activity N.N", "Exercise N.N", "Example N"
# (or "Example N.N"), "Case Study N", "Figure/Fig. N.N". Each pattern
# captures a normalized label used both to search lesson content AND
# to search rag_visual_assets.nearby_text.
#
# Grade 5 Maths (and other primary-stage NCERT books) use a DIFFERENT
# citation grammar with no decimal numbering at all -- section names
# such as "Let Us Do", "Let Us Solve", "Let Us Think", "Let Us Find",
# "Let Us Divide", "Let Us Compare", "Let Us Multiply", plain "Activity
# N" (integer, no decimal), and "Try This" -- confirmed live: 0 of 10
# Grade 5 Maths chapters matched any pattern above even though every
# chapter's lesson content repeatedly cites these exact section names
# (e.g. "NCERT Let Us Solve Question 4", "NCERT Activity 3"). The
# patterns below capture the BASE heading only (stripping any trailing
# "Question N"/"Q N" suffix) because that bare heading is what actually
# appears as the printed page heading in rag_visual_assets.nearby_text
# -- the question number itself is usually printed as a plain "1." or
# "4." list marker, not literally the word "Question 4".
_CITATION_PATTERNS = [
    (re.compile(r"\bActivity\s+(\d+\.\d+)\b", re.IGNORECASE), "Activity {0}"),
    (re.compile(r"\bExercise\s+(\d+\.\d+)\b", re.IGNORECASE), "Exercise {0}"),
    (re.compile(r"\bExample\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE), "Example {0}"),
    (re.compile(r"\bCase\s+Study\s+(\d+)\b", re.IGNORECASE), "Case Study {0}"),
    (re.compile(r"\bFig(?:ure)?\.?\s+(\d+\.\d+)\b", re.IGNORECASE), "Figure {0}"),
    # Primary-stage (Grade 3-5) NCERT citation grammar -- no decimals.
    (re.compile(r"\bActivity\s+(\d+)\b(?!\.\d)", re.IGNORECASE), "Activity {0}"),
    (
        re.compile(
            r"\bLet\s+Us\s+(Do|Solve|Think|Find|Divide|Compare|Multiply|"
            r"Learn(?:\s+to\s+Divide)?|Draw|Estimate|Try|Explore|Play)\b",
            re.IGNORECASE,
        ),
        "Let Us {0}",
    ),
    (re.compile(r"\bTry\s+This\b", re.IGNORECASE), "Try This"),
]


def find_citations_in_text(text: str) -> set[str]:
    """Return the set of normalized citation labels mentioned anywhere
    in a piece of lesson markdown."""
    found = set()
    for pattern, label_fmt in _CITATION_PATTERNS:
        for m in pattern.finditer(text):
            # Patterns with no capture group (e.g. "Try This") have a
            # fixed label_fmt with no {0} placeholder to fill.
            if m.groups():
                found.add(label_fmt.format(m.group(1)))
            else:
                found.add(label_fmt)
    return found


# rag_documents.chapter is consistently stored in the PREFIXED form
# ("Chapter 2: Cell: The Building Block of Life"), but lesson_cache
# rows for the same chapter are frequently stored in the BARE/
# unprefixed form ("Cell: The Building Block of Life" or even just
# "Cell") -- this exact mismatch was already documented as a recurring
# issue in GPT55_LESSON_UPDATE_STATUS.md (§Hindi chapters 7-12 session)
# and is confirmed here again live for Grade 9 Science: an exact
# equality match on `chapter` found 0 rows for 14 of Grade 9 Science's
# chapters even though their rag_documents rows clearly exist under the
# "Chapter N: ..." form. This function therefore falls back to a
# suffix/substring match so both naming conventions resolve to the
# same document(s).
_CHAPTER_NUM_PREFIX_RE = re.compile(r"^\s*Chapter\s+\d+\s*[:\-]\s*", re.IGNORECASE)


def _bare_chapter_title(chapter: str) -> str:
    """Strip a leading 'Chapter N:' prefix, if present, to get the bare
    title used for suffix-matching against lesson_cache's chapter form."""
    return _CHAPTER_NUM_PREFIX_RE.sub("", chapter or "").strip()


def find_document_ids(grade: str, subject: str, chapter: str, board: str = "CBSE") -> list[int]:
    """A chapter can have more than one rag_documents row (e.g. main
    textbook + supplementary reader); check all of them for the page
    image of a given citation. Tries an exact match first, then falls
    back to a bare-title suffix match to handle the prefixed/unprefixed
    chapter-naming mismatch between rag_documents and lesson_cache.

    NOTE: intentionally does NOT filter by `board` -- confirmed live
    that rag_documents.board can legitimately differ from
    lesson_cache.board for the same real-world book (e.g. Grade 9
    English "Kaveri" is stored as board='State Board' in
    rag_documents but the corresponding lesson_cache rows were seeded
    with board='CBSE'). Since grade+subject+chapter is already a
    highly specific key, filtering on board would only produce false
    negatives here, not prevent false positives."""
    try:
        r = (
            admin_client.table("rag_documents")
            .select("id")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .execute()
        )
        ids = [row["id"] for row in (r.data or [])]
        if ids:
            return ids

        # Fallback: fetch all chapters for this grade/subject and match
        # by bare title (case-insensitive), since lesson_cache's chapter
        # string may be missing the "Chapter N:" prefix that
        # rag_documents always includes.
        bare_target = _bare_chapter_title(chapter).lower()
        if not bare_target:
            return []
        all_rows = (
            admin_client.table("rag_documents")
            .select("id,chapter")
            .eq("grade", grade)
            .eq("subject", subject)
            .execute()
        ).data or []
        matched_ids = []
        for row in all_rows:
            bare_candidate = _bare_chapter_title(row["chapter"]).lower()
            if bare_candidate == bare_target or bare_candidate.endswith(bare_target) or bare_target.endswith(bare_candidate):
                matched_ids.append(row["id"])
        return matched_ids
    except Exception as e:
        print(f"    [warn] rag_documents lookup failed: {e}")
        return []


def build_citation_page_map(document_ids: list[int], citations: set[str]) -> dict:
    """For each requested citation label, search rag_visual_assets.
    nearby_text (across all given document_ids) for a page containing
    it, using the decorative-heading-normalized text so headings
    rendered with repeated characters still match."""
    if not document_ids or not citations:
        return {}

    result = {}
    try:
        rows = (
            admin_client.table("rag_visual_assets")
            .select("document_id,page_number,nearby_text,asset_url")
            .in_("document_id", document_ids)
            .order("page_number")
            .execute()
        ).data or []
    except Exception as e:
        print(f"    [warn] rag_visual_assets lookup failed: {e}")
        return {}

    for citation in citations:
        for row in rows:
            nearby = row.get("nearby_text") or ""
            if not nearby:
                continue
            normalized = normalize_decorative_headings(nearby)
            if citation.lower() in normalized.lower() and row.get("asset_url"):
                result[citation] = {
                    "page_number": row["page_number"],
                    "asset_url": row["asset_url"],
                }
                break  # first matching page wins
    return result


EXTRACT_FENCE_TEMPLATE = "```extract-ref\n{payload}\n```"


def build_extract_fence(citation, page_info, note=""):
    payload = json.dumps(
        {
            "citation": citation,
            "page_number": page_info["page_number"],
            "asset_url": page_info["asset_url"],
            "note": note,
        },
        ensure_ascii=False,
    )
    return EXTRACT_FENCE_TEMPLATE.format(payload=payload)


def _skip_existing_fence(lines, start_index):
    i = start_index
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and lines[i].strip().startswith("```extract-ref"):
        fence_start = i
        i += 1
        while i < len(lines) and lines[i].strip() != "```":
            i += 1
        if i < len(lines):
            i += 1
        return fence_start, i
    return None, start_index


def inject_into_content(content: str, citation_pages: dict, chapter_name: str) -> tuple[str, int]:
    """Insert an extract-ref fence immediately after EVERY line that
    mentions a citation we have a page image for (not just lines
    starting with "Question:" -- unlike the earlier Grade 10 Science
    version, bare narrative mentions such as "In Activity 2.1, a
    student places..." are just as important to link, since that's
    exactly the pattern the Grade 9 Science bug report showed)."""
    if not citation_pages:
        return content, 0

    lines = content.split("\n")
    out = []
    inserted = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)

        fence_start, resume_index = _skip_existing_fence(lines, i + 1)
        matched = None
        low = line.lower()
        for citation, page_info in citation_pages.items():
            if citation.lower() in low:
                matched = (citation, page_info)
                break

        if matched:
            label, page_info = matched
            fence = build_extract_fence(label, page_info, note=chapter_name)
            out.append("")
            out.append(fence)
            inserted += 1
            i = resume_index
            continue
        elif fence_start is not None:
            # No citation on this line but a stale fence follows it
            # (e.g. content was regenerated) -- drop the stale fence.
            i = resume_index
            continue

        i += 1
    return "\n".join(out), inserted


def discover_chapters(grade: str | None, subject: str | None, chapter: str | None) -> list[dict]:
    """Return every distinct (board, grade, subject, chapter) combination
    that has at least one active lesson_cache row, optionally filtered."""
    combos = {}
    grades_to_scan = [grade] if grade else [
        "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9",
        "Grade 10", "Grade 11", "Grade 12",
    ]
    for g in grades_to_scan:
        db = get_content_db(g)
        try:
            query = db.table("lesson_cache").select("board,grade,subject,chapter").eq(
                "grade", g
            ).eq("status", "active")
            if subject:
                query = query.eq("subject", subject)
            if chapter:
                query = query.eq("chapter", chapter)
            rows = query.execute().data or []
        except Exception as e:
            print(f"  [warn] could not scan lesson_cache for grade={g}: {e}")
            continue
        for row in rows:
            key = (row["board"], row["grade"], row["subject"], row["chapter"])
            combos[key] = True
    return [
        {"board": b, "grade": g, "subject": s, "chapter": c}
        for (b, g, s, c) in combos
    ]


def process_chapter(board: str, grade: str, subject: str, chapter: str, dry_run: bool) -> dict:
    """Process one chapter: find citations across its 5 lesson steps,
    resolve page images, inject fences, and invalidate the chapter doc
    cache if anything changed."""
    document_ids = find_document_ids(grade, subject, chapter, board)
    if not document_ids:
        return {"chapter": chapter, "status": "no_rag_documents"}

    # Pass 1: collect every citation mentioned across all 5 steps.
    step_contents = {}
    all_citations: set[str] = set()
    for step_title in REQUIRED_LESSON_STEPS:
        cache_key = make_lesson_cache_key(
            board=board, grade=grade, subject=subject, chapter=chapter,
            mode="CBSE", step_title=step_title, teacher_persona="",
        )
        row = get_cached_lesson(cache_key, grade=grade)
        content = row.get("lesson_content") if isinstance(row, dict) else None
        if not content:
            continue
        step_contents[step_title] = (cache_key, content)
        all_citations |= find_citations_in_text(content)

    if not all_citations:
        return {"chapter": chapter, "status": "no_citations_found"}

    citation_pages = build_citation_page_map(document_ids, all_citations)
    if not citation_pages:
        return {
            "chapter": chapter,
            "status": "citations_found_no_page_match",
            "citations": sorted(all_citations),
        }

    total_inserted = 0
    steps_changed = []
    for step_title, (cache_key, content) in step_contents.items():
        new_content, inserted = inject_into_content(content, citation_pages, chapter)
        if new_content == content:
            continue
        total_inserted += inserted
        steps_changed.append(step_title)
        if dry_run:
            continue
        store_lesson_cache(
            cache_key=cache_key,
            lesson_content=new_content,
            source_type="MANUAL",
            board=board, grade=grade, subject=subject, chapter=chapter,
            mode="CBSE", step_title=step_title, teacher_persona="",
            practice_questions=[],
        )

    if not dry_run and total_inserted > 0:
        try:
            db = get_content_db(grade)
            db.table("lesson_chapter_doc").delete().eq("grade", grade).eq(
                "subject", subject
            ).eq("chapter", chapter).execute()
        except Exception as e:
            print(f"    [warn] could not invalidate chapter doc cache: {e}")

    return {
        "chapter": chapter,
        "status": "ok",
        "citations_found": sorted(all_citations),
        "citations_matched_to_pages": sorted(citation_pages.keys()),
        "links_inserted": total_inserted,
        "steps_changed": steps_changed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Universal NCERT page-image citation linker (all grades/subjects)"
    )
    parser.add_argument("--grade", default=None, help='e.g. "Grade 9" (omit to scan all grades)')
    parser.add_argument("--subject", default=None, help='e.g. "Science" (omit to scan all subjects)')
    parser.add_argument("--chapter", default=None, help="exact chapter string (omit to scan all chapters)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("\n  Universal Page-Image Citation Linker")
    print(f"  Scope: grade={args.grade or 'ALL'} subject={args.subject or 'ALL'} chapter={args.chapter or 'ALL'}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}\n")

    chapters = discover_chapters(args.grade, args.subject, args.chapter)
    print(f"  Found {len(chapters)} chapter(s) with active lesson_cache content.\n")

    summary = {"ok": 0, "links_inserted_total": 0, "no_citations_found": 0,
               "citations_found_no_page_match": 0, "no_rag_documents": 0}

    for combo in chapters:
        result = process_chapter(
            combo["board"], combo["grade"], combo["subject"], combo["chapter"], args.dry_run
        )
        status = result["status"]
        summary[status] = summary.get(status, 0) + 1
        label = f"[{combo['grade']} / {combo['subject']}] {combo['chapter']}"
        if status == "ok":
            summary["links_inserted_total"] += result["links_inserted"]
            print(f"  OK   {label}")
            print(f"       citations found: {result['citations_found']}")
            print(f"       matched to pages: {result['citations_matched_to_pages']}")
            print(f"       links inserted: {result['links_inserted']} (steps: {result['steps_changed']})")
        elif status == "citations_found_no_page_match":
            print(f"  MISS {label} -- citations found but no page match: {result['citations']}")
        elif status == "no_citations_found":
            pass  # too noisy to print for every chapter with no citations
        elif status == "no_rag_documents":
            print(f"  SKIP {label} -- no rag_documents row found")

    print("\n  Summary:")
    for k, v in summary.items():
        print(f"    {k}: {v}")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
