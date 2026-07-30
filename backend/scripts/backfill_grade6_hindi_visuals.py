#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 6 Hindi chapters 1-5,
ingested this session from GPT-5.5 authored manifests (see
gpt_output/grade6_hindi/*.json).

The automatic textbook-image step inside batch_ingest_gpt55_outputs.py
already ran during ingestion, but it used the DEFAULT structural
(Fig.-caption-dependent) curator, which rejected every page for all 5
chapters ("no real figure caption found") -- the same known limitation
documented for Grade 5/9/10 Hindi (this NCERT reader series has no
"चित्र N.N" caption convention to anchor a deterministic curator).
This script re-curates using curate_hindi_illustrations.py, the
structural (non-caption-dependent) curator already proven for
Grade 5/9/10 Hindi.

Usage:
    cd backend
    python3 scripts/backfill_grade6_hindi_visuals.py --dry-run
    python3 scripts/backfill_grade6_hindi_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_hindi_illustrations import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/Class 6 - Hindi")

# (rag_documents.id, source pdf filename) -- matched 1:1 by chapter order.
CHAPTER_PDFS = [
    (541, "fhml101.pdf"),  # 1. मातृभूमि
    (542, "fhml102.pdf"),  # 2. गोल
    (543, "fhml103.pdf"),  # 3. पहली बूँद
    (544, "fhml104.pdf"),  # 4. हार की जीत
    (545, "fhml105.pdf"),  # 5. रहीम के दोहे
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 6 Hindi visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 6 Hindi visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
