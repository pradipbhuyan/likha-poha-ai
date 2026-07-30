#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 5 Maths chapters 1-10,
ingested this session from GPT-5.5 authored manifests (see
gpt_output/grade5_maths/*.json).

The automatic textbook-image step inside batch_ingest_gpt55_outputs.py
already ran during ingestion using the default structural (Fig.-caption-
dependent) curator, which left every extracted page as "needs_review"
with "no real figure caption found" — this NCERT primary-stage Maths
textbook has diagrams, number lines, and activity illustrations but no
"Fig. N.N:" numbering convention. This script re-curates using
curate_prose_textbook_visuals.py, the content-image-detection curator
already proven for Grade 5 English/EVS.

Usage:
    cd backend
    python3 scripts/backfill_grade5_maths_visuals.py --dry-run
    python3 scripts/backfill_grade5_maths_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/Class 5 - Maths")

# (rag_documents.id, source pdf filename) — matched 1:1 by chapter order.
# Filename pattern: eemm1{N:02d}.pdf for chapter N (1-10).
CHAPTER_PDFS = [
    (554, "eemm101.pdf"),   # Chapter 1: We the Travellers — I
    (555, "eemm102.pdf"),   # Chapter 2: Fractions
    (556, "eemm103.pdf"),   # Chapter 3: Angles as Turns
    (557, "eemm104.pdf"),   # Chapter 4: We the Travellers — II
    (558, "eemm105.pdf"),   # Chapter 5: Far and Near
    (559, "eemm106.pdf"),   # Chapter 6: The Dairy Farm
    (560, "eemm107.pdf"),   # Chapter 7: Shapes and Patterns
    (561, "eemm108.pdf"),   # Chapter 8: Weight and Capacity
    (562, "eemm109.pdf"),   # Chapter 9: Coconut Farm
    (563, "eemm110.pdf"),   # Chapter 10: Symmetrical Designs
    (564, "eemm111.pdf"),   # Chapter 11: Grandmother's Quilt
    (565, "eemm112.pdf"),   # Chapter 12: Racing Seconds
    (566, "eemm113.pdf"),   # Chapter 13: Animal Jumps
    (567, "eemm114.pdf"),   # Chapter 14: Maps and Locations
    (568, "eemm115.pdf"),   # Chapter 15: Data Through Pictures
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 5 Maths visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 5 Maths visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
