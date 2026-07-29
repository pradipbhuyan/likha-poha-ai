#!/usr/bin/env python3
"""
Inject Page-Image Citation Links into Grade 10 Science Lessons
====================================================================
Replaces the earlier "extracted-text popup" approach entirely. Instead
of reconstructing garbled activity text from pdfplumber extraction
(which repeatedly produced misaligned/garbled results — decorative
NCERT fonts, Private-Use-Area glyphs, bullet-symbol artifacts — despite
several rounds of text-cleanup patches), this script now:

  1. Finds which PDF page number contains each "Activity N.N" heading
     (scanning page-by-page, not on the whole concatenated document
     text, so the page number is exact).
  2. Looks up that page's pre-rendered image in `rag_visual_assets`
     (every page of every uploaded NCERT PDF already has a full-page
     image stored in Supabase Storage with a public URL, populated by
     the existing textbook-image backfill pipeline — confirmed live:
     all 16 pages of jesc101.pdf have an asset_url, not just the pages
     curated as "active" illustrative figures).
  3. Injects a ```extract-ref``` fence whose payload is a page image
     URL + page number, NOT reconstructed text. The frontend
     (ExtractPopupBlock.jsx) shows the actual scanned textbook page
     image with a "view full page" link, so students see the genuine
     NCERT page exactly as printed instead of an AI-cleaned text
     reconstruction.

Usage:
    cd backend
    python3 scripts/inject_extract_refs_grade10_science.py --chapter "Chapter 1: Chemical Reactions and Equations" --pdf jesc101.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber  # noqa: E402

from app.services.auth_service import admin_client  # noqa: E402
from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

BOARD = "CBSE"
GRADE = "Grade 10"
SUBJECT = "Science"
MODE = "CBSE"
REQUIRED_LESSON_STEPS = [
    "Concept introduction", "Core explanation", "Worked examples",
    "Exam-style problems", "Revision and recap",
]

PDF_ROOT = Path.home() / "Pradips_Project" / "cbse-tutor-platform" / "RAG DB" / "Grade_10" / "Science"

# Same decorative-heading normalizer as before: NCERT PDFs render
# "Activity N.N" headings with each character repeated ~5 times
# (e.g. "AAAAAccccctttttiiiiivvvvviiiiitttttyyyyy 11111.....11111").
# Still needed here purely to *locate* the heading on a page -- we no
# longer extract or clean any surrounding body text.
_REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")


def normalize_decorative_headings(text: str) -> str:
    """Collapse runs of 3+ repeated characters down to one occurrence."""
    return _REPEATED_CHAR_RE.sub(r"\1", text)


_ACTIVITY_HEADING_RE = re.compile(r"Activity\s+(\d+\.\d+)(?!\d)", re.IGNORECASE)


def find_activity_pages(pdf_path: Path) -> dict:
    """Scan a PDF page-by-page and record the first page number (1-indexed)
    on which each 'Activity N.N' heading appears.

    Page-by-page scanning (rather than the whole-document concatenated
    text used by the old text-extraction approach) is what makes exact
    page-number lookup possible."""
    activity_pages: dict[str, int] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_number = page_index + 1
            raw_text = page.extract_text() or ""
            normalized = normalize_decorative_headings(raw_text)
            for m in _ACTIVITY_HEADING_RE.finditer(normalized):
                label = "Activity " + m.group(1)
                if label not in activity_pages:
                    activity_pages[label] = page_number
    return activity_pages


def fetch_page_asset(document_id: int, page_number: int) -> dict | None:
    """Look up the pre-rendered page image for a given document/page in
    rag_visual_assets. Every page of every uploaded NCERT PDF has an
    asset_url populated by the existing textbook-image backfill
    pipeline, regardless of curation status (active/needs_review) --
    confirmed live: all 16 pages of jesc101.pdf have an asset_url."""
    try:
        r = (
            admin_client.table("rag_visual_assets")
            .select("asset_url,page_number,document_id")
            .eq("document_id", document_id)
            .eq("page_number", page_number)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]
    except Exception as e:
        print(f"    [warn] rag_visual_assets lookup failed for doc={document_id} page={page_number}: {e}")
    return None


def find_document_id(chapter_name: str) -> int | None:
    """Find the rag_documents row id for this chapter (needed to look up
    its pages in rag_visual_assets)."""
    try:
        r = (
            admin_client.table("rag_documents")
            .select("id")
            .eq("grade", GRADE)
            .eq("subject", SUBJECT)
            .eq("board", BOARD)
            .eq("chapter", chapter_name)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]["id"]
    except Exception as e:
        print(f"    [warn] rag_documents lookup failed for chapter={chapter_name!r}: {e}")
    return None


def build_citations(chapter_name: str, pdf_path: Path) -> dict:
    """Build citation -> {page_number, asset_url} for every Activity
    heading found in the PDF, using the real per-page textbook image
    already stored in Supabase Storage."""
    document_id = find_document_id(chapter_name)
    if document_id is None:
        print(f"    [error] could not find rag_documents row for chapter={chapter_name!r}")
        return {}

    activity_pages = find_activity_pages(pdf_path)
    citations = {}
    for label, page_number in activity_pages.items():
        asset = fetch_page_asset(document_id, page_number)
        if asset and asset.get("asset_url"):
            citations[label] = {
                "page_number": page_number,
                "asset_url": asset["asset_url"],
            }
        else:
            print(f"    [warn] no stored page image found for {label} (page {page_number}) -- skipping")
    return citations


def find_citation_for_line(line, citations):
    low = line.lower()
    for label in citations:
        if label.lower() in low:
            return label, citations[label]
    return None


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


def inject_into_content(content, citations, chapter_name):
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
                label, page_info = found
                fence = build_extract_fence(label, page_info, note=chapter_name)
                out.append("")
                out.append(fence)
                inserted += 1
                i = resume_index
                continue
            elif fence_start is not None:
                i = resume_index
                continue
        i += 1
    return "\n".join(out), inserted


def process_chapter(chapter_name: str, pdf_filename: str, dry_run: bool):
    pdf_path = PDF_ROOT / pdf_filename
    if not pdf_path.exists():
        print(f"  [error] PDF not found: {pdf_path}")
        return

    print(f"\n  Chapter: {chapter_name}")
    citations = build_citations(chapter_name, pdf_path)
    print(f"    Found {len(citations)} citation(s) with stored page images.")
    if not citations:
        print("    [skip] No citations available; nothing to inject.")
        return

    total_inserted = 0
    for step_title in REQUIRED_LESSON_STEPS:
        cache_key = make_lesson_cache_key(
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=chapter_name,
            mode=MODE, step_title=step_title, teacher_persona="",
        )
        row = get_cached_lesson(cache_key, grade=GRADE)
        if not row:
            print(f"    [warn] no cached row for step: {step_title}")
            continue
        content = row.get("lesson_content") if isinstance(row, dict) else None
        if not content:
            print(f"    [warn] empty content for step: {step_title}")
            continue

        new_content, inserted = inject_into_content(content, citations, chapter_name)
        content_changed = new_content != content
        if inserted == 0 and not content_changed:
            print(f"    [{step_title}] no new citations found to link.")
            continue

        total_inserted += inserted
        if inserted > 0:
            print(f"    [{step_title}] inserted {inserted} page-image link(s).")
        else:
            print(f"    [{step_title}] removed stale/invalid extract-ref block(s).")

        if dry_run:
            continue

        store_lesson_cache(
            cache_key=cache_key,
            lesson_content=new_content,
            source_type="MANUAL",
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=chapter_name,
            mode=MODE, step_title=step_title, teacher_persona="",
            practice_questions=[],
        )

    print(f"    Total page-image links inserted: {total_inserted}")

    if not dry_run and total_inserted > 0:
        try:
            from app.services.grade_db_router import get_content_db  # noqa: PLC0415
            db = get_content_db(GRADE)
            db.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
                "subject", SUBJECT
            ).eq("chapter", chapter_name).execute()
            print("    Invalidated stale lesson_chapter_doc for this chapter.")
        except Exception as e:
            print(f"    [warn] could not invalidate chapter doc cache: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inject page-image citation links into Grade 10 Science chapters")
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--pdf", required=True, help="PDF filename inside RAG DB/Grade_10/Science/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\n  Inject Page-Image Citation Links: {GRADE} / {SUBJECT}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}")

    process_chapter(args.chapter, args.pdf, args.dry_run)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
