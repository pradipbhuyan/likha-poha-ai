"""
cleanup_stale_lesson_cache.py
─────────────────────────────────────────────────────────────────────────────
One-time cleanup: find duplicate active rows per (grade, subject, chapter,
step_title) and keep ONLY the highest-quality row (most ## section headings
+ longest content). Mark all other active rows as status='stale'.

Validation logic (per step):
  1. Count ## headings (primary quality signal — 8-section structure)
  2. Count words (secondary signal — richer content is longer)
  3. Keep the row with highest (heading_count, word_count)
  4. Mark all others status='stale'

Also marks ANY row with 0 ## headings as status='stale' even if it has no
duplicate (old flat-text content that was never updated).

Usage:
  cd backend
  python scripts/cleanup_stale_lesson_cache.py          # dry run
  python scripts/cleanup_stale_lesson_cache.py --apply  # actually mark stale
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import os
import re

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

from app.services.grade_db_router import get_content_db

APPLY = "--apply" in sys.argv
DRY_RUN = not APPLY

# ⚠️  PRODUCTION SAFETY NOTICE ⚠️
# Running this script with --apply marks lesson_cache rows as status='stale'.
# This WILL break the live student lesson page because get_cached_lesson()
# filters to status='active' rows only. Students will get cache misses
# and trigger fresh LLM generation for affected chapters.
#
# ONLY run --apply during off-peak hours with explicit approval.
# The Lesson Lab uses in-memory quality selection and does NOT require
# this script to be run.
#
# To restore all stale rows: UPDATE lesson_cache SET status='active'
# WHERE status='stale' AND grade IN ('Grade 5', ..., 'Grade 10');
if APPLY:
    print("\n" + "="*60)
    print("⚠️  WARNING: --apply mode will mark rows as status='stale'")
    print("   This affects the live student lesson cache.")
    print("   Students will get cache misses for affected chapters.")
    print("   Press Ctrl+C to cancel, or wait 5 seconds to proceed.")
    print("="*60 + "\n")
    import time
    time.sleep(5)

GRADES = ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]
MIN_HEADINGS_TO_KEEP = 1  # rows with 0 headings are always marked stale


def content_quality(content: str) -> tuple:
    """Returns (heading_count, word_count) — higher = better."""
    heading_count = len(re.findall(r"^#{1,3}\s+", content or "", re.M))
    word_count = len((content or "").split())
    return (heading_count, word_count)


def run():
    total_checked = 0
    total_to_stale = 0
    total_marked = 0
    all_to_stale: dict[str, list] = {}  # grade → list of row IDs

    for grade in GRADES:
        print(f"\n{'='*60}")
        print(f"Grade: {grade}")
        print(f"{'='*60}")
        try:
            db = get_content_db(grade)
            resp = (db.table("lesson_cache")
                    .select("id, grade, subject, chapter, step_title, lesson_content, status, access_count, created_at")
                    .eq("grade", grade)
                    .eq("status", "active")
                    .limit(3000)
                    .execute())
            rows = resp.data or []
        except Exception as e:
            print(f"  ERROR fetching {grade}: {e}")
            continue

        print(f"  Total active rows: {len(rows)}")
        total_checked += len(rows)

        # Group by (subject, chapter, step_title)
        groups: dict[str, list] = {}
        for row in rows:
            key = f"{row.get('subject')}|{row.get('chapter')}|{row.get('step_title')}"
            groups.setdefault(key, []).append(row)

        grade_to_stale = []

        for key, candidates in groups.items():
            # Score all candidates
            scored = [(content_quality(r.get("lesson_content", "")), r) for r in candidates]
            scored.sort(key=lambda x: x[0], reverse=True)  # best first

            best_quality, best_row = scored[0]
            best_headings = best_quality[0]

            for quality, row in scored:
                heading_count = quality[0]

                should_stale = False
                reason = ""

                if heading_count == 0 and len(candidates) > 1:
                    # Only mark stale if there IS a better alternative for the SAME
                    # (grade, subject, chapter, step_title) group.
                    # Never mark the ONLY row stale — that would leave the step with no content.
                    should_stale = row["id"] != best_row["id"] or best_headings > 0
                    if should_stale:
                        reason = "0 ## headings (flat/old content) — better alternative exists"
                elif heading_count == 0 and len(candidates) == 1:
                    # Single row with 0 headings — mark stale only if we have a better row
                    # in a differently-named chapter for the same logical chapter
                    # (e.g. "Coordinate Geometry" vs "Chapter 7: Coordinate Geometry").
                    # Conservative: DON'T mark stale if it's the only row — keep it active.
                    should_stale = False
                elif len(candidates) > 1 and row["id"] != best_row["id"]:
                    should_stale = True
                    reason = f"duplicate: worse quality ({heading_count} headings, {quality[1]} words) vs best ({best_headings} headings, {scored[0][0][1]} words)"

                if should_stale:
                    grade_to_stale.append(row["id"])
                    subject = row.get("subject", "")[:20]
                    chapter = row.get("chapter", "")[:30]
                    step = row.get("step_title", "")[:25]
                    access = row.get("access_count", 0)
                    words = quality[1]
                    print(f"  → STALE: {subject} | {chapter} | {step}")
                    print(f"           reason: {reason} | access_count={access} | words={words}")

        all_to_stale[grade] = grade_to_stale
        print(f"  Rows to mark stale: {len(grade_to_stale)} / {len(rows)}")
        total_to_stale += len(grade_to_stale)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total rows checked:      {total_checked}")
    print(f"Rows to mark stale:      {total_to_stale}")
    print(f"Mode:                    {'DRY RUN' if DRY_RUN else 'APPLY'}")

    if DRY_RUN:
        print("\nDRY RUN — no changes made.")
        print("Run with --apply to actually mark rows as stale.")
        return

    print("\nApplying changes...")
    for grade, ids in all_to_stale.items():
        if not ids:
            continue
        try:
            db = get_content_db(grade)
            # Batch in chunks of 100 to avoid URL length limits
            for i in range(0, len(ids), 100):
                chunk = ids[i:i+100]
                db.table("lesson_cache").update({"status": "stale"}).in_("id", chunk).execute()
                total_marked += len(chunk)
            print(f"  {grade}: marked {len(ids)} rows as stale ✓")
        except Exception as e:
            print(f"  {grade}: ERROR marking stale — {e}")

    print(f"\nDone. {total_marked} rows marked as status='stale'.")
    print("Good-quality structured content remains active.")
    print("Run Lesson Lab to verify the correct content appears.")


if __name__ == "__main__":
    run()
