#!/usr/bin/env python3
"""
Lesson KB Quality Auditor
=========================
Scans the `lesson_kb` table (pre-generated "Ask about this chapter" chips
shown on the student lesson page, one set per grade/subject/chapter/step)
for garbled/corrupted answer text — specifically the repeated-substring
duplication pattern seen in bad PDF-extraction output, e.g.:

    "U UU UUNDERSTNDERSTNDERST NDERSTNDERST ANDING ANDINGANDING"

which is a mangled, duplicated rendering of a normal word/phrase.

READ-ONLY: This script makes NO changes to the database. It only reports.

Usage:
    cd backend
    python3 scripts/audit_doubt_kb_quality.py
    python3 scripts/audit_doubt_kb_quality.py --grade "Grade 10" --subject "Social Science"
    python3 scripts/audit_doubt_kb_quality.py --output reports/lesson_kb_quality

Detection heuristics (a row is flagged if ANY fire):
  1. overlapping-substring duplication: a run of 3+ letters immediately
     repeated one or more times, e.g. "NDERSTNDERST", "CONOMICCONOMIC"
  2. low character-level compression ratio (zlib) vs answer length — highly
     repetitive text compresses far better than normal prose
  3. digit/word noise fragments typical of broken page-footer text, e.g.
     bare page numbers glued into prose ("74 7474 7474")
  4. excessive single/double-letter "word" tokens ("U UU E E E E D D D D")

Output:
    reports/lesson_kb_quality/flagged_rows.json
    reports/lesson_kb_quality/flagged_rows.csv
    reports/lesson_kb_quality/summary.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

DUP_SUBSTR_RE = re.compile(r"([A-Za-z]{5,})\1+")
WORD_REPEAT_RE = re.compile(r"\b(\w+(?:\s\w+){0,2})\b(?:\s+\1\b){2,}", re.IGNORECASE)
PAGE_NUMBER_NOISE_RE = re.compile(r"\b\d{1,4}\s+\d{2,4}\s+\d{2,4}\b")
SHORT_TOKEN_RUN_RE = re.compile(r"(?:\b[A-Za-z]{1,2}\b\s+){6,}")

PAGE_SIZE = 1000


def fetch_all_active_rows(client, grade: str | None, subject: str | None) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        q = (
            client.table("lesson_kb")
            .select("id, grade, subject, chapter, step_title, question, answer, status, created_at")
            .eq("status", "active")
        )
        if grade:
            q = q.eq("grade", grade)
        if subject:
            q = q.eq("subject", subject)
        res = q.range(start, start + PAGE_SIZE - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return rows


def compression_ratio(text: str) -> float:
    """Lower ratio = more repetitive/compressible than normal prose (~0.35-0.55)."""
    if len(text) < 40:
        return 1.0
    raw = text.encode("utf-8", errors="ignore")
    compressed = zlib.compress(raw, level=9)
    return len(compressed) / len(raw)


def detect_issues(answer: str) -> list[str]:
    """Return issue tags only for answers that look genuinely corrupted.

    Individual heuristics are noisy on their own (real words can contain
    short repeated syllables, e.g. "testes", "silsila", "possess"; maths
    prose legitimately strings together single-letter variables). So a
    long (>=6 char) duplicated run is treated as strong signal by itself;
    everything else only counts when corroborated by a second signal.
    """
    weak = []
    strong = []

    dup_matches = DUP_SUBSTR_RE.findall(answer)
    if dup_matches:
        if any(len(m) >= 6 for m in dup_matches):
            strong.append(f"duplicated_substrings:{dup_matches[:5]}")
        else:
            weak.append(f"duplicated_substrings:{dup_matches[:5]}")

    # Single/double-char repeats are common in maths/physics notation
    # ("n n n", "0 1 1 0", summation indices) — only count as strong signal
    # when the repeated unit is a real word/token (3+ chars).
    word_repeat_matches = [m for m in WORD_REPEAT_RE.findall(answer) if len(m.strip()) >= 3]
    if word_repeat_matches:
        strong.append(f"repeated_phrase:{word_repeat_matches[:5]}")

    if PAGE_NUMBER_NOISE_RE.search(answer):
        weak.append("page_number_noise")

    short_runs = SHORT_TOKEN_RUN_RE.findall(answer)
    if short_runs:
        weak.append(f"short_token_run_x{len(short_runs)}")

    ratio = compression_ratio(answer)
    if ratio < 0.25:
        weak.append(f"low_compression_ratio:{ratio:.2f}")

    if strong:
        return strong + weak
    if len(weak) >= 2:
        return weak
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grade", default=None, help='e.g. "Grade 10"')
    ap.add_argument("--subject", default=None, help='e.g. "Social Science"')
    ap.add_argument("--output", default="reports/lesson_kb_quality")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching active doubt_kb rows (grade={args.grade!r}, subject={args.subject!r})...")
    rows = fetch_all_active_rows(admin_client, args.grade, args.subject)
    # Exemplar chapters are descoped from all grades — not shown on the live
    # platform — so their cards don't need fixing even if flagged.
    before = len(rows)
    rows = [r for r in rows if "exemplar" not in (r.get("chapter") or "").lower()]
    print(f"Fetched {before} rows ({before - len(rows)} Exemplar rows excluded — descoped, not live). Scanning...")

    flagged = []
    by_chapter: dict[tuple, list] = defaultdict(list)

    for row in rows:
        answer = row.get("answer") or ""
        issues = detect_issues(answer)
        if issues:
            entry = {
                "id": row["id"],
                "grade": row.get("grade"),
                "subject": row.get("subject"),
                "chapter": row.get("chapter"),
                "step_title": row.get("step_title"),
                "question": row.get("question"),
                "answer_preview": answer[:300],
                "issues": issues,
            }
            flagged.append(entry)
            by_chapter[(row.get("grade"), row.get("subject"), row.get("chapter"))].append(entry)

    (out_dir / "flagged_rows.json").write_text(json.dumps(flagged, indent=2, default=str))

    with (out_dir / "flagged_rows.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "grade", "subject", "chapter", "step_title", "question", "issues", "answer_preview"])
        for e in flagged:
            w.writerow([e["id"], e["grade"], e["subject"], e["chapter"], e["step_title"], e["question"],
                        "; ".join(e["issues"]), e["answer_preview"]])

    lines = [
        "# Lesson KB Quality Audit",
        "",
        f"Run at: {datetime.now(timezone.utc).isoformat()}",
        f"Rows scanned: {len(rows)}",
        f"Rows flagged: {len(flagged)}",
        "",
        "## Affected chapters",
        "",
    ]
    for (grade, subject, chapter), entries in sorted(by_chapter.items(), key=lambda kv: (-len(kv[1]),)):
        lines.append(f"- **{grade} / {subject} / {chapter}** — {len(entries)} flagged row(s)")
        for e in entries[:5]:
            lines.append(f"  - `{e['id']}` — {e['question']!r} — issues: {e['issues']}")
        if len(entries) > 5:
            lines.append(f"  - ...and {len(entries) - 5} more")
    (out_dir / "summary.md").write_text("\n".join(lines))

    print(f"\nFlagged {len(flagged)} / {len(rows)} rows across {len(by_chapter)} chapters.")
    print(f"Reports written to {out_dir}/")


if __name__ == "__main__":
    main()
