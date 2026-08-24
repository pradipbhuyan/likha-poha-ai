#!/usr/bin/env python3
"""
Apply GPT-regenerated fixes to lesson_kb
==========================================
Takes the JSON array(s) you get back from an external LLM (per
scripts/export_lesson_kb_gpt_handoff.py's instructions) and writes the
corrected `answer` text into the live `lesson_kb` table — after validating
each fix isn't itself still corrupted.

Safety model:
  - DRY RUN BY DEFAULT. Nothing is written unless you pass --apply.
  - Every row is re-run through the same corruption detector used by
    audit_lesson_kb_quality.py; a fix that still trips it is skipped and
    reported, never applied.
  - The id must already exist in lesson_kb with status='active'; unknown
    ids are skipped and reported, never inserted as new rows.
  - Before overwriting, the previous answer is appended to a local backup
    log (reports/lesson_kb_quality/applied_fixes_log.jsonl) so every change
    can be manually reverted by re-running an update from that log.

Input format — one JSON file, or multiple concatenated with --input passed
more than once. Each file: a JSON array of objects:
    [
      {"id": "<uuid>", "answer": "- bullet one\\n- bullet two", "note": ""},
      ...
    ]
A non-empty "note" means the LLM couldn't ground an answer — that row is
always skipped and listed separately, regardless of --apply.

Usage:
    cd backend
    python3 scripts/apply_lesson_kb_fixes.py --input fixed_cards.json          # dry run
    python3 scripts/apply_lesson_kb_fixes.py --input fixed_cards.json --apply  # writes
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# Same detector as audit_lesson_kb_quality.py, kept in sync manually since
# these are separate one-off scripts, not a shared library.
import re  # noqa: E402
import zlib  # noqa: E402

DUP_SUBSTR_RE = re.compile(r"([A-Za-z]{5,})\1+")
WORD_REPEAT_RE = re.compile(r"\b(\w+(?:\s\w+){0,2})\b(?:\s+\1\b){2,}", re.IGNORECASE)
PAGE_NUMBER_NOISE_RE = re.compile(r"\b\d{1,4}\s+\d{2,4}\s+\d{2,4}\b")
SHORT_TOKEN_RUN_RE = re.compile(r"(?:\b[A-Za-z]{1,2}\b\s+){6,}")


def compression_ratio(text: str) -> float:
    if len(text) < 40:
        return 1.0
    raw = text.encode("utf-8", errors="ignore")
    return len(zlib.compress(raw, level=9)) / len(raw)


def detect_issues(answer: str) -> list[str]:
    weak, strong = [], []
    dup = DUP_SUBSTR_RE.findall(answer)
    if dup:
        (strong if any(len(m) >= 6 for m in dup) else weak).append(f"duplicated_substrings:{dup[:5]}")
    wr = [m for m in WORD_REPEAT_RE.findall(answer) if len(m.strip()) >= 3]
    if wr:
        strong.append(f"repeated_phrase:{wr[:5]}")
    if PAGE_NUMBER_NOISE_RE.search(answer):
        weak.append("page_number_noise")
    if SHORT_TOKEN_RUN_RE.findall(answer):
        weak.append("short_token_run")
    ratio = compression_ratio(answer)
    if ratio < 0.25:
        weak.append(f"low_compression_ratio:{ratio:.2f}")
    if strong:
        return strong + weak
    if len(weak) >= 2:
        return weak
    return []


BACKUP_LOG = Path("reports/lesson_kb_quality/applied_fixes_log.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", action="append", required=True, help="JSON file with fixes (repeatable)")
    ap.add_argument("--apply", action="store_true", help="Actually write to the DB (default: dry run)")
    args = ap.parse_args()

    fixes: list[dict] = []
    for path in args.input:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, list):
            print(f"Skipping {path}: not a JSON array")
            continue
        fixes.extend(data)

    print(f"Loaded {len(fixes)} candidate fixes from {len(args.input)} file(s).")

    to_apply, skipped_note, skipped_missing, skipped_still_bad = [], [], [], []

    for fix in fixes:
        fid = fix.get("id")
        answer = (fix.get("answer") or "").strip()
        note = (fix.get("note") or "").strip()

        if note:
            skipped_note.append((fid, note))
            continue
        if not fid or not answer:
            skipped_missing.append((fid, "missing id or answer"))
            continue

        try:
            res = (
                admin_client.table("lesson_kb")
                .select("id, question, answer, status")
                .eq("id", fid)
                .eq("status", "active")
                .execute()
            )
            rows = res.data or []
        except Exception as exc:
            skipped_missing.append((fid, f"lookup failed (likely malformed id): {exc}"))
            continue
        if not rows:
            skipped_missing.append((fid, "no active lesson_kb row with this id"))
            continue

        issues = detect_issues(answer)
        if issues:
            skipped_still_bad.append((fid, issues))
            continue

        to_apply.append({"id": fid, "old_answer": rows[0]["answer"], "new_answer": answer, "question": rows[0]["question"]})

    print(f"\n{len(to_apply)} fix(es) pass validation and are ready to apply.")
    for f in to_apply:
        print(f"  - {f['id']} — {f['question'][:70]!r}")

    if skipped_note:
        print(f"\n{len(skipped_note)} skipped — LLM flagged insufficient context:")
        for fid, note in skipped_note:
            print(f"  - {fid}: {note}")

    if skipped_missing:
        print(f"\n{len(skipped_missing)} skipped — missing/unmatched id:")
        for fid, reason in skipped_missing:
            print(f"  - {fid}: {reason}")

    if skipped_still_bad:
        print(f"\n{len(skipped_still_bad)} skipped — regenerated answer STILL fails corruption check:")
        for fid, issues in skipped_still_bad:
            print(f"  - {fid}: {issues}")

    if not args.apply:
        print("\nDry run only — no changes written. Re-run with --apply to write these.")
        return

    if not to_apply:
        print("\nNothing to apply.")
        return

    BACKUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    applied = 0
    with BACKUP_LOG.open("a") as log:
        for f in to_apply:
            try:
                admin_client.table("lesson_kb").update({"answer": f["new_answer"]}).eq("id", f["id"]).execute()
                log.write(json.dumps({
                    "id": f["id"], "question": f["question"],
                    "old_answer": f["old_answer"], "new_answer": f["new_answer"],
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                applied += 1
            except Exception as exc:
                print(f"  FAILED to update {f['id']}: {exc}")

    print(f"\nApplied {applied} / {len(to_apply)} fixes. Backup of previous answers: {BACKUP_LOG}")


if __name__ == "__main__":
    main()
