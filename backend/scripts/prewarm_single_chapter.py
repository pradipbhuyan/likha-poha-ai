#!/usr/bin/env python3
"""
Single-chapter prewarm test
============================
Prewarms exactly one chapter and verifies all 5 steps are cached and
retrievable BEFORE running the full prewarm.

Usage (from backend/ directory):
    python3 scripts/prewarm_single_chapter.py

Edit the GRADE / SUBJECT / CHAPTER / MODE constants below to match the
chapter you want to test first.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

# ---------------------------------------------------------------------------
# Configure the single chapter to test here
# ---------------------------------------------------------------------------
GRADE   = "Grade 9"
MODE    = "CBSE"
BOARD   = "CBSE"
SUBJECT = "Science"
CHAPTER = "Chapter 8: Journey Inside the Atom"   # exact name from the UI dropdown
# ---------------------------------------------------------------------------

import time
from app.services.lesson_cache_service import make_lesson_cache_key, get_cached_lesson
from app.services.tutor_service import generate_step_lesson
from app.services.openai_service import PREWARM_TEXT_MODEL, force_refresh_settings

# Force the OpenAI client to reload settings from admin_settings DB
# (bypasses the 60-second TTL so the admin-console API key is used immediately)
force_refresh_settings()

LESSON_STEPS = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Practice questions",
    "Revision and recap",
]


def main():
    print(f"\n{'='*60}")
    print(f"Single-chapter prewarm test")
    print(f"  Grade:   {GRADE}")
    print(f"  Mode:    {MODE}")
    print(f"  Subject: {SUBJECT}")
    print(f"  Chapter: {CHAPTER}")
    print(f"{'='*60}\n")

    results = []

    for step in LESSON_STEPS:
        cache_key = make_lesson_cache_key(
            board=BOARD,
            grade=GRADE,
            subject=SUBJECT,
            chapter=CHAPTER,
            mode=MODE,
            step_title=step,
            teacher_persona="",
        )

        # Check if already cached
        existing = get_cached_lesson(cache_key)
        if existing:
            print(f"  ✅ {step} — already cached (skipping LLM call)")
            results.append((step, "already_cached"))
            continue

        # Generate and cache
        print(f"  ⏳ {step} — generating with {PREWARM_TEXT_MODEL} …", flush=True)
        try:
            result = generate_step_lesson(
                grade=GRADE,
                subject=SUBJECT,
                chapter=CHAPTER,
                mode=MODE,
                step_title=step,
                teacher_persona="",
                username="prewarm_test",
                board=BOARD,
                model=PREWARM_TEXT_MODEL,
            )
            lesson_len = len((result or {}).get("lesson", "") or "")
            cached_now = get_cached_lesson(cache_key)
            if cached_now:
                print(f"  ✅ {step} — generated & cached (lesson: {lesson_len} chars)")
                results.append((step, "generated_and_cached"))
            else:
                print(f"  ⚠️  {step} — generated but NOT found in cache!")
                results.append((step, "generated_not_cached"))
            time.sleep(1.5)
        except Exception as exc:
            print(f"  ❌ {step} — FAILED: {exc}")
            results.append((step, f"error: {exc}"))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for _, s in results if "cached" in s)
    print(f"  ✅ Cached:  {ok} / {len(LESSON_STEPS)} steps")
    print(f"  ❌ Failed:  {len(LESSON_STEPS) - ok} / {len(LESSON_STEPS)} steps")

    if ok == len(LESSON_STEPS):
        print(f"\n🎉 All 5 steps for '{CHAPTER}' are cached.")
        print("   Test a lesson request for this chapter in the UI —")
        print("   it should now load INSTANTLY with no LLM call.")
        print("\n   If the test passes, run the full prewarm from the")
        print("   Cache & Question Bank admin panel.")
    else:
        print("\n⚠️  Some steps failed. Check errors above before running")
        print("   the full prewarm.")


if __name__ == "__main__":
    main()
