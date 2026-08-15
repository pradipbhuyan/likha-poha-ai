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

# Defense-in-depth against the exact failure class this ingest script has
# hit live: GPT-5.5 (or a live-LLM fallback elsewhere) treating internal
# lesson-authoring markdown scaffolding as if it were real chapter content
# -- e.g. "Explain the chapter point about Faithfulness and connect it with
# another idea from the exam-style activities", where "Faithfulness" is a
# bolded sub-label lifted from a lesson_cache bullet and "exam-style
# activities" is a lesson-step SECTION NAME, not a real fact from the
# chapter/story/poem. These templated, meaningless-to-a-student questions
# must never reach subjective_question_bank even if a batch otherwise
# passes the basic length/marks/difficulty checks above.
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

# Second defense-in-depth pattern: catches a DIFFERENT but equally low-quality
# failure mode -- glossary-style, mechanically-templated questions generated
# from a term/definition table rather than genuine exam-style comprehension
# questions. Confirmed live in a "Grades 6-9 Maths/English" batch where most
# questions followed rigid templates such as "What does X mean, and how is
# it used in this topic?" or "Explain how X, Y, and Z are connected. Give a
# complete rule-based explanation." with generic filler like "These stated
# ideas should be applied together according to their definitions and
# conditions." These are not FALSE (the underlying facts are grounded), but
# they test rote glossary recall instead of comprehension, and are boring/
# repetitive compared to genuine CBSE exam-style phrasing.
_GLOSSARY_TEMPLATE_PATTERN = re.compile(
    r"what does .+ mean, and how is it used in this topic\?"
    r"|explain how .+ are connected\. give a complete rule-based explanation"
    r"|explain .+ and state the rule or meaning attached to it",
    re.IGNORECASE,
)
_GENERIC_FILLER_ANSWER_PATTERN = re.compile(
    r"these stated ideas should be applied together according to their "
    r"definitions and conditions"
    r"|the conclusion is obtained by applying those stated steps in order"
    r"|this follows directly from the stated definition or rule"
    r"|the same relationship must be kept when the rule is applied",
    re.IGNORECASE,
)

# Third defense-in-depth pattern: a different reusable-skeleton failure mode,
# confirmed live in a Grade 12 Biology batch where ~97% of questions across
# all 13 chapters were built from one of these same few sentence scaffolds
# with only the topic noun swapped in (e.g. "Explain pollen-pistil
# interaction and state its key features, mechanism or significance." /
# "Explain cyanobacteria and state its key features, mechanism or
# significance."). The underlying facts were accurate and grounded (this
# isn't a hallucination pattern like the first two), but rote reuse of the
# same skeleton is glossary recall, not genuine CBSE exam variety.
#
# "explain the major points relating to" was added after a second, separate
# incident: a Grade 12 Business Studies batch where exactly 5 of every 20
# questions in all 11 chapters used this exact scaffold (e.g. "Explain the
# major points relating to coordination." / "Explain the major points
# relating to directing and its principles.") — confirming this isn't a
# one-off phrasing but a recurring default GPT-5.5 falls back to whenever a
# prompt doesn't explicitly forbid it. Each new confirmed skeleton gets
# added here rather than assuming the prompt-level rule alone is sufficient.
#
# The literary-analysis group below was added after a Grade 12 English
# (prose/poetry) batch where 58% of 380 questions across all 19 chapters
# used one of these four scaffolds with just the story/poem's topic noun
# swapped in (e.g. "What role does the treatment of Bare feet play in the
# development of the scene?" reused verbatim in chapter after chapter with
# only the bolded topic changed) — the same failure shape as the STEM-
# subject skeletons above, just in literary-analysis phrasing, confirming
# this recurs across subject types and isn't specific to factual/technical
# content. Three more variants of the SAME batch ("What does the chapter
# reveal through the treatment of X?" / "How does the treatment of X
# contribute to the text's meaning?" / "What becomes clearer to the reader
# through the treatment of X?") were found on a second read of the same
# batch after the first four patterns still let ~30% of the batch's
# remaining questions through — a reminder to scan for ALL recurring
# openers found during triage, not just the first few noticed.
#
# The last five patterns were added after a Grade 12 Geography batch (33%
# of 340 questions across 17 chapters) using "Give a brief account of X
# [using two specific details from the text|including the relevant
# definition, pattern or example]." and "What is the significance of X in
# [Chapter]? Support your answer with two facts." and "State two features,
# examples or implications associated with X." and "What does the text
# state about X? Give two relevant details." — matched on each phrase's
# distinctive TAIL rather than its opener, since generic openers like
# "Give a brief account of" are legitimate CBSE phrasing on their own and
# only the fixed, reused tail marks these as templated.
_SENTENCE_SKELETON_PATTERN = re.compile(
    r"and state its (?:key features|important features)"
    r"|in detail, showing the (?:biological )?relationship between them"
    r"|distinguish the linked ideas where relevant"
    r"|including the mechanism, evidence, examples or consequences stated in the chapter"
    r"|explain the major points relating to"
    r"|play in the development of the scene"
    r"|significant in this episode"
    r"|what larger idea emerges when they are read together"
    r"|why is that relationship important to the meaning of"
    r"|reveal through the treatment of"
    r"|contribute to the text.?s meaning"
    r"|becomes clearer to the reader through the treatment of"
    r"|support your answer with two facts"
    r"|features, examples or implications associated with"
    r"|give two relevant details"
    r"|using two specific details from the text"
    r"|including the relevant definition, pattern or example",
    re.IGNORECASE,
)


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
    question_text = str(q.get("question", ""))
    if _TEMPLATE_PHRASE_PATTERN.search(question_text):
        return False, (
            "question uses a templated meta-structure phrase (e.g. 'chapter "
            "point about ... connect it with another idea') instead of a "
            "real chapter fact — reject and re-author"
        )
    if _SECTION_LABEL_PATTERN.search(question_text):
        return False, (
            "question references an internal lesson-authoring section "
            "label (e.g. 'Section B', 'Opening overview', 'Revision and "
            "recap') instead of real chapter content — reject and re-author"
        )
    if _GLOSSARY_TEMPLATE_PATTERN.search(question_text):
        return False, (
            "question uses a mechanically-templated glossary phrasing (e.g. "
            "'What does X mean, and how is it used in this topic?' or "
            "'Explain how X, Y, and Z are connected. Give a complete "
            "rule-based explanation.') instead of genuine exam-style "
            "phrasing — reject and re-author"
        )
    if _SENTENCE_SKELETON_PATTERN.search(question_text):
        return False, (
            "question reuses a fixed sentence skeleton with only the topic "
            "swapped in (e.g. 'Explain X and state its key features, "
            "mechanism or significance.' or 'Explain X and Y in detail, "
            "showing the relationship between them.') instead of varied "
            "CBSE exam-style phrasing — reject and re-author"
        )
    model_answer_text = str(q.get("model_answer", ""))
    if _GENERIC_FILLER_ANSWER_PATTERN.search(model_answer_text):
        return False, (
            "model_answer uses generic template filler (e.g. 'These stated "
            "ideas should be applied together according to their "
            "definitions and conditions') instead of a real, specific "
            "explanation — reject and re-author"
        )
    return True, ""


def _question_opener(question_text: str, n_words: int = 4) -> str:
    """First few words of a question, normalized for cross-chapter comparison."""
    cleaned = re.sub(r"[^\w\s]", "", question_text.lower())
    return " ".join(cleaned.split()[:n_words])


def detect_cross_chapter_templating(paths: list[Path], threshold: float = 0.5) -> dict[str, int]:
    """
    Detect a fixed roster of question-openers reused once per chapter across
    a whole batch — a structural templating pattern that per-question regex
    checks can't catch because each individual question looks fine (varied
    topic, no banned phrase) but the SET of questions in every chapter
    follows the same rigid slot structure.

    Confirmed live in a Grade 12 Biology re-authoring attempt: no single
    phrase repeated within a chapter (so _SENTENCE_SKELETON_PATTERN saw
    nothing), but openers like "state two important points", "give the
    main defining", "identify the main mechanism" each appeared in exactly
    13 of 13 chapters — the whole 20-question paper was a fixed template
    with only the topic noun changed per slot, not content-driven variety.

    Returns {opener: file_count} for any opener present in at least
    `threshold` fraction of the batch's files (and at least 3 files, so a
    tiny batch of 1-2 chapters never trips this). Only counts an opener
    once per file (a chapter naturally reusing an opener internally isn't
    the same signal as it recurring across chapters).
    """
    if len(paths) < 3:
        return {}

    opener_file_counts: dict[str, int] = {}
    usable_files = 0
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw.strip())
            data = json.loads(raw)
            questions = data.get("questions") or []
        except Exception:
            continue  # unreadable/malformed files are handled by the normal per-file path
        if not questions:
            continue
        usable_files += 1
        openers_in_this_file = {
            _question_opener(str(q.get("question", "")))
            for q in questions
            if isinstance(q, dict) and q.get("question")
        }
        for opener in openers_in_this_file:
            if len(opener.split()) < 3:
                continue  # too short to be a meaningful structural signal
            opener_file_counts[opener] = opener_file_counts.get(opener, 0) + 1

    if usable_files < 3:
        return {}

    min_count = max(3, round(usable_files * threshold))
    return {
        opener: count
        for opener, count in opener_file_counts.items()
        if count >= min_count
    }


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
    parser.add_argument(
        "--force", action="store_true",
        help="Skip the cross-chapter templating check (only use after manually "
             "confirming a flagged batch's repeated openers are a false positive)",
    )
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

    if not args.force:
        flagged = detect_cross_chapter_templating(paths)
        if flagged:
            print(f"\n  ERROR: cross-chapter templating detected across {len(paths)} files.\n")
            print("  These question openers each appear in most/all chapters — a fixed "
                  "question-slot template reused with only the topic swapped in, not "
                  "genuine per-chapter content variety:\n")
            for opener, count in sorted(flagged.items(), key=lambda kv: -kv[1]):
                print(f"    [{count}/{len(paths)} files]  {opener!r}...")
            print("\n  Nothing was written. Re-author this batch with more genuine "
                  "question-stem variety, or re-run with --force if you've manually "
                  "confirmed this is a false positive (e.g. a small, genuinely "
                  "repetitive topic like a single grammar rule).\n")
            sys.exit(1)

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
