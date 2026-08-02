#!/usr/bin/env python3
"""
Fix legacy text-only extract-ref popups for Grade 11 Psychology.

Same conversion pattern as fix_legacy_text_extract_refs_political_theory.py
-- converts {"citation", "extract_text", "note"} fences to
{"citation", "page_number", "asset_url"} fences using a per-chapter
target page (each chapter's NCERT Review Questions all sit on that
chapter's single last content page).

Usage:
    cd backend
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_psychology.py --dry-run
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_psychology.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# chapter -> (document_id, review_questions_page)
CHAPTER_PAGES: dict[str, tuple[int, int]] = {
    "Chapter 1: What is Psychology?": (1456, 17),
    "Chapter 2: Methods of Enquiry in Psychology": (1457, 21),
    "Chapter 3: Human Development": (1458, 20),
    "Chapter 4: Sensory, Attentional and Perceptual Processes": (1459, 17),
    "Chapter 5: Learning": (1460, 18),
    "Chapter 6: Human Memory": (1461, 14),
    "Chapter 7: Thinking": (1462, 16),
    "Chapter 8: Motivation and Emotion": (1463, 12),
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
            continue

        res = (
            admin_client.table("lesson_cache")
            .select("id, step_title, lesson_content")
            .eq("grade", "Grade 11")
            .eq("subject", "Psychology")
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
                "grade", "Grade 11"
            ).eq("subject", "Psychology").eq("chapter", chapter).execute()
        print("Invalidated lesson_chapter_doc cache for all touched chapters.")


if __name__ == "__main__":
    main()
