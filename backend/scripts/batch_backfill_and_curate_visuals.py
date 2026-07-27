#!/usr/bin/env python3
"""
Batch Backfill + Curate Textbook Visuals — run across every chapter of a subject
====================================================================================
Extends the single-chapter `backfill_and_curate_visuals.py` (built for the
Grade 9 Science Cell chapter pilot) to run automatically across every
core chapter of a grade/subject in one command — per the user's
instruction: "include this to be done for all the subjects and chapters
from now."

For each `(grade, subject)`:
  1. Reads the ordered chapter list from `backend/app/data/syllabus.py`
     (same source of truth used by `prepare_gpt55_prompts.py`).
  2. Maps each chapter to its `rag_documents` row (matched by exact
     chapter string) to get the `document_id`.
  3. Maps each chapter to its source PDF using the same book-code +
     chapter-number convention already used in `prepare_gpt55_prompts.py`
     (`BOOK_SOURCES`).
  4. Runs backfill (render PDF pages -> Supabase Storage) + deterministic
     curation (approve ONLY pages with genuine "Fig. N.N: <caption>" NCERT
     figures — see curate_textbook_visuals.py) for that chapter.
  5. Deletes that chapter's `lesson_chapter_doc` cache row so the Chapter
     Journey UI reconverts with the newly-approved images on next load.

Only chapters with genuine figures get real, grounded images attached —
chapters/pages with no diagrams are correctly left with zero images,
consistent with the "never randomly add pages" fix in §4k.

Usage:
    cd backend
    python3 scripts/batch_backfill_and_curate_visuals.py --grade "Grade 9" --subject Science --dry-run
    python3 scripts/batch_backfill_and_curate_visuals.py --grade "Grade 9" --subject Science --force
    python3 scripts/batch_backfill_and_curate_visuals.py --grade "Grade 9" --subject Science --limit 3 --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_textbook_visuals import curate_document  # noqa: E402
from scripts.prepare_gpt55_prompts import BOOK_SOURCES, get_chapter_list  # noqa: E402


def find_document_id(grade: str, subject: str, chapter: str, chapter_index: int) -> str | None:
    """
    Look up the rag_documents.id for a chapter.

    rag_documents.chapter often uses a "Chapter N: <title>" prefix
    convention (the platform's original naming, predating syllabus.py's
    unprefixed titles — the same mismatch documented in §4i of the plan).
    Try the exact syllabus.py string first, then the "Chapter N: " prefixed
    form, before giving up.
    """
    candidates = [chapter, f"Chapter {chapter_index}: {chapter}"]
    for candidate in candidates:
        try:
            result = (
                admin_client.table("rag_documents")
                .select("id")
                .eq("grade", grade)
                .eq("subject", subject)
                .eq("chapter", candidate)
                .limit(1)
                .execute()
            )
            if result.data:
                return str(result.data[0]["id"])
        except Exception:
            continue
    return None


def invalidate_chapter_doc(grade: str, subject: str, chapter: str) -> None:
    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        db.table("lesson_chapter_doc").delete() \
            .eq("grade", grade).eq("subject", subject).eq("chapter", chapter).execute()
    except Exception as e:
        print(f"    [warn] could not invalidate lesson_chapter_doc: {e}")


def run(grade: str, subject: str, dry_run: bool, force: bool, limit: int | None) -> None:
    key = (grade, subject)
    if key not in BOOK_SOURCES:
        print(f"ERROR: no BOOK_SOURCES entry for {grade}/{subject} in prepare_gpt55_prompts.py.")
        print(f"       Configured combinations: {list(BOOK_SOURCES.keys())}")
        sys.exit(1)

    source_cfg = BOOK_SOURCES[key]
    pdf_dir = source_cfg["pdf_dir"]
    book_code = source_cfg["book_code"]
    num_chapters = source_cfg["num_chapters"]

    chapters = get_chapter_list(grade, subject)
    n = min(len(chapters), num_chapters)
    if limit:
        n = min(n, limit)

    print(f"\n  Batch backfill + curate for {grade} / {subject} — {n} chapter(s)\n")

    for i in range(1, n + 1):
        chapter_name = chapters[i - 1]
        pdf_path = pdf_dir / f"{book_code}{i:02d}.pdf"

        print(f"[{i:02d}/{n}] {chapter_name}")

        if not pdf_path.exists():
            print(f"    [skip] source PDF not found: {pdf_path}")
            continue

        document_id = find_document_id(grade, subject, chapter_name, i)
        if not document_id:
            print(f"    [skip] no rag_documents row found for this exact chapter string")
            continue

        print(f"    document_id={document_id}, pdf={pdf_path.name}")

        if dry_run:
            print("    [DRY RUN] Would backfill + curate.")
            continue

        try:
            file_bytes = pdf_path.read_bytes()
            backfill_result = backfill_visual_assets_for_document(
                document_id=document_id,
                file_bytes=file_bytes,
                filename=pdf_path.name,
                uploaded_by=None,
            )
            print(f"    backfill: {backfill_result.get('message')}")
        except Exception as e:
            print(f"    [error] backfill failed: {e}")
            continue

        try:
            curate_document(document_id=document_id, pdf_path=str(pdf_path), dry_run=False, force=force)
        except Exception as e:
            print(f"    [error] curation failed: {e}")
            continue

        invalidate_chapter_doc(grade, subject, chapter_name)
        print(f"    -> lesson_chapter_doc invalidated for this chapter.\n")

    print("Done.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-run backfill+curate textbook visuals across every chapter of a grade/subject"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Science"')
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for already-active pages")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N chapters")
    args = parser.parse_args()

    run(grade=args.grade, subject=args.subject, dry_run=args.dry_run, force=args.force, limit=args.limit)


if __name__ == "__main__":
    main()
