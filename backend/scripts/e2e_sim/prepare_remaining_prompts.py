#!/usr/bin/env python3
"""Prepare GPT-5.5 question-bank prompts for every chapter still failing right
now (re-derived live from results.jsonl, not the stale Phase-3 candidate
list), all into ONE consolidated output folder with globally unique numbering."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))

from prepare_gpt55_question_prompts import (  # noqa: E402
    PROMPT_TEMPLATE, get_chapter_lesson_text, _slugify,
)

OUT_DIR = Path.home() / "Downloads" / "GPT55_Question_Prompts_REMAINING"
QUESTIONS_PER_CHAPTER = 30

REMAINING = [
    ("Grade 12", "Sociology", "Chapter 3: Social Institutions: Continuity and Change"),
    ("Grade 12", "Sociology", "Chapter 4: The Market as a Social Institution"),
    ("Grade 12", "Sociology", "Chapter 5: Patterns of Social Inequality and Exclusion"),
    ("Grade 12", "Sociology", "Chapter 6: The Challenges of Cultural Diversity"),
    ("Grade 11", "Accountancy", "Chapter 9: Financial Statements – II"),
    ("Grade 11", "Chemistry", "Chapter 8: Organic Chemistry – Some Basic Principles and Techniques"),
    ("Grade 11", "Geography", "Chapter 10: Climate"),
    ("Grade 11", "Hindi", "Chapter 4: Namak Ka Daroga"),
    ("Grade 12", "English", "Chapter 17: The Enemy"),
    ("Grade 12", "English", "Chapter 18: On the Face of It"),
    ("Grade 12", "Geography", "Chapter 10: Human Settlements"),
    ("Grade 12", "Geography", "Chapter 15: Transport and Communication in India"),
    ("Grade 12", "Geography", "Chapter 9: Population: Distribution, Density, Growth and Composition"),
    ("Grade 12", "History", "Chapter 5: Through the Eyes of Travellers: Perceptions of Society"),
    ("Grade 12", "Political Science", "Chapter 2: Contemporary Centres of Power"),
    ("Grade 7", "English", "Unit 4: Travel and Adventure"),
    ("Grade 9", "Science", "Matter in Our Surroundings"),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_easy = QUESTIONS_PER_CHAPTER // 3
    n_medium = QUESTIONS_PER_CHAPTER // 3
    n_hard = QUESTIONS_PER_CHAPTER - n_easy - n_medium

    index_lines = [
        "GPT-5.5 Question-Bank Authoring — all remaining chapters (consolidated)",
        "=" * 78,
        "",
        "For each chapter below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <chapter_slug>_question_bank.json in this folder.",
        "  4. Once done, ingest them all in one command:",
        "",
        "     cd backend",
        f"     ./venv/bin/python scripts/ingest_gpt55_question_bank_output.py --dir {OUT_DIR} --dry-run",
        f"     ./venv/bin/python scripts/ingest_gpt55_question_bank_output.py --dir {OUT_DIR}",
        "",
        "NOTE: a few of these chapters already have some bank content (either wrong",
        "topic or too few medium-difficulty questions) — ingestion clears existing",
        "rows for that exact chapter before inserting the fresh set, so this fully",
        "replaces the bad content rather than adding to it.",
        "",
        "Chapters:",
    ]

    written = 0
    skipped = []
    for i, (grade, subject, chapter) in enumerate(REMAINING, start=1):
        lesson_text = get_chapter_lesson_text(grade, subject, chapter)
        if len(lesson_text.strip()) < 200:
            print(f"[{i:02d}] {grade} / {subject} / {chapter} -- [skip] lesson content too short/missing")
            skipped.append((grade, subject, chapter))
            continue

        grade_number = grade.split()[-1]
        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade, grade_number=grade_number, subject=subject, chapter=chapter,
            chapter_lesson_text=lesson_text,
            n_easy=n_easy, n_medium=n_medium, n_hard=n_hard, total=QUESTIONS_PER_CHAPTER,
        )

        slug = _slugify(f"{grade}_{subject}_{chapter}")
        prompt_path = OUT_DIR / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        written += 1
        print(f"[{i:02d}] {grade} / {subject} / {chapter} -> {prompt_path.name} "
              f"({len(prompt_text):,} chars, grounded in {len(lesson_text):,} chars)")

        index_lines.append(f"  [{i:02d}] {grade} / {subject} / {chapter}")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {slug}_question_bank.json")

    (OUT_DIR / "00_README_and_index.txt").write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written}/{len(REMAINING)} prompts written to {OUT_DIR}")
    if skipped:
        print(f"Skipped ({len(skipped)}, no/insufficient lesson_cache content):")
        for g, s, c in skipped:
            print(f"  - {g} / {s} / {c}")


if __name__ == "__main__":
    main()
