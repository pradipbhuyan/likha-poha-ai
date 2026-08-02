#!/usr/bin/env python3
"""
Normalize question_bank.chapter to match current rag_documents naming
=======================================================================
Fixes the root data-quality issue behind the chapter-name mismatch bug (see
docs/ audit): question_bank rows were written under inconsistent chapter
display formats (bare titles, "Chapter N: Title", book-source-prefixed
titles) while the current syllabus/rag_documents naming has since been
cleaned up. The read-side fallback matching in mock_test_service.py already
makes the bank servable regardless of this, but the underlying data is still
messy — this script cleans it up at rest.

For each (grade, subject):
  1. Fetch the canonical chapter list from rag_documents.
  2. For each distinct question_bank.chapter value:
     - If it doesn't already exact-match a canonical chapter, compute its
       normalized "core" title and match against the normalized core of
       every canonical chapter.
     - Exactly one match -> UPDATE all rows with that chapter to the
       canonical string.
     - Zero matches -> genuinely orphaned (no current chapter corresponds
       to it) -> UPDATE status='needs_review' (soft-mark, not delete).
     - 2+ matches -> ambiguous -> skip, logged for manual review.

Always dry-run by default (prints planned changes, writes nothing) --
pass --live to actually apply them.

Usage:
    cd backend
    python3 scripts/normalize_question_bank_chapters.py --grade "Grade 11" --subject Biology
    python3 scripts/normalize_question_bank_chapters.py --grade "Grade 11" --subject Biology --live
    python3 scripts/normalize_question_bank_chapters.py --all-grade-12   # dry-run every Grade 12 subject
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.mock_test_service import normalize_chapter_core  # noqa: E402

PAGE = 1000


def fetch_all(table_query_builder, page: int = PAGE) -> list[dict]:
    """Paginate a Supabase query past the 1000-row PostgREST cap."""
    all_rows: list[dict] = []
    start = 0
    while True:
        result = table_query_builder().range(start, start + page - 1).execute()
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < page:
            break
        start += page
    return all_rows


def get_canonical_chapters(grade: str, subject: str) -> list[str]:
    db = get_content_db(grade)
    rows = fetch_all(lambda: (
        db.table("rag_documents")
        .select("chapter")
        .eq("grade", grade)
        .eq("subject", subject)
    ))
    seen: list[str] = []
    for r in rows:
        ch = r.get("chapter")
        if ch and ch not in seen:
            seen.append(ch)
    return seen


def get_distinct_bank_chapters(grade: str, subject: str) -> list[str]:
    db = get_content_db(grade)
    rows = fetch_all(lambda: (
        db.table("question_bank")
        .select("chapter")
        .eq("grade", grade)
        .eq("subject", subject)
    ))
    seen: list[str] = []
    for r in rows:
        ch = r.get("chapter")
        if ch and ch not in seen:
            seen.append(ch)
    return seen


def count_rows_for_chapter(db, grade: str, subject: str, chapter: str) -> int:
    r = (
        db.table("question_bank")
        .select("id", count="exact")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .limit(1)
        .execute()
    )
    return r.count or 0


def normalize_subject(grade: str, subject: str, live: bool, restore_status: bool = False) -> dict:
    """
    restore_status: when True, a successful RENAME also forces status='active'
    on those rows -- used for the recovery pass after the normalize_chapter_core
    stacked-prefix bug (fixed 2026-08-02) incorrectly flagged ~48k legitimately
    current chapters as needs_review because the single-pass stripping missed
    "Part N - Chapter M: Title"-style stacked prefixes.
    """
    canonical = get_canonical_chapters(grade, subject)
    canonical_by_core: dict[str, list[str]] = {}
    for c in canonical:
        canonical_by_core.setdefault(normalize_chapter_core(c), []).append(c)

    bank_chapters = get_distinct_bank_chapters(grade, subject)
    if not bank_chapters:
        return {"grade": grade, "subject": subject, "bank_chapters": 0}

    db = get_content_db(grade)
    stats = {"grade": grade, "subject": subject, "bank_chapters": len(bank_chapters),
              "already_canonical": 0, "renamed": 0, "renamed_rows": 0,
              "orphaned": 0, "ambiguous": 0}

    for old_chapter in bank_chapters:
        if old_chapter in canonical:
            stats["already_canonical"] += 1
            continue

        core = normalize_chapter_core(old_chapter)
        matches = canonical_by_core.get(core, [])

        if len(matches) == 1:
            new_chapter = matches[0]
            row_count = count_rows_for_chapter(db, grade, subject, old_chapter)
            print(f"  [RENAME] {grade} / {subject} ({row_count} rows)\n"
                  f"           {old_chapter!r}\n"
                  f"        -> {new_chapter!r}"
                  + (" [+ restoring status=active]" if restore_status else ""))
            stats["renamed"] += 1
            stats["renamed_rows"] += row_count
            if live:
                update = {"chapter": new_chapter}
                if restore_status:
                    update["status"] = "active"
                (
                    db.table("question_bank")
                    .update(update)
                    .eq("grade", grade)
                    .eq("subject", subject)
                    .eq("chapter", old_chapter)
                    .execute()
                )
        elif len(matches) == 0:
            print(f"  [ORPHAN] {grade} / {subject}\n"
                  f"           {old_chapter!r} -- no current chapter matches, "
                  f"marking needs_review")
            stats["orphaned"] += 1
            if live:
                (
                    db.table("question_bank")
                    .update({"status": "needs_review"})
                    .eq("grade", grade)
                    .eq("subject", subject)
                    .eq("chapter", old_chapter)
                    .execute()
                )
        else:
            print(f"  [SKIP-AMBIGUOUS] {grade} / {subject}\n"
                  f"           {old_chapter!r} matches {len(matches)} canonical chapters: "
                  f"{matches} -- leaving as-is, needs manual review")
            stats["ambiguous"] += 1

    return stats


def get_all_subjects(grade: str) -> list[str]:
    db = get_content_db(grade)
    rows = fetch_all(lambda: (
        db.table("question_bank")
        .select("subject")
        .eq("grade", grade)
    ))
    seen: list[str] = []
    for r in rows:
        s = r.get("subject")
        if s and s not in seen:
            seen.append(s)
    return seen


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize question_bank.chapter to match current rag_documents naming"
    )
    parser.add_argument("--grade", help='e.g. "Grade 11" (required unless --all-grade-11/--all-grade-12)')
    parser.add_argument("--subject", help="e.g. Biology (omit to process every subject in the grade)")
    parser.add_argument("--all-grade-11", action="store_true", help="Process every subject in Grade 11")
    parser.add_argument("--all-grade-12", action="store_true", help="Process every subject in Grade 12")
    parser.add_argument("--all-grades", action="store_true", help="Process every subject in every grade 5-12")
    parser.add_argument("--live", action="store_true", help="Actually write changes (default: dry-run)")
    parser.add_argument(
        "--restore-status", action="store_true",
        help="Also force status='active' on a successful RENAME match. Use this for the "
             "recovery pass after the normalize_chapter_core stacked-prefix bug (fixed "
             "2026-08-02) incorrectly flagged legitimately-current chapters as needs_review.",
    )
    args = parser.parse_args()

    jobs: list[tuple[str, str]] = []
    if args.all_grades:
        for grade in [f"Grade {i}" for i in range(5, 13)]:
            for subject in get_all_subjects(grade):
                jobs.append((grade, subject))
    elif args.all_grade_11 or args.all_grade_12:
        for grade, flag in (("Grade 11", args.all_grade_11), ("Grade 12", args.all_grade_12)):
            if flag:
                for subject in get_all_subjects(grade):
                    jobs.append((grade, subject))
    elif args.grade and args.subject:
        jobs.append((args.grade, args.subject))
    elif args.grade:
        for subject in get_all_subjects(args.grade):
            jobs.append((args.grade, subject))
    else:
        print("ERROR: provide --grade [--subject], --all-grade-11 / --all-grade-12, or --all-grades")
        sys.exit(1)

    print(f"\n  Normalize question_bank chapters")
    print(f"  Mode: {'LIVE WRITE' if args.live else 'DRY RUN'}"
          + (" + RESTORE STATUS on rename" if args.restore_status else ""))
    print(f"  Jobs: {len(jobs)}\n")

    all_stats = []
    for grade, subject in jobs:
        print(f"\n{'=' * 78}\n{grade} / {subject}\n{'=' * 78}")
        stats = normalize_subject(grade, subject, live=args.live, restore_status=args.restore_status)
        all_stats.append(stats)

    print(f"\n{'=' * 78}\nSUMMARY\n{'=' * 78}")
    print(f"{'Grade':<10}{'Subject':<24}{'Distinct':<10}{'OK':<6}{'Renamed':<9}{'RenamedRows':<13}{'Orphaned':<10}{'Ambiguous':<10}")
    totals = {"renamed": 0, "renamed_rows": 0, "orphaned": 0, "ambiguous": 0}
    for s in all_stats:
        if s.get("bank_chapters", 0) == 0:
            continue
        print(f"{s['grade']:<10}{s['subject']:<24}{s['bank_chapters']:<10}"
              f"{s.get('already_canonical', 0):<6}{s.get('renamed', 0):<9}"
              f"{s.get('renamed_rows', 0):<13}{s.get('orphaned', 0):<10}{s.get('ambiguous', 0):<10}")
        totals["renamed"] += s.get("renamed", 0)
        totals["renamed_rows"] += s.get("renamed_rows", 0)
        totals["orphaned"] += s.get("orphaned", 0)
        totals["ambiguous"] += s.get("ambiguous", 0)

    print(f"\nTotal: {totals['renamed']} chapter labels renamed ({totals['renamed_rows']} individual rows), "
          f"{totals['orphaned']} chapter labels orphaned (marked needs_review), "
          f"{totals['ambiguous']} ambiguous (left as-is)")
    if not args.live:
        print("\nThis was a DRY RUN — no changes were written. Re-run with --live to apply.\n")


if __name__ == "__main__":
    main()
