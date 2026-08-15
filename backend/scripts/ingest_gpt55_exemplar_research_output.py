#!/usr/bin/env python3
"""
Ingest GPT-5.5 Exemplar Research Explanation Output
====================================================
Takes the JSON output produced by pasting an Exemplar explanation authoring
prompt (see scripts/prepare_gpt55_exemplar_explanation_prompts.py) into a
GPT-5.5 chat session, validates it, renders it to a single markdown document,
and writes
backend/app/data/exemplar_research_bank/<grade_slug>/<subject_slug>/<topic_slug>.json
— overwriting any existing explanation for that topic. Keyed by TOPIC, not
chapter (see exemplar_research_bank_service.py's module docstring for why).

No DB access at all — unlike the sibling lesson-plan/question-bank ingest
scripts, there's no canonical-chapter resolution step here, since topic
strings come directly from TOPIC_CARDS in ExemplarResearchPage.jsx and are
matched exactly (with a filename-substring fallback at lookup time).

Validation:
  1. Schema — manifest{grade,subject,chapter,topic} + the 8 content keys
     the authoring prompt requires, each non-empty and long enough to be
     real content, not a stub.
  2. Refusal detection — GPT-5.5 is instructed to refuse rather than
     invent an explanation when the supplied EXEMPLAR_SOURCE_TEXT doesn't
     match the requested topic (a real, expected outcome — see
     docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §5). Refusals are reported
     and skipped, not ingested; they mean the source PDF <-> chapter-name
     catalogue needs fixing and the prompt needs regenerating, not a
     content bug.
  3. Cross-topic templating detector — same structural-templating check
     used in ingest_gpt55_subjective_question_bank_output.py
     (detect_cross_chapter_templating), adapted to this content's
     concept_overview opener instead of question openers. Catches a fixed
     boilerplate opening sentence reused across topics with only the noun
     swapped, which per-file checks can't see because no single file looks
     wrong in isolation.

Usage:
    cd backend
    python3 scripts/ingest_gpt55_exemplar_research_output.py --input topic.json --dry-run
    python3 scripts/ingest_gpt55_exemplar_research_output.py --input topic.json

    python3 scripts/ingest_gpt55_exemplar_research_output.py --dir ~/Downloads/some_batch --dry-run
    python3 scripts/ingest_gpt55_exemplar_research_output.py --dir ~/Downloads/some_batch
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_plan_bank_service import _slugify  # noqa: E402
from app.services.exemplar_research_bank_service import _BANK_ROOT  # noqa: E402

MANIFEST_KEYS = ["grade", "subject", "chapter", "topic"]
CONTENT_KEYS = [
    "concept_overview",
    "key_rules_formulas",
    "worked_examples",
    "what_makes_exemplar_questions_different",
    "common_mistakes",
    "problem_solving_strategy",
    "quick_recall",
    "practice_problem",
]

MIN_CONCEPT_OVERVIEW_LENGTH = 150
MIN_WORKED_EXAMPLES = 2
MIN_COMMON_MISTAKES = 3
MIN_RULES = 3

# GPT-5.5 is instructed to write exactly this kind of sentence when the
# supplied source text doesn't actually cover the requested topic — see the
# binding rules in prepare_gpt55_exemplar_explanation_prompts.py.
#
# "cannot be (?:produced|generated|written)" originally had no requirement
# of nearby source/supplied context, so it false-positived on ordinary math
# phrasing that has nothing to do with a refusal -- confirmed live on Grade
# 9 Maths "Number Systems": the legitimate irrational-number definition
# "...real numbers that cannot be written as p/q with integers p and q..."
# tripped it even though the rest of the file was well-grounded, on-topic
# content. Narrowed with a lookahead requiring "source"/"supplied"/
# "provided" within the same sentence, so a genuine refusal like "this
# section cannot be written from the supplied source text" still matches.
_REFUSAL_PATTERN = re.compile(
    r"does not (?:cover|match)|"
    r"cannot be (?:produced|generated|written)(?=[^.]{0,60}\b(?:source|supplied|provided)\b)|"
    r"not covered by (?:the|this) (?:supplied|source)|"
    r"source text (?:does not|doesn't) (?:cover|match|correspond)",
    re.IGNORECASE,
)


def _opener(text: str, n_words: int = 6) -> str:
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower())
    return " ".join(cleaned.split()[:n_words])


def detect_cross_topic_templating(paths: list[Path], threshold: float = 0.5) -> dict[str, int]:
    """
    Flag a fixed concept_overview opening sentence reused across >= threshold
    of the batch's files (min 3 usable files) — see module docstring point 3.
    """
    if len(paths) < 3:
        return {}

    opener_counts: dict[str, int] = {}
    usable_files = 0
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw.strip())
            data = json.loads(raw)
            overview = data.get("concept_overview")
        except Exception:
            continue
        if not overview:
            continue
        usable_files += 1
        opener = _opener(overview)
        if len(opener.split()) < 4:
            continue
        opener_counts[opener] = opener_counts.get(opener, 0) + 1

    if usable_files < 3:
        return {}

    min_count = max(3, round(usable_files * threshold))
    return {o: c for o, c in opener_counts.items() if c >= min_count}


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

    manifest = data.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Missing or invalid 'manifest' object")
    missing_manifest = [k for k in MANIFEST_KEYS if not manifest.get(k)]
    if missing_manifest:
        raise ValueError(f"manifest is missing required keys: {missing_manifest}")

    missing_content = [k for k in CONTENT_KEYS if not data.get(k)]
    if missing_content:
        raise ValueError(f"JSON is missing required content keys: {missing_content}")

    overview = str(data["concept_overview"]).strip()
    if _REFUSAL_PATTERN.search(overview):
        raise ValueError(
            "REFUSAL — GPT-5.5 reports the supplied source text doesn't cover this topic. "
            "This means the catalogue<->PDF mapping is still wrong for this chapter, or the "
            "prompt was generated before a catalogue fix. Regenerate the prompt, don't force-ingest. "
            f"(concept_overview: {overview[:200]!r})"
        )
    if len(overview) < MIN_CONCEPT_OVERVIEW_LENGTH:
        raise ValueError(f"concept_overview is too short ({len(overview)} chars, need >= {MIN_CONCEPT_OVERVIEW_LENGTH})")

    rules = data["key_rules_formulas"]
    if not isinstance(rules, list) or len(rules) < MIN_RULES:
        raise ValueError(f"key_rules_formulas needs >= {MIN_RULES} entries, got {len(rules) if isinstance(rules, list) else 'non-list'}")

    examples = data["worked_examples"]
    if not isinstance(examples, list) or len(examples) < MIN_WORKED_EXAMPLES:
        raise ValueError(f"worked_examples needs >= {MIN_WORKED_EXAMPLES} entries, got {len(examples) if isinstance(examples, list) else 'non-list'}")
    for i, ex in enumerate(examples):
        if not isinstance(ex, dict) or not ex.get("problem") or not ex.get("solution"):
            raise ValueError(f"worked_examples[{i}] missing 'problem' or 'solution'")

    mistakes = data["common_mistakes"]
    if not isinstance(mistakes, list) or len(mistakes) < MIN_COMMON_MISTAKES:
        raise ValueError(f"common_mistakes needs >= {MIN_COMMON_MISTAKES} entries, got {len(mistakes) if isinstance(mistakes, list) else 'non-list'}")

    practice = data["practice_problem"]
    if not isinstance(practice, dict) or not practice.get("problem") or not practice.get("answer"):
        raise ValueError("practice_problem missing 'problem' or 'answer'")

    return data


def render_markdown(data: dict) -> str:
    """Flatten the 8 structured content fields into one markdown document —
    matches the single-markdown-field shape lesson_plan_bank uses, so the
    frontend's existing ReactMarkdown renderer needs no changes."""
    parts: list[str] = []

    parts.append("## Concept Overview\n\n" + str(data["concept_overview"]).strip())

    rules_lines = []
    for r in data["key_rules_formulas"]:
        rule = str(r.get("rule", "")).strip()
        explanation = str(r.get("explanation", "")).strip()
        rules_lines.append(f"- **{rule}** — {explanation}" if explanation else f"- **{rule}**")
    parts.append("## Key Rules & Formulas\n\n" + "\n".join(rules_lines))

    example_blocks = []
    for i, ex in enumerate(data["worked_examples"], start=1):
        problem = str(ex.get("problem", "")).strip()
        solution = str(ex.get("solution", "")).strip()
        example_blocks.append(f"**Example {i}:** {problem}\n\n*Solution:* {solution}")
    parts.append("## Worked Examples\n\n" + "\n\n".join(example_blocks))

    parts.append(
        "## What Makes Exemplar Questions on This Topic Harder\n\n"
        + str(data["what_makes_exemplar_questions_different"]).strip()
    )

    mistake_lines = []
    for m in data["common_mistakes"]:
        mistake = str(m.get("mistake", "")).strip()
        why = str(m.get("why_it_happens", "")).strip()
        avoid = str(m.get("how_to_avoid", "")).strip()
        line = f"- **{mistake}**"
        if why:
            line += f" — {why}"
        if avoid:
            line += f" *How to avoid:* {avoid}"
        mistake_lines.append(line)
    parts.append("## Common Mistakes\n\n" + "\n".join(mistake_lines))

    parts.append("## Problem-Solving Strategy\n\n" + str(data["problem_solving_strategy"]).strip())

    parts.append("## Quick Recall\n\n" + str(data["quick_recall"]).strip())

    practice = data["practice_problem"]
    practice_block = "**Problem:** " + str(practice.get("problem", "")).strip()
    if practice.get("hint"):
        practice_block += "\n\n**Hint:** " + str(practice["hint"]).strip()
    practice_block += "\n\n**Answer:** " + str(practice.get("answer", "")).strip()
    parts.append("## Practice Problem\n\n" + practice_block)

    return "\n\n".join(parts) + "\n"


def ingest(data: dict, dry_run: bool) -> dict:
    manifest = data["manifest"]
    grade, subject, chapter, topic = (
        manifest["grade"], manifest["subject"], manifest["chapter"], manifest["topic"],
    )
    markdown = render_markdown(data)

    explanation_path = _BANK_ROOT / _slugify(grade) / _slugify(subject) / f"{_slugify(topic)}.json"

    print(f"  {grade} / {subject} / {topic}  (chapter: {chapter})")
    print(f"    {len(markdown):,} chars of rendered markdown -> {explanation_path}")

    if dry_run:
        print(f"    [DRY RUN] Would write this file"
              f"{' (overwriting existing explanation)' if explanation_path.exists() else ''}.")
        return {"grade": grade, "subject": subject, "topic": topic, "status": "dry-run"}

    explanation_path.parent.mkdir(parents=True, exist_ok=True)
    explanation_path.write_text(
        json.dumps(
            {"grade": grade, "subject": subject, "chapter": chapter, "topic": topic, "explanation_markdown": markdown},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("    Written.")
    return {"grade": grade, "subject": subject, "topic": topic, "status": "ingested"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 Exemplar Research explanation authoring JSON output")
    parser.add_argument("--input", help="Path to a single GPT-5.5 JSON output file")
    parser.add_argument("--dir", help="Folder to scan for *.json Exemplar Research output files")
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

    print("\n  Ingest GPT-5.5 Exemplar Research Explanation Output")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}")
    print(f"  Files to check: {len(paths)}\n")

    templated = detect_cross_topic_templating(paths)
    if templated:
        print("  [WARN] Possible cross-topic templating detected — the same concept_overview")
        print("         opener recurs across multiple files (see module docstring point 3):")
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
