#!/usr/bin/env python3
"""
Ingest GPT-5.5 Exam Prep Center Output
========================================
Paired with scripts/prepare_exam_prep_gpt55_prompts.py.

Reads the JSON question arrays produced by pasting each *_PROMPT.txt into a
GPT-5.5 chat session and saving the response as <slug>_questions.json in the
same folder as _manifest.json (written by the prepare script).

exam_type/grade/subject/chapter/topic are taken ONLY from the manifest (i.e.
from which prompt file the output came from) — never trusted from the LLM's
own output — so this can't reintroduce the subject-name mismatch bug that
originally hid 60 CUET questions from students. Each batch is imported via
the platform's own admin_import_bulk() validated path (schema checks, dedup,
and the subject/EXAM_SUBJECTS_MAP mapping-integrity check), so ingestion here
is held to exactly the same bar as the in-app admin paste-import workflow.

Everything lands as status=draft (admin_import_bulk's own behavior) — a
separate publish pass is required before any of it is visible to students.

Usage:
    cd backend
    ./venv/bin/python scripts/ingest_exam_prep_gpt55_output.py --dir ~/Downloads/GPT55_ExamPrep_Prompts --dry-run
    ./venv/bin/python scripts/ingest_exam_prep_gpt55_output.py --dir ~/Downloads/GPT55_ExamPrep_Prompts
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes.exam_prep import admin_import_bulk, BulkImportRequest  # noqa: E402
from app.services.auth_service import admin_client  # noqa: E402

_SCRIPT_ADMIN = {"profile": {"id": "script:ingest_exam_prep_gpt55_output"}}

# admin_import_bulk's own dedup only catches EXACT question_text matches
# (MD5 fingerprint). This catches near-duplicates/close paraphrases — most
# commonly the same word-problem template with different numbers — that
# slip past a prompt instruction alone. Lightweight heuristic, not semantic
# dedup: see prepare_exam_prep_month1_prompts.py for the stronger primary
# defense (embedding the existing bank in the prompt itself).
NEAR_DUPLICATE_THRESHOLD = 0.55


def _existing_texts_for(exam_type: str, subject: str) -> list[str]:
    rows = (
        admin_client.table("exam_prep_questions")
        .select("question_text")
        .eq("exam_type", exam_type).eq("subject", subject)
        .neq("status", "archived")
        .execute().data
    )
    return [r["question_text"] for r in rows if r.get("question_text")]


def _tokens(text: str) -> set[str]:
    # Strip only common ASCII punctuation — deliberately does NOT strip
    # unicode math notation (see ingest_exam_prep_month1_output.py for the
    # false-positive case this fixes: stripping all non-[a-z0-9] characters
    # collapsed two different calculus questions down to the same leftover
    # connector words and scored them as 100% identical).
    text = re.sub(r"[,.:;!?()]", " ", text.lower())
    return {w for w in text.split() if len(w) > 1}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    char_ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return max(jaccard, char_ratio)


def _find_near_duplicate(text: str, candidates: list[str]) -> tuple[str, float] | None:
    best_match, best_score = None, 0.0
    for c in candidates:
        score = _similarity(text, c)
        if score > best_score:
            best_match, best_score = c, score
    if best_score >= NEAR_DUPLICATE_THRESHOLD:
        return best_match, best_score
    return None

REQUIRED_LLM_FIELDS = ["question_text", "options", "correct_option", "detailed_explanation", "difficulty"]


def _load_manifest(folder: Path) -> list[dict]:
    manifest_path = folder / "_manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found — run prepare_exam_prep_gpt55_prompts.py first.")
        sys.exit(1)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _parse_questions_file(path: Path) -> list[dict] | None:
    raw = path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    [error] {path.name}: not valid JSON ({e})")
        return None
    if not isinstance(data, list) or not data:
        print(f"    [error] {path.name}: expected a non-empty JSON array")
        return None
    return data


def build_rows(target: dict, llm_questions: list[dict]) -> tuple[list[dict], list[str]]:
    """Combine manifest-driven fields (trusted) with LLM-provided content fields."""
    rows, rejected = [], []
    existing_texts = _existing_texts_for(target["exam_type"], target["subject"])
    for q in llm_questions:
        if not isinstance(q, dict) or any(not q.get(f) for f in REQUIRED_LLM_FIELDS):
            continue
        near_dup = _find_near_duplicate(q["question_text"], existing_texts)
        if near_dup:
            match_text, score = near_dup
            rejected.append(
                f"near-duplicate ({score:.0%} similar to existing question {match_text[:60]!r}): "
                f"{q['question_text'][:60]!r}"
            )
            continue
        existing_texts.append(q["question_text"])
        rows.append({
            "exam_type": target["exam_type"],
            "grade": target["grade"],
            "subject": target["subject"],
            "chapter": target["chapter"],
            "topic": q.get("subtopic") or target["topic"],
            "subtopic": q.get("subtopic", ""),
            "question_text": q["question_text"],
            "options": q["options"],
            "correct_option": q["correct_option"],
            "detailed_explanation": q["detailed_explanation"],
            "difficulty": q["difficulty"],
            "formula_used": q.get("formula_used", ""),
            "ncert_reference": q.get("ncert_reference", ""),
            "source_type": "llm_generated",
        })
    return rows, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 exam-prep authoring JSON output")
    parser.add_argument("--dir", required=True, help="Folder containing _manifest.json and *_questions.json files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true",
                         help="Re-import targets already recorded as ingested in _ingested.json")
    args = parser.parse_args()

    folder = Path(args.dir).expanduser()
    if not folder.is_dir():
        print(f"ERROR: not a directory: {folder}")
        sys.exit(1)

    manifest = _load_manifest(folder)
    print(f"{len(manifest)} target(s) in manifest.\n")

    # Local idempotency guard — this script's own record of what it already
    # successfully imported, independent of the DB-side dedup check (which
    # is a second layer of defense, not the only one; a re-run over an
    # already-ingested folder must not require the DB check to work
    # perfectly to stay safe).
    state_path = folder / "_ingested.json"
    ingested_indices: set[int] = set(json.loads(state_path.read_text())) if state_path.exists() else set()

    totals = {"found": 0, "missing": 0, "imported": 0, "skipped_duplicate": 0, "skipped_invalid": 0}

    for target in manifest:
        json_path = folder / target["expected_json"]
        label = f"[{target['index']:02d}] {target['exam_type']} / {target['subject']} / {target['chapter']}"

        if target["index"] in ingested_indices and not args.force:
            print(f"{label}: ALREADY INGESTED (recorded in _ingested.json — use --force to re-import)")
            continue

        if not json_path.exists():
            print(f"{label}: MISSING ({json_path.name} not found yet — skipping)")
            totals["missing"] += 1
            continue

        llm_questions = _parse_questions_file(json_path)
        if llm_questions is None:
            totals["missing"] += 1
            continue

        rows, rejected = build_rows(target, llm_questions)
        totals["found"] += 1
        print(f"{label}: {len(rows)}/{len(llm_questions)} question(s) well-formed "
              f"(expected {target['question_count']})")
        for r in rejected:
            print(f"    [reject] {r}")

        if args.dry_run:
            print(f"    [DRY RUN] Would import {len(rows)} question(s) via admin_import_bulk().")
            continue

        result = admin_import_bulk(BulkImportRequest(questions=rows), _admin=_SCRIPT_ADMIN)
        print(f"    imported={result['imported']}  "
              f"skipped_duplicate={result['skipped_duplicate']}  "
              f"skipped_invalid={result['skipped_invalid']}")
        for item in result["report"]:
            if item["status"] != "imported":
                print(f"      [{item['status']}] {item['question_text']!r}: {item['issues'] or item['warnings']}")
        totals["imported"] += result["imported"]
        totals["skipped_duplicate"] += result["skipped_duplicate"]
        totals["skipped_invalid"] += result["skipped_invalid"]

        ingested_indices.add(target["index"])
        state_path.write_text(json.dumps(sorted(ingested_indices), indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Targets with output found: {totals['found']}/{len(manifest)}  "
          f"(missing: {totals['missing']})")
    if not args.dry_run:
        print(f"Imported: {totals['imported']}  "
              f"Skipped duplicate: {totals['skipped_duplicate']}  "
              f"Skipped invalid: {totals['skipped_invalid']}")
        print("\nAll imported rows are status=draft. Review then publish via the "
              "admin question-bank UI or POST /api/admin/exam-prep/questions/{id}/publish.")


if __name__ == "__main__":
    main()
