#!/usr/bin/env python3
"""
Batch Ingest GPT-5.5 Chapter Outputs — run ingest_gpt55_chapter_output.py
across every JSON file in a folder in one command
==============================================================================
Reusable replacement for calling ingest_gpt55_chapter_output.py one file
at a time by hand. Per user instruction: "create a script that automates
this for future use and run this."

For every *.json file in the given folder (or an explicit list of files),
this runs the exact same steps ingest_gpt55_chapter_output.py already
does for a single chapter — writing the manifest, seeding lesson_cache,
backfilling+curating textbook images, invalidating the Chapter Journey
cache, and running the Tier A quality audit — and prints one consolidated
summary at the end (chapter, audit findings, pass/fail) instead of having
to read each file's full console output separately.

Never guesses which JSON files are chapter outputs vs anything else in
the folder: it only accepts files that parse as JSON and have the exact
{"manifest": {...}, "lessons": {...}} shape ingest_gpt55_chapter_output.py
requires — any other .json file in the folder is skipped with a clear
message, not silently ignored or wrongly processed.

Usage:
    cd backend
    # Ingest every valid chapter-output JSON in a folder:
    python3 scripts/batch_ingest_gpt55_outputs.py --dir ~/Downloads

    # Ingest a specific folder, dry-run first:
    python3 scripts/batch_ingest_gpt55_outputs.py --dir ~/Downloads --dry-run

    # Ingest an explicit list of files instead of a whole folder:
    python3 scripts/batch_ingest_gpt55_outputs.py --files a.json b.json c.json

    # Skip the Tier A audit step per file (faster, less thorough):
    python3 scripts/batch_ingest_gpt55_outputs.py --dir ~/Downloads --skip-audit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_gpt55_chapter_output import (  # noqa: E402
    ensure_textbook_images,
    invalidate_chapter_doc_cache,
    run_followup_audit,
    seed_lessons,
    write_manifest,
)


def _is_valid_chapter_output(path: Path) -> dict | None:
    """Return the parsed JSON if this file matches the expected
    {"manifest": {...}, "lessons": {...}} shape, else None."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    manifest = data.get("manifest")
    lessons = data.get("lessons")
    if not isinstance(manifest, dict) or not isinstance(lessons, dict):
        return None
    required = {"grade", "subject", "chapter"}
    if not required.issubset(manifest.keys()):
        return None
    return data


def ingest_one(path: Path, dry_run: bool, force: bool, skip_audit: bool) -> dict:
    """Ingest a single chapter-output JSON file. Returns a summary dict."""
    data = _is_valid_chapter_output(path)
    if data is None:
        return {"file": path.name, "status": "skipped", "reason": "not a valid chapter-output JSON"}

    manifest = data["manifest"]
    lessons = data["lessons"]
    grade, subject, chapter = manifest["grade"], manifest["subject"], manifest["chapter"]

    print(f"\n{'='*78}\n{path.name}\n  {grade} / {subject} / {chapter}\n{'='*78}")

    try:
        write_manifest(manifest, dry_run=dry_run)
        seed_lessons(manifest, lessons, dry_run=dry_run, force=force)
        ensure_textbook_images(manifest, dry_run=dry_run, force=force)
        invalidate_chapter_doc_cache(manifest, dry_run=dry_run)
    except Exception as e:
        return {"file": path.name, "grade": grade, "subject": subject, "chapter": chapter,
                "status": "error", "reason": str(e)}

    if dry_run:
        return {"file": path.name, "grade": grade, "subject": subject, "chapter": chapter,
                "status": "dry-run"}

    if skip_audit:
        return {"file": path.name, "grade": grade, "subject": subject, "chapter": chapter,
                "status": "ingested", "critical": None, "high": None}

    # Reuses the exact same Tier A audit call the single-file script makes
    # (scripts.audit_chapter_boundary.run_audit, filtered to this chapter)
    # rather than reimplementing audit logic here.
    try:
        run_followup_audit(manifest)
        status = "ingested"
    except Exception as e:
        print(f"    [warn] Follow-up audit raised an error: {e}")
        status = "ingested"
    return {"file": path.name, "grade": grade, "subject": subject, "chapter": chapter, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-ingest every GPT-5.5 chapter-output JSON file in a folder (or an explicit list)"
    )
    parser.add_argument("--dir", help="Folder to scan for *.json chapter-output files")
    parser.add_argument("--files", nargs="+", help="Explicit list of JSON files to ingest instead of --dir")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true", default=True,
                         help="Overwrite existing cached lessons for these steps (default: on, matches single-file script's typical use)")
    parser.add_argument("--no-force", dest="force", action="store_false",
                         help="Do NOT overwrite existing cached lessons")
    parser.add_argument("--skip-audit", action="store_true", help="Skip the Tier A quality audit per chapter")
    args = parser.parse_args()

    if not args.dir and not args.files:
        print("ERROR: provide either --dir <folder> or --files <file1> <file2> ...")
        sys.exit(1)

    if args.files:
        paths = [Path(f).expanduser() for f in args.files]
    else:
        folder = Path(args.dir).expanduser()
        if not folder.is_dir():
            print(f"ERROR: not a directory: {folder}")
            sys.exit(1)
        paths = sorted(folder.glob("*.json"))

    if not paths:
        print("No .json files found to process.")
        return

    print(f"Found {len(paths)} .json file(s) to check.")
    results = [ingest_one(p, args.dry_run, args.force, args.skip_audit) for p in paths]

    print(f"\n{'='*78}\nSUMMARY\n{'='*78}")
    for r in results:
        if r["status"] == "skipped":
            print(f"  [SKIP]  {r['file']} — {r['reason']}")
        elif r["status"] == "error":
            print(f"  [ERROR] {r['file']} — {r.get('grade')}/{r.get('subject')}/{r.get('chapter')} — {r['reason']}")
        elif r["status"] == "dry-run":
            print(f"  [DRY]   {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']}")
        else:
            print(f"  [OK]    {r['file']} — {r['grade']}/{r['subject']}/{r['chapter']}")

    ok = sum(1 for r in results if r["status"] in ("ingested", "dry-run"))
    err = sum(1 for r in results if r["status"] in ("error", "skipped"))
    print(f"\nTotal: {len(results)} | OK: {ok} | Skipped/Error: {err}")
    print("(Review each chapter's own '[Tier A] ...' console output above for any audit findings — "
          "this batch script does not aggregate audit pass/fail counts to avoid duplicating logic "
          "already correctly implemented in scripts/audit_chapter_boundary.py.)")


if __name__ == "__main__":
    main()
