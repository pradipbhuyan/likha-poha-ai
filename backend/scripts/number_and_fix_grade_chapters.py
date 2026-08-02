#!/usr/bin/env python3
"""
Number and Fix Grade Chapters
================================
For a given grade (and optionally one subject), this script:

  1. Reads the verified ground-truth chapter list from
     scripts/prepare_gpt55_prompts.py::CHAPTER_NAME_OVERRIDES.
  2. Identifies "extra" chapters live in rag_documents that are NOT in
     ground truth (stale/wrong-edition/Exemplar chapters) and CLEANLY
     deletes all their dependent data (rag_chunks, lesson_cache,
     lesson_chapter_doc, rag_visual_assets, rag_documents) -- same
     pattern used for the Grade 11 History fix on 2026-08-01.
  3. Renames every KEPT chapter's rag_documents.chapter (and lesson_cache
     .chapter, lesson_chapter_doc.chapter, rag_visual_assets.chapter) to
     add a "Chapter N: " prefix, where N is the chapter's 1-based
     position in the ground-truth list. This uses the exact same
     rename pattern as app/routes/syllabus.py's rename_rag_chapter_labels
     (used when an admin renames a dropdown entry), so retrieval
     continues to work identically -- and chapter_doc_service.py's
     existing "Chapter N: <title>" <-> bare-title fallback logic (see
     _strip_display_prefixes / _query_suffix, added 2026-07-31 for
     Grade 11 Maths/Biology) means EITHER prefixed or bare rows resolve
     correctly, so this rename is safe even if it's applied gradually.
  4. Rewrites (or creates) the syllabus_chapter_overrides row for this
     (grade, mode, subject) with the newly-numbered, correctly-ordered
     chapter list, so the student dropdown immediately reflects the fix.

IMPORTANT: after running this for any subject, you MUST restart the
locally-running backend server (or wait out its 30-minute in-process
_RAG_CACHE TTL) before the change is visible in the live dropdown --
see docs/GPT55_LESSON_UPDATE_STATUS.md, "IMPORTANT correction" note
dated 2026-08-01, for why a database change alone is not enough.

Usage:
    cd backend
    # Dry run first -- always review before applying:
    python3 scripts/number_and_fix_grade_chapters.py --grade "Grade 11" --subject History --dry-run
    # Apply for one subject:
    python3 scripts/number_and_fix_grade_chapters.py --grade "Grade 11" --subject History --force
    # Apply for ALL subjects configured for this grade in CHAPTER_NAME_OVERRIDES:
    python3 scripts/number_and_fix_grade_chapters.py --grade "Grade 11" --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

from app.services.auth_service import admin_client  # noqa: E402
from scripts.audit_grade_chapter_mismatches import (  # noqa: E402
    audit_subject,
    discover_subjects,
    normalize,
)

MODE = "CBSE"

_EXISTING_CHAPTER_PREFIX_RE = re.compile(r"^\s*chapter\s*\d+\s*:\s*", re.IGNORECASE)


def strip_existing_chapter_prefix(title: str) -> str:
    """Strip any existing 'Chapter N: ' prefix so re-numbering never doubles
    up -- some subjects' CHAPTER_NAME_OVERRIDES ground-truth entries already
    include a baked-in 'Chapter N: ' prefix (e.g. Mathematics), while others
    don't (e.g. History) -- normalize both to a bare title first."""
    return _EXISTING_CHAPTER_PREFIX_RE.sub("", title or "").strip()


def numbered(chapter_index_1based: int, title: str) -> str:
    """Return the 'Chapter N: <title>' display/storage form, stripping any
    pre-existing 'Chapter N: ' prefix from the input title first."""
    bare_title = strip_existing_chapter_prefix(title)
    return f"Chapter {chapter_index_1based}: {bare_title}"


def delete_extra_chapter(grade: str, subject: str, chapter_label: str, dry_run: bool) -> None:
    """Cleanly remove a stale/extra chapter's data from every dependent table."""
    docs_res = (
        admin_client.table("rag_documents")
        .select("id,chapter")
        .eq("grade", grade)
        .eq("subject", subject)
        .execute()
    )
    matching_ids = [
        d["id"] for d in (docs_res.data or [])
        if normalize(d.get("chapter") or "") == normalize(chapter_label)
    ]

    if not matching_ids:
        print(f"    [warn] no rag_documents row found for extra chapter {chapter_label!r} -- skipping")
        return

    print(f"    Deleting extra chapter {chapter_label!r} (rag_documents ids={matching_ids})")
    if dry_run:
        return

    for doc_id in matching_ids:
        admin_client.table("rag_chunks").delete().eq("document_id", doc_id).execute()
        admin_client.table("rag_visual_assets").delete().eq("document_id", doc_id).execute()

    admin_client.table("lesson_cache").delete().eq("grade", grade).eq("subject", subject).eq(
        "chapter", chapter_label
    ).execute()
    admin_client.table("lesson_chapter_doc").delete().eq("grade", grade).eq("subject", subject).eq(
        "chapter", chapter_label
    ).execute()

    for doc_id in matching_ids:
        admin_client.table("rag_documents").delete().eq("id", doc_id).execute()


def rename_chapter_everywhere(
    grade: str, subject: str, old_label: str, new_label: str, dry_run: bool
) -> None:
    """Rename one chapter's stored label across rag_documents, lesson_cache,
    lesson_chapter_doc, and rag_visual_assets -- same tables
    rename_rag_chapter_labels() (app/routes/syllabus.py) touches for an
    admin-driven rename, extended here to also cover lesson_chapter_doc
    and rag_visual_assets directly (belt-and-braces; chapter_doc_service.py
    already has fallback logic for these two, but keeping the stored label
    consistent avoids relying on that fallback at all)."""
    if old_label == new_label:
        # Exact match (not fuzzy-normalized) -- nothing to actually rename.
        # Using normalize() here would be WRONG: normalize() strips
        # "Chapter N: " prefixes for fuzzy comparison purposes, so
        # normalize(old_label) == normalize(new_label) is true for EVERY
        # bare-title -> "Chapter N: <title>" rename, which would silently
        # skip every rename this function is supposed to perform. Confirmed
        # live: this bug caused the 2026-08-01 --force run to report
        # "Done. N chapter(s) numbered" for every subject while actually
        # renaming zero rows anywhere.
        return

    print(f"    Renaming {old_label!r} -> {new_label!r}")
    if dry_run:
        return

    docs_res = (
        admin_client.table("rag_documents")
        .select("id,title,chapter")
        .eq("grade", grade)
        .eq("subject", subject)
        .execute()
    )
    for d in docs_res.data or []:
        if normalize(d.get("chapter") or "") != normalize(old_label):
            continue
        stored_chapter = d.get("chapter") or ""
        current_title = d.get("title") or ""
        next_title = (
            current_title.replace(stored_chapter, new_label)
            if stored_chapter and stored_chapter in current_title
            else current_title
        )
        admin_client.table("rag_documents").update(
            {"chapter": new_label, "title": next_title}
        ).eq("id", d["id"]).execute()

    admin_client.table("lesson_cache").update({"chapter": new_label}).eq(
        "grade", grade
    ).eq("subject", subject).eq("chapter", old_label).execute()

    admin_client.table("lesson_chapter_doc").update({"chapter": new_label}).eq(
        "grade", grade
    ).eq("subject", subject).eq("chapter", old_label).execute()

    admin_client.table("rag_visual_assets").update({"chapter": new_label}).eq(
        "grade", grade
    ).eq("subject", subject).eq("chapter", old_label).execute()


def upsert_dropdown_override(
    grade: str, mode: str, subject: str, numbered_chapters: list[str], dry_run: bool
) -> None:
    print(f"    Setting dropdown override to {len(numbered_chapters)} numbered chapters")
    if dry_run:
        return

    admin_client.table("syllabus_chapter_overrides").upsert(
        {
            "grade": grade,
            "mode": mode,
            "subject": subject,
            "chapters": numbered_chapters,
        },
        on_conflict="grade,mode,subject",
    ).execute()


def process_subject(grade: str, subject: str, dry_run: bool) -> None:
    report = audit_subject(grade, subject)
    print(f"\n{'=' * 70}\n{grade} / {subject}\n{'=' * 70}")

    if report["ground_truth"] is None:
        print("  [no ground truth configured -- skipping]")
        return

    if not report["keep_ordered"]:
        print("  [no live chapters match ground truth -- nothing to number, skipping]")
        return

    # Step 1: delete extras (stale/Exemplar/wrong-edition chapters)
    for extra in report["extra"]:
        delete_extra_chapter(grade, subject, extra, dry_run)

    # Step 2: rename each kept chapter to its numbered form
    numbered_chapters = []
    for idx, bare_title in enumerate(report["keep_ordered"], start=1):
        new_label = numbered(idx, bare_title)
        numbered_chapters.append(new_label)
        rename_chapter_everywhere(grade, subject, bare_title, new_label, dry_run)

    # Step 3: rewrite the dropdown override with the numbered, ordered list
    upsert_dropdown_override(grade, MODE, subject, numbered_chapters, dry_run)

    print(f"  Done. {len(numbered_chapters)} chapter(s) numbered, {len(report['extra'])} extra removed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", required=True)
    parser.add_argument("--subject", default=None, help="Limit to one subject")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.force:
        print("ERROR: pass either --dry-run or --force.")
        sys.exit(1)

    subjects = discover_subjects(args.grade)
    if args.subject:
        subjects = [args.subject]

    for subject in subjects:
        process_subject(args.grade, subject, args.dry_run)

    print(
        "\nIMPORTANT: restart the locally-running backend server now (or wait "
        "out its 30-minute in-process cache) before checking the live dropdown."
    )


if __name__ == "__main__":
    main()
