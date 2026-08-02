#!/usr/bin/env python3
"""
Fix legacy text-only extract-ref popups for Grade 12 English.

Same conversion pattern as fix_legacy_text_extract_refs_psychology.py --
converts {"citation", "extract_text", "note"} fences to
{"citation", "page_number", "asset_url"} fences using a per-chapter
target page (each chapter's Think it out / Reading with Insight
questions all sit on that chapter's single last content page).

Covers all 19 Grade 12 English chapters now that image storage has
been enabled for CBSE Grade 12 in rag_visual_service.py
(RAG_VISUAL_ENABLED_CONTEXTS).

Usage:
    cd backend
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_grade12_english.py --dry-run
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_grade12_english.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# chapter -> (document_id, exercise_questions_page)
CHAPTER_PAGES: dict[str, tuple[int, int]] = {
    "Chapter 1: The Last Lesson": (1179, 12),
    "Chapter 2: Lost Spring": (1180, 10),
    "Chapter 3: Deep Water": (1181, 9),
    "Chapter 4: The Rattrap": (1182, 13),
    "Chapter 5: Indigo": (1183, 11),
    "Chapter 6: Poets and Pancakes": (1184, 10),
    "Chapter 7: The Interview": (1185, 9),
    "Chapter 8: Going Places": (1186, 12),
    "Chapter 9: My Mother at Sixty-six": (1405, 3),
    "Chapter 10: Keeping Quiet": (1406, 3),
    "Chapter 11: A Thing of Beauty": (1407, 2),
    "Chapter 12: A Roadside Stand": (1408, 3),
    "Chapter 13: Aunt Jennifer's Tigers": (1409, 2),
    "Chapter 14: The Third Level": (1410, 6),
    "Chapter 15: The Tiger King": (1411, 10),
    "Chapter 16: Journey to the End of the Earth": (1412, 5),
    "Chapter 17: The Enemy": (1413, 23),
    "Chapter 18: On the Face of It": (1414, 14),
    "Chapter 19: Memories of Childhood": (1415, 7),
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

    for chapter, (document_id, page) in CHAPTER_PAGES.items():
        asset_url = get_asset_url(document_id, page)
        if not asset_url:
            print(f"[MISS] {chapter} -> page {page} has no asset_url, skipping chapter")
            total_missing += 1
            continue

        res = (
            admin_client.table("lesson_cache")
            .select("id, step_title, lesson_content")
            .eq("grade", "Grade 12")
            .eq("subject", "English")
            .eq("chapter", chapter)
            .execute()
        )

        for row in res.data:
            content = row["lesson_content"]
            changed = False

            def _replace(m: re.Match) -> str:
                nonlocal changed, total_fixed
                raw = m.group(1)
                try:
                    payload = json.loads(raw)
                except Exception:
                    return m.group(0)
                citation = payload.get("citation")
                if "asset_url" in payload:
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
        for chapter in CHAPTER_PAGES:
            admin_client.table("lesson_chapter_doc").delete().eq(
                "grade", "Grade 12"
            ).eq("subject", "English").eq("chapter", chapter).execute()
        print("Invalidated lesson_chapter_doc cache for all touched chapters.")


if __name__ == "__main__":
    main()
