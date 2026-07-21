"""
Batch Chapter-Doc Conversion
============================
Converts every chapter with cached lesson steps into a typed-block Chapter
Journey document (lesson_chapter_doc), and reports syllabus coverage.

Deterministic and zero-token: only reads lesson_cache and writes
lesson_chapter_doc via chapter_doc_service. Chapters that fail to convert are
listed in the report — that list is the prewarm gap list.

Usage:
    cd backend
    .venv/bin/python scripts/convert_chapter_docs.py                # all grades
    .venv/bin/python scripts/convert_chapter_docs.py --grade "Grade 6"
    .venv/bin/python scripts/convert_chapter_docs.py --force        # re-convert
    .venv/bin/python scripts/convert_chapter_docs.py --dry-run      # no writes

Outputs:
    reports/chapter_docs/conversion_report.csv   (one row per chapter)
    reports/chapter_docs/conversion_summary.md   (per-grade rollup)
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.chapter_doc_service import (  # noqa: E402
    _fetch_step_rows,
    convert_chapter,
    get_stored_chapter_doc,
    store_chapter_doc,
)
from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.lesson_kb_service import _get_lesson_steps  # noqa: E402

ALL_GRADES = [f"Grade {n}" for n in range(5, 13)]
PAGE_SIZE = 1000

REPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports", "chapter_docs",
)


def fetch_cached_chapter_combos(grades: list[str]) -> list[dict]:
    """Return distinct {board, grade, subject, chapter, mode} combos that have
    active lesson_cache rows, across both Supabase projects."""
    combos: dict[tuple, dict] = {}
    # One DB client per routing group (primary vs Grade 11/12)
    routing_groups: dict[int, list[str]] = defaultdict(list)
    for grade in grades:
        routing_groups[id(get_content_db(grade))].append(grade)

    for group_grades in routing_groups.values():
        db = get_content_db(group_grades[0])
        offset = 0
        while True:
            try:
                result = (
                    db.table("lesson_cache")
                    .select("board, grade, subject, chapter, mode")
                    .in_("grade", group_grades)
                    .eq("status", "active")
                    .range(offset, offset + PAGE_SIZE - 1)
                    .execute()
                )
            except Exception as exc:
                print(f"  ⚠️  lesson_cache query failed for {group_grades}: {exc}")
                break
            rows = result.data or []
            for row in rows:
                key = (
                    row.get("board") or "CBSE",
                    row.get("grade"),
                    row.get("subject"),
                    row.get("chapter"),
                    row.get("mode") or "CBSE",
                )
                if all(key[1:4]):
                    combos.setdefault(key, {
                        "board": key[0], "grade": key[1], "subject": key[2],
                        "chapter": key[3], "mode": key[4],
                    })
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    return sorted(combos.values(), key=lambda c: (c["grade"], c["subject"], c["chapter"]))


def convert_all(grades: list[str], force: bool, dry_run: bool, limit: int | None) -> list[dict]:
    combos = fetch_cached_chapter_combos(grades)
    if limit:
        combos = combos[:limit]
    print(f"Found {len(combos)} cached chapter combination(s) across {len(grades)} grade(s)\n")

    results = []
    for index, combo in enumerate(combos, 1):
        grade, subject, chapter = combo["grade"], combo["subject"], combo["chapter"]
        label = f"[{index}/{len(combos)}] {grade} · {subject} · {chapter[:48]}"

        step_rows = _fetch_step_rows(
            get_content_db(grade), grade, subject, chapter, combo["mode"]
        )
        expected_steps = len(_get_lesson_steps(grade))
        record = {
            **combo,
            "cached_steps": len(step_rows),
            "expected_steps": expected_steps,
            "milestones": 0,
            "quickchecks": 0,
            "status": "",
        }

        if not force and get_stored_chapter_doc(
            combo["board"], grade, subject, chapter, combo["mode"]
        ):
            record["status"] = "already_stored"
            print(f"  ⏭  SKIP    {label}")
            results.append(record)
            continue

        doc = convert_chapter(combo["board"], grade, subject, chapter, combo["mode"])
        if doc is None:
            record["status"] = "not_convertible"
            print(f"  ❌ FAILED  {label}  ({len(step_rows)} cached step(s))")
            results.append(record)
            continue

        record["milestones"] = len(doc.milestones)
        record["quickchecks"] = sum(
            1 for m in doc.milestones for b in m.blocks if b.type == "quickcheck"
        )

        if dry_run:
            record["status"] = "convertible (dry-run)"
            print(f"  ✅ OK      {label}  ({record['milestones']} milestones, dry-run)")
        elif store_chapter_doc(doc):
            record["status"] = "stored"
            print(f"  ✅ STORED  {label}  ({record['milestones']} milestones)")
        else:
            record["status"] = "store_failed"
            print(f"  ⚠️  NOSTORE {label}  (converted but DB write failed)")

        results.append(record)

    return results


def write_reports(results: list[dict], grades: list[str]) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)

    csv_path = os.path.join(REPORT_DIR, "conversion_report.csv")
    fields = ["grade", "subject", "chapter", "mode", "board",
              "cached_steps", "expected_steps", "milestones", "quickchecks", "status"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in fields} for r in results)

    by_grade: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        by_grade[r["grade"]][r["status"]] += 1
        by_grade[r["grade"]]["total"] += 1

    md_path = os.path.join(REPORT_DIR, "conversion_summary.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Chapter-Doc Conversion Summary\n\nGenerated: {now}\n\n")
        f.write("| Grade | Total | Stored | Already | Not convertible | Store failed |\n")
        f.write("|---|---|---|---|---|---|\n")
        for grade in grades:
            c = by_grade.get(grade, Counter())
            f.write(
                f"| {grade} | {c['total']} | {c['stored'] + c['convertible (dry-run)']} "
                f"| {c['already_stored']} | {c['not_convertible']} | {c['store_failed']} |\n"
            )
        failures = [r for r in results if r["status"] == "not_convertible"]
        if failures:
            f.write("\n## Not convertible (prewarm gap list)\n\n")
            for r in failures:
                f.write(f"- {r['grade']} · {r['subject']} · {r['chapter']} "
                        f"({r['cached_steps']}/{r['expected_steps']} steps cached)\n")

    print(f"\n📄 Report: {csv_path}")
    print(f"📄 Summary: {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-convert cached lessons into chapter docs")
    parser.add_argument("--grade", action="append", help="Limit to grade(s), e.g. --grade 'Grade 6'")
    parser.add_argument("--force", action="store_true", help="Re-convert even if a doc is stored")
    parser.add_argument("--dry-run", action="store_true", help="Convert + report, no DB writes")
    parser.add_argument("--limit", type=int, help="Stop after N chapters (smoke testing)")
    args = parser.parse_args()

    grades = args.grade or ALL_GRADES
    invalid = [g for g in grades if g not in ALL_GRADES]
    if invalid:
        print(f"Unknown grade(s): {invalid}. Valid: {ALL_GRADES}")
        sys.exit(1)

    print("=" * 62)
    print("Likha Poha AI — Batch Chapter-Doc Conversion (zero-token)")
    print(f"Grades: {', '.join(grades)}  force={args.force}  dry_run={args.dry_run}")
    print("=" * 62 + "\n")

    results = convert_all(grades, force=args.force, dry_run=args.dry_run, limit=args.limit)
    write_reports(results, grades)

    totals = Counter(r["status"] for r in results)
    print("\n" + "=" * 62)
    for status, count in totals.most_common():
        print(f"  {status:24s} {count}")
    print("=" * 62)


if __name__ == "__main__":
    main()
