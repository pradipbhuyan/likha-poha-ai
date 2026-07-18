"""
Lesson Pre-Warming Script
=========================
Generates all Grade 9 lesson steps and stores them in lesson_cache.

Run this ONCE when your OpenAI API key is ready and the lesson_cache table
has been created in Supabase (backend/sql/add_lesson_cache.sql).

Uses gpt-4.1-nano (PREWARM_TEXT_MODEL) — 75% cheaper than gpt-4.1-mini.
Estimated cost: ~$0.44 for all 750 Grade 9 lesson steps (was ~$1.77 with mini).
Estimated time: ~25 minutes (rate limited to ~0.5 req/sec).

Usage:
    cd backend
    python3 scripts/prewarm_lessons.py

After completion, all Grade 9 lesson requests will be served from cache
at zero token cost until RAG content changes for a chapter.
"""

import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.syllabus import CBSE_9
from app.services.tutor_service import generate_step_lesson
from app.services.lesson_cache_service import get_cached_lesson, make_lesson_cache_key
from app.services.openai_service import PREWARM_TEXT_MODEL
from app.services.prewarm_service import has_rag_content_for_chapter

# The 5 fixed lesson steps used by the frontend for every chapter
LESSON_STEPS = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Practice questions",
    "Revision and recap",
]

GRADE = "Grade 9"
BOARD = "CBSE"
TEACHER_PERSONA = ""  # Standard persona — blank means CBSE default

# Rate limit: pause between requests to avoid OpenAI rate limit errors
REQUEST_DELAY_SECONDS = 2.0


def count_total_steps():
    """Count total lesson steps to generate for progress display."""
    total = 0
    for subject, chapters in CBSE_9.items():
        total += len(chapters) * len(LESSON_STEPS)
    return total


def prewarm_cbse():
    """Generate and cache RAG-backed CBSE Grade 9 lesson steps using gpt-4.1-nano."""
    total_generated = 0
    total_skipped = 0
    total_no_rag = 0

    for subject, chapters in CBSE_9.items():
        mode = BOARD

        for chapter in chapters:
            # Skip chapters with no uploaded RAG content
            if not has_rag_content_for_chapter(BOARD, GRADE, subject, chapter):
                print(f"  ⛔ NO RAG {subject} → {chapter[:40]} — skipping all steps")
                total_no_rag += 5
                continue

            for step_title in LESSON_STEPS:
                cache_key = make_lesson_cache_key(
                    board=BOARD,
                    grade=GRADE,
                    subject=subject,
                    chapter=chapter,
                    mode=mode,
                    step_title=step_title,
                    teacher_persona=TEACHER_PERSONA,
                )

                if get_cached_lesson(cache_key):
                    print(f"  ⏭  SKIP  {subject} → {chapter[:40]} → {step_title}")
                    total_skipped += 1
                    continue

                print(f"  ⚡ GEN   {subject} → {chapter[:40]} → {step_title}")

                try:
                    generate_step_lesson(
                        grade=GRADE,
                        subject=subject,
                        chapter=chapter,
                        mode=mode,
                        step_title=step_title,
                        teacher_persona=TEACHER_PERSONA,
                        username="prewarm_admin",
                        board=BOARD,
                        model=PREWARM_TEXT_MODEL,
                    )
                    total_generated += 1
                    time.sleep(REQUEST_DELAY_SECONDS)

                except Exception as e:
                    print(f"  ❌ ERROR {subject} → {chapter[:40]} → {step_title}: {e}")
                    time.sleep(REQUEST_DELAY_SECONDS * 2)

    return total_generated, total_skipped, total_no_rag


if __name__ == "__main__":
    total_steps = count_total_steps()

    print("=" * 60)
    print("LikhaPoha AI — Lesson Pre-Warming Script")
    print("=" * 60)
    print(f"Grade: {GRADE}")
    print(f"Model: {PREWARM_TEXT_MODEL} (gpt-4.1-nano, 75% cheaper than mini)")
    print(f"Chapters in syllabus: {total_steps} steps total")
    print(f"  Only chapters with RAG content will be generated.")
    print(f"  Chapters without RAG uploads will be skipped.")
    print(f"Estimated cost: ~$0.44 max (fewer if not all chapters have RAG)")
    print(f"Estimated time: ~{total_steps * REQUEST_DELAY_SECONDS / 60:.0f} minutes max")
    print()
    print("Note: Already-cached steps will be skipped automatically.")
    print("Run this script again to resume after an interruption.")
    print()

    confirm = input("Type 'yes' to start pre-generation: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    print()
    print("--- Generating CBSE lessons (RAG-backed chapters only) ---")
    cbse_gen, cbse_skip, cbse_no_rag = prewarm_cbse()

    print()
    print("=" * 60)
    print("Pre-warming complete!")
    print(f"Generated:            {cbse_gen} lessons")
    print(f"Skipped (cached):     {cbse_skip}")
    print(f"Skipped (no RAG):     {cbse_no_rag} steps (upload textbooks to enable)")
    print()
    print("All generated lessons will be served from cache at zero token cost.")
    print("=" * 60)
