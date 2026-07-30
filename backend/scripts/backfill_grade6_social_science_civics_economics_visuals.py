#!/usr/bin/env python3
"""
Backfill + curate textbook images for Grade 6 Social Science chapters
7-14 (India's Cultural Roots through Economic Activities Around Us).

rag_visual_assets rows already exist for document_id 533-540 (created
during the original chapter upload), but they were never curated
(status remains "needs_review" and asset_url points to raw page
renders rather than approved, cropped figures). This script re-runs
backfill_visual_assets_for_document (idempotent -- re-renders pages
from the source PDF) and then curate_document (PyMuPDF page-image
hashing + size/uniqueness heuristics) so that the chapter's actual
textbook figures (e.g. Fig. 8.1-8.7, Fig. 10.1-10.5, Fig. 11.1, Fig.
12.1-12.4, Fig. 14.1) become approved and available for citation
matching by inject_page_refs_universal.py.

Usage:
    cd backend
    python3 scripts/backfill_grade6_social_science_civics_economics_visuals.py --dry-run
    python3 scripts/backfill_grade6_social_science_civics_economics_visuals.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.curate_prose_textbook_visuals import curate_document  # noqa: E402

SOURCE_DIR = Path("/Users/a0247716/Downloads/GPT55_Prompts_grade_6_social_science")

# (rag_documents.id, source pdf filename)
CHAPTER_PDFS = [
    (533, "07_7_indias_cultural_roots_source.pdf"),
    (534, "08_8_unity_in_diversity_or_many_in_the_one_source.pdf"),
    (535, "09_9_family_and_community_source.pdf"),
    (536, "10_10_grassroots_democracy_part_1_governance_source.pdf"),
    (537, "11_11_grassroots_democracy_part_2_local_government_in_rural_areas_source.pdf"),
    (538, "12_12_grassroots_democracy_part_3_local_government_in_urban_areas_source.pdf"),
    (539, "13_13_the_value_of_work_source.pdf"),
    (540, "14_14_economic_activities_around_us_source.pdf"),
]


def run(dry_run: bool, force: bool) -> None:
    print(f"\n  Backfill + curate Grade 6 Social Science (Chapters 7-14) visuals")
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
    parser = argparse.ArgumentParser(description="Backfill + curate Grade 6 Social Science (Chapters 7-14) visuals")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
