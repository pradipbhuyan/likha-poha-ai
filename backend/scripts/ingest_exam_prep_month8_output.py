#!/usr/bin/env python3
"""
Ingest Month 8 GPT-5.5 Exam Prep Center Output
=================================================
Paired with scripts/prepare_exam_prep_month8_prompts.py. Identical logic to
ingest_exam_prep_month1_output.py — see that file's docstring for the full
rationale (manifest-trusted exam_type/grade/subject/chapter, topic-field
mapping, and the two-tier near-duplicate check calibrated against Month 1's
real false-positive rate).

Usage:
    cd backend
    ./venv/bin/python scripts/ingest_exam_prep_month8_output.py --dir ~/Downloads/GPT55_ExamPrep_Month8_Prompts --dry-run
    ./venv/bin/python scripts/ingest_exam_prep_month8_output.py --dir ~/Downloads/GPT55_ExamPrep_Month8_Prompts
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

_SCRIPT_ADMIN = {"profile": {"id": "script:ingest_exam_prep_month8_output"}}

REQUIRED_LLM_FIELDS = ["topic", "question_text", "options", "correct_option", "detailed_explanation", "difficulty"]

# See ingest_exam_prep_month1_output.py for the calibration rationale:
# math/formula-heavy questions share templated phrasing even when testing
# different concepts, so only >=REJECT_THRESHOLD is dropped outright; the
# WARN band is imported as draft with a review flag, same as the
# answer-mismatch check.
NEAR_DUPLICATE_WARN_THRESHOLD = 0.55
NEAR_DUPLICATE_REJECT_THRESHOLD = 0.88


def _existing_texts_for_subject(exam_type: str, subject: str) -> list[str]:
    rows = (
        admin_client.table("exam_prep_questions")
        .select("question_text")
        .eq("exam_type", exam_type).eq("subject", subject)
        .neq("status", "archived")
        .execute().data
    )
    return [r["question_text"] for r in rows if r.get("question_text")]


def _tokens(text: str) -> set[str]:
    # Strip only common ASCII punctuation — NOT unicode math notation
    # (∫, subscripts/superscripts, operators). See month1 script for the
    # false-positive this avoids.
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
    if best_score >= NEAR_DUPLICATE_WARN_THRESHOLD:
        return best_match, best_score
    return None


def _normalize_topic(raw_topic: str, topic_to_chapter: dict) -> str | None:
    """
    Recover the intended topic name when the LLM echoed the prompt's display
    format ("Name (Chapter): N question(s)" in the topic-breakdown table)
    instead of the bare name — confirmed live: an entire 355-question batch
    had every question's "topic" field set to "Name (Chapter)" verbatim,
    which would otherwise reject 100% of genuinely valid content. Exact
    match first; falls back to stripping a trailing " (...)" parenthetical.

    That suffix-strip alone isn't enough when the chapter text itself
    contains parentheses — confirmed live: SAT Mathematics's ncert_chapter
    values include a trailing "(~35%)"/"(~15%)" weight hint (e.g. "Algebra
    (Linear equations, inequalities, functions (~35%))"), so the full echoed
    string has nested parens and the single-level trailing-parenthetical
    regex can't strip it (rejected all 24/24 questions before this fix, even
    though every one was genuinely valid). Falls back further to a
    known-topic-name prefix match, which doesn't care how many parens follow.
    """
    if raw_topic in topic_to_chapter:
        return raw_topic
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", raw_topic).strip()
    if stripped in topic_to_chapter:
        return stripped
    for name in topic_to_chapter:
        if raw_topic == name or raw_topic.startswith(name + " ("):
            return name
    return None


def _load_manifest(folder: Path) -> list[dict]:
    manifest_path = folder / "_manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found — run prepare_exam_prep_month8_prompts.py first.")
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


def build_rows(target: dict, llm_questions: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """
    Combine manifest-driven fields (trusted) with LLM-provided content fields.
    Returns (rows_to_import, hard_rejections, review_warnings) — rows in the
    warn band are still included in rows_to_import, just called out for a
    human to sanity-check before publishing.
    """
    rows, rejected, warnings = [], [], []
    topic_to_chapter = target["topic_to_chapter"]

    existing_texts = _existing_texts_for_subject(target["exam_type"], target["subject"])

    for q in llm_questions:
        if not isinstance(q, dict) or any(not q.get(f) for f in REQUIRED_LLM_FIELDS):
            rejected.append(f"missing required field(s): {q.get('question_text', '')[:60]!r}")
            continue
        topic = _normalize_topic(q["topic"], topic_to_chapter)
        if topic is None:
            rejected.append(f"unknown topic {q['topic']!r} (not in {list(topic_to_chapter)}): "
                             f"{q.get('question_text', '')[:60]!r}")
            continue
        near_dup = _find_near_duplicate(q["question_text"], existing_texts)
        if near_dup:
            match_text, score = near_dup
            msg = (f"{score:.0%} similar to existing question {match_text[:60]!r}: "
                   f"{q['question_text'][:60]!r}")
            if score >= NEAR_DUPLICATE_REJECT_THRESHOLD:
                rejected.append(f"near-duplicate (auto-rejected) {msg}")
                continue
            warnings.append(f"near-duplicate (review before publishing) {msg}")
        existing_texts.append(q["question_text"])
        rows.append({
            "exam_type": target["exam_type"],
            "grade": target["topic_to_grade"][topic],
            "subject": target["subject"],
            "chapter": topic_to_chapter[topic],
            "topic": topic,
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
    return rows, rejected, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Month 8 GPT-5.5 exam-prep authoring JSON output")
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

    state_path = folder / "_ingested.json"
    ingested_indices: set[int] = set(json.loads(state_path.read_text())) if state_path.exists() else set()

    totals = {"found": 0, "missing": 0, "imported": 0, "skipped_duplicate": 0, "skipped_invalid": 0}

    for target in manifest:
        json_path = folder / target["expected_json"]
        label = f"[{target['index']:02d}] {target['exam_type']} / {target['subject']}"

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

        rows, rejected, warnings = build_rows(target, llm_questions)
        totals["found"] += 1
        print(f"{label}: {len(rows)}/{len(llm_questions)} question(s) well-formed "
              f"(expected {target['question_count']})")
        for r in rejected:
            print(f"    [reject] {r}")
        for w in warnings:
            print(f"    [warn]   {w}")

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
