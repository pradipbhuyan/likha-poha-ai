#!/usr/bin/env python3
"""
One-off patch: add ```extract-ref``` blocks to the live "How I Taught My
Grandmother to Read" (Grade 9 English) lesson content so the bare
citations "NCERT Critical Reflection I.1(v)" and "NCERT Critical
Reflection I.2(iv)" are no longer dangling references with nothing for
the student to look up.

Background: user feedback (with screenshot) — a Worked example/Quick
check cites a specific NCERT extract sub-question by number, but the
extract text itself is never shown anywhere in the lesson, so the
citation is meaningless to the student. Fix: frontend now supports a
```extract-ref``` fenced JSON block that renders as a clickable citation
pill opening a modal with the actual source text (see
frontend/src/components/ExtractPopupBlock.jsx). This script inserts that
block right after each "Question:" line that cites a Critical Reflection
sub-question, using the actual verbatim extract text read directly from
the source PDF (RAG DB/English/iebe101.pdf).

Usage:
    cd backend
    python3 scripts/patch_extract_refs_g9_english_grandmother.py --force
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.lesson_cache_service import (  # noqa: E402
    make_lesson_cache_key,
    store_lesson_cache,
)

GRADE = "Grade 9"
SUBJECT = "English"
BOARD = "CBSE"
MODE = "CBSE"
CHAPTER = "Chapter 1: How I Taught My Grandmother to Read"

# Verbatim extract text, read directly from RAG DB/English/iebe101.pdf
# (Critical Reflection I, extracts 1 and 2, "How I Taught My Grandmother
# to Read", Kaveri — NCERT Grade 9 English).
EXTRACT_I_1 = (
    "When I came back to my village, I saw my grandmother in tears. "
    "I was surprised, for I had never seen her cry even in the most "
    "difficult situations. What had happened? I was worried.\n\n"
    "'Avva, is everything all right? Are you okay?' I used to call her "
    "Avva, which means mother in the Kannada spoken in north Karnataka.\n\n"
    "She nodded but did not reply. I did not understand and forgot "
    "about it. In the night, after dinner, we were sleeping in the open "
    "terrace of our house. It was a summer night and there was a full "
    "moon. Avva came and sat next to me. Her affectionate hands touched "
    "my forehead.\n\n"
    "(i) Complete the following sentence with the appropriate option. "
    "The phrase 'never seen her cry in the most difficult situations' "
    "tells us that the grandmother was ________. "
    "A. strong-willed  B. understanding  C. considerate  D. bold\n\n"
    "(ii) Complete the following with the correct option from those "
    "given in the brackets. Grandmother did not reply when the narrator "
    "asked if she was alright because she might have been too ________ "
    "(emotional/tired) to respond.\n\n"
    "(iii) Identify the clue from the extract that indicates a rural "
    "setting with traditional customs.\n\n"
    "(iv) Which lines of the extract establish a tender atmosphere?\n\n"
    "(v) Which of the following aspect is NOT emphasised in the given "
    "extract? A. the emotional turmoil of the grandmother  B. the "
    "affectionate bond between the narrator and her grandmother  "
    "C. the grandmother's regret over her lack of education  D. the "
    "narrator's concern for her grandmother"
)

EXTRACT_I_2 = (
    "'I have decided I want to learn the Kannada alphabet from tomorrow "
    "onwards. I will work very hard. I will keep Saraswati Puja day "
    "during Dassara as the deadline. That day I should be able to read "
    "a novel on my own. I want to be independent.'\n\n"
    "I saw the determination on her face. Yet I laughed at her.\n\n"
    "'Avva, at this age of sixty-two you want to learn the alphabet? "
    "All your hair is grey, your hands are wrinkled, you wear "
    "spectacles and you work so much in the kitchen...' Childishly I "
    "made fun of the old lady. But she just smiled.\n\n"
    "'For a good cause if you are determined, you can overcome any "
    "obstacle. I will work harder than anybody but I will do it. For "
    "learning there is no age bar.'\n\n"
    "(iv) List any two qualities displayed by the grandmother in this "
    "extract."
)


def build_extract_ref_block(citation: str, extract_text: str, note: str) -> str:
    import json
    payload = {"citation": citation, "extract_text": extract_text, "note": note}
    return "```extract-ref\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def patch_content(content: str) -> tuple[str, int]:
    """Insert an extract-ref block right after each matching Question: line
    that doesn't already have one immediately following it. Returns the
    patched content and the number of insertions made."""
    insertions = 0

    def make_replacer(citation_pattern: str, extract_text: str, note: str):
        def _replace(m: re.Match) -> str:
            nonlocal insertions
            full_line = m.group(0)
            # Skip if an extract-ref block already immediately follows
            tail = content[m.end():m.end() + 20]
            if "```extract-ref" in tail:
                return full_line
            citation = re.search(citation_pattern, full_line, re.IGNORECASE).group(0)
            block = build_extract_ref_block(citation, extract_text, note)
            insertions += 1
            return f"{full_line}\n\n{block}"
        return _replace

    # Worked example: "Question: Based on NCERT Critical Reflection I.1(v), ..."
    content = re.sub(
        r"^Question:.*Critical Reflection I\.1\([a-z]+\).*$",
        make_replacer(
            r"NCERT Critical Reflection I\.1\([a-z]+\)",
            EXTRACT_I_1,
            "How I Taught My Grandmother to Read — Critical Reflection I, extract 1 (the narrator finds Avva in tears).",
        ),
        content,
        flags=re.MULTILINE,
    )

    # Quick check question: "Question: Based on NCERT Critical Reflection I.2(iv), ..."
    content = re.sub(
        r"^Question:.*Critical Reflection I\.2\([a-z]+\).*$",
        make_replacer(
            r"NCERT Critical Reflection I\.2\([a-z]+\)",
            EXTRACT_I_2,
            "How I Taught My Grandmother to Read — Critical Reflection I, extract 2 (Avva's decision to learn the alphabet).",
        ),
        content,
        flags=re.MULTILINE,
    )

    return content, insertions


def run(dry_run: bool = True) -> None:
    rows = (
        admin_client.table("lesson_cache")
        .select("step_title, lesson_content, practice_questions, teacher_persona")
        .eq("grade", GRADE)
        .eq("subject", SUBJECT)
        .eq("chapter", CHAPTER)
        .execute()
        .data
    )

    if not rows:
        print(f"No lesson_cache rows found for chapter '{CHAPTER}'.")
        return

    total_insertions = 0
    for row in rows:
        step_title = row["step_title"]
        content = row["lesson_content"]
        patched, n = patch_content(content)
        if n == 0:
            print(f"  [skip] '{step_title}' — no matching citations found or already patched")
            continue

        total_insertions += n
        print(f"  [{'dry-run' if dry_run else 'patch'}] '{step_title}' — {n} extract-ref block(s) inserted")

        if dry_run:
            continue

        persona = row.get("teacher_persona") or ""
        new_key = make_lesson_cache_key(
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=CHAPTER,
            mode=MODE, step_title=step_title, teacher_persona=persona,
        )
        store_lesson_cache(
            cache_key=new_key,
            lesson_content=patched,
            source_type="MANUAL",
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=CHAPTER,
            mode=MODE, step_title=step_title, teacher_persona=persona,
            practice_questions=row.get("practice_questions") or [],
        )

    if not dry_run and total_insertions > 0:
        admin_client.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
            "subject", SUBJECT
        ).eq("chapter", CHAPTER).eq("mode", MODE).execute()
        print(f"  [cache] invalidated lesson_chapter_doc for '{CHAPTER}'")

    print(f"\nTotal extract-ref blocks {'would be' if dry_run else ''} inserted: {total_insertions}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.force)


if __name__ == "__main__":
    main()
