#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 10 Social Science (History,
"India and the Contemporary World II") chapters.

Same pattern as backfill_grade10_english_visuals.py / backfill_grade10_
english_footprints_visuals.py: no BOOK_SOURCES entry exists for Grade
10/Social Science in prepare_gpt55_prompts.py, so the automatic image
step in batch_ingest_gpt55_outputs.py silently skips this subject.
This script backfills page images directly from the local source PDFs
supplied by the user (Downloads/GPT55_Prompts_grade_10_history/
*_source.pdf) and curates them with curate_prose_textbook_visuals.py's
deterministic size+uniqueness signal.

Currently only Chapter 1 has been ingested this session; the other 4
PDFs are listed here too so this script can be re-run as-is once those
chapters are ingested in a future session.

Usage:
    cd backend
    python3 scripts/backfill_grade10_social_science_history_visuals.py --dry-run
    python3 scripts/backfill_grade10_social_science_history_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/GPT55_Prompts_grade_10_history")

# (rag_documents.id, source pdf filename)
CHAPTER_PDFS = [
    (335, "01_chapter_1_the_rise_of_nationalism_in_europe_source.pdf"),
    (336, "02_chapter_2_nationalism_in_india_source.pdf"),
    (337, "03_chapter_3_the_making_of_a_global_world_source.pdf"),
    (338, "04_chapter_4_the_age_of_industrialisation_source.pdf"),
    (339, "05_chapter_5_print_culture_and_the_modern_world_source.pdf"),
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 10 Social Science (History) visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 10 Social Science (History) visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
