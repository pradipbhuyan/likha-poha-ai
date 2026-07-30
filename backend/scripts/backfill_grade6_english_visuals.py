#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 6 English (all 5 units).

Same pattern as backfill_grade5_english_visuals.py: uses the local source
PDFs already downloaded to ~/Downloads/Class 6 - English/*.pdf and curates
them with curate_prose_textbook_visuals.py's deterministic size+uniqueness
curator (appropriate for storybook/poem chapters with no numbered
"Fig. N.N" caption convention).

Requires RAG_VISUAL_ENABLED_CONTEXTS in rag_visual_service.py to include
("CBSE", "Grade 6") -- added 2026-07-30 per direct user request ("add text
book images, add reference pdfs wherever applicable" for the Grade 6
English ingestion).

Usage:
    cd backend
    python3 scripts/backfill_grade6_english_visuals.py --dry-run
    python3 scripts/backfill_grade6_english_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/Class 6 - English")

# (rag_documents.id, source pdf filename) -- matched 1:1 by unit order.
CHAPTER_PDFS = [
    (517, "fepr101.pdf"),  # Unit 1: Fables and Folk Tales
    (518, "fepr102.pdf"),  # Unit 2: Friendship
    (519, "fepr103.pdf"),  # Unit 3: Nurturing Nature
    (520, "fepr104.pdf"),  # Unit 4: Sports and Wellness
    (521, "fepr105.pdf"),  # Unit 5: Culture and Tradition
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 6 English visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 6 English visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
