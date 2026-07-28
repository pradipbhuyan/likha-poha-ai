#!/usr/bin/env python3
"""
Migrate GPT-5.5-authored (MANUAL) Grade 9 Hindi lesson_cache content from
its bare chapter-name key to the "अध्याय N: <title>" key the live app
actually reads — same fix as
scripts/migrate_g9_english_manual_to_prefixed_key.py, see
docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4q for background.

The "अध्याय N:" prefixed keys were extracted via OCR/RAG from the source
PDF and contain real typos (e.g. "क््या लिखू", "आलखरी चट्टान तक",
"ऐसी भी बातीें होती हैं") — these exact strings (with typos) are what is
actually stored in lesson_cache.chapter for the OLD rows and therefore
must be matched exactly, not "corrected", so the live app's existing
lookup continues to work.

Usage:
    cd backend
    python3 scripts/migrate_g9_hindi_manual_to_prefixed_key.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.lesson_cache_service import store_lesson_cache  # noqa: E402

GRADE = "Grade 9"
SUBJECT = "Hindi"
BOARD = "CBSE"
MODE = "CBSE"

# bare GPT-5.5 title -> exact (including any OCR typos) "अध्याय N: <title>"
# key actually stored in lesson_cache from the older RAG-generated content.
CHAPTER_MAP = {
    "दो बैलों की कथा": "अध्याय 1: दो बैलों की कथा",
    "क्या लिखूँ?": "अध्याय 2:  क््या लिखू",
    "संवादहीन": "अध्याय 3: संवादहीन",
    "ऐसी भी बातें होती हैं (लता मंगेशकर से साक्षात्कार)": "अध्याय 4: ऐसी भी बातीें होती हैं",
    "आखिरी चट्टान तक": "अध्याय 5: आलखरी चट्टान तक",
    "रीढ़ की हड्डी": "अध्याय 6: रीढ़ की हड्डी",
}


def migrate(dry_run: bool = True) -> None:
    for bare_title, prefixed_title in CHAPTER_MAP.items():
        print(f"\n=== {bare_title}  ->  {prefixed_title} ===")

        rows = (
            admin_client.table("lesson_cache")
            .select("step_title, lesson_content, practice_questions, teacher_persona")
            .eq("grade", GRADE)
            .eq("subject", SUBJECT)
            .eq("chapter", bare_title)
            .execute()
            .data
        )

        if not rows:
            print("  [skip] no MANUAL rows found under bare title")
            continue

        for row in rows:
            step_title = row["step_title"]
            content = row["lesson_content"]
            practice_qs = row.get("practice_questions") or []
            persona = row.get("teacher_persona") or ""

            if dry_run:
                print(f"  [dry-run] would migrate step '{step_title}' "
                      f"({len(content)} chars) to key '{prefixed_title}'")
                continue

            from app.services.lesson_cache_service import make_lesson_cache_key

            new_key = make_lesson_cache_key(
                board=BOARD,
                grade=GRADE,
                subject=SUBJECT,
                chapter=prefixed_title,
                mode=MODE,
                step_title=step_title,
                teacher_persona=persona,
            )

            store_lesson_cache(
                cache_key=new_key,
                lesson_content=content,
                source_type="MANUAL",
                board=BOARD,
                grade=GRADE,
                subject=SUBJECT,
                chapter=prefixed_title,
                mode=MODE,
                step_title=step_title,
                teacher_persona=persona,
                practice_questions=practice_qs,
            )
            print(f"  [migrated] step '{step_title}' -> key '{prefixed_title}'")

        if dry_run:
            continue

        admin_client.table("lesson_cache").delete().eq("grade", GRADE).eq(
            "subject", SUBJECT
        ).eq("chapter", bare_title).execute()
        print(f"  [cleanup] deleted bare-title rows for '{bare_title}'")

        admin_client.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
            "subject", SUBJECT
        ).eq("chapter", prefixed_title).eq("mode", MODE).execute()
        print(f"  [cache] invalidated lesson_chapter_doc for '{prefixed_title}'")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    migrate(dry_run=not args.force)


if __name__ == "__main__":
    main()
