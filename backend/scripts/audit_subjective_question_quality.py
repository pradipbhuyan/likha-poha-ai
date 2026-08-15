#!/usr/bin/env python3
"""
Audit subjective_question_bank for Templated/Ungrounded Questions
=====================================================================
Read-only audit companion to purge_templated_subjective_questions.py.
Scans every grade's subjective_question_bank table and reports which
chapters contain questions that treat internal lesson-authoring markdown
scaffolding (bolded sub-labels, section names like "Section B", "Opening
overview", "Worked example", "Revision and recap") as if it were real
chapter content -- e.g. "Explain the chapter point about Faithfulness and
connect it with another idea from the exam-style activities."

Makes NO changes to the database. Writes a full report to
reports/subjective_question_quality_audit.md (and prints a summary).

Usage:
    cd backend
    python3 scripts/audit_subjective_question_quality.py
    python3 scripts/audit_subjective_question_quality.py --grade "Grade 5"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402

ALL_GRADES = [
    "Grade 5", "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11", "Grade 12",
]

# Same detection patterns as ingest_gpt55_subjective_question_bank_output.py
# and purge_templated_subjective_questions.py -- kept in sync manually.
_TEMPLATE_PHRASE_PATTERN = re.compile(
    r"chapter point about"
    r"|connect it with another idea"
    r"|and show how it connects with the point"
    r"|explained in (?:the )?(?:opening overview|core explanation|"
    r"revision activities|exam-style activities|the revision|the exam)",
    re.IGNORECASE,
)
_SECTION_LABEL_PATTERN = re.compile(
    r"\b(?:section [a-z]|opening overview|core explanation|worked example|"
    r"quick check question|exam-style problems?|revision (?:and )?recap|"
    r"step-by-step breakdown)\b",
    re.IGNORECASE,
)


def _flag_reasons(question_text: str) -> list[str]:
    reasons = []
    if _TEMPLATE_PHRASE_PATTERN.search(question_text):
        reasons.append("templated meta-structure phrase")
    if _SECTION_LABEL_PATTERN.search(question_text):
        reasons.append("references internal section/label name")
    return reasons


def _fetch_all_rows(db, grade: str) -> list[dict]:
    """Paginate past Supabase's 1000-row default page cap."""
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        page = (
            db.table("subjective_question_bank")
            .select("id, subject, chapter, difficulty, question")
            .eq("grade", grade)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        page_rows = page.data or []
        all_rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        offset += page_size
    return all_rows


def audit_grade(grade: str) -> dict:
    db = get_content_db(grade)
    rows = _fetch_all_rows(db, grade)

    total = len(rows)
    flagged_rows = []
    for r in rows:
        reasons = _flag_reasons(r.get("question", ""))
        if reasons:
            flagged_rows.append({**r, "reasons": reasons})

    by_chapter: dict[tuple, dict] = {}
    for r in flagged_rows:
        key = (r.get("subject", ""), r.get("chapter", ""))
        entry = by_chapter.setdefault(key, {"count": 0, "total_in_chapter": 0, "examples": []})
        entry["count"] += 1
        if len(entry["examples"]) < 2:
            entry["examples"].append(r.get("question", "")[:140])

    # total_in_chapter: how many questions this chapter has overall (for context)
    chapter_totals: dict[tuple, int] = {}
    for r in rows:
        key = (r.get("subject", ""), r.get("chapter", ""))
        chapter_totals[key] = chapter_totals.get(key, 0) + 1
    for key, entry in by_chapter.items():
        entry["total_in_chapter"] = chapter_totals.get(key, 0)

    return {
        "grade": grade,
        "total_rows": total,
        "flagged_rows": len(flagged_rows),
        "affected_chapters": by_chapter,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit subjective_question_bank for templated/ungrounded questions (read-only)"
    )
    parser.add_argument("--grade", help='e.g. "Grade 5" — audit a single grade')
    args = parser.parse_args()

    grades = [args.grade] if args.grade else ALL_GRADES

    results = []
    for grade in grades:
        print(f"Scanning {grade} ...")
        results.append(audit_grade(grade))

    # ── Console summary ──────────────────────────────────────────────────
    print(f"\n{'=' * 78}")
    print("  SUBJECTIVE QUESTION QUALITY AUDIT — SUMMARY")
    print(f"{'=' * 78}")
    grand_total = 0
    grand_flagged = 0
    grand_chapters = 0
    for r in results:
        pct = (r["flagged_rows"] / r["total_rows"] * 100) if r["total_rows"] else 0
        print(
            f"  {r['grade']:<10} total={r['total_rows']:<6} "
            f"flagged={r['flagged_rows']:<6} ({pct:.1f}%)  "
            f"chapters_affected={len(r['affected_chapters'])}"
        )
        grand_total += r["total_rows"]
        grand_flagged += r["flagged_rows"]
        grand_chapters += len(r["affected_chapters"])
    overall_pct = (grand_flagged / grand_total * 100) if grand_total else 0
    print(f"{'-' * 78}")
    print(
        f"  {'TOTAL':<10} total={grand_total:<6} flagged={grand_flagged:<6} "
        f"({overall_pct:.1f}%)  chapters_affected={grand_chapters}"
    )

    # ── Markdown report ──────────────────────────────────────────────────
    reports_dir = Path(__file__).resolve().parents[1] / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / "subjective_question_quality_audit.md"

    lines = [
        "# Subjective Question Bank Quality Audit",
        "",
        "Flags questions that treat internal lesson-authoring markdown scaffolding",
        "(bolded sub-labels, section names like 'Section B', 'Opening overview',",
        "'Worked example', 'Revision and recap') as if it were real chapter content,",
        "instead of testing actual facts, characters, events, or concepts from the",
        "chapter/story/poem itself.",
        "",
        "This is a READ-ONLY audit. No rows were modified.",
        "",
        "## Summary",
        "",
        "| Grade | Total Questions | Flagged | % Flagged | Chapters Affected |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        pct = (r["flagged_rows"] / r["total_rows"] * 100) if r["total_rows"] else 0
        lines.append(
            f"| {r['grade']} | {r['total_rows']} | {r['flagged_rows']} | "
            f"{pct:.1f}% | {len(r['affected_chapters'])} |"
        )
    lines.append(
        f"| **TOTAL** | **{grand_total}** | **{grand_flagged}** | "
        f"**{overall_pct:.1f}%** | **{grand_chapters}** |"
    )

    lines.append("")
    lines.append("## Details by Grade / Chapter")
    lines.append("")

    for r in results:
        if not r["affected_chapters"]:
            continue
        lines.append(f"### {r['grade']}")
        lines.append("")
        for (subject, chapter), entry in sorted(r["affected_chapters"].items()):
            lines.append(
                f"- **{subject} / {chapter}** — "
                f"{entry['count']}/{entry['total_in_chapter']} question(s) flagged"
            )
            for ex in entry["examples"]:
                lines.append(f"  - _example:_ \"{ex}...\"")
        lines.append("")

    lines.append("## Recommended Next Steps")
    lines.append("")
    lines.append(
        "1. Review the flagged chapters above. For each affected chapter, run:\n"
        "   ```\n"
        "   python3 scripts/purge_templated_subjective_questions.py --grade \"<grade>\" --dry-run\n"
        "   python3 scripts/purge_templated_subjective_questions.py --grade \"<grade>\"\n"
        "   ```\n"
        "2. Re-author the affected chapter(s) using the now-fixed prompt template:\n"
        "   ```\n"
        "   python3 scripts/prepare_gpt55_subjective_question_prompts.py --grade \"<grade>\" "
        "--subject \"<subject>\" --chapters \"<chapter>\"\n"
        "   ```\n"
        "3. Paste into a fresh GPT-5.5 session, save the JSON, then ingest:\n"
        "   ```\n"
        "   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir <folder> --dry-run\n"
        "   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir <folder>\n"
        "   ```\n"
        "   The updated ingest script now automatically rejects any question matching\n"
        "   this same bad pattern, so a re-authored batch cannot silently reintroduce it."
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nFull report written to: {report_path}\n")


if __name__ == "__main__":
    main()
