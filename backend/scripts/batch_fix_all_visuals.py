#!/usr/bin/env python3
"""
Batch Fix ALL Textbook Visuals — backfill + correct curator + cache-bust,
for every chapter of a grade/subject in one command
==============================================================================
Reusable replacement for running backfill_visual_assets_for_document() and
the right per-subject curator script one chapter at a time by hand. Per
user instruction: "create a script for the same for future use rather than
doing individually."

For each (grade, subject) in BOOK_SOURCES (prepare_gpt55_prompts.py):
  1. Looks up every chapter's rag_documents.id (tries the exact syllabus
     chapter string, then "Chapter N: " prefixed, then a bare-suffix
     match — the same three-tier fallback used throughout this project).
  2. Re-backfills that chapter's PDF pages to Supabase Storage as FULL,
     UNCROPPED page screenshots (rag_visual_service.
     backfill_visual_assets_for_document) — this always resets every
     page for that chapter to a fresh, full page image before curation
     decides which ones qualify as "active".
  3. Runs the correct deterministic curator for that subject:
       - Science / Maths / Social Science -> curate_textbook_visuals
         (NCERT "Fig. N.N:" caption convention)
       - English -> curate_prose_textbook_visuals (no caption
         convention; unique/non-decorative-image + full-page, no-crop)
       - Hindi -> curate_hindi_illustrations (structural image-frequency
         filtering; also full-page, no-crop)
  4. Deletes that chapter's lesson_chapter_doc cache row so the Chapter
     Journey UI reconverts with the freshly-approved images on next load.

IMPORTANT — full-page policy: every curator this script calls now leaves
the page as the FULL, UNCROPPED screenshot rendered by the backfill step
(see curate_prose_textbook_visuals.py's crop_and_reupload(), which is now
a no-op, and curate_textbook_visuals.py / curate_hindi_illustrations.py's
crop functions, which only ever trim vertically with generous padding,
never touching the page width). This directly satisfies the user's
instruction: "Review and replace all the cropped images to show full
width of the page. Only do vertical cropping where no text or context is
cut in the process. Prefer to show entire page wherever context suits
it." A curator only ever marks a page "active" (i.e. genuinely relevant
to that chapter's content) or "needs_review" (excluded) — it never
invents or trims content out of an approved page.

Usage:
    cd backend
    # Run for every Grade 9 subject that has a BOOK_SOURCES entry:
    python3 scripts/batch_fix_all_visuals.py --grade "Grade 9"

    # Run for a single subject only:
    python3 scripts/batch_fix_all_visuals.py --grade "Grade 9" --subject English

    # Preview without writing anything:
    python3 scripts/batch_fix_all_visuals.py --grade "Grade 9" --dry-run

    # Limit to the first N chapters of each subject (useful for testing):
    python3 scripts/batch_fix_all_visuals.py --grade "Grade 9" --subject Hindi --limit 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.chapter_doc_service import invalidate_stored_chapter_doc  # noqa: E402
from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: E402
from scripts.prepare_gpt55_prompts import BOOK_SOURCES, get_chapter_list  # noqa: E402

BOARD = "CBSE"
MODE = "CBSE"

# Which curator function to call for each subject. Falls back to the
# NCERT-Fig.-caption curator (curate_textbook_visuals) for any subject not
# explicitly listed here — that curator simply approves 0 pages if the
# book has no "Fig. N.N:" convention, which is a safe (if uninformative)
# default rather than a crash.
_CURATOR_BY_SUBJECT = {
    "English": "prose",
    "Hindi": "hindi",
    "Science": "figcaption",
    "Maths": "figcaption",
    "Social Science": "figcaption",
}


def find_document_id(grade: str, subject: str, chapter: str, chapter_index: int) -> str | None:
    """Look up rag_documents.id for a chapter — exact match, then
    'Chapter N: ' prefixed, then bare-suffix match, before giving up."""
    candidates = [chapter, f"Chapter {chapter_index}: {chapter}"]
    for candidate in candidates:
        try:
            result = (
                admin_client.table("rag_documents")
                .select("id")
                .eq("grade", grade)
                .eq("subject", subject)
                .eq("chapter", candidate)
                .limit(1)
                .execute()
            )
            if result.data:
                return str(result.data[0]["id"])
        except Exception:
            continue
    try:
        result = (
            admin_client.table("rag_documents")
            .select("id")
            .eq("grade", grade)
            .eq("subject", subject)
            .ilike("chapter", f"%{chapter}")
            .limit(1)
            .execute()
        )
        if result.data:
            return str(result.data[0]["id"])
    except Exception:
        pass
    return None


def run_curator(kind: str, document_id: str, pdf_path: Path, dry_run: bool) -> None:
    if kind == "prose":
        from scripts.curate_prose_textbook_visuals import curate_document as curate  # noqa: PLC0415
    elif kind == "hindi":
        from scripts.curate_hindi_illustrations import curate_document as curate  # noqa: PLC0415
    else:
        from scripts.curate_textbook_visuals import curate_document as curate  # noqa: PLC0415
    curate(document_id=document_id, pdf_path=str(pdf_path), dry_run=dry_run, force=True)


def process_subject(grade: str, subject: str, limit: int | None, dry_run: bool) -> None:
    key = (grade, subject)
    if key not in BOOK_SOURCES:
        print(f"\n[skip subject] No BOOK_SOURCES entry for {grade}/{subject} — "
              f"add one to prepare_gpt55_prompts.py to enable this.")
        return

    cfg = BOOK_SOURCES[key]
    pdf_dir: Path = cfg["pdf_dir"]
    book_code = cfg["book_code"]
    num_chapters = cfg["num_chapters"]
    curator_kind = _CURATOR_BY_SUBJECT.get(subject, "figcaption")

    try:
        chapters = get_chapter_list(grade, subject)
    except Exception as e:
        print(f"\n[skip subject] Could not load chapter list for {grade}/{subject}: {e}")
        return

    chapters = chapters[:num_chapters]
    if limit:
        chapters = chapters[:limit]

    print(f"\n{'='*78}\n{grade} / {subject} — {len(chapters)} chapter(s), curator={curator_kind}\n{'='*78}")

    for i, chapter in enumerate(chapters, start=1):
        pdf_path = pdf_dir / f"{book_code}{i:02d}.pdf"
        print(f"\n--- Chapter {i}: {chapter} ---")
        if not pdf_path.exists():
            print(f"  [skip] Source PDF not found: {pdf_path}")
            continue

        document_id = find_document_id(grade, subject, chapter, i)
        if document_id is None:
            print("  [skip] No rag_documents row found for this chapter.")
            continue

        print(f"  document_id={document_id}, pdf={pdf_path.name}")

        if dry_run:
            print("  [DRY RUN] Would backfill (full-page re-render) + curate + invalidate cache.")
            continue

        try:
            file_bytes = pdf_path.read_bytes()
            backfill_result = backfill_visual_assets_for_document(
                document_id=document_id, file_bytes=file_bytes,
                filename=pdf_path.name, uploaded_by=None,
            )
            print(f"  backfill: {backfill_result.get('message')}")
        except Exception as e:
            print(f"  [warn] Backfill failed: {e}")
            continue

        try:
            run_curator(curator_kind, document_id, pdf_path, dry_run=False)
        except Exception as e:
            print(f"  [warn] Curation failed: {e}")

        try:
            deleted = invalidate_stored_chapter_doc(grade, subject, chapter, MODE)
            print(f"  cache: invalidated {deleted} stored lesson_chapter_doc row(s)")
        except Exception as e:
            print(f"  [warn] Cache invalidation failed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch backfill + curate (full-page, no cropping) textbook visuals for every chapter of a grade/subject"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", help="Limit to one subject (default: every subject in BOOK_SOURCES for this grade)")
    parser.add_argument("--limit", type=int, help="Only process the first N chapters (useful for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without writing anything")
    args = parser.parse_args()

    if args.subject:
        subjects = [args.subject]
    else:
        subjects = [s for (g, s) in BOOK_SOURCES if g == args.grade]

    if not subjects:
        print(f"No BOOK_SOURCES entries found for grade={args.grade!r}.")
        return

    for subject in subjects:
        process_subject(args.grade, subject, args.limit, args.dry_run)

    print(f"\n{'='*78}\nDone.\n{'='*78}")


if __name__ == "__main__":
    main()
