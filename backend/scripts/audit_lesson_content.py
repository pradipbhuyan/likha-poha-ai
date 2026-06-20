#!/usr/bin/env python3
"""
Lesson Content Audit Script
============================
Validates every lesson_cache entry for content quality issues.

Usage:
    # Run audit only (no fixes)
    cd backend && python3 scripts/audit_lesson_content.py

    # Run audit and auto-mark stale entries that can be fixed
    python3 scripts/audit_lesson_content.py --fix

    # Run audit, fix, then re-run to verify
    python3 scripts/audit_lesson_content.py --fix --rerun

    # Filter to specific grade
    python3 scripts/audit_lesson_content.py --grade "Grade 6"

    # Compare with a previous report to see what changed
    python3 scripts/audit_lesson_content.py --diff reports/audit_2026-06-19_10-00.json

Output:
    reports/audit_YYYY-MM-DD_HH-MM.json  -- machine-readable defect list
    reports/audit_YYYY-MM-DD_HH-MM.txt   -- human-readable summary

Defect types:
    INCOMPLETE_QUESTION    "Question:" label has data but no task instruction
    TRUNCATED_CONTENT      Lesson content ends mid-sentence
    MISSING_WORKED_EXAMPLE No "Worked example" section found
    MISSING_QUICK_CHECK    No "Quick check question" section found
    MISSING_SUMMARY        No "Summary" section found
    CONTROL_CHARS          Non-printable characters found in content
    TOO_SHORT              Content < 400 chars (likely generation failure)
    INCOMPLETE_WORKED_STEP A step inside Worked example ends mid-sentence
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running from the backend directory or project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.services.auth_service import admin_client  # noqa: E402


# ---------------------------------------------------------------------------
# Quality rules
# ---------------------------------------------------------------------------

TASK_VERB_PATTERN = re.compile(
    r"\b(draw|find|calculate|represent|construct|solve|compute|create|make|show|"
    r"determine|identify|list|write|plot|prepare|arrange|organise|organize|describe|"
    r"state|explain|using the data|use the data|what is|how many|how much|which|"
    r"compare|prove|verify|convert|simplify|evaluate|expand|factorise|factorize|"
    r"fill|complete|match|classify|label|shade|measure|estimate|approximate|"
    r"justify|define|give|name|suggest|predict|comment|summarise|summarize|"
    # English / humanities verbs
    r"rewrite|read|answer|analyse|analyze|discuss|interpret|examine|assess|"
    r"how|why|what|who|when|where|based on|refer to|support your|"
    r"translate|paraphrase|annotate|infer|deduce|contrast|highlight|"
    r"summarize|narrate|compose|draft|edit|correct|rearrange|sequence)\b",
    re.IGNORECASE,
)

SECTION_PATTERNS = {
    "worked_example": re.compile(r"(?i)\bworked\s+example\b"),
    "quick_check":    re.compile(r"(?i)\bquick\s+check\b"),
    "summary":        re.compile(r"(?i)\bsummary\b"),
}

# Characters that are not ordinary text or standard whitespace/Unicode
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def check_incomplete_question(content):
    """Return defect message if Worked example Question: has no task verb."""
    q_match = re.search(
        r"(?i)\bquestion\b\s*:\s*(.+?)(?=step\s*\d+\s*:|$)",
        content,
        re.DOTALL,
    )
    if not q_match:
        return None
    question_text = q_match.group(1).strip()[:400]
    if not TASK_VERB_PATTERN.search(question_text):
        preview = question_text[:120].replace("\n", " ")
        return "'Question:' has no task instruction. Preview: <<{}>>".format(preview)
    return None


def check_truncated_content(content):
    """Return defect if content ends abruptly (very short last line, no punctuation)."""
    if not content:
        return "Empty content"
    last_line = content.rstrip().split("\n")[-1].strip()
    if last_line and 3 < len(last_line) < 40:
        if not re.search(r'[.!?)\]"\u201d\u00bb]$', last_line):
            return "Content may be truncated — last line: <<{}>>".format(last_line)
    return None


def check_control_chars(content):
    """Return defect if non-printable ASCII control characters are present."""
    bad = CONTROL_CHAR_PATTERN.findall(content)
    if bad:
        codes = sorted({hex(ord(c)) for c in bad})
        return "Non-printable chars found: {}".format(codes)
    return None


def check_too_short(content):
    """Return defect if content is suspiciously short."""
    length = len(content or "")
    if length < 400:
        return "Content only {} chars — possible generation failure".format(length)
    return None


def check_missing_section(content, section):
    """Return defect if a required section heading is absent."""
    if not SECTION_PATTERNS[section].search(content):
        return "Missing '{}' section".format(section.replace("_", " "))
    return None


def check_worked_step_truncation(content):
    """
    Return defect if a step inside the Worked example ends mid-sentence.

    False-positive guard: skip lines that are:
    - Bullet/list items  (start with - * + or a number+dot)
    - Data table rows    (contain : or →)
    - Single-word lines  (< 10 chars — too short to judge)
    These patterns legitimately end without sentence-final punctuation.
    """
    steps = re.findall(
        r"(?i)step\s*\d+\s*:.*?(?=step\s*\d+\s*:|##|\Z)",
        content,
        re.DOTALL,
    )
    for step in steps:
        last = step.rstrip().split("\n")[-1].strip()
        if not last or len(last) < 10 or len(last) >= 60:
            continue
        # Skip list items, data rows, table entries — these never end with "."
        if re.match(r"^[-*+]", last):          # bullet point
            continue
        if re.match(r"^\d+[.)]\s", last):       # numbered list item
            continue
        if "→" in last or ":" in last:          # data/table row
            continue
        if not re.search(r'[.!?)\]"\u201d]$', last):
            return "Step appears truncated — ends: <<{}>>".format(last)
    return None


ALL_CHECKS = [
    ("INCOMPLETE_QUESTION",    check_incomplete_question),
    ("TRUNCATED_CONTENT",      check_truncated_content),
    ("CONTROL_CHARS",          check_control_chars),
    ("TOO_SHORT",              check_too_short),
    ("MISSING_WORKED_EXAMPLE", lambda c: check_missing_section(c, "worked_example")),
    ("MISSING_QUICK_CHECK",    lambda c: check_missing_section(c, "quick_check")),
    ("MISSING_SUMMARY",        lambda c: check_missing_section(c, "summary")),
    ("INCOMPLETE_WORKED_STEP", check_worked_step_truncation),
]


# ---------------------------------------------------------------------------
# Audit engine
# ---------------------------------------------------------------------------

def load_all_active_lessons(grade_filter=None):
    """
    Fetch all active lesson_cache rows, paginating in 1000-row chunks to
    bypass the Supabase default row limit.
    """
    FIELDS = "id, grade, subject, chapter, step_title, mode, board, status, lesson_content, created_at"
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        query = (
            admin_client.table("lesson_cache")
            .select(FIELDS)
            .eq("status", "active")
        )
        if grade_filter:
            query = query.eq("grade", grade_filter)
        result = (
            query
            .order("grade")
            .order("subject")
            .order("chapter")
            .order("step_title")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        page = result.data or []
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def audit_lessons(rows):
    """Run all quality checks against every row. Returns list of defects."""
    defects = []
    for row in rows:
        content = row.get("lesson_content") or ""
        for defect_type, check_fn in ALL_CHECKS:
            message = check_fn(content)
            if message:
                defects.append({
                    "id":          row["id"],
                    "grade":       row["grade"],
                    "subject":     row["subject"],
                    "chapter":     row["chapter"],
                    "step_title":  row["step_title"],
                    "mode":        row.get("mode", "CBSE"),
                    "defect_type": defect_type,
                    "message":     message,
                    "created_at":  row.get("created_at", ""),
                })
    return defects


def apply_fixes(defects, dry_run=False):
    """Mark defective lesson_cache entries stale so they regenerate on next access."""
    stale_ids = list({d["id"] for d in defects})
    if not stale_ids:
        return 0
    if dry_run:
        print("  [DRY RUN] Would mark {} entries stale".format(len(stale_ids)))
        return len(stale_ids)
    result = (
        admin_client.table("lesson_cache")
        .update({"status": "stale"})
        .in_("id", stale_ids)
        .execute()
    )
    return len(result.data or [])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def save_report(defects, run_label, reports_dir):
    """Save JSON and text reports. Returns (json_path, txt_path)."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    json_path = reports_dir / "audit_{}.json".format(ts)
    txt_path  = reports_dir / "audit_{}.txt".format(ts)

    # ── JSON report ───────────────────────────────────────────────────────
    by_type  = {}
    by_grade = {}
    for d in defects:
        by_type[d["defect_type"]]  = by_type.get(d["defect_type"], 0) + 1
        by_grade[d["grade"]]       = by_grade.get(d["grade"], 0) + 1

    report = {
        "run_label":       run_label,
        "generated_at":    datetime.now().isoformat(),
        "total_defects":   len(defects),
        "defects_by_type": by_type,
        "defects_by_grade": by_grade,
        "defects":         defects,
    }
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    # ── Text report ───────────────────────────────────────────────────────
    lines = [
        "Lesson Content Audit — {}".format(run_label),
        "Generated: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")),
        "Total defects: {}".format(len(defects)),
        "",
        "── By defect type ──",
    ]
    for dtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append("  {:<30} {:>4}".format(dtype, count))
    lines += ["", "── By grade ──"]
    for grade, count in sorted(by_grade.items()):
        lines.append("  {:<12} {:>4} defects".format(grade, count))
    lines += ["", "── Defect details ──", ""]
    prev_grade = None
    for d in defects:
        if d["grade"] != prev_grade:
            lines.append("\n" + "=" * 60)
            lines.append("  " + d["grade"])
            lines.append("=" * 60)
            prev_grade = d["grade"]
        lines.append(
            "  [{}]\n  {} > {} > {}\n  {}\n".format(
                d["defect_type"],
                d["subject"],
                d["chapter"],
                d["step_title"],
                d["message"],
            )
        )
    txt_path.write_text("\n".join(lines))
    return json_path, txt_path


def diff_reports(current_defects, prev_path):
    """Return (new_defects, fixed_defects) comparing with a previous JSON report."""
    prev_data = json.loads(Path(prev_path).read_text())
    prev_keys = {(d["id"], d["defect_type"]) for d in prev_data.get("defects", [])}
    curr_keys = {(d["id"], d["defect_type"]) for d in current_defects}
    new_defects  = [d for d in current_defects            if (d["id"], d["defect_type"]) not in prev_keys]
    fixed        = [d for d in prev_data.get("defects", []) if (d["id"], d["defect_type"]) not in curr_keys]
    return new_defects, fixed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_separator(char="=", width=60):
    print(char * width)


def main():
    parser = argparse.ArgumentParser(description="Audit lesson_cache content quality")
    parser.add_argument("--fix",     action="store_true", help="Mark defective entries stale (triggers LLM regeneration on next access)")
    parser.add_argument("--rerun",   action="store_true", help="After fixing, re-run the audit to measure improvement")
    parser.add_argument("--grade",   default=None, help="Limit audit to one grade, e.g. 'Grade 6'")
    parser.add_argument("--diff",    default=None, help="Path to previous JSON report to compare against")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without writing to DB")
    args = parser.parse_args()

    reports_dir = Path(__file__).parent.parent / "reports"
    label = "Audit-only"
    if args.fix:
        label = "With auto-fix"
    if args.grade:
        label += " | {}".format(args.grade)

    print("\n" + "=" * 60)
    print("  Lesson Content Quality Audit")
    print("  {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("=" * 60)

    # ── Pass 1 ────────────────────────────────────────────────────────────
    filter_msg = " for " + args.grade if args.grade else " (all grades)"
    print("\n[1/3] Loading lesson_cache{}...".format(filter_msg))
    rows = load_all_active_lessons(args.grade)
    print("      {} active entries loaded".format(len(rows)))

    print("\n[2/3] Running {} quality checks on {} entries...".format(len(ALL_CHECKS), len(rows)))
    t0 = time.time()
    defects = audit_lessons(rows)
    elapsed = time.time() - t0
    print("      {} defects found in {:.1f}s".format(len(defects), elapsed))

    # ── Diff against previous report ──────────────────────────────────────
    if args.diff:
        new_defects, fixed = diff_reports(defects, args.diff)
        print("\n  Compared with: {}".format(args.diff))
        print("  NEW defects since last run : {}".format(len(new_defects)))
        print("  FIXED since last run       : {}".format(len(fixed)))

    # ── Print summary ─────────────────────────────────────────────────────
    by_type  = {}
    by_grade = {}
    for d in defects:
        by_type[d["defect_type"]]  = by_type.get(d["defect_type"], 0) + 1
        by_grade[d["grade"]]       = by_grade.get(d["grade"], 0) + 1

    print("\n  Defects by type:")
    for dtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print("    {:<30} {}".format(dtype, count))
    print("\n  Defects by grade:")
    for grade, count in sorted(by_grade.items()):
        print("    {:<14} {}".format(grade, count))

    # ── Save report ───────────────────────────────────────────────────────
    print("\n[3/3] Saving reports to {}...".format(reports_dir))
    json_path, txt_path = save_report(defects, label, reports_dir)
    print("      JSON: {}".format(json_path))
    print("      TEXT: {}".format(txt_path))

    # ── Apply fixes ───────────────────────────────────────────────────────
    if args.fix and defects:
        print("\n[FIX] Marking {} unique lesson entries as stale...".format(
            len({d["id"] for d in defects})
        ))
        fixed_count = apply_fixes(defects, dry_run=getattr(args, "dry_run", False))
        print("      {} entries marked stale — will regenerate on next student visit".format(fixed_count))

        if args.rerun:
            print("\n[RERUN] Waiting 3 seconds then re-auditing...")
            time.sleep(3)
            rows2 = load_all_active_lessons(args.grade)
            defects2 = audit_lessons(rows2)
            label2 = label.replace("With auto-fix", "Post-fix verification")
            json2, txt2 = save_report(defects2, label2, reports_dir)
            new_d, fixed_d = diff_reports(defects2, json_path)
            print("\n  Post-fix results:")
            print("    Before : {} defects".format(len(defects)))
            print("    After  : {} defects".format(len(defects2)))
            print("    Fixed  : {}".format(len(fixed_d)))
            print("    New    : {}".format(len(new_d)))
            print("    Report : {}".format(txt2))

    print("\nDone.\n")


if __name__ == "__main__":
    main()
