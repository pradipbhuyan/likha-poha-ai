#!/usr/bin/env python3
"""
Ingest GPT-5.5 Lesson-Plan Handout Output
=====================================
See docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md for the full workflow this
script completes (paired with scripts/prepare_gpt55_lesson_plan_prompts.py).

Takes the JSON output produced by pasting a lesson-plan authoring prompt into
a GPT-5.5 chat session, validates it against the expected schema, resolves
the CURRENT canonical (rag_documents-format) chapter name — same resolution
ingest_gpt55_question_bank_output.py uses — and writes
backend/app/data/lesson_plan_bank/<grade_slug>/<subject_slug>/<chapter_slug>.json,
overwriting any existing handout for that chapter.

Usage:
    cd backend
    # Single file:
    python3 scripts/ingest_gpt55_lesson_plan_output.py --input chapter_lesson_plan.json --dry-run
    python3 scripts/ingest_gpt55_lesson_plan_output.py --input chapter_lesson_plan.json

    # Whole folder:
    python3 scripts/ingest_gpt55_lesson_plan_output.py --dir ~/Downloads/GPT55_Lesson_Plan_Prompts_Grade_9_Social_Science --dry-run
    python3 scripts/ingest_gpt55_lesson_plan_output.py --dir ~/Downloads/GPT55_Lesson_Plan_Prompts_Grade_9_Social_Science
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.lesson_plan_bank_service import _slugify, _BANK_ROOT  # noqa: E402

REQUIRED_KEYS = ["grade", "subject", "chapter", "lesson_plan_markdown"]
MIN_MARKDOWN_LENGTH = 200


def load_and_validate(input_path: Path) -> dict:
    """Load the GPT-5.5 JSON output and validate its schema. Raises ValueError on failure."""
    raw = input_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Input is not valid JSON: {e}")

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"JSON is missing required keys: {missing}")

    markdown = str(data.get("lesson_plan_markdown") or "").strip()
    if len(markdown) < MIN_MARKDOWN_LENGTH:
        raise ValueError(
            f"lesson_plan_markdown is too short ({len(markdown)} chars, "
            f"need >= {MIN_MARKDOWN_LENGTH})."
        )

    return data


def resolve_canonical_chapter(grade: str, subject: str, chapter: str) -> str:
    """Same canonical-chapter resolution as ingest_gpt55_question_bank_output.py."""
    from app.services.mock_test_service import normalize_chapter_core  # noqa: PLC0415

    db = get_content_db(grade)
    try:
        exact = (
            db.table("rag_documents")
            .select("chapter")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .limit(1)
            .execute()
        )
        if exact.data:
            return exact.data[0]["chapter"]

        core = normalize_chapter_core(chapter)
        if core:
            candidates = (
                db.table("rag_documents")
                .select("chapter")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", f"%{core}%")
                .limit(5)
                .execute()
            )
            rows = candidates.data or []
            if len(rows) == 1:
                return rows[0]["chapter"]
            if len(rows) > 1:
                print(f"    [warn] Ambiguous chapter match for {chapter!r} "
                      f"({len(rows)} rag_documents candidates) — using given chapter as-is.")
    except Exception as e:
        print(f"    [warn] Could not resolve canonical chapter name: {e}")

    return chapter


def ingest(data: dict, dry_run: bool) -> dict:
    grade, subject = data["grade"], data["subject"]
    chapter = resolve_canonical_chapter(grade, subject, data["chapter"])
    markdown = data["lesson_plan_markdown"]

    handout_path = _BANK_ROOT / _slugify(grade) / _slugify(subject) / f"{_slugify(chapter)}.json"

    print(f"  {grade} / {subject} / {chapter}")
    print(f"    {len(markdown):,} chars of lesson-plan markdown -> {handout_path}")

    if dry_run:
        print(f"    [DRY RUN] Would write this file"
              f"{' (overwriting existing handout)' if handout_path.exists() else ''}.")
        return {"grade": grade, "subject": subject, "chapter": chapter, "status": "dry-run"}

    handout_path.parent.mkdir(parents=True, exist_ok=True)
    handout_path.write_text(
        json.dumps(
            {"grade": grade, "subject": subject, "chapter": chapter, "lesson_plan_markdown": markdown},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"    Written.")
    return {"grade": grade, "subject": subject, "chapter": chapter, "status": "ingested"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 lesson-plan handout authoring JSON output")
    parser.add_argument("--input", help="Path to a single GPT-5.5 JSON output file")
    parser.add_argument("--dir", help="Folder to scan for *.json lesson-plan output files")
    parser.add_argument("--files", nargs="+", help="Explicit list of JSON files to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()

    if not args.input and not args.dir and not args.files:
        print("ERROR: provide --input <file>, --dir <folder>, or --files <file1> <file2> ...")
        sys.exit(1)

    if args.input:
        paths = [Path(args.input)]
    elif args.files:
        paths = [Path(f) for f in args.files]
    else:
        folder = Path(args.dir).expanduser()
        if not folder.is_dir():
            print(f"ERROR: not a directory: {folder}")
            sys.exit(1)
        paths = sorted(p for p in folder.glob("*.json"))

    if not paths:
        print("No .json files found to process.")
        return

    print(f"\n  Ingest GPT-5.5 Lesson-Plan Handout Output")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}")
    print(f"  Files to check: {len(paths)}\n")

    results = []
    for path in paths:
        if not path.exists():
            results.append({"file": path.name, "status": "error", "reason": "file not found"})
            continue

        print(f"\n{'=' * 78}\n{path.name}\n{'=' * 78}")
        try:
            data = load_and_validate(path)
            result = ingest(data, dry_run=args.dry_run)
            result["file"] = path.name
            results.append(result)
        except ValueError as e:
            print(f"  ERROR: {e}")
            results.append({"file": path.name, "status": "error", "reason": str(e)})
        except Exception as e:
            print(f"  ERROR (unexpected): {e}")
            results.append({"file": path.name, "status": "error", "reason": str(e)})

    print(f"\n{'=' * 78}\nSUMMARY\n{'=' * 78}")
    for r in results:
        if r["status"] == "error":
            print(f"  [ERROR] {r['file']} — {r['reason']}")
        elif r["status"] == "dry-run":
            print(f"  [DRY]   {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']}")
        else:
            print(f"  [OK]    {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']}")

    ok = sum(1 for r in results if r["status"] in ("ingested", "dry-run"))
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\nTotal: {len(results)} | OK: {ok} | Error: {err}\n")


if __name__ == "__main__":
    main()
