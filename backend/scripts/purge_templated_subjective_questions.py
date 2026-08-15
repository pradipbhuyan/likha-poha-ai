#!/usr/bin/env python3
"""
Purge Templated/Ungrounded Rows from subjective_question_bank
=================================================================
One-off cleanup for the failure class documented in
ingest_gpt55_subjective_question_bank_output.py's _TEMPLATE_PHRASE_PATTERN /
_SECTION_LABEL_PATTERN: questions that treat internal lesson-authoring
markdown scaffolding (bolded sub-labels, section names like "Section B",
"Opening overview", "Revision and recap") as if it were real chapter
content -- e.g. "Explain the chapter point about Faithfulness and connect
it with another idea from the exam-style activities."

This script finds and deletes any row in subjective_question_bank whose
`question` text matches either pattern, for a given grade (or all grades),
so the chapter can be safely re-authored with the fixed prompt template.

Usage:
    cd backend
    # Preview only:
    python3 scripts/purge_templated_subjective_questions.py --grade "Grade 5" --dry-run
    # Actually delete:
    python3 scripts/purge_templated_subjective_questions.py --grade "Grade 5"

    # All grades:
    python3 scripts/purge_templated_subjective_questions.py --all-grades --dry-run
    python3 scripts/purge_templated_subjective_questions.py --all-grades
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402

ALL_GRADES = [
    "Grade 5", "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11", "Grade 12",
]

# Same detection patterns as ingest_gpt55_subjective_question_bank_output.py
_TEMPLATE_PHRASE_PATTERN = re.compile(
    r"chapter point about"
    r"|connect it with another idea"
    r"|and show how it connects with the point"
    r"|explained in (?:the )?(?:opening overview|core explanation|"
    r"revision activities|exam-style activities|the revision|the exam)",
    re.IGNORECASE,
)
_SECTION_LABEL_PATTERN = re.compile(
    r"\b(?:section [a-z]|opening overview|core explanation|worked example|"
    r"quick check question|exam-style problems?|revision (?:and )?recap|"
    r"step-by-step breakdown)\b",
    re.IGNORECASE,
)


def _is_templated(question_text: str) -> bool:
    return bool(
        _TEMPLATE_PHRASE_PATTERN.search(question_text)
        or _SECTION_LABEL_PATTERN.search(question_text)
    )


def purge_grade(grade: str, dry_run: bool) -> dict:
    db = get_content_db(grade)

    print(f"\n{'=' * 70}")
    print(f"  Grade: {grade}{'  [DRY RUN — no deletes]' if dry_run else ''}")
    print(f"{'=' * 70}")

    # Paginate — same 1000-row Supabase page cap other scripts in this repo
    # already work around (see seed_doubt_kb_from_lessons.py).
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        page = (
            db.table("subjective_question_bank")
            .select("id, subject, chapter, question")
            .eq("grade", grade)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        page_rows = page.data or []
        all_rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        offset += page_size

    print(f"  Scanned {len(all_rows)} row(s) for {grade}.")

    bad_rows = [r for r in all_rows if _is_templated(r.get("question", ""))]
    print(f"  Found {len(bad_rows)} templated/ungrounded row(s) to remove.")

    by_chapter: dict[tuple, int] = {}
    for r in bad_rows:
        key = (r.get("subject", ""), r.get("chapter", ""))
        by_chapter[key] = by_chapter.get(key, 0) + 1

    for (subject, chapter), count in sorted(by_chapter.items()):
        print(f"    - {subject} / {chapter}: {count} row(s)")

    deleted = 0
    if not dry_run and bad_rows:
        bad_ids = [r["id"] for r in bad_rows]
        # Delete in batches to avoid overly long IN clauses.
        batch_size = 200
        for i in range(0, len(bad_ids), batch_size):
            batch = bad_ids[i:i + batch_size]
            db.table("subjective_question_bank").delete().in_("id", batch).execute()
            deleted += len(batch)
        print(f"  Deleted {deleted} row(s).")
    elif dry_run and bad_rows:
        print(f"  [DRY RUN] Would delete {len(bad_rows)} row(s).")

    return {
        "grade": grade,
        "scanned": len(all_rows),
        "bad_found": len(bad_rows),
        "deleted": deleted if not dry_run else 0,
        "affected_chapters": len(by_chapter),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purge templated/ungrounded rows from subjective_question_bank"
    )
    parser.add_argument("--grade", help='e.g. "Grade 5" — process a single grade')
    parser.add_argument("--all-grades", action="store_true", help="Process every grade")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    args = parser.parse_args()

    if not args.grade and not args.all_grades:
        print("ERROR: pass --grade \"Grade N\" or --all-grades")
        sys.exit(1)

    grades = ALL_GRADES if args.all_grades else [args.grade]

    totals = {"scanned": 0, "bad_found": 0, "deleted": 0, "affected_chapters": 0}
    for grade in grades:
        result = purge_grade(grade, dry_run=args.dry_run)
        for key in totals:
            totals[key] += result[key]

    print(f"\n{'=' * 70}")
    print("  GRAND TOTAL")
    print(f"{'=' * 70}")
    for key, value in totals.items():
        print(f"  {key}: {value}")
    if args.dry_run and totals["bad_found"]:
        print(
            "\n  Re-run WITHOUT --dry-run to actually delete these rows, then "
            "re-author affected chapters with:\n"
            "    python3 scripts/prepare_gpt55_subjective_question_prompts.py "
            "--grade <grade> --subject <subject> --chapters \"<chapter>\"\n"
            "  (uses the now-fixed prompt template that explicitly forbids "
            "treating lesson-authoring markdown/section names as content)"
        )
    print()


if __name__ == "__main__":
    main()
