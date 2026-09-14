#!/usr/bin/env python3
"""
Ingest GPT-5.5 Exemplar Research Practice-Question Output
====================================================
Takes the JSON output produced by pasting a practice-question authoring
prompt (see scripts/prepare_gpt55_exemplar_practice_prompts.py) into a
GPT-5.5 chat session, validates it, and writes
backend/app/data/exemplar_practice_bank/<grade_slug>/<subject_slug>/<topic_slug>.json
— overwriting any existing practice set for that topic. Keyed by TOPIC, same
reasoning as exemplar_research_bank_service.py's explanation bank.

Validation:
  1. Schema — manifest{grade,subject,chapter,topic} + questions[] with
     exactly 4 entries, each with q/options(4)/answer/explanation, answer
     matching one of options verbatim, explanation long enough to be real
     step-by-step working.
  2. Refusal detection — the prompt allows GPT-5.5 to return a top-level
     "refusal" string instead of questions when the supplied source text
     doesn't cover the topic (same reasoning as the sibling explanation
     ingest script — a catalogue/PDF mismatch, not a content bug).
  3. Cross-topic templating detector — flags a fixed opening sentence on
     question 1 reused across many files in one batch, same technique as
     ingest_gpt55_exemplar_research_output.py's concept_overview check.

Usage:
    cd backend
    python3 scripts/ingest_gpt55_exemplar_practice_output.py --input topic.json --dry-run
    python3 scripts/ingest_gpt55_exemplar_practice_output.py --input topic.json

    python3 scripts/ingest_gpt55_exemplar_practice_output.py --dir ~/Downloads/some_batch --dry-run
    python3 scripts/ingest_gpt55_exemplar_practice_output.py --dir ~/Downloads/some_batch
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_plan_bank_service import _slugify  # noqa: E402
from app.services.exemplar_research_bank_service import _PRACTICE_BANK_ROOT  # noqa: E402

MANIFEST_KEYS = ["grade", "subject", "chapter", "topic"]
REQUIRED_QUESTIONS = 4
MIN_EXPLANATION_LENGTH = 80

_REFUSAL_PATTERN = re.compile(
    r"does not (?:cover|match)(?=[^.]{0,60}\b(?:source|supplied|provided|topic)\b)|"
    r"cannot be (?:produced|generated|written)(?=[^.]{0,60}\b(?:source|supplied|provided)\b)|"
    r"not covered by (?:the|this) (?:supplied|source)|"
    r"source text (?:does not|doesn't) (?:cover|match|correspond)",
    re.IGNORECASE,
)


def _opener(text: str, n_words: int = 6) -> str:
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower())
    return " ".join(cleaned.split()[:n_words])


def detect_cross_topic_templating(paths: list[Path], threshold: float = 0.5) -> dict[str, int]:
    """Flag a fixed question-1 opening reused across >= threshold of the batch's files."""
    if len(paths) < 3:
        return {}

    opener_counts: dict[str, int] = {}
    usable_files = 0
    for path in paths:
        try:
            data = _load_json(path)
            questions = data.get("questions")
            q1 = questions[0].get("q") if isinstance(questions, list) and questions else None
        except Exception:
            continue
        if not q1:
            continue
        usable_files += 1
        opener = _opener(q1)
        if len(opener.split()) < 4:
            continue
        opener_counts[opener] = opener_counts.get(opener, 0) + 1

    if usable_files < 3:
        return {}

    min_count = max(3, round(usable_files * threshold))
    return {o: c for o, c in opener_counts.items() if c >= min_count}


def _load_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    return json.loads(raw)


def load_and_validate(input_path: Path) -> dict:
    """Load the GPT-5.5 JSON output and validate its schema. Raises ValueError on failure."""
    try:
        data = _load_json(input_path)
    except json.JSONDecodeError as e:
        raise ValueError(f"Input is not valid JSON: {e}")

    manifest = data.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Missing or invalid 'manifest' object")
    missing_manifest = [k for k in MANIFEST_KEYS if not manifest.get(k)]
    if missing_manifest:
        raise ValueError(f"manifest is missing required keys: {missing_manifest}")

    if "refusal" in data and data["refusal"]:
        raise ValueError(
            "REFUSAL — GPT-5.5 reports the supplied source text doesn't cover this topic. "
            "This means the catalogue<->PDF mapping is wrong for this chapter, or the prompt "
            "was generated before a catalogue fix. Regenerate the prompt, don't force-ingest. "
            f"(refusal: {str(data['refusal'])[:200]!r})"
        )

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != REQUIRED_QUESTIONS:
        raise ValueError(
            f"'questions' must be a list of exactly {REQUIRED_QUESTIONS} entries, "
            f"got {len(questions) if isinstance(questions, list) else 'non-list'}"
        )

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"questions[{i}] is not an object")
        text = str(q.get("q") or "").strip()
        if not text:
            raise ValueError(f"questions[{i}] missing 'q'")
        options = q.get("options")
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"questions[{i}] 'options' must have exactly 4 entries, got {len(options) if isinstance(options, list) else 'non-list'}")
        if any(not str(o).strip() for o in options):
            raise ValueError(f"questions[{i}] has an empty option")
        answer = str(q.get("answer") or "").strip()
        if not answer:
            raise ValueError(f"questions[{i}] missing 'answer'")
        if answer not in [str(o).strip() for o in options]:
            raise ValueError(f"questions[{i}] 'answer' does not match any entry in 'options' verbatim: {answer!r}")
        explanation = str(q.get("explanation") or "").strip()
        if len(explanation) < MIN_EXPLANATION_LENGTH:
            raise ValueError(f"questions[{i}] 'explanation' is too short ({len(explanation)} chars, need >= {MIN_EXPLANATION_LENGTH})")
        if _REFUSAL_PATTERN.search(text) or _REFUSAL_PATTERN.search(explanation):
            raise ValueError(f"questions[{i}] looks like a refusal, not a real question: {text[:200]!r}")

    return data


def ingest(data: dict, dry_run: bool) -> dict:
    manifest = data["manifest"]
    grade, subject, chapter, topic = (
        manifest["grade"], manifest["subject"], manifest["chapter"], manifest["topic"],
    )
    questions = data["questions"]

    practice_path = _PRACTICE_BANK_ROOT / _slugify(grade) / _slugify(subject) / f"{_slugify(topic)}.json"

    print(f"  {grade} / {subject} / {topic}  (chapter: {chapter})")
    print(f"    {len(questions)} question(s) -> {practice_path}")

    if dry_run:
        print(f"    [DRY RUN] Would write this file"
              f"{' (overwriting existing practice set)' if practice_path.exists() else ''}.")
        return {"grade": grade, "subject": subject, "topic": topic, "status": "dry-run"}

    practice_path.parent.mkdir(parents=True, exist_ok=True)
    practice_path.write_text(
        json.dumps(
            {"grade": grade, "subject": subject, "chapter": chapter, "topic": topic, "questions": questions},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("    Written.")
    return {"grade": grade, "subject": subject, "topic": topic, "status": "ingested"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 Exemplar Research practice-question authoring JSON output")
    parser.add_argument("--input", help="Path to a single GPT-5.5 JSON output file")
    parser.add_argument("--dir", help="Folder to scan for *.json practice-question output files")
    parser.add_argument("--files", nargs="+", help="Explicit list of JSON files to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true", help="Ingest anyway even if cross-topic templating is detected")
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

    print("\n  Ingest GPT-5.5 Exemplar Research Practice-Question Output")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}")
    print(f"  Files to check: {len(paths)}\n")

    templated = detect_cross_topic_templating(paths)
    if templated:
        print("  [WARN] Possible cross-topic templating detected — the same question-1 opener")
        print("         recurs across multiple files (see module docstring point 3):")
        for opener, count in sorted(templated.items(), key=lambda kv: -kv[1]):
            print(f"           {count}x  {opener!r}...")
        if not args.force:
            print("\n  Refusing to ingest. Re-author with more varied openings, or pass --force")
            print("  if you've confirmed by reading the files this is a false positive.\n")
            sys.exit(1)
        print("  --force passed, continuing anyway.\n")

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
            print(f"  [DRY]   {r['file']} — {r['grade']}/{r['subject']}/{r['topic']}")
        else:
            print(f"  [OK]    {r['file']} — {r['grade']}/{r['subject']}/{r['topic']}")

    ok = sum(1 for r in results if r["status"] in ("ingested", "dry-run"))
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\nTotal: {len(results)} | OK: {ok} | Error: {err}\n")


if __name__ == "__main__":
    main()
