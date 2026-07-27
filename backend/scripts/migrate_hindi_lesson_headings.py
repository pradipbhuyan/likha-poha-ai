#!/usr/bin/env python3
"""
Migrate Hindi Lesson Headings — English -> Hindi
====================================================
Fixes user report: "why Hindi chapters are written in English?" — the
lesson BODY text for Grade 9 Hindi chapters was already correctly
authored in Hindi (grounded in the Hindi source PDFs), but the 7
structural section headings ("## What you will learn", "## Simple
explanation", etc.) were hardcoded in English by the old prompt
template (see scripts/prepare_gpt55_prompts.py) and stayed English in
every already-ingested Hindi lesson_cache row.

This is a one-time migration for content ingested BEFORE the prompt
template fix: it finds every lesson_cache row for grade="Grade 9",
subject="Hindi" and replaces the 7 English heading lines with their
Hindi equivalents (scripts/prepare_gpt55_prompts.py HEADING_SETS["hi"]),
leaving every other character of the lesson body completely untouched.

Deliberately NOT translated (must stay English, matched by regex
elsewhere): "Question:", "Solution:", "Step N:", "Final answer:",
"Answer:", "Explanation:" — see the note in HEADING_SETS' docstring.

Usage:
    cd backend
    python3 scripts/migrate_hindi_lesson_headings.py --dry-run
    python3 scripts/migrate_hindi_lesson_headings.py --force
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from scripts.prepare_gpt55_prompts import HEADING_SETS  # noqa: E402

EN = HEADING_SETS["en"]
HI = HEADING_SETS["hi"]

# Ordered (regex-matching-English-heading -> Hindi heading) replacement
# pairs. FOUR+ English heading formats were found in production data
# across different content-generation pipelines used before the prompt
# template fix, e.g. for "What you will learn":
#   - Plain:                "## What you will learn"
#   - Numbered:              "## 1. What you will learn"
#   - Deeper hash+numbered:  "#### 1. What you will learn"  (3 or 4 #'s)
#   - No hash at all:        "1. What you will learn"       (plain numbered line)
#   - Mixed Hindi/English:   "## आप क्या सीखेंगे (What You Will Learn)"
# The pattern below is intentionally permissive:
#   - "#{0,4}\s*"     matches 0 to 4 leading hashes (optional)
#   - "(?:\d+\.\s*)?" absorbs an optional numbering prefix
#   - "(?:[^\n(]*\()?" absorbs any leading Hindi text + opening paren, so
#     a heading that already contains "(What You Will Learn)" is also
#     normalized to the same clean, unnumbered Hindi-only heading.
#   - trailing "\)?\s*$" absorbs the matching closing paren.
# A zero-hash match is restricted to a short standalone line (<=80 chars,
# via requiring the WHOLE line to be just this heading) to avoid
# accidentally matching this phrase if it ever appears mid-sentence.
# All matched variants collapse to the same clean "## <Hindi heading>"
# with no numbering, no hash-level drift, and no English text.
HEADING_REPLACEMENTS = [
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['what_you_will_learn'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['what_you_will_learn']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['simple_explanation'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['simple_explanation']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['step_by_step_breakdown'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['step_by_step_breakdown']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['worked_example'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['worked_example']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['common_mistake'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['common_mistake']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['quick_check_question'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['quick_check_question']}"),
    (re.compile(rf"^#{{0,4}}\s*(?:\d+\.\s*)?(?:[^\n(]*\()?{re.escape(EN['summary'])}\)?\s*$", re.MULTILINE | re.IGNORECASE),
     f"## {HI['summary']}"),
]


def migrate(dry_run: bool) -> None:
    print(f"\n  Migrate Hindi Lesson Headings — English -> Hindi")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    result = (
        admin_client.table("lesson_cache")
        .select("id, chapter, step_title, lesson_content")
        .eq("grade", "Grade 9")
        .eq("subject", "Hindi")
        .execute()
    )
    rows = result.data or []
    print(f"  Found {len(rows)} Grade 9 Hindi lesson_cache row(s).\n")

    changed_count = 0
    unchanged_count = 0

    for row in rows:
        content = row["lesson_content"] or ""
        original = content
        for pattern, hi_heading in HEADING_REPLACEMENTS:
            content = pattern.sub(hi_heading, content)

        if content == original:
            print(f"  [{row['chapter']}] {row['step_title']}: no English headings found, skipping.")
            unchanged_count += 1
            continue

        changed_count += 1
        print(f"  [{row['chapter']}] {row['step_title']}: translating headings...")

        if dry_run:
            print(f"    -> [DRY RUN] Would update row id={row['id']}.")
            continue

        admin_client.table("lesson_cache").update(
            {"lesson_content": content}
        ).eq("id", row["id"]).execute()
        print(f"    -> Updated row id={row['id']}.")

    print(f"\n  Summary: {changed_count} row(s) migrated, {unchanged_count} row(s) already clean/unchanged.\n")


def invalidate_chapter_docs(dry_run: bool) -> None:
    """
    Delete all Grade 9 Hindi lesson_chapter_doc rows so the Chapter
    Journey UI reconverts from the freshly-translated lesson_cache
    content instead of serving a stale pre-migration document.
    """
    print("  Invalidating Grade 9 Hindi lesson_chapter_doc cache...")
    if dry_run:
        print("    -> [DRY RUN] Would delete all Grade 9 Hindi lesson_chapter_doc rows.")
        return

    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db("Grade 9")
        result = (
            db.table("lesson_chapter_doc")
            .delete()
            .eq("grade", "Grade 9")
            .eq("subject", "Hindi")
            .execute()
        )
        deleted = len(result.data or [])
        print(f"    -> Invalidated {deleted} stale lesson_chapter_doc row(s).")
    except Exception as e:
        print(f"    [warn] Could not invalidate lesson_chapter_doc cache: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Grade 9 Hindi lesson_cache section headings from English to Hindi"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--force", action="store_true", help="Actually write the changes (required to run live)")
    args = parser.parse_args()

    if not args.dry_run and not args.force:
        print("ERROR: pass either --dry-run or --force.")
        sys.exit(1)

    migrate(dry_run=args.dry_run)
    invalidate_chapter_docs(dry_run=args.dry_run)

    print("Done.\n")


if __name__ == "__main__":
    main()
