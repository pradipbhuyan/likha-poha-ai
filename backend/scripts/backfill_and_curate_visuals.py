#!/usr/bin/env python3
"""
Backfill + Curate Textbook Visuals — one command, per chapter
==================================================================
Combines the two steps needed to add real, relevant NCERT textbook
images to any chapter's lessons:

  1. Backfill: render every page of the chapter's source PDF to JPEG,
     upload to Supabase Storage, and create rag_visual_assets rows
     (status="needs_review" by default).
  2. Curate: deterministically approve ONLY pages containing a genuine
     NCERT figure caption ("Fig. N.N: <description>"), using the real
     printed caption text — never a subjective/guessed description.
     Pages with no real figure stay unapproved (or get reverted if they
     were previously mis-approved).

This is the single reusable command for extending the "relevant textbook
images in lessons" feature (built for Grade 9 Science, Cell chapter) to
any other chapter, subject, or grade — see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4j/§4k.

After running this for a chapter, delete its lesson_chapter_doc cache row
(see ingest_gpt55_chapter_output.py's invalidate_chapter_doc_cache, or run
the snippet in the docstring below) so the Chapter Journey UI picks up
the newly-approved images on next load.

Usage:
    cd backend
    python3 scripts/backfill_and_curate_visuals.py \\
        --document-id 346 \\
        --pdf-path "../RAG DB/Science/iesc102.pdf" \\
        --dry-run

    python3 scripts/backfill_and_curate_visuals.py \\
        --document-id 346 \\
        --pdf-path "../RAG DB/Science/iesc102.pdf" \\
        --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_textbook_visuals import curate_document  # noqa: E402


def run(document_id: str, pdf_path: str, dry_run: bool, force: bool) -> None:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"\n  Step 1/2 — Backfill: rendering pages from {pdf_file.name}")
    if dry_run:
        print("    [DRY RUN] Skipping actual backfill (would render+upload all pages).")
    else:
        file_bytes = pdf_file.read_bytes()
        result = backfill_visual_assets_for_document(
            document_id=document_id,
            file_bytes=file_bytes,
            filename=pdf_file.name,
            uploaded_by=None,
        )
        print(f"    {result.get('message')}")
        if not result.get("success"):
            print("    Backfill failed — aborting curation step.")
            return

    print(f"\n  Step 2/2 — Curate: approving only pages with genuine NCERT figures")
    curate_document(document_id=document_id, pdf_path=pdf_path, dry_run=dry_run, force=force)

    if not dry_run:
        print("  Reminder: delete this chapter's lesson_chapter_doc cache row so the")
        print("  Chapter Journey UI reconverts with the newly-approved images:")
        print("""
    from app.services.grade_db_router import get_content_db
    db = get_content_db(GRADE)
    db.table("lesson_chapter_doc").delete() \\
        .eq("grade", GRADE).eq("subject", SUBJECT).eq("chapter", CHAPTER).execute()
""")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill textbook page images + deterministically curate to only genuine NCERT figures, in one command"
    )
    parser.add_argument("--document-id", required=True, help="rag_documents.id for this chapter")
    parser.add_argument("--pdf-path", required=True, help="Path to the chapter's source NCERT PDF")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for already-active pages")
    args = parser.parse_args()

    run(document_id=args.document_id, pdf_path=args.pdf_path, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
