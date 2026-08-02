#!/usr/bin/env python3
"""
Question Bank Reachability Audit (READ-ONLY)
================================================
Phase 1 of the deep quality check requested after the normalize_question_bank_chapters.py
incident. Computes, for every one of the ~150,000 question_bank rows, whether its
chapter can be reconciled against the CURRENT canonical chapter list (rag_documents,
board='CBSE', excluding Exemplar/Olympiad/placeholder -- the same exclusions
syllabus.merge_uploaded_rag_chapters() applies to the real student-facing dropdown).

Does NOT write anything to the database. Pure read + in-memory computation.

Lessons applied from the prior incident + follow-up research (see conversation):
- rag_documents is used as the canonical "current chapter" source, NOT lesson_cache
  (lesson_cache was found to carry conflicting old/new chapter numbering under
  status='active' for at least one real subject, with no way to disambiguate).
- Exemplar chapters (is_exemplar_chapter), Olympiad subjects, the "Uploaded Book
  Content" placeholder, and known junk chapter codes are excluded from the
  "in-scope" population BEFORE computing any match rate -- mixing them in
  understates match quality by ~15 points.
- Matching is 5-tier, mirroring the app's own proven fallback chain
  (mock_test_service.get_questions_from_bank_with_fallback) plus the two gaps
  that specific research found still missing from it: case-folding and a final
  ILIKE-equivalent substring tier.
- rag_documents.(grade,subject,chapter) is 1:N to id (confirmed real duplicates
  exist) -- canonical set is built from all matching rows, not assumed unique.
- board='CBSE' is filtered explicitly on every table query, even though
  question_bank itself has no board diversity today (rag_documents does, and a
  future non-CBSE upload with a colliding grade/subject could otherwise corrupt
  the comparison).

Usage:
    cd backend
    ./venv/bin/python scripts/qbank_reachability_audit.py
    ./venv/bin/python scripts/qbank_reachability_audit.py --out /path/to/report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.routes.syllabus import is_exemplar_chapter, is_uploaded_placeholder  # noqa: E402
from app.services.mock_test_service import (  # noqa: E402
    strip_source_display_prefix,
    normalize_chapter_core,
)

BOARD = "CBSE"

_JUNK_CODE_RE = re.compile(r"^[a-z]{2,6}\d{2,4}$", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_CHAPTER_NO_SEP_RE = re.compile(r"^\s*chapter\s+(\d+)\s+", re.IGNORECASE)

# Unicode punctuation variants that render near-identically but don't compare
# equal as strings -- confirmed live: "Papa's Spectacles" (curly ' U+2019) vs
# a straight-apostrophe canonical form, and "Nelson Mandela — Long Walk to
# Freedom" (em-dash U+2014) vs a hyphen-dash canonical form.
_PUNCT_FOLD = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ",
})


def fetch_all(table_query_builder, page: int = 1000) -> list[dict]:
    all_rows: list[dict] = []
    start = 0
    while True:
        result = table_query_builder().range(start, start + page - 1).execute()
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < page:
            break
        start += page
    return all_rows


def casefold_collapsed(text: str) -> str:
    """Case-fold + collapse whitespace, for tier-3 comparison."""
    return _WHITESPACE_RE.sub(" ", (text or "").strip()).casefold()


def deep_normalize(text: str) -> str:
    """
    Maximally-permissive normalization for the final match tier: NFC unicode
    normalize, fold curly quotes/apostrophes and en/en-dashes to their plain
    ASCII equivalents, strip a "Chapter N" prefix even with no colon/dash
    separator, run through normalize_chapter_core's prefix-stripping loop,
    then case-fold and collapse whitespace. Confirmed live-necessary: "Papa's
    Spectacles" (curly ') vs a straight-apostrophe canonical, and "Nelson
    Mandela — Long Walk to Freedom" (em-dash) vs a hyphen-dash canonical.
    """
    text = unicodedata.normalize("NFC", text or "")
    text = text.translate(_PUNCT_FOLD)
    text = _CHAPTER_NO_SEP_RE.sub("", text)
    text = normalize_chapter_core(text)
    return _WHITESPACE_RE.sub(" ", text.strip()).casefold()


def classify_scope(subject: str, chapter: str) -> str | None:
    """
    Return an out-of-scope bucket name, or None if the row is in-scope for
    chapter-matching. Mirrors the exclusions syllabus.merge_uploaded_rag_chapters()
    applies to the real student-facing dropdown, plus junk patterns found live
    during the follow-up research pass (feprNNN codes, blank chapters).
    """
    chapter = (chapter or "").strip()
    if not chapter:
        return "blank"
    if "Olympiad" in (subject or ""):
        return "olympiad"
    if is_exemplar_chapter(chapter):
        return "exemplar"
    if is_uploaded_placeholder(chapter):
        return "placeholder"
    if _JUNK_CODE_RE.match(chapter):
        return "junk_code"
    return None


def build_canonical_index(rag_rows: list[dict]) -> dict[tuple[str, str], dict]:
    """
    Build, per (grade, subject), the canonical chapter list (excluding Exemplar/
    Olympiad, board='CBSE' only -- already filtered by caller) plus a
    normalized-core -> [canonical chapters] index for tiers 2-4.
    """
    by_subject: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rag_rows:
        grade, subject, chapter = r.get("grade"), r.get("subject"), r.get("chapter")
        if not grade or not subject or not chapter:
            continue
        if is_exemplar_chapter(chapter):
            continue
        if chapter not in by_subject[(grade, subject)]:
            by_subject[(grade, subject)].append(chapter)

    index: dict[tuple[str, str], dict] = {}
    for key, chapters in by_subject.items():
        core_map: dict[str, list[str]] = defaultdict(list)
        casefold_map: dict[str, list[str]] = defaultdict(list)
        deep_map: dict[str, list[str]] = defaultdict(list)
        for c in chapters:
            core_map[normalize_chapter_core(c)].append(c)
            casefold_map[casefold_collapsed(c)].append(c)
            deep_map[deep_normalize(c)].append(c)
        index[key] = {
            "chapters": chapters, "core_map": core_map,
            "casefold_map": casefold_map, "deep_map": deep_map,
        }
    return index


def resolve_chapter(chapter: str, canonical: dict) -> tuple[str | None, list[str]]:
    """
    Try each match tier in order. Returns (tier_name, matched_canonical_chapters).
    tier_name is None if nothing matched at any tier.
    """
    chapters = canonical["chapters"]
    core_map = canonical["core_map"]
    casefold_map = canonical["casefold_map"]
    deep_map = canonical["deep_map"]

    if chapter in chapters:
        return "exact", [chapter]

    stripped = strip_source_display_prefix(chapter)
    if stripped != chapter and stripped in chapters:
        return "source_prefix_strip", [stripped]

    core = normalize_chapter_core(chapter)
    if core in core_map:
        return "normalized_core", core_map[core]

    cf = casefold_collapsed(chapter)
    if cf in casefold_map:
        return "case_insensitive", casefold_map[cf]

    deep = deep_normalize(chapter)
    if deep in deep_map:
        return "deep_normalize", deep_map[deep]

    cf_core = casefold_collapsed(core)
    if cf_core:
        for canon_core, canon_chapters in core_map.items():
            canon_cf = casefold_collapsed(canon_core)
            if cf_core and canon_cf and (cf_core in canon_cf or canon_cf in cf_core):
                return "substring_fuzzy", canon_chapters

    deep_substr_candidates = [
        (d, chs) for d, chs in deep_map.items() if d and deep and (d in deep or deep in d)
    ]
    if deep_substr_candidates:
        # Prefer the closest-length match to avoid over-eager short-string containment.
        deep_substr_candidates.sort(key=lambda x: abs(len(x[0]) - len(deep)))
        return "deep_substring_fuzzy", deep_substr_candidates[0][1]

    return None, []


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only question_bank reachability audit")
    parser.add_argument("--out", default=None, help="Optional path to write full JSON report")
    args = parser.parse_args()

    print("Fetching question_bank (all rows, all statuses)...")
    qb_rows = fetch_all(lambda: admin_client.table("question_bank").select(
        "id,grade,subject,chapter,difficulty,status"
    ).eq("board", BOARD))
    print(f"  {len(qb_rows)} rows")

    print("Fetching rag_documents (board=CBSE)...")
    rag_rows = fetch_all(lambda: admin_client.table("rag_documents").select(
        "grade,subject,chapter"
    ).eq("board", BOARD))
    print(f"  {len(rag_rows)} rows")

    canonical_index = build_canonical_index(rag_rows)

    # ---- classify + resolve every row ----
    scope_counts = defaultdict(int)
    tier_counts = defaultdict(int)
    unresolved: dict[tuple[str, str, str], int] = defaultdict(int)
    recoverable: dict[tuple[str, str, str], tuple[str, list[str], int]] = {}
    per_subject = defaultdict(lambda: defaultdict(int))

    for row in qb_rows:
        grade, subject, chapter = row["grade"], row["subject"], row.get("chapter") or ""
        scope = classify_scope(subject, chapter)
        if scope:
            scope_counts[scope] += 1
            continue

        scope_counts["in_scope"] += 1
        canonical = canonical_index.get((grade, subject))
        if not canonical:
            tier_counts["no_canonical_subject"] += 1
            unresolved[(grade, subject, chapter)] += 1
            per_subject[(grade, subject)]["unresolved"] += 1
            continue

        tier, matched = resolve_chapter(chapter, canonical)
        if tier is None:
            tier_counts["unresolved"] += 1
            unresolved[(grade, subject, chapter)] += 1
            per_subject[(grade, subject)]["unresolved"] += 1
        else:
            tier_counts[tier] += 1
            per_subject[(grade, subject)][tier] += 1
            if tier != "exact":
                key = (grade, subject, chapter)
                recoverable[key] = (tier, matched, recoverable.get(key, (None, None, 0))[2] + 1)

    total = len(qb_rows)
    in_scope = scope_counts["in_scope"]
    resolved = sum(v for k, v in tier_counts.items() if k not in ("unresolved", "no_canonical_subject"))

    print(f"\n{'=' * 78}\nSCOPE BREAKDOWN (all {total} rows)\n{'=' * 78}")
    for bucket in ["in_scope", "exemplar", "olympiad", "placeholder", "junk_code", "blank"]:
        n = scope_counts.get(bucket, 0)
        print(f"  {bucket:<15} {n:>8}  ({100*n/total:.1f}%)")

    print(f"\n{'=' * 78}\nMATCH TIER BREAKDOWN (in-scope rows only: {in_scope})\n{'=' * 78}")
    for tier in ["exact", "source_prefix_strip", "normalized_core", "case_insensitive",
                 "deep_normalize", "substring_fuzzy", "deep_substring_fuzzy",
                 "unresolved", "no_canonical_subject"]:
        n = tier_counts.get(tier, 0)
        pct = 100 * n / in_scope if in_scope else 0
        print(f"  {tier:<22} {n:>8}  ({pct:.1f}%)")

    print(f"\nOverall: {resolved}/{in_scope} in-scope rows reconcile to a current chapter "
          f"({100*resolved/in_scope:.1f}%)")

    print(f"\n{'=' * 78}\nPER-SUBJECT BREAKDOWN\n{'=' * 78}")
    print(f"{'Grade':<10}{'Subject':<26}{'Exact':<8}{'Recov.':<8}{'Unresolved':<12}{'Resolved%':<10}")
    for (grade, subject), counts in sorted(per_subject.items(), key=lambda x: (int(x[0][0].split()[1]), x[0][1])):
        exact = counts.get("exact", 0)
        recov = sum(v for k, v in counts.items() if k not in ("exact", "unresolved"))
        unres = counts.get("unresolved", 0)
        total_s = exact + recov + unres
        pct = 100 * (exact + recov) / total_s if total_s else 0
        print(f"{grade:<10}{subject:<26}{exact:<8}{recov:<8}{unres:<12}{pct:.1f}%")

    print(f"\n{'=' * 78}\nTOP UNRESOLVED CHAPTERS (by row count, top 40)\n{'=' * 78}")
    for (grade, subject, chapter), n in sorted(unresolved.items(), key=lambda x: -x[1])[:40]:
        print(f"  {n:>4} rows  {grade:<10}{subject:<22}{chapter!r}")

    if args.out:
        report = {
            "total_rows": total,
            "scope_counts": dict(scope_counts),
            "tier_counts": dict(tier_counts),
            "per_subject": {f"{g}|{s}": dict(c) for (g, s), c in per_subject.items()},
            "unresolved": [{"grade": g, "subject": s, "chapter": c, "rows": n}
                            for (g, s, c), n in sorted(unresolved.items(), key=lambda x: -x[1])],
            "recoverable_sample": [{"grade": g, "subject": s, "chapter": c, "tier": t, "matches": m}
                                    for (g, s, c), (t, m, _n) in list(recoverable.items())[:500]],
        }
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFull JSON report written to {args.out}")


if __name__ == "__main__":
    main()
