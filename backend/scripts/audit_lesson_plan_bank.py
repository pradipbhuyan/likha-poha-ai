#!/usr/bin/env python3
"""
Audit Lesson Plan Bank
=======================
Read-only audit of every handout in app/data/lesson_plan_bank/ against the
current deterministic quality rules (app/services/lesson_plan_quality_checks.py).

This is the file-based equivalent of a database "dry-run migration report"
for a codebase that has no lesson_plans DB table and no automated
regeneration pipeline (see ../../ARCHITECTURE_MISMATCH_NOTE.md for why).
Every handout in the bank was produced by the same offline, human-in-the-loop
workflow (scripts/prepare_gpt55_lesson_plan_prompts.py +
scripts/ingest_gpt55_lesson_plan_output.py) — there is no "teacher-edited"
vs "AI-only" distinction to make here, because there is no editing feature
at all. So the only meaningful classification this script can make,
without fabricating data the codebase doesn't track, is:

  - PASS:    no hard errors, no warnings           -> nothing to do
  - WARN:    no hard errors, but 1+ warnings        -> optional re-authoring
  - ERROR:   1+ hard errors                          -> should be re-authored
             (these should never exist post-ingestion-gate, but the gate
             was only added partway through the bank's history — this
             script is exactly how such legacy violations get found)

Never writes to any file. Exit code is non-zero if any ERROR-level handout
is found, so this can be wired into CI as a regression guard.

Usage:
    cd backend
    python3 scripts/audit_lesson_plan_bank.py
    python3 scripts/audit_lesson_plan_bank.py --grade "Grade 9"
    python3 scripts/audit_lesson_plan_bank.py --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_plan_quality_checks import check_lesson_plan_markdown, has_errors  # noqa: E402

BANK_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "lesson_plan_bank"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit every lesson_plan_bank handout against current quality rules (read-only).")
    parser.add_argument("--grade", help="Only audit one grade folder slug, e.g. 'Grade 9' or 'grade_9'.")
    parser.add_argument("--subject", help="Only audit one subject folder slug.")
    parser.add_argument("--verbose", action="store_true", help="Print every issue found, not just counts.")
    args = parser.parse_args()

    if not BANK_ROOT.is_dir():
        print(f"ERROR: bank root not found: {BANK_ROOT}")
        sys.exit(1)

    files = sorted(BANK_ROOT.rglob("*.json"))
    if args.grade:
        grade_slug = args.grade.lower().replace(" ", "_")
        files = [f for f in files if grade_slug in f.parts]
    if args.subject:
        subject_slug = args.subject.lower().replace(" ", "_")
        files = [f for f in files if subject_slug in f.parts]

    n_pass = n_warn = n_error = n_unreadable = 0
    error_files: list[tuple[Path, list[str]]] = []
    warn_files: list[tuple[Path, list[str]]] = []

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            n_unreadable += 1
            print(f"  [UNREADABLE] {f.relative_to(BANK_ROOT)} — {e}")
            continue

        markdown = data.get("lesson_plan_markdown", "")
        grade = data.get("grade", "")
        subject = data.get("subject", "")
        issues = check_lesson_plan_markdown(markdown, grade, subject)

        if has_errors(issues):
            n_error += 1
            error_files.append((f, [str(i) for i in issues]))
        elif issues:
            n_warn += 1
            warn_files.append((f, [str(i) for i in issues]))
        else:
            n_pass += 1

    print("\n" + "=" * 78)
    print("Lesson Plan Bank Audit (read-only, no writes)")
    print("=" * 78)
    print(f"Bank root:       {BANK_ROOT}")
    print(f"Files scanned:   {len(files)}")
    print(f"  PASS (clean):  {n_pass}")
    print(f"  WARN only:     {n_warn}")
    print(f"  ERROR:         {n_error}")
    if n_unreadable:
        print(f"  UNREADABLE:    {n_unreadable}")
    print("=" * 78)

    if error_files:
        print("\nFiles with hard ERRORS (should be re-authored):")
        for f, msgs in error_files:
            print(f"\n  {f.relative_to(BANK_ROOT)}")
            for m in msgs:
                if "[ERROR]" in m:
                    print(f"    {m}")

    if args.verbose and warn_files:
        print("\nFiles with WARNINGS only (optional re-authoring):")
        for f, msgs in warn_files:
            print(f"\n  {f.relative_to(BANK_ROOT)}")
            for m in msgs:
                print(f"    {m}")
    elif warn_files:
        print(f"\n({len(warn_files)} files have warnings only — re-run with --verbose to list them.)")

    print()
    sys.exit(1 if error_files else 0)


if __name__ == "__main__":
    main()
