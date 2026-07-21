"""
Prewarm v2 — native chapter-doc generation
==========================================
Generates chapter documents directly as typed blocks (no markdown, no
conversion) and stores them in lesson_chapter_doc. TOKEN-SPENDING: uses the
prewarm model at ~(2 + milestones) LLM calls per chapter — asks for
confirmation before starting.

Usage:
    cd backend
    # One chapter (e.g. the Grade 9 gap chapter):
    .venv/bin/python scripts/prewarm_chapter_docs_v2.py \
        --grade "Grade 9" --subject "Science" --chapter "Matter in Our Surroundings"

    # All chapters in a grade that have NO stored doc yet:
    .venv/bin/python scripts/prewarm_chapter_docs_v2.py --grade "Grade 9" --missing-only

    # Regenerate natively even where a converted doc exists:
    .venv/bin/python scripts/prewarm_chapter_docs_v2.py --grade "Grade 9" --subject "Science" \
        --chapter "..." --force
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.chapter_doc_prewarm_service import generate_chapter_doc_v2  # noqa: E402
from app.services.chapter_doc_service import (  # noqa: E402
    get_stored_chapter_doc,
    store_chapter_doc,
)
from scripts.convert_chapter_docs import fetch_cached_chapter_combos  # noqa: E402

BOARD = "CBSE"
MODE = "CBSE"
REQUEST_DELAY_SECONDS = 2.0


def build_targets(args) -> list[dict]:
    if args.subject and args.chapter:
        return [{
            "board": BOARD, "grade": args.grade[0], "subject": args.subject,
            "chapter": args.chapter, "mode": MODE,
        }]
    # --missing-only: chapters known to the platform (via lesson_cache combos)
    # that have no stored doc yet.
    combos = fetch_cached_chapter_combos(args.grade)
    targets = []
    for combo in combos:
        if get_stored_chapter_doc(
            combo["board"], combo["grade"], combo["subject"], combo["chapter"], combo["mode"]
        ):
            continue
        targets.append(combo)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate chapter docs natively (prewarm v2)")
    parser.add_argument("--grade", action="append", required=True)
    parser.add_argument("--subject")
    parser.add_argument("--chapter")
    parser.add_argument("--missing-only", action="store_true",
                        help="Generate only chapters with no stored doc")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing stored doc")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    args = parser.parse_args()

    if not (args.subject and args.chapter) and not args.missing_only:
        print("Pass either --subject + --chapter, or --missing-only.")
        sys.exit(1)

    targets = build_targets(args)
    if not targets:
        print("Nothing to generate — all targeted chapters already have docs.")
        return

    print("=" * 62)
    print("Prewarm v2 — native chapter-doc generation (TOKEN-SPENDING)")
    print(f"Chapters to generate: {len(targets)}")
    print(f"Estimated LLM calls:  ~{len(targets) * 7} (outline + blocks + recap/exam)")
    print("=" * 62)
    for t in targets[:10]:
        print(f"  • {t['grade']} · {t['subject']} · {t['chapter'][:55]}")
    if len(targets) > 10:
        print(f"  … and {len(targets) - 10} more")

    if not args.yes:
        confirm = input("\nType 'yes' to start generation: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return

    generated = skipped = failed = 0
    for index, t in enumerate(targets, 1):
        label = f"[{index}/{len(targets)}] {t['grade']} · {t['subject']} · {t['chapter'][:50]}"
        if not args.force and get_stored_chapter_doc(
            t["board"], t["grade"], t["subject"], t["chapter"], t["mode"]
        ):
            print(f"  ⏭  SKIP    {label}")
            skipped += 1
            continue

        print(f"  ⚡ GEN     {label}")
        doc = generate_chapter_doc_v2(
            board=t["board"], grade=t["grade"], subject=t["subject"],
            chapter=t["chapter"], mode=t["mode"],
        )
        if doc is None:
            print(f"  ❌ FAILED  {label} (refused or invalid — see logs)")
            failed += 1
        elif store_chapter_doc(doc):
            exam_note = f", {len(doc.exam)} board Qs" if doc.exam else ""
            print(f"  ✅ STORED  {label} ({len(doc.milestones)} milestones{exam_note})")
            generated += 1
        else:
            print(f"  ⚠️  NOSTORE {label} (generated but DB write failed)")
            failed += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    print("\n" + "=" * 62)
    print(f"Generated: {generated}   Skipped: {skipped}   Failed: {failed}")
    print("=" * 62)


if __name__ == "__main__":
    main()
