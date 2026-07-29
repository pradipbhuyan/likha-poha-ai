#!/usr/bin/env python3
"""
Upgrade legacy text-only extract-ref citations for Grade 10 Social
Science (Political Science, "Democratic Politics II") to the current
page-image form.

Same pattern as fix_legacy_text_extract_refs.py /
fix_legacy_text_extract_refs_geography.py: GPT-5.5 baked in the older
{"citation": ..., "extract_text": ...} form (no asset_url) for every
NCERT Exercise citation in this batch, instead of the current
{"citation": ..., "page_number": ..., "asset_url": ...} page-image
form. This script rewrites each citation's fenced ```extract-ref```
block in lesson_cache.lesson_content to the page-image form, using a
citation -> (document_id, page_number) mapping determined by full-text
PDF search against the local source PDFs
(~/Downloads/GPT55_Prompts_grade_10_political_science/*_source.pdf).

Usage:
    cd backend
    python3 scripts/fix_legacy_text_extract_refs_political_science.py --dry-run
    python3 scripts/fix_legacy_text_extract_refs_political_science.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from scripts.ingest_gpt55_chapter_output import invalidate_chapter_doc_cache  # noqa: E402

# chapter -> (document_id, {citation: page_number})
CHAPTER_CITATION_PAGES: dict[str, tuple[int, dict[str, int]]] = {
    "Chapter 1: Power-sharing": (340, {
        "NCERT Exercise 4": 10,
        "NCERT Exercise 5": 11,
        "NCERT Exercise 7": 11,
        "NCERT Exercise 8": 12,
        "NCERT Exercise 9": 12,
    }),
    "Chapter 2: Federalism": (341, {
        "NCERT Exercise 4": 15,
        "NCERT Exercise 5": 15,
        "NCERT Exercise 7": 15,
        "NCERT Exercise 9": 15,
        "NCERT Exercise 12": 16,
    }),
    "Chapter 3: Gender, Religion and Caste": (342, {
        "NCERT Exercise 1": 16,
        "NCERT Exercise 2": 16,
        "NCERT Exercise 3": 16,
        "NCERT Exercise 4": 16,
        "NCERT Exercise 5": 16,
    }),
    "Chapter 4: Political Parties": (343, {
        "NCERT Exercise 1": 16,
        "NCERT Exercise 2": 16,
        "NCERT Exercise 3": 16,
        "NCERT Exercise 7": 16,
        "NCERT Exercise 10": 17,
    }),
    "Chapter 5: Outcomes of Democracy": (344, {
        "NCERT Exercise 1": 11,
        "NCERT Exercise 2": 11,
        "NCERT Exercise 3": 11,
        "NCERT Exercise 5": 11,
        "NCERT Exercise 7": 11,
    }),
}

EXTRACT_REF_RE = re.compile(r"```extract-ref\s*\n(\{.*?\})\s*```", re.DOTALL)


def get_asset_url(document_id: int, page_number: int) -> str | None:
    res = (
        admin_client.table("rag_visual_assets")
        .select("asset_url")
        .eq("document_id", document_id)
        .eq("page_number", page_number)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]["asset_url"]
    return None


def upgrade_content(content: str, page_map: dict[str, int], asset_urls: dict[int, str]) -> tuple[str, int]:
    count = 0

    def _replace(match: re.Match) -> str:
        nonlocal count
        payload = json.loads(match.group(1))
        citation = payload.get("citation")
        if citation in page_map and "asset_url" not in payload:
            page_number = page_map[citation]
            asset_url = asset_urls.get(page_number)
            if asset_url:
                new_payload = {
                    "citation": citation,
                    "page_number": page_number,
                    "asset_url": asset_url,
                }
                count += 1
                return "```extract-ref\n" + json.dumps(new_payload, ensure_ascii=False) + "\n```"
        return match.group(0)

    new_content = EXTRACT_REF_RE.sub(_replace, content)
    return new_content, count


def run(dry_run: bool) -> None:
    total_fixed = 0
    for chapter, (document_id, page_map) in CHAPTER_CITATION_PAGES.items():
        asset_urls = {pg: get_asset_url(document_id, pg) for pg in set(page_map.values())}
        missing = [pg for pg, url in asset_urls.items() if not url]
        if missing:
            print(f"  [warn] {chapter}: no asset_url found for page(s) {missing}")

        rows = (
            admin_client.table("lesson_cache")
            .select("id,step_title,lesson_content")
            .eq("grade", "Grade 10")
            .eq("subject", "Social Science")
            .eq("chapter", chapter)
            .execute()
        )
        print(f"\n=== {chapter} (document_id={document_id}) — {len(rows.data)} step row(s) ===")
        for row in rows.data:
            new_content, count = upgrade_content(row["lesson_content"], page_map, asset_urls)
            if count:
                print(f"  [{row['step_title']}] upgraded {count} citation(s)")
                total_fixed += count
                if not dry_run:
                    admin_client.table("lesson_cache").update({"lesson_content": new_content}).eq(
                        "id", row["id"]
                    ).execute()
            else:
                print(f"  [{row['step_title']}] no legacy citations found (already fixed or none present)")

        if not dry_run:
            try:
                invalidate_chapter_doc_cache(
                    {"grade": "Grade 10", "subject": "Social Science", "chapter": chapter},
                    dry_run=False,
                )
            except Exception as e:
                print(f"  [warn] cache invalidation failed: {e}")

    print(f"\nTotal citations upgraded: {total_fixed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade legacy extract-ref citations for Grade 10 Political Science")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
