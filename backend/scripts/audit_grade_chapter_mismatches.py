#!/usr/bin/env python3
"""
Audit Grade Chapter Mismatches (read-only)
============================================
Compares each subject's LIVE rag_documents chapter list against the
verified ground-truth chapter list in
scripts/prepare_gpt55_prompts.py::CHAPTER_NAME_OVERRIDES, and reports:

  - "extra" chapters: live in rag_documents but NOT in ground truth
    (these are usually stale/wrong-edition chapters that should be
    hidden from the student dropdown, e.g. the 4 old-edition History
    chapters found and removed on 2026-08-01).
  - "missing" chapters: in ground truth but with no live rag_documents
    row yet (just informational -- nothing to fix, simply not yet
    ingested).
  - the correctly-ordered "keep" list, i.e. ground truth chapters that
    ARE live, in ground-truth order -- this is what
    number_and_fix_grade_chapters.py will number and use to rebuild the
    dropdown override.

This script makes NO changes -- it only prints a report. Run this BEFORE
number_and_fix_grade_chapters.py so you can review what will change.

Usage:
    cd backend
    python3 scripts/audit_grade_chapter_mismatches.py --grade "Grade 11"
    python3 scripts/audit_grade_chapter_mismatches.py --grade "Grade 11" --subject History
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from scripts.prepare_gpt55_prompts import CHAPTER_NAME_OVERRIDES  # noqa: E402


def get_ground_truth(grade: str, subject: str) -> list[str] | None:
    """Return the verified ground-truth chapter list for (grade, subject).

    Prefers CHAPTER_NAME_OVERRIDES (used for Grade 10/11/12, whose
    syllabus.py entries are placeholder-only), but falls back to the
    real curated chapter list in app.data.syllabus.SYLLABUS for grades
    that DO have one there (e.g. Grade 9, which lists real chapter
    titles directly in syllabus.py rather than needing an override) --
    this is exactly the same precedence order
    app/routes/syllabus.py::get_chapter_list() and
    scripts/prepare_gpt55_prompts.py::get_chapter_list() already use
    elsewhere in the codebase, so this function stays consistent with
    how the rest of the platform decides "what SHOULD this subject's
    chapters be" for any given grade."""
    override = CHAPTER_NAME_OVERRIDES.get((grade, subject))
    if override is not None:
        return list(override)

    try:
        from app.data.syllabus import SYLLABUS  # noqa: PLC0415
        chapters = SYLLABUS[grade]["CBSE"][subject]
        # A single "Uploaded Book Content" (or similar upload-only
        # placeholder) entry means syllabus.py has no real ground truth
        # for this subject either -- treat it the same as "no override
        # configured" rather than a 1-chapter ground truth that would
        # incorrectly flag every real live chapter as EXTRA.
        if len(chapters) == 1 and "uploaded" in chapters[0].lower():
            return None
        return list(chapters)
    except (KeyError, ImportError):
        return None


def normalize(s: str) -> str:
    """Normalize a chapter label for fuzzy comparison (case/dash/space insensitive).

    Strips a leading "Chapter N:" prefix (English) OR "अध्याय N:" prefix
    (Hindi -- "अध्याय" is the Hindi word for "chapter") so bare and
    already-numbered Hindi chapter titles compare equal, exactly like the
    English case. Without this, e.g. Grade 9 Hindi's already-correctly-
    numbered live rows ("अध्याय 1: दो बैलों की कथा") would falsely show
    as EXTRA against the bare ground-truth title ("दो बैलों की कथा"),
    even though the subject's dropdown is already fully correct via its
    own syllabus_chapter_overrides row -- confirmed live 2026-08-01."""
    s = s.strip().lower()
    s = re.sub(r"^chapter\s*\d+\s*[:\-]\s*", "", s)  # strip English "Chapter N:" prefix
    s = re.sub(r"^अध्याय\s*\d+\s*[:\-]\s*", "", s)  # strip Hindi "अध्याय N:" prefix
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[’']", "'", s)
    return s.strip()


def get_live_chapters(grade: str, subject: str) -> list[str]:
    res = (
        admin_client.table("rag_documents")
        .select("chapter,created_at")
        .eq("grade", grade)
        .eq("subject", subject)
        .execute()
    )
    # de-dup while preserving first-seen order (created_at ascending)
    rows = sorted(res.data or [], key=lambda r: r.get("created_at") or "")
    seen = set()
    out = []
    for r in rows:
        ch = (r.get("chapter") or "").strip()
        if not ch or ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return out


def audit_subject(grade: str, subject: str) -> dict:
    ground_truth = get_ground_truth(grade, subject)
    live = get_live_chapters(grade, subject)

    if ground_truth is None:
        return {
            "subject": subject,
            "ground_truth": None,
            "live": live,
            "extra": [],
            "missing": [],
            "keep_ordered": live,  # no ground truth -> can't determine order/extras
        }

    gt_norm_map = {normalize(c): c for c in ground_truth}
    live_norm_map = {normalize(c): c for c in live}

    extra = [live_norm_map[n] for n in live_norm_map if n not in gt_norm_map]
    missing = [gt for n, gt in gt_norm_map.items() if n not in live_norm_map]

    # IMPORTANT: keep_ordered must return the ACTUAL LIVE label (from
    # live_norm_map), never the ground-truth label -- some subjects'
    # ground-truth entries already have a baked-in "Chapter N: " prefix
    # (e.g. Mathematics), while the live rag_documents.chapter is bare
    # (e.g. "Sets"). If this returned the ground-truth label instead, a
    # caller trying to rename "old live label" -> "new numbered label"
    # would compute old_label == new_label (both "Chapter 1: Sets") even
    # though the live row is actually still bare "Sets", and would then
    # skip the actual rename entirely -- confirmed live: this exact bug
    # caused the 2026-08-01 fix run to silently leave every Grade 11
    # Mathematics rag_documents.chapter row unprefixed.
    keep_ordered = [live_norm_map[normalize(gt)] for gt in ground_truth if normalize(gt) in live_norm_map]

    return {
        "subject": subject,
        "ground_truth": ground_truth,
        "live": live,
        "extra": extra,
        "missing": missing,
        "keep_ordered": keep_ordered,
    }


def discover_subjects(grade: str) -> list[str]:
    """Return every subject this grade has EITHER a CHAPTER_NAME_OVERRIDES
    entry OR a real (non-placeholder) syllabus.py chapter list for."""
    subjects = {s for (g, s) in CHAPTER_NAME_OVERRIDES if g == grade}

    try:
        from app.data.syllabus import SYLLABUS  # noqa: PLC0415
        for subject, chapters in SYLLABUS.get(grade, {}).get("CBSE", {}).items():
            if len(chapters) == 1 and "uploaded" in chapters[0].lower():
                continue
            subjects.add(subject)
    except ImportError:
        pass

    return sorted(subjects)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", required=True)
    parser.add_argument("--subject", default=None, help="Limit to one subject")
    args = parser.parse_args()

    subjects = discover_subjects(args.grade)
    if args.subject:
        subjects = [args.subject]

    for subject in subjects:
        report = audit_subject(args.grade, subject)
        print(f"\n{'=' * 70}")
        print(f"{args.grade} / {subject}")
        print(f"{'=' * 70}")

        if report["ground_truth"] is None:
            print("  [no ground truth configured for this subject]")
            continue

        print(f"  Ground truth: {len(report['ground_truth'])} chapters")
        print(f"  Live rag_documents: {len(report['live'])} chapters")
        print(f"  Keep (matches ground truth, correctly ordered): {len(report['keep_ordered'])}")

        if report["extra"]:
            print(f"\n  EXTRA (live but NOT in ground truth -- candidates to HIDE):")
            for c in report["extra"]:
                print(f"    - {c}")

        if report["missing"]:
            print(f"\n  MISSING (in ground truth but not yet ingested -- informational only):")
            for c in report["missing"]:
                print(f"    - {c}")

        if not report["extra"] and not report["missing"]:
            print("\n  Clean -- live chapters exactly match ground truth.")


if __name__ == "__main__":
    main()
