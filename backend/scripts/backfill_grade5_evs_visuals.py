#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 5 EVS ("Our Wondrous World")
chapters 1-10, ingested this session from GPT-5.5 authored manifests
(see gpt_output/grade5_evs/*.json).

The automatic textbook-image step inside batch_ingest_gpt55_outputs.py
already ran during ingestion using the default structural (Fig.-caption-
dependent) curator, which left every extracted page as "needs_review"
with a generic "Chapter N - page N" placeholder caption (no real figure
caption was found) — this NCERT primary-stage EVS textbook is a
photo/illustration-heavy prose book with no "Fig. N.N:" numbering
convention, the same limitation documented for Grade 5 English. This
script re-curates using curate_prose_textbook_visuals.py, the
content-image-detection curator already proven for Grade 5 English.

Usage:
    cd backend
    python3 scripts/backfill_grade5_evs_visuals.py --dry-run
    python3 scripts/backfill_grade5_evs_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/Class 5 - World Around Us")

# (rag_documents.id, source pdf filename) — matched 1:1 by chapter order.
# Filename pattern: eeev1{N:02d}.pdf for chapter N (1-10).
CHAPTER_PDFS = [
    (591, "eeev101.pdf"),   # Chapter 1: Water — The Essence of Life
    (592, "eeev102.pdf"),   # Chapter 2: Journey of a River
    (593, "eeev103.pdf"),   # Chapter 3: The Mystery of Food
    (594, "eeev104.pdf"),   # Chapter 4: Our School — A Happy Place
    (595, "eeev105.pdf"),   # Chapter 5: Our Vibrant Country
    (596, "eeev106.pdf"),   # Chapter 6: Some Unique Places
    (597, "eeev107.pdf"),   # Chapter 7: Energy — How Things Work
    (598, "eeev108.pdf"),   # Chapter 8: Clothes — How Things are Made
    (599, "eeev109.pdf"),   # Chapter 9: Rhythms of Nature
    (600, "eeev110.pdf"),   # Chapter 10: Earth — Our Shared Home
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 5 EVS visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 5 EVS visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
