#!/usr/bin/env python3
"""
Fix legacy text-only extract-ref popups for Grade 11 Political Science
("Political Theory" book: Political Theory: An Introduction, Freedom,
Equality, Social Justice, Rights, Citizenship, Nationalism, Secularism).

Same pattern as fix_legacy_text_extract_refs_political_science.py (the
Grade 10 Social Science version) -- converts {"citation", "extract_text",
"note"} fences to {"citation", "page_number", "asset_url"} fences using a
per-chapter, per-citation page mapping determined by full-text PDF search.

Usage:
    cd backend
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_political_theory.py --dry-run
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_political_theory.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# chapter -> (document_id, {citation: page_number})
CHAPTER_CITATION_PAGES: dict[str, tuple[int, dict[str, int]]] = {
    "Political Theory: An Introduction": (1241, {
        "NCERT Exercise Q1": 16,
        "NCERT Exercise Q2": 16,
        "NCERT Exercise Q3": 16,
        "NCERT Exercise Q4": 16,
        "NCERT Exercise Q6": 16,
    }),
    "Freedom": (1242, {
        "NCERT Exercise Q1": 14,
        "NCERT Exercise Q2": 14,
        "NCERT Exercise Q3": 14,
        "NCERT Exercise Q4": 14,
        "NCERT Exercise Q5": 14,
    }),
    "Equality": (1243, {
        "NCERT Exercise Q1": 21,
        "NCERT Exercise Q2": 21,
        "NCERT Exercise Q4": 21,
        "NCERT Exercise Q5": 21,
        "NCERT Exercise Q6": 22,
    }),
    "Social Justice": (1244, {
        "NCERT Exercise Q1": 14,
        "NCERT Exercise Q2": 14,
        "NCERT Exercise Q3": 14,
        "NCERT Exercise Q4": 14,
        "NCERT Exercise Q5": 14,
    }),
    "Rights": (1245, {
        "NCERT Exercise Q1": 12,
        "NCERT Exercise Q2": 12,
        "NCERT Exercise Q3": 12,
        "NCERT Exercise Q4": 12,
        "NCERT Exercise Q5": 12,
    }),
    "Citizenship": (1246, {
        "NCERT Exercise Q1": 18,
        "NCERT Exercise Q2": 18,
        "NCERT Exercise Q4": 18,
        "NCERT Exercise Q5": 18,
        "NCERT Exercise Q6": 18,
    }),
    "Nationalism": (1247, {
        "NCERT Exercise Q1": 14,
        "NCERT Exercise Q2": 14,
        "NCERT Exercise Q3": 14,
        "NCERT Exercise Q4": 14,
        "NCERT Exercise Q6": 14,
    }),
    "Secularism": (1248, {
        "NCERT Exercise Q1": 17,
        "NCERT Exercise Q2": 17,
        "NCERT Exercise Q3": 18,
        "NCERT Exercise Q4": 18,
        "NCERT Exercise Q6": 18,
    }),
}

EXTRACT_RE = re.compile(r"```extract-ref\n(.*?)\n```", re.DOTALL)


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    total_fixed = 0
    total_missing = 0

    for chapter, (document_id, citation_pages) in CHAPTER_CITATION_PAGES.items():
        # Pre-resolve asset URLs for all target pages in this chapter
        page_url_cache: dict[int, str | None] = {}
        for page in set(citation_pages.values()):
            page_url_cache[page] = get_asset_url(document_id, page)

        res = (
            admin_client.table("lesson_cache")
            .select("id, step_title, lesson_content")
            .eq("grade", "Grade 11")
            .eq("subject", "Political Science")
            .eq("chapter", chapter)
            .execute()
        )

        for row in res.data:
            content = row["lesson_content"]
            changed = False

            def _replace(m: re.Match) -> str:
                nonlocal changed, total_fixed, total_missing
                raw = m.group(1)
                try:
                    payload = json.loads(raw)
                except Exception:
                    return m.group(0)
                citation = payload.get("citation")
                if "asset_url" in payload:
                    return m.group(0)  # already upgraded
                page = citation_pages.get(citation)
                if page is None:
                    print(f"  [SKIP] {chapter} | {row['step_title']} | {citation!r} -> no page mapping")
                    total_missing += 1
                    return m.group(0)
                asset_url = page_url_cache.get(page)
                if not asset_url:
                    print(f"  [MISS] {chapter} | {row['step_title']} | {citation!r} -> page {page} has no asset_url")
                    total_missing += 1
                    return m.group(0)
                new_payload = {
                    "citation": citation,
                    "page_number": page,
                    "asset_url": asset_url,
                }
                changed = True
                total_fixed += 1
                new_json = json.dumps(new_payload, ensure_ascii=False)
                return f"```extract-ref\n{new_json}\n```"

            new_content = EXTRACT_RE.sub(_replace, content)

            if changed:
                print(f"[{'DRY' if args.dry_run else 'LIVE'}] {chapter} | {row['step_title']} -> updating")
                if not args.dry_run:
                    admin_client.table("lesson_cache").update(
                        {"lesson_content": new_content}
                    ).eq("id", row["id"]).execute()

    print(f"\nTotal fixed: {total_fixed}, total missing/skip: {total_missing}")

    if not args.dry_run and total_fixed > 0:
        # Invalidate lesson_chapter_doc cache for all touched chapters
        for chapter in CHAPTER_CITATION_PAGES:
            admin_client.table("lesson_chapter_doc").delete().eq(
                "grade", "Grade 11"
            ).eq("subject", "Political Science").eq("chapter", chapter).execute()
        print("Invalidated lesson_chapter_doc cache for all touched chapters.")


if __name__ == "__main__":
    main()
