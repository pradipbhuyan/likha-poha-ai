#!/usr/bin/env python3
"""
Invalidate ALL stored lesson_chapter_doc rows, platform-wide.
=========================================================================
The student-facing "Refresh lesson" button calls
chapter_doc_service.invalidate_stored_chapter_doc() for ONE chapter at a
time, deleting its cached lesson_chapter_doc row so the next request
reconverts fresh from lesson_cache. This script does the exact same
thing, but for EVERY lesson_chapter_doc row in the database in one pass
— useful after a platform-wide fix to the conversion logic itself (e.g.
the 2026-07-29 Grade 4/5 step-title-mapping fix, or any future fix to
chapter_doc_service.convert_chapter()) where every already-cached
chapter's stored doc could be stale/wrong regardless of grade/subject.

This does NOT touch lesson_cache (the actual authored lesson content) —
it only clears the CONVERTED/CACHED ChapterDoc, which is deterministically
rebuilt from lesson_cache on the next request. Safe to run any time;
worst case is a few extra reconversions (fast, no LLM call).

Usage:
    cd backend
    python3 scripts/invalidate_all_chapter_docs.py --dry-run
    python3 scripts/invalidate_all_chapter_docs.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402


def run(dry_run: bool) -> None:
    print(f"\n  Invalidate ALL lesson_chapter_doc rows (platform-wide)")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE DELETE'}\n")

    # Count + break down by grade/subject first, for visibility.
    result = (
        admin_client.table("lesson_chapter_doc")
        .select("id, grade, subject, chapter")
        .execute()
    )
    rows = result.data or []
    total = len(rows)
    print(f"  Found {total} stored lesson_chapter_doc row(s) total.\n")

    if total == 0:
        print("  Nothing to invalidate. Done.\n")
        return

    by_grade_subject: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row.get("grade") or "?", row.get("subject") or "?")
        by_grade_subject[key] = by_grade_subject.get(key, 0) + 1

    print("  Breakdown by grade/subject:")
    for (grade, subject), count in sorted(by_grade_subject.items()):
        print(f"    {grade:12s} / {subject:20s} : {count:4d} chapter(s)")
    print()

    if dry_run:
        print(f"  [DRY RUN] Would delete all {total} row(s) above. Re-run without --dry-run to apply.\n")
        return

    # Delete in batches by id to avoid any single-request payload limits.
    ids = [row["id"] for row in rows]
    batch_size = 200
    deleted = 0
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        admin_client.table("lesson_chapter_doc").delete().in_("id", batch).execute()
        deleted += len(batch)
        print(f"  Deleted {deleted}/{total}...")

    print(f"\n  Done. Deleted {deleted} stored lesson_chapter_doc row(s).")
    print("  Every chapter will reconvert fresh from lesson_cache on next student visit —")
    print("  no per-chapter 'Refresh lesson' click needed.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Invalidate ALL stored lesson_chapter_doc rows platform-wide"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
