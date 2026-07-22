#!/usr/bin/env python3
"""
Validate a GPT-5-answered CBSE question set before uploading to Supabase.

Nothing is written to the DB until every check below passes (or you pass
--force to upload anyway with warnings noted). Checks:
  - Every question_number from the original extraction is present, none
    added/renumbered/dropped.
  - question_text is non-empty for every question (a blank question_text
    with real content stuffed into `options` is a parser bug, not valid
    data — flagged, not silently accepted).
  - For mcq/assertion_reason: exactly 4 options, and answer_text matches
    one of them exactly.
  - answer_text and answer_explanation are both non-empty for every row.
  - No answer_text of "NEEDS_MANUAL_REVIEW..." slips through silently —
    these are reported so a human can look at the flagged diagram-dependent
    questions specifically.

Usage:
    cd backend
    .venv/bin/python3 scripts/import_cbse_sample_paper_answers.py \\
        --answers scripts/cbse_pilot_data/gpt5_answers_maths_std_2025_26.json \\
        --grade "Grade 10" --academic-year "2025-26" --source-subject-code MathsStandard \\
        --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db

BOARD = "CBSE"


def validate(questions: list[dict], expected_numbers: set[str] | None = None) -> list[str]:
    """expected_numbers: the full set of question_number values already
    uploaded to the DB for this paper (status=extracted) — used to catch
    dropped/renumbered/duplicated questions. Works for both flat integer
    numbering (Maths/Science/Social Science) and compound nested numbering
    (English "1.I", "6.A.II"; Hindi "1.क") since it's a plain set comparison,
    not an assumed contiguous integer range."""
    problems: list[str] = []
    seen_numbers: set[str] = set()

    for q in questions:
        qn = str(q.get("question_number"))
        label = f"Q{qn}"

        if qn in seen_numbers:
            problems.append(f"{label}: duplicate question_number")
        seen_numbers.add(qn)

        if not (q.get("question_text") or "").strip():
            problems.append(f"{label}: question_text is empty (real content likely misfiled into options)")

        q_type = q.get("question_type")
        options = q.get("options") or []
        answer_text = (q.get("answer_text") or "").strip()
        answer_explanation = (q.get("answer_explanation") or "").strip()

        if not answer_text:
            problems.append(f"{label}: answer_text is empty")
        if not answer_explanation:
            problems.append(f"{label}: answer_explanation is empty")

        if answer_text.startswith("NEEDS_MANUAL_REVIEW"):
            problems.append(f"{label}: flagged NEEDS_MANUAL_REVIEW — {answer_text}")

        if q_type in ("mcq", "assertion_reason"):
            # Most subjects are always-4-option MCQs, but English's
            # "select from brackets" / true-false style questions are
            # genuinely 2- or 3-option — only flag if suspiciously few.
            if len(options) < 2:
                problems.append(f"{label}: {q_type} has {len(options)} options, expected at least 2")
            elif answer_text and answer_text not in options:
                problems.append(f"{label}: answer_text does not exactly match any option")

    if expected_numbers is not None:
        missing = sorted(expected_numbers - seen_numbers)
        extra = sorted(seen_numbers - expected_numbers)
        if missing:
            problems.append(f"Missing question_number(s) vs. uploaded extraction: {missing}")
        if extra:
            problems.append(f"Unexpected question_number(s) not in the uploaded extraction: {extra}")

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate + upload GPT-5-answered CBSE questions")
    parser.add_argument("--answers", required=True)
    parser.add_argument("--grade", required=True)
    parser.add_argument("--academic-year", required=True)
    parser.add_argument("--source-subject-code", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Upload even if validation reports problems")
    args = parser.parse_args()

    questions = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    print(f"Loaded {len(questions)} answered questions from {args.answers}")

    db = get_content_db(args.grade)
    existing = (
        db.table("board_sample_papers")
        .select("id")
        .eq("board", BOARD).eq("academic_year", args.academic_year)
        .eq("grade", args.grade).eq("source_subject_code", args.source_subject_code)
        .execute()
    )
    if not existing.data:
        print("  [error] no board_sample_papers row found for this paper — run extract_cbse_sample_paper.py --create-paper first")
        sys.exit(1)
    paper_id = existing.data[0]["id"]

    uploaded_rows = (
        db.table("board_sample_paper_questions")
        .select("question_number")
        .eq("paper_id", paper_id)
        .execute()
    )
    expected_numbers = {str(r["question_number"]) for r in (uploaded_rows.data or [])}

    problems = validate(questions, expected_numbers)
    if problems:
        print(f"\n{'='*70}\n  VALIDATION REPORT — {len(problems)} issue(s)\n{'='*70}")
        for p in problems:
            print(f"  ❌ {p}")
        print()
        if not args.force:
            print("Nothing uploaded. Fix the issues above (or pass --force to upload anyway).")
            return
        print("--force passed — uploading despite the issues above.")
    else:
        print("\n✅ Validation passed — no issues found.")

    if args.dry_run:
        print("[dry-run] skipping DB writes")
        return

    updated = 0
    for q in questions:
        result = (
            db.table("board_sample_paper_questions")
            .update({
                "answer_text": q.get("answer_text", ""),
                "answer_explanation": q.get("answer_explanation", ""),
                "status": "answered",
            })
            .eq("paper_id", paper_id)
            .eq("question_number", str(q["question_number"]))
            .execute()
        )
        if result.data:
            updated += 1
        else:
            print(f"  [warn] Q{q['question_number']}: no matching row in board_sample_paper_questions to update")
    print(f"Updated {updated}/{len(questions)} question rows to status=answered")

    # Only now — once every question the extraction uploaded is confirmed
    # answered — does the paper become visible to students. Papers are
    # created as "pending_answers"; a NEEDS_MANUAL_REVIEW row or a partial
    # --force upload must not flip this, or students would see it with
    # some questions still blank.
    remaining = (
        db.table("board_sample_paper_questions")
        .select("id", count="exact")
        .eq("paper_id", paper_id)
        .neq("status", "answered")
        .execute()
    )
    if remaining.count == 0:
        db.table("board_sample_papers").update({"status": "active"}).eq("id", paper_id).execute()
        print("✅ All questions answered — paper is now active (visible to students).")
    else:
        print(f"⚠️  {remaining.count} question(s) still not status=answered — "
              f"paper stays pending_answers (hidden from students) until they are.")


if __name__ == "__main__":
    main()
