#!/usr/bin/env python3
"""
Migrate GPT-5.5-authored (MANUAL) Grade 9 English lesson_cache content from
its bare chapter-name key to the "Chapter N: <title>" key the live app
actually reads.

Background (see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4q):
- prepare_gpt55_prompts.py + ingest_gpt55_chapter_output.py wrote clean,
  well-grounded content under the BARE chapter title (e.g.
  "How I Taught My Grandmother to Read"), matching syllabus.py.
- The live app's lesson_chapter_doc conversion queries lesson_cache using
  the "Chapter N: <title>" form (e.g. "Chapter 1: How I Taught My
  Grandmother to Read"), which still holds the OLDER, lower-quality
  RAG-generated content from June 2026.
- Net effect: the clean GPT-5.5 content was silently invisible to
  students; they were served the old poor-quality content instead.

This script, for each configured chapter:
  1. Reads the 5 MANUAL rows stored under the bare title.
  2. Re-stores that same content under the "Chapter N: <title>" key via
     store_lesson_cache() (UPDATE-then-INSERT, so it correctly overwrites
     whatever the old RAG row had).
  3. Deletes the now-redundant bare-title rows.
  4. Deletes the corresponding lesson_chapter_doc cache row so the
     Chapter Journey UI reconverts fresh with the migrated content.

Usage:
    cd backend
    python3 scripts/migrate_g9_english_manual_to_prefixed_key.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.lesson_cache_service import store_lesson_cache  # noqa: E402

GRADE = "Grade 9"
SUBJECT = "English"
BOARD = "CBSE"
MODE = "CBSE"

# bare GPT-5.5 title -> correct "Chapter N: <title>" key used by the live app
CHAPTER_MAP = {
    "How I Taught My Grandmother to Read": "Chapter 1: How I Taught My Grandmother to Read",
    "The Pot Maker": "Chapter 2: The Pot Maker",
    "Winds of Change": "Chapter 3: Winds of Change",
    "Vitamin-M": "Chapter 4: Vitamin-M",
    "The World of Limitless Possibilities": "Chapter 5: The World of Limitless Possibilities",
    "Twin Melodies": "Chapter 6: Twin Melodies",
    "Carrier of Words": "Chapter 7: Carrier of Words",
    "Follow That Dream": "Chapter 8: Follow That Dream",
}


def migrate(dry_run: bool = True) -> None:
    for bare_title, prefixed_title in CHAPTER_MAP.items():
        print(f"\n=== {bare_title}  ->  {prefixed_title} ===")

        rows = (
            admin_client.table("lesson_cache")
            .select("step_title, lesson_content, practice_questions, teacher_persona")
            .eq("grade", GRADE)
            .eq("subject", SUBJECT)
            .eq("chapter", bare_title)
            .execute()
            .data
        )

        if not rows:
            print("  [skip] no MANUAL rows found under bare title")
            continue

        for row in rows:
            step_title = row["step_title"]
            content = row["lesson_content"]
            practice_qs = row.get("practice_questions") or []
            persona = row.get("teacher_persona") or ""

            if dry_run:
                print(f"  [dry-run] would migrate step '{step_title}' "
                      f"({len(content)} chars) to key '{prefixed_title}'")
                continue

            from app.services.lesson_cache_service import make_lesson_cache_key

            new_key = make_lesson_cache_key(
                board=BOARD,
                grade=GRADE,
                subject=SUBJECT,
                chapter=prefixed_title,
                mode=MODE,
                step_title=step_title,
                teacher_persona=persona,
            )

            store_lesson_cache(
                cache_key=new_key,
                lesson_content=content,
                source_type="MANUAL",
                board=BOARD,
                grade=GRADE,
                subject=SUBJECT,
                chapter=prefixed_title,
                mode=MODE,
                step_title=step_title,
                teacher_persona=persona,
                practice_questions=practice_qs,
            )
            print(f"  [migrated] step '{step_title}' -> key '{prefixed_title}'")

        if dry_run:
            continue

        # Delete the now-redundant bare-title rows
        admin_client.table("lesson_cache").delete().eq("grade", GRADE).eq(
            "subject", SUBJECT
        ).eq("chapter", bare_title).execute()
        print(f"  [cleanup] deleted bare-title rows for '{bare_title}'")

        # Invalidate the lesson_chapter_doc cache so Chapter Journey reconverts
        admin_client.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
            "subject", SUBJECT
        ).eq("chapter", prefixed_title).eq("mode", MODE).execute()
        print(f"  [cache] invalidated lesson_chapter_doc for '{prefixed_title}'")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true",
        help="Actually perform the migration (default is dry-run)."
    )
    args = parser.parse_args()
    migrate(dry_run=not args.force)


if __name__ == "__main__":
    main()
