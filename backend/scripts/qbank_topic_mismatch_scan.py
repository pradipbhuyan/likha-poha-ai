#!/usr/bin/env python3
"""
Question Bank Topic-Mismatch Scan (READ-ONLY)
================================================
Sizes the "bank question filed under the wrong chapter" problem found by
manual spot-check in qbank_vs_lesson_cache_recheck.py, across the FULL
question_bank table (not just the 14-chapter sample).

Method: for every (grade, subject) group, build a term-frequency profile
per chapter from that chapter's lesson_cache content (the confirmed
authoritative source). Weight terms by inverse chapter-frequency within
the same subject, so profile signal is genuinely distinctive per chapter
(a plain keyword-presence check was shown to both false-positive and
false-negative earlier this session -- this is a best-match-among-siblings
test instead, which is more robust).

For every question_bank row, tokenize question+explanation text and score
it against every chapter profile in its own (grade, subject) group. If
some OTHER chapter scores meaningfully higher than the row's own assigned
chapter, flag it as a candidate mismatch.

Does NOT write anything to the database. Only .select() calls are used.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.auth_service import admin_client  # noqa: E402

BOARD = "CBSE"
MIN_QUESTION_TOKENS = 4          # skip too-short questions, noisy signal
MARGIN = 3.0                     # best-match must beat own-chapter score by this factor
                                  # (calibrated: real mismatches scored 1.7x-78x better elsewhere;
                                  # false positives from incidental shared keywords clustered at 1.2x-1.6x)
MIN_BEST_SCORE = 30.0             # best-match score itself must be non-trivial
MIN_CHAPTERS_FOR_SCAN = 2        # need >=2 chapters with lesson_cache to compare within a subject
LESSON_CONTENT_CAP = 8000        # chars per chapter profile, keeps cost bounded

STOPWORDS = set("""
the a an and or of to in on for with is are was were be been being this
that these those as by from at it its it's you your yours we our ours
they their theirs he she his her him them what which who whom will would
should could can may might must shall not no nor so than then thus hence
therefore because since while during before after above below between
into onto upon over under again further once here there when where why
how all each few more most other some such only own same too very just
don now also using used use given following different several various
each such new one two three four five following statement statements
following which following the according text passage chapter following
example true false correct incorrect above below option options answer
answers question questions following term terms called known referred
also often may can within about above like such
""".split())

TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def fetch_all(qb, page: int = 1000) -> list[dict]:
    rows, start = [], 0
    while True:
        r = qb().range(start, start + page - 1).execute()
        d = r.data or []
        rows.extend(d)
        if len(d) < page:
            break
        start += page
    return rows


def main() -> None:
    print("Fetching lesson_cache (active, CBSE)...")
    lesson_rows = fetch_all(lambda: admin_client.table("lesson_cache")
                             .select("grade,subject,chapter,lesson_content")
                             .eq("status", "active").eq("mode", "CBSE"))
    print(f"  {len(lesson_rows)} lesson_cache rows")

    # Aggregate lesson content per (grade, subject, chapter)
    chapter_text: dict[tuple, str] = defaultdict(str)
    for r in lesson_rows:
        key = (r["grade"], r["subject"], r["chapter"])
        if len(chapter_text[key]) < LESSON_CONTENT_CAP:
            chapter_text[key] += " " + (r.get("lesson_content") or "")

    # Group chapters by (grade, subject)
    subject_chapters: dict[tuple, list[str]] = defaultdict(list)
    for (grade, subject, chapter) in chapter_text:
        subject_chapters[(grade, subject)].append(chapter)

    # Build per-chapter TF, then IDF across sibling chapters in the same subject,
    # then per-chapter TF-IDF weight dict.
    chapter_profile: dict[tuple, dict[str, float]] = {}
    for (grade, subject), chapters in subject_chapters.items():
        if len(chapters) < MIN_CHAPTERS_FOR_SCAN:
            continue
        tfs = {}
        df = Counter()
        for ch in chapters:
            toks = tokenize(chapter_text[(grade, subject, ch)])
            tf = Counter(toks)
            tfs[ch] = tf
            for term in tf:
                df[term] += 1
        n_chapters = len(chapters)
        for ch in chapters:
            profile = {}
            for term, count in tfs[ch].items():
                idf = (n_chapters / df[term])
                profile[term] = count * idf
            chapter_profile[(grade, subject, ch)] = profile

    scannable_groups = {k: v for k, v in subject_chapters.items() if len(v) >= MIN_CHAPTERS_FOR_SCAN}
    print(f"  {len(scannable_groups)} (grade,subject) groups scannable "
          f"({sum(len(v) for v in scannable_groups.values())} chapters with lesson_cache)")

    skipped_groups = {k: v for k, v in subject_chapters.items() if len(v) < MIN_CHAPTERS_FOR_SCAN}
    if skipped_groups:
        print(f"  {len(skipped_groups)} (grade,subject) groups skipped (only 1 chapter has lesson_cache, no sibling to compare against)")

    print("\nFetching question_bank (all rows)...")
    bank_rows = fetch_all(lambda: admin_client.table("question_bank")
                           .select("id,grade,subject,chapter,question,explanation,status")
                           .eq("board", BOARD))
    print(f"  {len(bank_rows)} question_bank rows")

    def title_overlap(a: str, b: str) -> float:
        # crude same-chapter-under-different-string detector: fraction of a's
        # distinctive tokens also present in b's tokens
        ta, tb = set(tokenize(a)), set(tokenize(b))
        if not ta:
            return 0.0
        return len(ta & tb) / len(ta)

    total_scanned = 0
    total_no_profile = 0     # category A: row's chapter label has zero lesson_cache match at all
    total_dup_naming = 0     # category B: own has profile, but "better" chapter is same chapter under a different title string
    total_too_short = 0
    flagged = []              # category C: genuine candidate topic mismatch
    orphaned = []              # category A rows, for reporting
    dup_naming = []            # category B rows, for reporting

    per_group_totals = Counter()
    per_group_flagged = Counter()
    per_group_orphaned = Counter()
    per_group_dupnaming = Counter()

    for row in bank_rows:
        grade, subject, chapter = row["grade"], row["subject"], row["chapter"]
        group = (grade, subject)
        if group not in scannable_groups:
            continue
        own_key = (grade, subject, chapter)
        per_group_totals[group] += 1

        toks = tokenize((row.get("question") or "") + " " + (row.get("explanation") or ""))
        if len(toks) < MIN_QUESTION_TOKENS:
            total_too_short += 1
            continue

        qtf = Counter(toks)
        own_profile = chapter_profile.get(own_key)
        total_scanned += 1

        if own_profile is None:
            # chapter label itself doesn't exist in lesson_cache for this subject at all
            total_no_profile += 1
            per_group_orphaned[group] += 1
            orphaned.append((grade, subject, chapter, row))
            continue

        own_score = sum(qtf[t] * own_profile.get(t, 0.0) for t in qtf)

        best_chapter, best_score = None, 0.0
        for ch in scannable_groups[group]:
            if ch == chapter:
                continue
            profile = chapter_profile[(grade, subject, ch)]
            score = sum(qtf[t] * profile.get(t, 0.0) for t in qtf)
            if score > best_score:
                best_score, best_chapter = score, ch

        if not (best_chapter and best_score >= MIN_BEST_SCORE and best_score >= own_score * MARGIN):
            continue

        if title_overlap(chapter, best_chapter) >= 0.5 or title_overlap(best_chapter, chapter) >= 0.5:
            # own_ch and best_ch titles overlap heavily -- almost certainly the same
            # real-world chapter present twice under different title strings in
            # lesson_cache, not a genuine topic mismatch.
            total_dup_naming += 1
            per_group_dupnaming[group] += 1
            dup_naming.append((grade, subject, chapter, best_chapter, own_score, best_score, row))
            continue

        flagged.append((grade, subject, chapter, best_chapter, own_score, best_score, row))
        per_group_flagged[group] += 1

    print(f"\nScanned {total_scanned} rows across {len(scannable_groups)} groups ({total_too_short} too-short skipped)")
    print(f"  Category A -- orphaned chapter label (no lesson_cache match at all): {total_no_profile} rows "
          f"({100*total_no_profile/max(total_scanned,1):.1f}%)")
    print(f"  Category B -- duplicate chapter naming (same chapter, two title strings in lesson_cache): {total_dup_naming} rows "
          f"({100*total_dup_naming/max(total_scanned,1):.1f}%)")
    print(f"  Category C -- genuine candidate topic mismatch: {len(flagged)} rows "
          f"({100*len(flagged)/max(total_scanned,1):.1f}%)")

    print(f"\n{'=' * 90}\nCATEGORY A: orphaned chapter labels, per (grade, subject)\n{'=' * 90}")
    for group in sorted(per_group_orphaned, key=lambda g: -per_group_orphaned[g])[:20]:
        grade, subject = group
        total = per_group_totals[group]
        o = per_group_orphaned[group]
        labels = Counter(c for (g, s, c, r) in orphaned if (g, s) == group)
        print(f"  {grade:10s} {subject:20s} {o:5d} / {total:5d} orphaned  ({100*o/total:.1f}%)  labels: {labels.most_common(3)}")

    print(f"\n{'=' * 90}\nCATEGORY B: duplicate-naming, per (grade, subject)\n{'=' * 90}")
    for group in sorted(per_group_dupnaming, key=lambda g: -per_group_dupnaming[g])[:20]:
        grade, subject = group
        total = per_group_totals[group]
        d = per_group_dupnaming[group]
        print(f"  {grade:10s} {subject:20s} {d:5d} / {total:5d} dup-naming  ({100*d/total:.1f}%)")

    print(f"\n{'=' * 90}\nCATEGORY C: genuine candidate topic mismatch, per (grade, subject)\n{'=' * 90}")
    for group in sorted(per_group_flagged, key=lambda g: -per_group_flagged[g]):
        grade, subject = group
        total = per_group_totals[group]
        f = per_group_flagged[group]
        print(f"  {grade:10s} {subject:20s} {f:5d} / {total:5d} flagged  ({100*f/total:.1f}%)")

    # Per-chapter breakdown for the flagged rows
    per_chapter = defaultdict(list)
    for (grade, subject, chapter, best_chapter, own_score, best_score, row) in flagged:
        per_chapter[(grade, subject, chapter)].append((best_chapter, own_score, best_score, row))

    out_lines = []
    out_lines.append(f"Total scanned: {total_scanned}  |  Category A (orphaned): {total_no_profile}  "
                      f"|  Category B (dup-naming): {total_dup_naming}  |  Category C (genuine mismatch): {len(flagged)}\n")

    out_lines.append(f"\n{'#' * 90}\n# CATEGORY A DETAIL: orphaned chapter labels (sample per group)\n{'#' * 90}")
    per_group_orphan_rows = defaultdict(list)
    for (grade, subject, chapter, row) in orphaned:
        per_group_orphan_rows[(grade, subject, chapter)].append(row)
    for key in sorted(per_group_orphan_rows, key=lambda k: -len(per_group_orphan_rows[k]))[:40]:
        grade, subject, chapter = key
        rows = per_group_orphan_rows[key]
        out_lines.append(f"\n{grade} / {subject} / chapter label = {chapter!r}  -- {len(rows)} rows")
        out_lines.append(f"    e.g. Q: {rows[0]['question'][:150]}")

    out_lines.append(f"\n{'#' * 90}\n# CATEGORY B DETAIL: duplicate chapter naming (sample per group)\n{'#' * 90}")
    per_group_dup_rows = defaultdict(list)
    for (grade, subject, chapter, best_chapter, own_score, best_score, row) in dup_naming:
        per_group_dup_rows[(grade, subject, chapter, best_chapter)].append(row)
    for key in sorted(per_group_dup_rows, key=lambda k: -len(per_group_dup_rows[k]))[:40]:
        grade, subject, chapter, best_chapter = key
        rows = per_group_dup_rows[key]
        out_lines.append(f"\n{grade} / {subject}: {chapter!r}  <-->  {best_chapter!r}  -- {len(rows)} rows")

    out_lines.append(f"\n{'#' * 90}\n# CATEGORY C DETAIL: genuine candidate topic mismatch\n{'#' * 90}")
    for key in sorted(per_chapter, key=lambda k: -len(per_chapter[k])):
        grade, subject, chapter = key
        items = per_chapter[key]
        out_lines.append(f"\n{'=' * 90}\n{grade} / {subject} / {chapter}  -- {len(items)} flagged of "
                          f"{per_group_totals[(grade, subject)]} rows in this (grade,subject) group\n{'=' * 90}")
        best_ch_counts = Counter(b for b, *_ in items)
        out_lines.append(f"  Most common better-match chapter(s): {best_ch_counts.most_common(3)}")
        for best_chapter, own_score, best_score, row in items[:5]:
            out_lines.append(f"\n  [id={row['id']}] own_score={own_score:.1f} vs best_score={best_score:.1f} (better match: {best_chapter})")
            out_lines.append(f"    Q: {row['question'][:200]}")
            out_lines.append(f"    Explanation: {(row.get('explanation') or '')[:200]}")

    out_path = "/private/tmp/claude-501/-Users-a0247716/0ff84df7-214d-4ae0-a83b-8c9062438dbc/scratchpad/qbank_topic_mismatch_scan.txt"
    Path(out_path).write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nFull per-chapter detail (with sample flagged questions) written to {out_path}")


if __name__ == "__main__":
    main()
