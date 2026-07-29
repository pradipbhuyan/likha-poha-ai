#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 10 English (Text Book, First
Flight) chapters.

Confirmed live: all 9 Grade 10 English Text Book rag_documents rows (ids
296-304) have ZERO rows in rag_visual_assets. This script backfills the
page images directly from the local source PDFs supplied by the user
(Downloads/GPT55_Prompts_grade_10_first_flight/*_source.pdf) and curates
them with curate_prose_textbook_visuals's deterministic size+uniqueness
signal (this book has no Fig. N.N captions, so the Fig.-based curator
would approve 0 pages).

Usage:
    cd backend
    python3 scripts/backfill_grade10_english_visuals.py --dry-run
    python3 scripts/backfill_grade10_english_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/GPT55_Prompts_grade_10_first_flight")

# (rag_documents.id, source pdf filename)
CHAPTER_PDFS = [
    (296, "01_chapter_1_a_letter_to_god_source.pdf"),
    (297, "02_chapter_2_nelson_mandela_long_walk_to_freedom_source.pdf"),
    (298, "03_chapter_3_two_stories_about_flying_source.pdf"),
    (299, "04_chapter_4_from_the_diary_of_anne_frank_source.pdf"),
    (300, "05_chapter_5_glimpses_of_india_source.pdf"),
    (301, "06_chapter_6_mijbil_the_otter_source.pdf"),
    (302, "07_chapter_7_madam_rides_the_bus_source.pdf"),
    (303, "08_chapter_8_the_sermon_at_benares_source.pdf"),
    (304, "09_chapter_9_the_proposal_source.pdf"),
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 10 English Text Book visuals")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    for document_id, filename in CHAPTER_PDFS:
        pdf_path = SOURCE_DIR / filename
        if not pdf_path.exists():
            print(f"  [skip] document_id={document_id}: source PDF not found at {pdf_path}")
            continue

        row = (
            admin_client.table("rag_documents")
            .select("chapter")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )
        chapter_name = row.data[0]["chapter"] if row.data else f"id={document_id}"
        print(f"  === {chapter_name} (document_id={document_id}) ===")

        if dry_run:
            print(f"    [DRY RUN] Would backfill from {pdf_path.name} and curate.")
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
            curate_document(document_id=str(document_id), pdf_path=str(pdf_path), dry_run=False, force=force)
        except Exception as e:
            print(f"    [error] curation failed: {e}")

    print("\nDone.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 10 English visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
