#!/usr/bin/env python3
"""
Ingest GPT-5.5 Subjective Question-Bank Output
=====================================
See docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md for the full
workflow this script completes (paired with
scripts/prepare_gpt55_subjective_question_prompts.py). Sibling of
ingest_gpt55_question_bank_output.py (MCQ bank), adapted for subjective
questions.

Takes the JSON output produced by pasting a subjective-question authoring
prompt into a GPT-5.5 chat session, validates it against the expected schema
(question/model_answer minimum length, marks a positive integer, difficulty
in Easy/Medium/Hard), writes the chapter string using the CURRENT canonical
(rag_documents-format) chapter name, clears any existing
subjective_question_bank rows for that exact chapter first, and inserts the
validated questions via
app.services.subjective_question_bank_service.add_questions_to_subjective_bank.

Usage:
    cd backend
    # Single file:
    python3 scripts/ingest_gpt55_subjective_question_bank_output.py --input chapter_subjective.json --dry-run
    python3 scripts/ingest_gpt55_subjective_question_bank_output.py --input chapter_subjective.json

    # Whole folder:
    python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir ~/Downloads/GPT55_Subjective_Prompts_Grade_9_Social_Science --dry-run
    python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir ~/Downloads/GPT55_Subjective_Prompts_Grade_9_Social_Science
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.subjective_question_bank_service import (  # noqa: E402
    add_questions_to_subjective_bank,
    clear_subjective_bank_for_chapter,
)

BOARD = "CBSE"
DIFFICULTIES = {"Easy", "Medium", "Hard"}
REQUIRED_MANIFEST_KEYS = ["grade", "subject", "chapter"]


def _is_valid_question(q: dict) -> tuple[bool, str]:
    if not isinstance(q, dict):
        return False, "not an object"
    if not q.get("question") or len(str(q["question"]).strip()) < 10:
        return False, "question text missing or too short"
    if not q.get("model_answer") or len(str(q["model_answer"]).strip()) < 15:
        return False, "model_answer missing or too short"
    marks = q.get("marks")
    if not isinstance(marks, int) or marks <= 0:
        return False, "marks must be a positive integer"
    if q.get("difficulty") not in DIFFICULTIES:
        return False, f"difficulty must be one of {sorted(DIFFICULTIES)}"
    return True, ""


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

    if "manifest" not in data or "questions" not in data:
        raise ValueError("Top-level JSON must have both 'manifest' and 'questions' keys.")

    manifest = data["manifest"]
    questions = data["questions"]

    missing_manifest_keys = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing_manifest_keys:
        raise ValueError(f"Manifest is missing required keys: {missing_manifest_keys}")

    if not isinstance(questions, list) or not questions:
        raise ValueError("'questions' must be a non-empty array.")

    valid_questions = []
    rejected = 0
    for i, q in enumerate(questions):
        ok, reason = _is_valid_question(q)
        if ok:
            valid_questions.append(q)
        else:
            rejected += 1
            print(f"    [reject] question {i + 1}: {reason}")

    if not valid_questions:
        raise ValueError("No valid questions survived validation.")
    if rejected:
        print(f"    {rejected}/{len(questions)} question(s) rejected by validation, "
              f"{len(valid_questions)} will be ingested.")

    data["questions"] = valid_questions
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
                      f"({len(rows)} rag_documents candidates) — using manifest chapter as-is.")
    except Exception as e:
        print(f"    [warn] Could not resolve canonical chapter name: {e}")

    return chapter


def ingest(data: dict, dry_run: bool) -> dict:
    manifest = data["manifest"]
    questions = data["questions"]
    grade, subject = manifest["grade"], manifest["subject"]
    chapter = resolve_canonical_chapter(grade, subject, manifest["chapter"])

    by_difficulty: dict[str, list] = {"Easy": [], "Medium": [], "Hard": []}
    for q in questions:
        by_difficulty[q["difficulty"]].append(q)

    print(f"  {grade} / {subject} / {chapter}")
    print(f"    {len(questions)} valid question(s): "
          f"{len(by_difficulty['Easy'])} Easy, "
          f"{len(by_difficulty['Medium'])} Medium, "
          f"{len(by_difficulty['Hard'])} Hard")

    if dry_run:
        print(f"    [DRY RUN] Would clear existing subjective_question_bank rows for this "
              f"chapter, then insert {len(questions)} new question(s).")
        return {"grade": grade, "subject": subject, "chapter": chapter,
                "status": "dry-run", "inserted": len(questions)}

    deleted = clear_subjective_bank_for_chapter(grade, subject, chapter)
    print(f"    Cleared {deleted} existing row(s) for this chapter.")

    for difficulty, qs in by_difficulty.items():
        if not qs:
            continue
        add_questions_to_subjective_bank(
            questions=qs,
            board=BOARD,
            grade=grade,
            subject=subject,
            chapter=chapter,
            difficulty=difficulty,
        )

    print(f"    Inserted (deduped against any remaining rows automatically).")
    return {"grade": grade, "subject": subject, "chapter": chapter,
            "status": "ingested", "inserted": len(questions), "cleared": deleted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 subjective question-bank authoring JSON output")
    parser.add_argument("--input", help="Path to a single GPT-5.5 JSON output file")
    parser.add_argument("--dir", help="Folder to scan for *.json subjective-bank output files")
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

    print(f"\n  Ingest GPT-5.5 Subjective Question-Bank Output")
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
            print(f"  [DRY]   {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']} "
                  f"({r['inserted']} questions)")
        else:
            print(f"  [OK]    {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']} "
                  f"({r['inserted']} questions, {r.get('cleared', 0)} old rows cleared)")

    ok = sum(1 for r in results if r["status"] in ("ingested", "dry-run"))
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\nTotal: {len(results)} | OK: {ok} | Error: {err}\n")


if __name__ == "__main__":
    main()
