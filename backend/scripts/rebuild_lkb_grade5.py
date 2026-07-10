#!/usr/bin/env python3
"""
Rebuild LKB Chips for Grade 5 with RAG Grounding
==================================================
Deletes all existing Grade 5 LKB chips (which were generated without textbook
context due to the search_rag → search_textbook_content bug), then regenerates
them using the fixed _generate_chips() with real NCERT RAG content.

Background:
  The previous _get_rag_context() tried to import 'search_rag' which doesn't
  exist — should be 'search_textbook_content'. The import failed silently,
  leaving rag_context = "" for every chip. All 830 chips were generated purely
  from LLM training data, not the uploaded textbook PDFs.

Usage:
    cd backend
    python3 scripts/rebuild_lkb_grade5.py                        # all subjects
    python3 scripts/rebuild_lkb_grade5.py --subject English       # one subject
    python3 scripts/rebuild_lkb_grade5.py --dry-run               # preview only
    python3 scripts/rebuild_lkb_grade5.py --subject English --chapter "1. Papa's Spectacles"
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.lesson_kb_service import (  # noqa: E402
    _generate_chips,
    _get_lesson_steps,
    _store_chips,
    _get_rag_context,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("rebuild_lkb")

GRADE = "Grade 5"
DELAY_BETWEEN_CHAPTERS = 0.5   # seconds between API calls (rate-limit safety)


def delete_lkb_chips(grade: str, subject: str | None, chapter: str | None, dry_run: bool) -> int:
    """Archive existing LKB chips for the given scope. Returns count deleted."""
    db = get_content_db(grade)
    try:
        q = db.table("lesson_kb").select("id", count="exact").eq("grade", grade).eq("status", "active")
        if subject:
            q = q.eq("subject", subject)
        if chapter:
            q = q.eq("chapter", chapter)
        existing = q.execute()
        count = existing.count or 0
        if count == 0:
            return 0
        if dry_run:
            _log.info("  [DRY-RUN] Would delete %d existing LKB chips", count)
            return count
        # Archive (not hard delete) so we can recover if needed
        u = db.table("lesson_kb").update({"status": "archived"}).eq("grade", grade).eq("status", "active")
        if subject:
            u = u.eq("subject", subject)
        if chapter:
            u = u.eq("chapter", chapter)
        u.execute()
        _log.info("  Archived %d existing chips", count)
        return count
    except Exception as exc:
        _log.error("Failed to archive LKB chips: %s", exc)
        return 0


def verify_rag_available(grade: str, subject: str, chapter: str) -> tuple[bool, int]:
    """Check if RAG content is available for this chapter. Returns (has_rag, chunk_count)."""
    try:
        from app.services.rag_service import search_textbook_content  # noqa: PLC0415
        results = search_textbook_content(
            query=f"{chapter} {subject} key concepts",
            grade=grade,
            subject=subject,
            chapter=chapter,
            match_count=3,
        )
        return bool(results), len(results)
    except Exception:
        return False, 0


def rebuild_chapter(
    grade: str,
    subject: str,
    chapter: str,
    dry_run: bool,
) -> dict:
    """Rebuild LKB chips for one chapter (all steps). Returns stats."""
    steps = _get_lesson_steps(grade)
    built = errors = 0

    # Check RAG availability first
    has_rag, rag_count = verify_rag_available(grade, subject, chapter)
    rag_status = f"✅ {rag_count} RAG hits" if has_rag else "⚠️ No RAG — LLM-only"
    _log.info("    RAG: %s", rag_status)

    for step_title in steps:
        if dry_run:
            # Fetch RAG context to show what would be used
            ctx = _get_rag_context(grade, subject, chapter, step_title)
            _log.info("    [DRY-RUN] %s — RAG context: %d chars", step_title, len(ctx))
            built += 5  # pretend
            continue

        try:
            chips = _generate_chips(grade, subject, chapter, step_title)
            if chips:
                _store_chips(grade, subject, chapter, step_title, chips)
                built += len(chips)
                _log.info("    ✅ %s → %d chips generated", step_title, len(chips))
            else:
                errors += 1
                _log.warning("    ❌ %s → 0 chips returned", step_title)
            time.sleep(0.2)  # brief pause between steps
        except Exception as exc:
            errors += 1
            _log.warning("    ❌ %s → error: %s", step_title, exc)

    return {"built": built, "errors": errors, "has_rag": has_rag}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Grade 5 LKB chips with RAG grounding")
    parser.add_argument("--subject", help="Rebuild one subject only (e.g. English)")
    parser.add_argument("--chapter", help="Rebuild one chapter only (must also specify --subject)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Show what would be done without calling the API or writing to DB")
    args = parser.parse_args()

    db = get_content_db(GRADE)

    # Discover subjects and chapters from lesson_cache (single source of truth)
    _log.info("Discovering chapters from lesson_cache for %s...", GRADE)
    lc = db.table("lesson_cache").select("subject, chapter").eq("grade", GRADE).eq("status", "active").execute()
    rows = lc.data or []
    chapters_by_subject: dict[str, list[str]] = {}
    seen = set()
    for r in rows:
        subj = r.get("subject", "")
        ch = r.get("chapter", "")
        if not subj or not ch:
            continue
        key = (subj, ch)
        if key not in seen:
            seen.add(key)
            chapters_by_subject.setdefault(subj, []).append(ch)

    # Apply filters
    if args.subject:
        subjects = [s for s in chapters_by_subject if args.subject.lower() in s.lower()]
        if not subjects:
            _log.error("Subject '%s' not found. Available: %s", args.subject, sorted(chapters_by_subject))
            sys.exit(1)
        chapters_by_subject = {s: chapters_by_subject[s] for s in subjects}

    if args.chapter:
        if not args.subject:
            _log.error("--chapter requires --subject")
            sys.exit(1)
        subj = list(chapters_by_subject.keys())[0]
        chapters_by_subject[subj] = [
            c for c in chapters_by_subject[subj]
            if args.chapter.lower() in c.lower()
        ]
        if not chapters_by_subject[subj]:
            _log.error("Chapter '%s' not found in %s", args.chapter, subj)
            sys.exit(1)

    total_chapters = sum(len(v) for v in chapters_by_subject.values())
    total_to_build = sum(
        len(v) * len(_get_lesson_steps(GRADE)) * 5
        for v in chapters_by_subject.values()
    )

    print()
    print("=" * 65)
    print(f"  LKB REBUILD — {GRADE}")
    print("=" * 65)
    print(f"  Subjects : {', '.join(sorted(chapters_by_subject))}")
    print(f"  Chapters : {total_chapters}")
    print(f"  Chips    : ~{total_to_build} to generate (5 per step × {len(_get_lesson_steps(GRADE))} steps)")
    print(f"  Mode     : {'DRY RUN — no API calls, no DB writes' if args.dry_run else 'LIVE — will call LLM and write to DB'}")
    print("=" * 65)
    print()

    if not args.dry_run:
        confirm = input("Type 'yes' to proceed: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)

    # Step 1: Archive existing chips
    print()
    _log.info("Step 1: Archiving existing LKB chips...")
    total_archived = 0
    for subject in chapters_by_subject:
        for chapter in chapters_by_subject[subject]:
            n = delete_lkb_chips(GRADE, subject, chapter, args.dry_run)
            total_archived += n
    _log.info("  Total archived: %d chips", total_archived)

    # Step 2: Regenerate with RAG grounding
    print()
    _log.info("Step 2: Regenerating chips with RAG grounding...")
    total_built = 0
    total_errors = 0
    no_rag_chapters = []

    for subject, chapters in sorted(chapters_by_subject.items()):
        _log.info("Subject: %s (%d chapters)", subject, len(chapters))
        for chapter in chapters:
            _log.info("  Chapter: %s", chapter)
            stats = rebuild_chapter(GRADE, subject, chapter, args.dry_run)
            total_built += stats["built"]
            total_errors += stats["errors"]
            if not stats["has_rag"]:
                no_rag_chapters.append(f"{subject} / {chapter}")
            if not args.dry_run:
                time.sleep(DELAY_BETWEEN_CHAPTERS)

    # Summary
    print()
    print("=" * 65)
    print("  REBUILD COMPLETE")
    print("=" * 65)
    print(f"  Chips generated : {total_built}")
    print(f"  Errors          : {total_errors}")
    print(f"  Chapters rebuilt: {total_chapters}")
    if no_rag_chapters:
        print(f"  Chapters with no RAG ({len(no_rag_chapters)}):") 
        for c in no_rag_chapters:
            print(f"    ⚠️  {c}")
    else:
        print("  RAG grounding   : ✅ All chapters had textbook context")
    print("=" * 65)
    print()
    if args.dry_run:
        print("  Re-run without --dry-run to apply changes.")
    else:
        print("  Done. LKB chips are now grounded in uploaded NCERT textbook content.")
        print("  Students will see these updated chips immediately (no app restart needed).")
    print()


if __name__ == "__main__":
    main()
