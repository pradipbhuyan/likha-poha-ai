#!/usr/bin/env python3
"""
Lesson Topic Alignment Audit (read-only)
=========================================
Finds lesson_cache chapters whose actual authored content is about a
DIFFERENT topic than the chapter label says -- the exact bug class found
manually in Grade 11 Physics/Chemistry while building the subjective
question bank (e.g. the row labeled "Chapter 8: Mechanical Properties of
Solids" actually contained Gravitation content; "States of Matter"
actually contained Thermodynamics content).

The platform's coverage report (Platform Content Quality report) checks
only whether lesson content EXISTS for a chapter (all 5 steps present),
never whether the content's topic matches its label -- so this class of
bug is invisible to it. This script closes that gap with a direct
LLM-based topic-alignment check, one call per (grade, subject, chapter),
using the admin-configured model via ask_llm() (no model override, so it
always reflects whatever provider/model the admin has active in Admin
Control -- never a hardcoded model).

For each chapter, the FIRST lesson_cache step (by step_title) is used as
the representative sample -- if a chapter's content is wholesale the
wrong topic, the intro step already shows it (confirmed manually against
the 5 known-bad Grade 11 chapters before trusting this approach platform-
wide).

Output:
  reports/lesson_topic_audit/lesson_topic_audit.md
  reports/lesson_topic_audit/lesson_topic_audit.csv

Usage:
    cd backend
    python3 scripts/audit_lesson_topic_alignment.py                    # all grades 5-12
    python3 scripts/audit_lesson_topic_alignment.py --grade "Grade 11" # one grade
    python3 scripts/audit_lesson_topic_alignment.py --grade "Grade 11" --subject Physics
    python3 scripts/audit_lesson_topic_alignment.py --limit 20         # smoke test
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.openai_service import ask_llm  # noqa: E402

GRADES = [f"Grade {n}" for n in range(5, 13)]
MODE = "CBSE"
REQUEST_DELAY_SECONDS = 0.3
EXCERPT_CHARS = 600

SYSTEM_PROMPT = """\
You are a strict content auditor for a CBSE tutoring platform. You will be
given a CHAPTER LABEL (grade, subject, chapter title) and an EXCERPT of
lesson text that is stored in the database under that exact chapter label.

Your only job: judge whether the excerpt's actual subject matter matches
the chapter label's topic. Chapter labels are sometimes wrong -- the
stored text can be authored content for a completely different chapter
(e.g. a chapter labeled "Waves" containing content that is actually about
Oscillations, or a chapter labeled "States of Matter" containing content
that is actually about Thermodynamics). You are checking for exactly this
kind of mislabeling, not grading quality or accuracy.

Return ONLY a single valid JSON object, no markdown fences, no commentary:
{
  "match": true or false,
  "observed_topic": "one short phrase naming the excerpt's actual topic",
  "confidence": "high" | "medium" | "low"
}

match=false means the excerpt is clearly about a different topic than the
chapter label. match=true means the excerpt is consistent with the
chapter label (even if brief, introductory, or only partially covers it).
When uncertain, prefer confidence="low" over guessing match=false.
"""


def fetch_chapters(grade: str, subject: str | None = None) -> list[dict]:
    """One representative row per (subject, chapter): the first lesson_cache
    step alphabetically by step_title, active status only."""
    db = get_content_db(grade)
    q = (
        db.table("lesson_cache")
        .select("subject, chapter, step_title, lesson_content")
        .eq("grade", grade)
        .eq("mode", MODE)
        .eq("status", "active")
    )
    if subject:
        q = q.eq("subject", subject)
    rows = q.order("subject").order("chapter").order("step_title").limit(5000).execute().data or []

    seen = set()
    reps = []
    for r in rows:
        key = (r.get("subject"), r.get("chapter"))
        if key in seen:
            continue
        seen.add(key)
        reps.append(r)
    return reps


def strip_json_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def audit_chapter(grade: str, subject: str, chapter: str, lesson_content: str) -> dict:
    excerpt = (lesson_content or "").strip()[:EXCERPT_CHARS]

    user_prompt = f"""\
CHAPTER LABEL:
Grade: {grade}
Subject: {subject}
Chapter: {chapter}

EXCERPT (first ~{EXCERPT_CHARS} characters of the stored lesson text):
\"\"\"
{excerpt}
\"\"\"

Does the excerpt's topic match the chapter label?
"""

    try:
        raw = ask_llm(
            SYSTEM_PROMPT,
            user_prompt,
            username="content_audit_script",
            feature="content_audit",
        )
        data = json.loads(strip_json_fence(raw))
        match = bool(data.get("match"))
        return {
            "grade": grade,
            "subject": subject,
            "chapter": chapter,
            "status": "MATCH" if match else "MISMATCH",
            "observed_topic": data.get("observed_topic", ""),
            "confidence": data.get("confidence", ""),
            "error": "",
        }
    except json.JSONDecodeError as e:
        return {
            "grade": grade, "subject": subject, "chapter": chapter,
            "status": "ERROR", "observed_topic": "", "confidence": "",
            "error": f"unparseable LLM response: {e}",
        }
    except Exception as e:
        return {
            "grade": grade, "subject": subject, "chapter": chapter,
            "status": "ERROR", "observed_topic": "", "confidence": "",
            "error": str(e),
        }


def write_reports(results: list[dict], out_dir: Path) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mismatches = [r for r in results if r["status"] == "MISMATCH"]
    errors = [r for r in results if r["status"] == "ERROR"]
    matches = [r for r in results if r["status"] == "MATCH"]

    lines = [
        "# Lesson Topic Alignment Audit",
        f"_Generated: {ts}_",
        "",
        "Checks whether each chapter's stored lesson_cache content actually "
        "matches its chapter label, using the admin-configured LLM (via "
        "ask_llm, no hardcoded model). This catches mislabeled content "
        "(e.g. Chapter 8 containing Chapter 7's text) that the platform's "
        "coverage report cannot detect, since coverage only checks "
        "presence/completeness, not topic correctness.",
        "",
        "## Summary",
        "| Status | Count |",
        "|---|---|",
        f"| ✅ MATCH | {len(matches)} |",
        f"| ❌ MISMATCH | {len(mismatches)} |",
        f"| ⚠️ ERROR | {len(errors)} |",
        f"| **Total audited** | **{len(results)}** |",
        "",
        "---",
        "",
        "## Mismatches found",
        "",
    ]

    if not mismatches:
        lines.append("None found. 🎉")
    else:
        lines += ["| Grade | Subject | Chapter (label) | Observed actual topic | Confidence |",
                   "|---|---|---|---|---|"]
        for r in sorted(mismatches, key=lambda x: (x["grade"], x["subject"], x["chapter"])):
            lines.append(
                f"| {r['grade']} | {r['subject']} | {r['chapter']} "
                f"| {r['observed_topic']} | {r['confidence']} |"
            )

    if errors:
        lines += ["", "---", "", "## Errors (could not audit — investigate separately)", ""]
        for r in sorted(errors, key=lambda x: (x["grade"], x["subject"], x["chapter"])):
            lines.append(f"- {r['grade']} / {r['subject']} / {r['chapter']}: {r['error']}")

    lines += ["", "---", "_Generated by audit_lesson_topic_alignment.py_"]

    md_path = out_dir / "lesson_topic_audit.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    csv_path = out_dir / "lesson_topic_audit.csv"
    fields = ["grade", "subject", "chapter", "status", "observed_topic", "confidence", "error"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in fields})

    return md_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit lesson_cache content vs its chapter label")
    parser.add_argument("--grade", default=None, help='e.g. "Grade 11" (default: all Grade 5-12)')
    parser.add_argument("--subject", default=None, help="Filter by subject (requires --grade)")
    parser.add_argument("--output", default="reports/lesson_topic_audit")
    parser.add_argument("--limit", type=int, default=None, help="Cap total chapters audited (smoke test)")
    args = parser.parse_args()

    grades = [args.grade] if args.grade else GRADES

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_chapters: list[tuple[str, dict]] = []
    for grade in grades:
        chapters = fetch_chapters(grade, args.subject)
        print(f"  {grade}: {len(chapters)} chapters found")
        for c in chapters:
            all_chapters.append((grade, c))

    if args.limit:
        all_chapters = all_chapters[: args.limit]

    total = len(all_chapters)
    print(f"\nAuditing {total} chapters via admin-configured LLM...\n")

    results = []
    for i, (grade, row) in enumerate(all_chapters, start=1):
        subject = row.get("subject", "")
        chapter = row.get("chapter", "")
        content = row.get("lesson_content", "")

        result = audit_chapter(grade, subject, chapter, content)
        results.append(result)

        icon = {"MATCH": "✅", "MISMATCH": "❌", "ERROR": "⚠️"}.get(result["status"], "?")
        print(f"  [{i}/{total}] {icon} {grade} / {subject} / {chapter[:50]}"
              + (f"  -> looks like: {result['observed_topic']}" if result["status"] == "MISMATCH" else ""))

        time.sleep(REQUEST_DELAY_SECONDS)

    md_path, csv_path = write_reports(results, out_dir)

    mismatches = sum(1 for r in results if r["status"] == "MISMATCH")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    matches = sum(1 for r in results if r["status"] == "MATCH")

    print()
    print("=" * 60)
    print("  LESSON TOPIC ALIGNMENT AUDIT")
    print("=" * 60)
    print(f"  Total audited : {total}")
    print(f"  ✅ MATCH      : {matches}")
    print(f"  ❌ MISMATCH   : {mismatches}")
    print(f"  ⚠️  ERROR      : {errors}")
    print(f"  Reports in    : {out_dir.resolve()}/")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
