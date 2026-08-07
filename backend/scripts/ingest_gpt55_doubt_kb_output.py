#!/usr/bin/env python3
"""
Ingest GPT-5.5 Doubt Knowledge Base (DKB) Output
=====================================
See docs/GPT55_DOUBT_KB_AUTHORING_PROMPT.md for the full workflow this
script completes (paired with scripts/prepare_gpt55_doubt_kb_prompts.py).

Takes the JSON output produced by pasting a DKB authoring prompt into a
GPT-5.5 chat session, validates it against the expected schema (non-trivial
question/answer text), writes the chapter string using the CURRENT canonical
(rag_documents-format) chapter name, and stores each Q&A pair via
app.services.doubt_kb_service.store_in_doubt_kb with source="gpt55".

Unlike the question-bank ingester, this does NOT clear-and-replace existing
rows -- the doubt_kb table is an accumulating cache (module docstring:
"every LLM-generated answer is stored back ... so the same question never
triggers an LLM call again"). Re-running this script for the same chapter is
safe: any question already present (exact/near-exact text match, case- and
whitespace-insensitive) is skipped rather than duplicated.

Usage:
    cd backend
    # Single file:
    python3 scripts/ingest_gpt55_doubt_kb_output.py --input chapter_dkb.json --dry-run
    python3 scripts/ingest_gpt55_doubt_kb_output.py --input chapter_dkb.json

    # Whole folder (mirrors ingest_gpt55_question_bank_output.py):
    python3 scripts/ingest_gpt55_doubt_kb_output.py --dir ~/Downloads/GPT55_DKB_Prompts_Grade_9_Science --dry-run
    python3 scripts/ingest_gpt55_doubt_kb_output.py --dir ~/Downloads/GPT55_DKB_Prompts_Grade_9_Science
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.doubt_kb_service import store_in_doubt_kb  # noqa: E402

BOARD = "CBSE"
MODE = "CBSE"
SOURCE = "gpt55"
REQUIRED_MANIFEST_KEYS = ["grade", "subject", "chapter"]


def _is_valid_qa_pair(qa: dict) -> tuple[bool, str]:
    if not isinstance(qa, dict):
        return False, "not an object"
    question = qa.get("question")
    answer = qa.get("answer")
    if not question or len(str(question).strip()) < 10:
        return False, "question text missing or too short"
    if not answer or len(str(answer).strip()) < 15:
        return False, "answer text missing or too short"
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

    if "manifest" not in data or "qa_pairs" not in data:
        raise ValueError("Top-level JSON must have both 'manifest' and 'qa_pairs' keys.")

    manifest = data["manifest"]
    qa_pairs = data["qa_pairs"]

    missing_manifest_keys = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing_manifest_keys:
        raise ValueError(f"Manifest is missing required keys: {missing_manifest_keys}")

    if not isinstance(qa_pairs, list) or not qa_pairs:
        raise ValueError("'qa_pairs' must be a non-empty array.")

    valid_pairs = []
    rejected = 0
    for i, qa in enumerate(qa_pairs):
        ok, reason = _is_valid_qa_pair(qa)
        if ok:
            valid_pairs.append(qa)
        else:
            rejected += 1
            print(f"    [reject] pair {i + 1}: {reason}")

    if not valid_pairs:
        raise ValueError("No valid Q&A pairs survived validation.")
    if rejected:
        print(f"    {rejected}/{len(qa_pairs)} pair(s) rejected by validation, "
              f"{len(valid_pairs)} will be considered for ingestion.")

    data["qa_pairs"] = valid_pairs
    return data


def resolve_canonical_chapter(grade: str, subject: str, chapter: str) -> str:
    """
    Resolve the chapter string to write.

    PREFERS an existing doubt_kb chapter string for this grade/subject whose
    normalized core matches (see normalize_chapter_core) -- confirmed live
    that /api/doubt/answer sends a DISPLAY-PREFIXED chapter name for
    multi-book subjects (e.g. "Text Book - Part 1 - 1. Locating Places on
    the Earth", built by routes/syllabus.py's sort_uploaded_chapters), which
    is what earlier DKB prewarm runs stored -- while rag_documents.chapter
    stores the BARE form. Writing new rows under the bare form would make
    them unreachable by search_doubt_kb's exact-chapter Pass 1 for those
    subjects (falling back to the less-precise subject-wide Pass 2 only).
    Reusing whatever convention is already live for this chapter keeps new
    rows matchable the same way the existing ones already are.

    Falls back to matching against rag_documents (old behavior, same
    approach as ingest_gpt55_question_bank_output.py) only when no existing
    doubt_kb rows exist yet for this chapter -- there's no established
    convention to inherit for a chapter that's never been prewarmed before.
    """
    from app.services.mock_test_service import normalize_chapter_core  # noqa: PLC0415

    db = get_content_db(grade)
    target_core = normalize_chapter_core(chapter)

    # ── Preferred: match an existing doubt_kb chapter-string convention ──────
    if target_core:
        try:
            existing = (
                db.table("doubt_kb")
                .select("chapter")
                .eq("grade", grade)
                .eq("subject", subject)
                .eq("status", "active")
                .execute()
            )
            existing_chapters = {row["chapter"] for row in (existing.data or []) if row.get("chapter")}
            matches = {c for c in existing_chapters if normalize_chapter_core(c) == target_core}
            if len(matches) == 1:
                return next(iter(matches))
            if len(matches) > 1:
                print(f"    [warn] Multiple existing doubt_kb chapter variants match "
                      f"{chapter!r} ({sorted(matches)}) — falling back to rag_documents resolution.")
        except Exception as e:
            print(f"    [warn] Could not check existing doubt_kb chapter strings: {e}")

    # ── Fallback: resolve against rag_documents (no existing DKB convention) ─
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

        if target_core:
            candidates = (
                db.table("rag_documents")
                .select("chapter")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", f"%{target_core}%")
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


def _normalize_question(q: str) -> str:
    return re.sub(r"\s+", " ", q or "").strip().rstrip("?").strip().lower()


def _existing_questions(grade: str, subject: str, chapter: str) -> set[str]:
    db = get_content_db(grade)
    try:
        rows = (
            db.table("doubt_kb")
            .select("question")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .eq("status", "active")
            .execute()
        )
        return {_normalize_question(r["question"]) for r in (rows.data or [])}
    except Exception as e:
        print(f"    [warn] Could not fetch existing DKB questions (assuming none): {e}")
        return set()


def ingest(data: dict, dry_run: bool) -> dict:
    manifest = data["manifest"]
    qa_pairs = data["qa_pairs"]
    grade, subject = manifest["grade"], manifest["subject"]
    chapter = resolve_canonical_chapter(grade, subject, manifest["chapter"])

    existing = _existing_questions(grade, subject, chapter)
    new_pairs = [qa for qa in qa_pairs if _normalize_question(qa["question"]) not in existing]
    duplicates = len(qa_pairs) - len(new_pairs)

    print(f"  {grade} / {subject} / {chapter}")
    print(f"    {len(qa_pairs)} valid pair(s) in file, {duplicates} already in DKB, "
          f"{len(new_pairs)} new to insert.")

    if not new_pairs:
        return {"grade": grade, "subject": subject, "chapter": chapter,
                "status": "skipped", "inserted": 0, "duplicates": duplicates,
                "reason": "all questions already in DKB"}

    if dry_run:
        print(f"    [DRY RUN] Would insert {len(new_pairs)} new Q&A pair(s) with source='{SOURCE}'.")
        return {"grade": grade, "subject": subject, "chapter": chapter,
                "status": "dry-run", "inserted": len(new_pairs), "duplicates": duplicates}

    inserted = 0
    errors = 0
    for qa in new_pairs:
        row_id = store_in_doubt_kb(
            question=str(qa["question"]).strip(),
            answer=str(qa["answer"]).strip(),
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=MODE,
            board=BOARD,
            source=SOURCE,
        )
        if row_id:
            inserted += 1
        else:
            errors += 1

    print(f"    Inserted {inserted} new pair(s), {errors} failed.")
    return {"grade": grade, "subject": subject, "chapter": chapter,
            "status": "ingested", "inserted": inserted, "duplicates": duplicates, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 Doubt Knowledge Base authoring JSON output")
    parser.add_argument("--input", help="Path to a single GPT-5.5 JSON output file")
    parser.add_argument("--dir", help="Folder to scan for *.json DKB output files")
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

    print(f"\n  Ingest GPT-5.5 Doubt Knowledge Base Output")
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
        if r["status"] == "skipped":
            print(f"  [SKIP]  {r['file']} — {r.get('grade', '?')}/{r.get('subject', '?')}/{r.get('chapter', '?')} "
                  f"— {r.get('reason', 'skipped')} ({r.get('duplicates', 0)} duplicate(s))")
        elif r["status"] == "error":
            print(f"  [ERROR] {r['file']} — {r['reason']}")
        elif r["status"] == "dry-run":
            print(f"  [DRY]   {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']} "
                  f"({r['inserted']} new, {r['duplicates']} duplicate)")
        else:
            print(f"  [OK]    {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']} "
                  f"({r['inserted']} inserted, {r['duplicates']} duplicate, {r.get('errors', 0)} errors)")

    ok = sum(1 for r in results if r["status"] in ("ingested", "dry-run", "skipped"))
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\nTotal: {len(results)} | OK: {ok} | Errors: {err}\n")


if __name__ == "__main__":
    main()
