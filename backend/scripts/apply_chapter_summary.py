#!/usr/bin/env python3
"""
Apply Chapter Summary Infographics to lesson_cache
==================================================
Appends (or replaces) a ```chapter-summary fenced block at the end of a
chapter's final lesson step, under an "## Chapter at a glance" heading.

The block is rendered by frontend/src/components/ChapterSummaryBlock.jsx as a
responsive, dark-mode-aware, selectable revision wall-chart — deliberately real
DOM text rather than a flat image, so it reflows on phones, stays searchable
and translatable, and can be corrected by editing one JSON field.

Source files live in:
    backend/app/data/chapter_summaries/<grade_slug>/<subject_slug>/<chapter_slug>.json

Each file holds the routing keys (grade, subject, chapter, step_title) plus a
"summary" object matching the schema validateChapterSummary() enforces on the
frontend. This script mirrors those caps so a bad file is rejected here rather
than silently rendering as nothing in the student's browser.

Idempotent: re-running replaces the existing block instead of appending a
second copy, so a re-authored summary fully supersedes the old one.

Usage:
    cd backend
    # Single file
    python3 scripts/apply_chapter_summary.py \
        --input app/data/chapter_summaries/grade-12/biology/chapter-9-biotechnology-principles-and-processes.json --dry-run
    python3 scripts/apply_chapter_summary.py --input <path>

    # Whole folder (recursive)
    python3 scripts/apply_chapter_summary.py --dir app/data/chapter_summaries --dry-run
    python3 scripts/apply_chapter_summary.py --dir app/data/chapter_summaries

    # Remove a previously applied block
    python3 scripts/apply_chapter_summary.py --input <path> --remove
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402

SECTION_HEADING = "## Chapter at a glance"

# Matches the whole appended section — heading plus fence — so re-running
# replaces it rather than stacking copies. Non-greedy up to the closing fence.
_APPLIED_BLOCK_RE = re.compile(
    r"\n*##\s*Chapter at a glance\s*\n+```chapter-summary\n.*?\n```\s*",
    re.DOTALL,
)

REQUIRED_KEYS = ["grade", "subject", "chapter", "step_title", "summary"]

# Mirrors the caps in frontend/src/components/ChapterSummaryBlock.jsx. Kept in
# sync deliberately: a payload that passes here must render there, so an author
# never has to discover a truncation by looking at the live page.
MAX_PANELS = 8
MAX_POINTS_PER_PANEL = 6
MAX_PIPELINE_STEPS = 12
MAX_TERMS = 10
MAX_REMEMBER = 8

LIMITS = {
    "title": 90,
    "subtitle": 140,
    "definition": 260,
    "panel_heading": 60,
    "panel_point": 180,
    "pipeline_heading": 80,
    "pipeline_label": 45,
    "pipeline_detail": 160,
    "term": 45,
    "meaning": 180,
    "remember": 200,
}


def _check_text(errors: list[str], value, kind: str, where: str, *, required: bool = True) -> None:
    """Validate one string against the frontend's length and safety rules."""
    if value is None or value == "":
        if required:
            errors.append(f"{where}: missing required text")
        return
    if not isinstance(value, str):
        errors.append(f"{where}: expected a string, got {type(value).__name__}")
        return
    text = " ".join(value.split())
    limit = LIMITS[kind]
    if len(text) < 2:
        errors.append(f"{where}: too short")
    if len(text) > limit:
        errors.append(f"{where}: {len(text)} chars exceeds the {limit}-char cap (would be dropped by the renderer)")
    if "<" in text or ">" in text:
        errors.append(f"{where}: contains < or >, which the renderer rejects")


def validate_summary(summary: dict) -> list[str]:
    """Return a list of human-readable problems; empty means the payload is good."""
    errors: list[str] = []
    if not isinstance(summary, dict):
        return ["summary: expected an object"]

    _check_text(errors, summary.get("title"), "title", "summary.title")
    _check_text(errors, summary.get("subtitle"), "subtitle", "summary.subtitle", required=False)
    _check_text(errors, summary.get("definition"), "definition", "summary.definition", required=False)

    panels = summary.get("panels") or []
    if not isinstance(panels, list):
        errors.append("summary.panels: expected a list")
        panels = []
    if len(panels) > MAX_PANELS:
        errors.append(f"summary.panels: {len(panels)} panels exceeds the cap of {MAX_PANELS}")
    for i, panel in enumerate(panels):
        where = f"summary.panels[{i}]"
        if not isinstance(panel, dict):
            errors.append(f"{where}: expected an object")
            continue
        _check_text(errors, panel.get("heading"), "panel_heading", f"{where}.heading")
        points = panel.get("points") or []
        if not isinstance(points, list) or not points:
            errors.append(f"{where}.points: expected a non-empty list")
            continue
        if len(points) > MAX_POINTS_PER_PANEL:
            errors.append(f"{where}.points: {len(points)} exceeds the cap of {MAX_POINTS_PER_PANEL}")
        for j, point in enumerate(points):
            _check_text(errors, point, "panel_point", f"{where}.points[{j}]")

    pipeline = summary.get("pipeline")
    if pipeline is not None:
        if not isinstance(pipeline, dict):
            errors.append("summary.pipeline: expected an object")
        else:
            _check_text(errors, pipeline.get("heading"), "pipeline_heading", "summary.pipeline.heading")
            steps = pipeline.get("steps") or []
            if not isinstance(steps, list) or len(steps) < 2:
                errors.append("summary.pipeline.steps: a pipeline needs at least 2 steps")
                steps = steps if isinstance(steps, list) else []
            if len(steps) > MAX_PIPELINE_STEPS:
                errors.append(f"summary.pipeline.steps: {len(steps)} exceeds the cap of {MAX_PIPELINE_STEPS}")
            for i, step in enumerate(steps):
                where = f"summary.pipeline.steps[{i}]"
                if not isinstance(step, dict):
                    errors.append(f"{where}: expected an object")
                    continue
                _check_text(errors, step.get("label"), "pipeline_label", f"{where}.label")
                _check_text(errors, step.get("detail"), "pipeline_detail", f"{where}.detail", required=False)

    terms = summary.get("terms") or []
    if not isinstance(terms, list):
        errors.append("summary.terms: expected a list")
        terms = []
    if len(terms) > MAX_TERMS:
        errors.append(f"summary.terms: {len(terms)} exceeds the cap of {MAX_TERMS}")
    for i, entry in enumerate(terms):
        where = f"summary.terms[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected an object")
            continue
        _check_text(errors, entry.get("term"), "term", f"{where}.term")
        _check_text(errors, entry.get("meaning"), "meaning", f"{where}.meaning")

    remember = summary.get("remember") or []
    if not isinstance(remember, list):
        errors.append("summary.remember: expected a list")
        remember = []
    if len(remember) > MAX_REMEMBER:
        errors.append(f"summary.remember: {len(remember)} exceeds the cap of {MAX_REMEMBER}")
    for i, point in enumerate(remember):
        _check_text(errors, point, "remember", f"summary.remember[{i}]")

    if not panels and not pipeline and not terms and not remember:
        errors.append("summary: every section is empty, so the renderer would show nothing")

    return errors


def load_and_validate(path: Path) -> dict:
    """Load one chapter-summary source file and validate it. Raises ValueError."""
    raw = path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc

    missing = [k for k in REQUIRED_KEYS if not data.get(k)]
    if missing:
        raise ValueError(f"missing required key(s): {', '.join(missing)}")

    errors = validate_summary(data["summary"])
    if errors:
        raise ValueError("summary failed validation:\n  - " + "\n  - ".join(errors))

    return data


def build_block(summary: dict) -> str:
    """Render the summary as the markdown section appended to the lesson step."""
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    return f"\n\n{SECTION_HEADING}\n\n```chapter-summary\n{payload}\n```\n"


def apply_to_content(content: str, block: str) -> str:
    """Replace an already-applied block, or append if there isn't one yet."""
    stripped = _APPLIED_BLOCK_RE.sub("", content).rstrip()
    return stripped + block


def remove_from_content(content: str) -> str:
    """Strip a previously applied block, leaving the original lesson intact."""
    return _APPLIED_BLOCK_RE.sub("", content).rstrip() + "\n"


def refresh_chapter_doc(*, grade: str, subject: str, chapter: str, board: str = "CBSE", mode: str = "CBSE") -> None:
    """Rebuild the stored lesson_chapter_doc from the just-updated lesson_cache.

    Grades 9-12 are served the Chapter Journey view, which reads the CACHED
    lesson_chapter_doc row rather than lesson_cache directly. Without this the
    summary is written to lesson_cache but the student keeps seeing whatever
    the doc was last built from — which looks exactly like the change not
    working. See docs/CHAPTER_INFOGRAPHIC_FEATURE.md §5 trap 1.
    """
    try:
        from app.services.chapter_doc_service import get_or_convert_chapter_doc  # noqa: PLC0415
        doc = get_or_convert_chapter_doc(
            board=board, grade=grade, subject=subject, chapter=chapter,
            mode=mode, force_refresh=True,
        )
        print("  ✓ chapter doc rebuilt" if doc else "  · no chapter doc for this chapter (per-step view only)")
    except Exception as exc:
        # Never fail the apply over this — the lesson_cache write already
        # succeeded, and the doc can be rebuilt from the UI "Refresh lesson".
        print(f"  ! chapter doc refresh failed ({exc}); use the 'Refresh lesson' button in the app")


def process(path: Path, *, dry_run: bool, remove: bool) -> bool:
    """Apply (or remove) one summary file. Returns True on success."""
    try:
        data = load_and_validate(path)
    except ValueError as exc:
        print(f"  ✗ {path.name}: {exc}")
        return False

    grade, subject = data["grade"], data["subject"]
    chapter, step_title = data["chapter"], data["step_title"]

    db = get_content_db(grade)
    result = (
        db.table("lesson_cache")
        .select("id, lesson_content, teacher_persona")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .eq("step_title", step_title)
        .eq("status", "active")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print(f"  ✗ {path.name}: no active lesson_cache row for {grade} / {subject} / {chapter} / {step_title}")
        return False

    block = build_block(data["summary"])
    action, past_action = ("remove", "removed") if remove else ("apply", "applied")

    # A chapter step can have several rows (one per teacher_persona variant,
    # since persona is part of the cache key). Every variant a student may be
    # served must carry the same summary, so update them all.
    for row in rows:
        original = row.get("lesson_content") or ""
        updated = remove_from_content(original) if remove else apply_to_content(original, block)

        if updated == original:
            print(f"  = {path.name}: already up to date (row {row['id'][:8]})")
            continue

        persona = row.get("teacher_persona") or "default"
        if dry_run:
            delta = len(updated) - len(original)
            print(f"  → would {action} on row {row['id'][:8]} (persona: {persona}, {delta:+d} chars)")
        else:
            db.table("lesson_cache").update({"lesson_content": updated}).eq("id", row["id"]).execute()
            print(f"  ✓ {past_action} on row {row['id'][:8]} (persona: {persona})")

    if not dry_run:
        refresh_chapter_doc(grade=grade, subject=subject, chapter=chapter)

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="A single chapter-summary JSON file")
    source.add_argument("--dir", type=Path, help="A folder of chapter-summary JSON files (searched recursively)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--remove", action="store_true", help="Strip a previously applied block instead of applying")
    args = parser.parse_args()

    if args.input:
        paths = [args.input]
    else:
        paths = sorted(args.dir.rglob("*.json"))
        if not paths:
            print(f"No .json files found under {args.dir}")
            return 1

    mode = "DRY RUN — no writes" if args.dry_run else "LIVE"
    print(f"{mode}: {'removing' if args.remove else 'applying'} {len(paths)} chapter summary file(s)\n")

    failures = 0
    for path in paths:
        print(f"{path}")
        if not process(path, dry_run=args.dry_run, remove=args.remove):
            failures += 1
        print()

    print(f"Done: {len(paths) - failures} succeeded, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
