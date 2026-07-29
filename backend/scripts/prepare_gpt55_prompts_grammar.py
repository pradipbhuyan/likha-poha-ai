#!/usr/bin/env python3
"""
Prepare GPT-5.5 Chapter-Authoring Prompts for Grade 9 & 10 English Grammar
=============================================================================
See docs/GPT55_CHAPTER_AUTHORING_PROMPT.md for the base literature-chapter
workflow. This variant is GRAMMAR-SPECIFIC: CBSE Grammar has no single
source PDF (unlike literature chapters), so this script uses hand-written
reference text (see grammar_reference_data.py) as the grounding source
instead of extracted PDF text, and uses a grammar-tailored prompt template
that asks for rule explanations, transformation-style worked examples, and
editing/error-correction style practice -- NOT literary analysis.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 9"
    python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 10"
    python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 9" --topic "Grammar: Tenses"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.grammar_reference_data import (  # noqa: E402
    GRADE_9_TOPICS, GRADE_10_TOPICS, REFERENCE_TEXT,
)

SUBJECT_NAME = "English"

TOPIC_LISTS = {
    "Grade 9": GRADE_9_TOPICS,
    "Grade 10": GRADE_10_TOPICS,
}

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE English grammar teacher and textbook author. You are
writing ONE grammar topic for a Grade {grade_number} CBSE English AI
tutoring platform. You must act like a strict, rule-accurate grammar
teacher who never invents a grammar rule, never gives an incorrect
example sentence, and never contradicts standard English grammar as
taught in the CBSE curriculum.

This is a GRAMMAR topic, not a literature chapter. There is no
storyline, no author, and no literary analysis. Every explanation must
be a grammar RULE with its FORM (structure) and USAGE, illustrated with
simple, clear, grammatically correct example sentences.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every rule, form, and example sentence you write MUST be
   consistent with the GRAMMAR_REFERENCE_TEXT provided below. You may
   phrase explanations in your own words and provide ADDITIONAL correct
   example sentences beyond those given, but you must NEVER state a
   rule that contradicts or is not grounded in GRAMMAR_REFERENCE_TEXT.
2. NO INCORRECT EXAMPLES: Every single example sentence you write --
   in explanations, worked examples, and quick-check questions -- must
   itself be grammatically correct English (unless it is explicitly
   being shown as an INCORRECT example for the purpose of contrast,
   in which case it must be clearly labelled "Incorrect:").
3. TOPIC BOUNDARY: Only cover the grammar topic given below. Do not
   drift into an unrelated grammar topic (e.g. do not teach Reported
   Speech inside a Tenses topic) unless GRAMMAR_REFERENCE_TEXT itself
   connects the two directly.
4. WORKED EXAMPLES MUST BE TRANSFORMATION-STYLE, MATCHING REAL CBSE
   EXAM PATTERNS: e.g. "Fill in the blank with the correct form of the
   verb", "Rewrite the sentence in reported speech", "Change the voice
   of the sentence", "Identify and correct the error", "Combine the
   sentences using a suitable clause" -- NOT abstract essay-style
   questions. Every worked example and quick-check question must show
   a REAL sentence being transformed/corrected/completed, with the
   full correct answer.
5. NO PLACEHOLDER OR VAGUE TEXT: Every "Quick check question" must have
   a complete, correct, specific Answer and Explanation that names the
   exact grammar rule applied.
6. LANGUAGE LEVEL: Write for Grade {grade_number} level -- simple, clear,
   age-appropriate English, but grammatically precise and exam-accurate.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER (grammar topic): {topic}
SUBJECT_CLASS: grammar_topic

GRAMMAR_REFERENCE_TEXT:
\"\"\"
{reference_text}
\"\"\"

Your task has two parts. Return ONLY a single valid JSON object (no
markdown fences, no commentary before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{topic}",
    "central_question": "<one sentence: what grammar rule/skill does this topic teach a student to use correctly?>",
    "in_scope_units": [
      "<one string per sub-rule/form actually present in GRAMMAR_REFERENCE_TEXT, in the order they appear>"
    ],
    "banned_topics": [
      "<any DIFFERENT grammar topic that might mistakenly get mixed in here -- empty array if none>"
    ],
    "must_include_keywords": [
      "<10-25 specific grammar terms/forms that MUST appear somewhere across the 5 lesson steps combined, e.g. 'past perfect', 'subject-verb agreement', 'modal verb'>"
    ],
    "known_pitfalls": [
      {{
        "claim": "<a specific, plausible grammar mistake a student commonly makes on this topic>",
        "correction": "<the precise correct rule, grounded in GRAMMAR_REFERENCE_TEXT>"
      }}
    ],
    "recommended_example_progression": [
      "<a short ordered list of worked-example ideas, each describing the transformation/correction task it will use, e.g. 'Fill in the blank with correct tense of the given verb'>"
    ],
    "ncert_end_of_chapter_exercises_reference": "<one sentence describing the typical CBSE exercise format for this grammar topic (e.g. fill-in-the-blanks, sentence transformation, error correction)>"
  }},
  "lessons": {{
    "Concept introduction": "<full markdown lesson content, see FORMAT below>",
    "Core explanation": "<full markdown lesson content, see FORMAT below>",
    "Worked examples": "<full markdown lesson content, see FORMAT below>",
    "Exam-style problems": "<full markdown lesson content, see FORMAT below>",
    "Revision and recap": "<full markdown lesson content, see FORMAT below>"
  }}
}}

FORMAT for each value inside "lessons" (a single markdown string, using
exactly these 7 headings in this order):

# <Step Title>: {topic}

## What you will learn
<2-4 sentences describing the grammar rule/skill covered in this step>

## Simple explanation
<a short, plain-language paragraph introducing the core rule(s) for this step>

## Step-by-step breakdown
- **<sub-rule/form>**: <explanation with structure, grounded in GRAMMAR_REFERENCE_TEXT>
- **<sub-rule/form>**: <explanation with structure, grounded in GRAMMAR_REFERENCE_TEXT>
  (as many bullet points as needed to cover this step's share of the topic)

## Worked example
Question: <a real transformation/fill-in/correction task, e.g. "Fill in
the blank with the correct form of the verb in brackets: 'She ___
(finish) her homework before dinner.'">

Solution:
- Step 1: <identify which rule applies>
- Step 2: <apply the rule>
- Final answer: <the complete correct sentence>

## Common mistake
<one specific, plausible grammar error on this exact sub-topic and its correction>

## Quick check question
Question: <a specific transformation/fill-in/correction task>
Answer: <the complete, correct answer>
Explanation: <name the exact grammar rule that makes this the correct answer>

## Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>
(3-6 bullets recapping this step's key rules)

IMPORTANT: split the topic's content across the 5 steps so that,
combined, they cover ALL of GRAMMAR_REFERENCE_TEXT roughly proportionally
-- do NOT let one sub-rule dominate more than 1-2 of the 5 steps while
other sub-rules from GRAMMAR_REFERENCE_TEXT get no coverage. Every single
worked example and quick-check question across all 5 steps MUST be a
genuine grammar transformation/correction/fill-in task with a fully
correct answer -- never an essay-style or opinion-style question.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def run(grade: str, output_dir: Path, only_topic: str | None) -> None:
    if grade not in TOPIC_LISTS:
        print(f"ERROR: unknown grade {grade!r}. Use 'Grade 9' or 'Grade 10'.")
        sys.exit(1)

    grade_number = grade.split()[-1]
    topics = TOPIC_LISTS[grade]
    if only_topic:
        topics = [t for t in topics if t == only_topic]
        if not topics:
            print(f"ERROR: topic {only_topic!r} not found for {grade}.")
            sys.exit(1)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 Grammar prompts for {grade} / {SUBJECT_NAME}")
    print(f"  Output folder: {output_dir}")
    print(f"  Topics to process: {len(topics)}\n")

    for i, topic in enumerate(topics, start=1):
        reference_text = REFERENCE_TEXT.get(topic, "").strip()
        if not reference_text:
            print(f"  [{i:02d}] {topic} -- [error] no reference text found, skipping")
            continue

        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade,
            grade_number=grade_number,
            subject=SUBJECT_NAME,
            topic=topic,
            reference_text=reference_text,
        )

        slug = _slugify(topic)
        out_path = output_dir / f"{i:02d}_{slug}_PROMPT.txt"
        out_path.write_text(prompt_text, encoding="utf-8")
        print(f"  [{i:02d}] {topic}")
        print(f"       -> wrote {out_path.name} ({len(prompt_text):,} chars)")

    print(f"\nDone. Prompt(s) prepared in:\n  {output_dir}")
    print("Paste each *_PROMPT.txt text into a GPT-5.5 chat session, save the JSON")
    print("response, then ingest it with scripts/ingest_gpt55_chapter_output.py")
    print("exactly as with the standard chapter-authoring workflow.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 prompts for Grade 9/10 English Grammar topics"
    )
    parser.add_argument("--grade", required=True, choices=["Grade 9", "Grade 10"])
    parser.add_argument("--topic", default=None, help="Only generate the prompt for this exact topic name")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        output_dir = Path.home() / "Downloads" / f"GPT55_Grammar_Prompts_{grade_slug}"

    run(grade=args.grade, output_dir=output_dir, only_topic=args.topic)


if __name__ == "__main__":
    main()
