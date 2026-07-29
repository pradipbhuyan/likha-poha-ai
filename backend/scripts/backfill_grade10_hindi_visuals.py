#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 10 Hindi (Kshitiz) chapters.

Confirmed live: all 12 Grade 10 Hindi rag_documents rows (ids 410-421)
had zero rows in rag_visual_assets, and there is no BOOK_SOURCES entry
for Grade 10/Hindi in prepare_gpt55_prompts.py, so the automatic
textbook-image step in ingest_gpt55_chapter_output.py/batch_ingest_
gpt55_outputs.py silently skipped this subject for all 12 chapters.
This script backfills page images directly from the local source PDFs
supplied by the user (Downloads/GPT55_Prompts_grade_10_kshitiz/
*_source.pdf) and curates them with curate_hindi_illustrations.py — the
structural (non-caption-dependent) curator already proven for Grade 9
Hindi, since this NCERT Hindi series has no "Fig. N.N:" caption
convention to anchor a deterministic Fig.-based curator.

Usage:
    cd backend
    python3 scripts/backfill_grade10_hindi_visuals.py --dry-run
    python3 scripts/backfill_grade10_hindi_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_hindi_illustrations import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/GPT55_Prompts_grade_10_kshitiz")

# (rag_documents.id, source pdf filename) — matched 1:1 by chapter order.
CHAPTER_PDFS = [
    (410, "01_अधयय_1_सरदस_source.pdf"),
    (411, "02_अधयय_2_तलसदस_source.pdf"),
    (412, "03_अधयय_3_जयशकर_परसद_source.pdf"),
    (413, "04_अधयय_4_सरयकत_तरपठ_नरल_source.pdf"),
    (414, "05_अधयय_5_नगरजन_source.pdf"),
    (415, "06_अधयय_6_मगलश_डबरल_source.pdf"),
    (416, "07_अधयय_7_सवय_परकश_source.pdf"),
    (417, "08_अधयय_8_रमवकष_बनपर_source.pdf"),
    (418, "09_अधयय_9_यशपल_source.pdf"),
    (419, "10_अधयय_10_मनन_भडर_source.pdf"),
    (420, "11_अधयय_11_यतदर_मशर_source.pdf"),
    (421, "12_अधयय_12_भदत_आनद_कसलययन_source.pdf"),
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 10 Hindi (Kshitiz) visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 10 Hindi visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
