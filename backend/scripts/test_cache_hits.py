#!/usr/bin/env python3
"""
Cache Hit Verification
======================
Reads every row from lesson_cache, reconstructs the lookup key,
and verifies that get_cached_lesson() finds each one.

Run from the backend/ directory:
    python3 scripts/test_cache_hits.py

A row is a MISS if the key stored in the DB does not match
the key computed by make_lesson_cache_key() from its metadata.
This means that live lesson requests will call the LLM instead
of serving the cached content.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Inject the macOS system truststore so Supabase SSL works outside the FastAPI app
from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

from app.services.lesson_cache_service import make_lesson_cache_key, get_cached_lesson
from app.services.supabase_client import supabase


def main():
    print("Fetching all lesson_cache rows …")

    response = (
        supabase
        .table("lesson_cache")
        .select("cache_key, board, grade, subject, chapter, mode, step_title, teacher_persona, status")
        .eq("status", "active")
        .execute()
    )

    rows = response.data or []
    print(f"Found {len(rows)} active cached lessons.\n")

    hits = 0
    misses = []

    for row in rows:
        stored_key = row["cache_key"]

        computed_key = make_lesson_cache_key(
            board=row["board"],
            grade=row["grade"],
            subject=row["subject"],
            chapter=row["chapter"],
            mode=row["mode"],
            step_title=row["step_title"],
            teacher_persona=row.get("teacher_persona") or "",
        )

        if stored_key == computed_key:
            # Key matches — verify the DB lookup actually returns data
            result = get_cached_lesson(computed_key)
            if result:
                hits += 1
            else:
                misses.append({
                    "reason": "get_cached_lesson returned None (DB error?)",
                    "row": row,
                    "computed_key": computed_key,
                })
        else:
            misses.append({
                "reason": "Key mismatch: stored != computed",
                "stored_key":   stored_key[:16] + "…",
                "computed_key": computed_key[:16] + "…",
                "row": row,
            })

    print(f"✅ HITS  : {hits}")
    print(f"❌ MISSES: {len(misses)}")

    if misses:
        print("\n--- MISSES DETAIL ---")
        for i, miss in enumerate(misses[:20], 1):
            row = miss["row"]
            print(
                f"\n[{i}] {miss['reason']}"
                f"\n    grade={row['grade']}  mode={row['mode']}"
                f"\n    subject={row['subject']}"
                f"\n    chapter={row['chapter']}"
                f"\n    step_title={row['step_title']}"
                f"\n    teacher_persona='{row.get('teacher_persona', '')}'"
            )
            if "stored_key" in miss:
                print(f"    stored   key: {miss['stored_key']}")
                print(f"    computed key: {miss['computed_key']}")
        if len(misses) > 20:
            print(f"\n… and {len(misses) - 20} more misses.")
    else:
        print("\n🎉 All cached lessons are correctly indexed.")
        print("   Every lesson request for pre-warmed content will be served")
        print("   from cache without calling the LLM or the embedding API.")


if __name__ == "__main__":
    main()
