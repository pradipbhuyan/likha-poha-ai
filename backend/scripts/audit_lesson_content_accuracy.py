#!/usr/bin/env python3
"""
Comprehensive Lesson Content Accuracy Audit (read-only)
=========================================================
A deeper follow-up to audit_lesson_topic_alignment.py. That script only
checked whether a chapter's FIRST step matched its chapter label (a coarse
excerpt-based topic classifier). This script reads a chapter's FULL content
-- all 5 lesson_cache steps (Concept introduction, Core explanation, Worked
examples, Exam-style problems, Revision and recap) -- against that
chapter's own RAG-sourced textbook text, and asks the admin-configured LLM
(via ask_llm, no hardcoded/overridden model) to review it the way a careful
human fact-checker would: flagging unsupported claims, fabricated numbers/
data not present in the source, arithmetic errors in worked examples,
internal inconsistencies between steps, and topic mismatches.

One call per chapter (all 5 steps + RAG source reviewed together, so the
model can cross-check consistency between steps and so the RAG source
context is only sent once per chapter rather than 5x).

Output:
  reports/lesson_accuracy_audit/lesson_accuracy_audit.md
  reports/lesson_accuracy_audit/lesson_accuracy_audit_issues.csv   (one row per issue)
  reports/lesson_accuracy_audit/lesson_accuracy_audit_chapters.csv (one row per chapter)

Usage:
    cd backend
    python3 scripts/audit_lesson_content_accuracy.py                    # all grades 5-12
    python3 scripts/audit_lesson_content_accuracy.py --grade "Grade 11"
    python3 scripts/audit_lesson_content_accuracy.py --grade "Grade 11" --subject Physics
    python3 scripts/audit_lesson_content_accuracy.py --limit 10         # smoke test
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
from scripts.audit_lesson_vs_rag import fetch_rag_chunks_for_chapter  # noqa: E402

GRADES = [f"Grade {n}" for n in range(5, 13)]
MODE = "CBSE"
REQUEST_DELAY_SECONDS = 0.3
MAX_SOURCE_CHARS = 10_000   # cap RAG source text sent per chapter (bound prompt size/cost)
MAX_STEP_CHARS = 4_000      # cap each individual step's content sent (bound prompt size/cost)

SYSTEM_PROMPT = """\
You are a meticulous CBSE subject-matter fact-checker, reading a chapter's
lesson content the way a careful human teacher would -- line by line,
checking every claim.

You will be given:
  - SOURCE_TEXT: the chapter's real textbook content (ground truth).
  - Up to 5 LESSON STEPS: the platform's authored teaching content for this
    chapter, which is supposed to be grounded in SOURCE_TEXT.

For EACH lesson step, carefully check for:
  1. UNSUPPORTED_CLAIM -- a factual statement, definition, or claim not
     supported by (or contradicting) SOURCE_TEXT. Well-known universal
     facts/constants (e.g. speed of light, basic arithmetic) that any
     qualified teacher would treat as textbook-level common knowledge are
     fine even if not verbatim in SOURCE_TEXT -- only flag claims that are
     actually wrong or clearly fabricated/invented, not just "not verbatim
     in the excerpt."
  2. FABRICATED_NUMBER -- a specific number, quantity, date, or data point
     used in an explanation or worked example that does not appear in
     SOURCE_TEXT and is not a well-known constant.
  3. ARITHMETIC_ERROR -- a worked example whose stated calculation or final
     answer is mathematically wrong given its own stated inputs.
  4. TOPIC_MISMATCH -- this step's content is substantively about a
     DIFFERENT chapter/topic than the given chapter label, not just this
     specific chapter's material.
  5. INCONSISTENCY -- this step contradicts another step in the same
     chapter (e.g. different numbers for the same quantity).

Only flag genuine problems. Do not flag stylistic choices, simplification
for a school grade level, or claims that are merely brief/incomplete but
not wrong. When uncertain whether something is truly an error, use
severity "low" rather than omitting it or inflating it to "high".

Return ONLY a single valid JSON object, no markdown fences, no commentary:
{
  "steps": {
    "<step_title>": {
      "topic_match": true or false,
      "issues": [
        {"type": "UNSUPPORTED_CLAIM"|"FABRICATED_NUMBER"|"ARITHMETIC_ERROR"|"TOPIC_MISMATCH"|"INCONSISTENCY",
         "severity": "high"|"medium"|"low",
         "quote": "<short exact quote from the step showing the issue>",
         "problem": "<one sentence explaining what's wrong>"}
      ]
    }
  }
}
If a step has no issues, return "issues": [].
"""


def fetch_chapters(grade: str, subject: str | None = None) -> dict[tuple, list[dict]]:
    """Return {(subject, chapter): [step_rows...]} for every active chapter."""
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
    rows = q.order("subject").order("chapter").order("step_title").limit(6000).execute().data or []

    chapters: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (r.get("subject"), r.get("chapter"))
        chapters.setdefault(key, []).append(r)
    return chapters


def strip_json_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def build_prompt(grade: str, subject: str, chapter: str, source_text: str, steps: list[dict]) -> str:
    source_excerpt = source_text.strip()[:MAX_SOURCE_CHARS]
    if not source_excerpt:
        source_excerpt = "(No RAG source text available for this chapter -- review for internal consistency, fabricated-looking numbers, and arithmetic only; do not flag TOPIC_MISMATCH or UNSUPPORTED_CLAIM based on source comparison.)"

    steps_block = []
    for s in steps:
        content = (s.get("lesson_content") or "").strip()[:MAX_STEP_CHARS]
        steps_block.append(f"--- STEP: {s.get('step_title')} ---\n{content}")

    return f"""\
CHAPTER LABEL: {grade} / {subject} / {chapter}

SOURCE_TEXT:
\"\"\"
{source_excerpt}
\"\"\"

LESSON STEPS:
{chr(10).join(steps_block)}

Review every step as described in your instructions and return the JSON object.
"""


def audit_chapter(grade: str, subject: str, chapter: str, source_text: str, steps: list[dict]) -> dict:
    prompt = build_prompt(grade, subject, chapter, source_text, steps)
    try:
        raw = ask_llm(
            SYSTEM_PROMPT,
            prompt,
            username="content_audit_script",
            feature="content_audit",
        )
        data = json.loads(strip_json_fence(raw))
        return {"status": "OK", "steps": data.get("steps", {}), "error": ""}
    except json.JSONDecodeError as e:
        return {"status": "ERROR", "steps": {}, "error": f"unparseable LLM response: {e}"}
    except Exception as e:
        return {"status": "ERROR", "steps": {}, "error": str(e)}


def write_reports(chapter_results: list[dict], out_dir: Path) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    all_issues = []
    for cr in chapter_results:
        for step_title, step_data in cr.get("steps", {}).items():
            for issue in step_data.get("issues", []):
                all_issues.append({
                    "grade": cr["grade"], "subject": cr["subject"], "chapter": cr["chapter"],
                    "step": step_title, "type": issue.get("type", ""),
                    "severity": issue.get("severity", ""), "quote": issue.get("quote", ""),
                    "problem": issue.get("problem", ""),
                })

    high = [i for i in all_issues if i["severity"] == "high"]
    medium = [i for i in all_issues if i["severity"] == "medium"]
    low = [i for i in all_issues if i["severity"] == "low"]
    errors = [cr for cr in chapter_results if cr["status"] == "ERROR"]
    clean_chapters = sum(
        1 for cr in chapter_results
        if cr["status"] == "OK" and not any(
            step_data.get("issues") for step_data in cr.get("steps", {}).values()
        )
    )

    lines = [
        "# Comprehensive Lesson Content Accuracy Audit",
        f"_Generated: {ts}_",
        "",
        "Reads all 5 lesson_cache steps per chapter against that chapter's RAG-sourced "
        "textbook text, using the admin-configured LLM to fact-check line by line: "
        "unsupported claims, fabricated numbers, arithmetic errors, topic mismatches, "
        "and cross-step inconsistencies.",
        "",
        "## Summary",
        "| Metric | Count |",
        "|---|---|",
        f"| Chapters audited | {len(chapter_results)} |",
        f"| Chapters with zero flagged issues | {clean_chapters} |",
        f"| Chapters that errored (could not audit) | {len(errors)} |",
        f"| 🔴 High severity issues | {len(high)} |",
        f"| 🟠 Medium severity issues | {len(medium)} |",
        f"| ⚪ Low severity issues | {len(low)} |",
        f"| **Total issues** | **{len(all_issues)}** |",
        "",
        "---",
        "",
        "## High severity issues",
        "",
    ]

    if not high:
        lines.append("None found. 🎉")
    else:
        for i in sorted(high, key=lambda x: (x["grade"], x["subject"], x["chapter"], x["step"])):
            lines.append(f"### {i['grade']} / {i['subject']} / {i['chapter']} — {i['step']}")
            lines.append(f"- **Type:** {i['type']}")
            lines.append(f"- **Quote:** \"{i['quote']}\"")
            lines.append(f"- **Problem:** {i['problem']}")
            lines.append("")

    lines += ["---", "", "## Medium severity issues", ""]
    if not medium:
        lines.append("None found.")
    else:
        for i in sorted(medium, key=lambda x: (x["grade"], x["subject"], x["chapter"], x["step"])):
            lines.append(f"- **{i['grade']} / {i['subject']} / {i['chapter']} — {i['step']}** "
                         f"[{i['type']}]: \"{i['quote']}\" — {i['problem']}")

    if errors:
        lines += ["", "---", "", "## Chapters that errored (could not audit)", ""]
        for cr in errors:
            lines.append(f"- {cr['grade']} / {cr['subject']} / {cr['chapter']}: {cr['error']}")

    lines += ["", "---",
               "_Low-severity issues are omitted from this report for readability — see the CSV for the full list._",
               "_Generated by audit_lesson_content_accuracy.py_"]

    (out_dir / "lesson_accuracy_audit.md").write_text("\n".join(lines), encoding="utf-8")

    issues_csv = out_dir / "lesson_accuracy_audit_issues.csv"
    with open(issues_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["grade", "subject", "chapter", "step", "type", "severity", "quote", "problem"])
        w.writeheader()
        for i in all_issues:
            w.writerow(i)

    chapters_csv = out_dir / "lesson_accuracy_audit_chapters.csv"
    with open(chapters_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["grade", "subject", "chapter", "status", "issue_count", "high_count", "error"])
        w.writeheader()
        for cr in chapter_results:
            issue_count = sum(len(sd.get("issues", [])) for sd in cr.get("steps", {}).values())
            high_count = sum(
                1 for sd in cr.get("steps", {}).values()
                for iss in sd.get("issues", []) if iss.get("severity") == "high"
            )
            w.writerow({
                "grade": cr["grade"], "subject": cr["subject"], "chapter": cr["chapter"],
                "status": cr["status"], "issue_count": issue_count, "high_count": high_count,
                "error": cr.get("error", ""),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprehensive per-chapter lesson content accuracy audit")
    parser.add_argument("--grade", default=None, help='e.g. "Grade 11" (default: all Grade 5-12)')
    parser.add_argument("--subject", default=None, help="Filter by subject (requires --grade)")
    parser.add_argument("--output", default="reports/lesson_accuracy_audit")
    parser.add_argument("--limit", type=int, default=None, help="Cap total chapters audited (smoke test)")
    args = parser.parse_args()

    grades = [args.grade] if args.grade else GRADES

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_chapters: list[tuple[str, str, str, list[dict]]] = []
    for grade in grades:
        chapters = fetch_chapters(grade, args.subject)
        print(f"  {grade}: {len(chapters)} chapters found")
        for (subject, chapter), steps in chapters.items():
            all_chapters.append((grade, subject, chapter, steps))

    if args.limit:
        all_chapters = all_chapters[: args.limit]

    total = len(all_chapters)
    print(f"\nAuditing {total} chapters (full content, all steps) via admin-configured LLM...\n")

    results = []
    rag_cache: dict[tuple, str] = {}

    for i, (grade, subject, chapter, steps) in enumerate(all_chapters, start=1):
        try:
            rag_key = (grade, subject, chapter)
            if rag_key not in rag_cache:
                chunks = []
                for attempt in range(3):
                    try:
                        chunks = fetch_rag_chunks_for_chapter(grade, subject, chapter)
                        break
                    except Exception as e:
                        if attempt == 2:
                            print(f"  [warn] RAG fetch failed for {grade}/{subject}/{chapter[:40]} "
                                  f"after 3 attempts ({e}) — auditing without source text")
                        else:
                            time.sleep(2)
                rag_cache[rag_key] = " ".join(c.get("chunk_text", "") for c in chunks)
            source_text = rag_cache[rag_key]

            result = audit_chapter(grade, subject, chapter, source_text, steps)
            result.update({"grade": grade, "subject": subject, "chapter": chapter})
        except Exception as e:
            result = {"status": "ERROR", "steps": {}, "error": f"unexpected: {e}",
                      "grade": grade, "subject": subject, "chapter": chapter}

        results.append(result)

        issue_count = sum(len(sd.get("issues", [])) for sd in result.get("steps", {}).values())
        icon = "⚠️" if result["status"] == "ERROR" else ("❌" if issue_count else "✅")
        print(f"  [{i}/{total}] {icon} {grade} / {subject} / {chapter[:45]}"
              + (f"  -> {issue_count} issue(s)" if issue_count else ""))

        time.sleep(REQUEST_DELAY_SECONDS)

        if i % 10 == 0:
            write_reports(results, out_dir)

    write_reports(results, out_dir)

    all_issues_count = sum(
        len(sd.get("issues", [])) for r in results for sd in r.get("steps", {}).values()
    )
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print()
    print("=" * 60)
    print("  COMPREHENSIVE LESSON CONTENT ACCURACY AUDIT")
    print("=" * 60)
    print(f"  Chapters audited : {total}")
    print(f"  Total issues     : {all_issues_count}")
    print(f"  Errors           : {errors}")
    print(f"  Reports in       : {out_dir.resolve()}/")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
