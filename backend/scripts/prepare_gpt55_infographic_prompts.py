#!/usr/bin/env python3
"""
Prepare GPT-5.5 Chapter Infographic Authoring Prompts
=============================================================================
See docs/CHAPTER_INFOGRAPHIC_FEATURE.md for the full workflow this script
starts (completed by scripts/apply_chapter_infographic.py).

Generates one prompt .txt per chapter, grounded in the chapter's ALREADY
AUTHORED lesson_cache content — the same grounding source the lesson-plan and
question-bank workflows use. A chapter with no authored lesson content is
skipped with a clear warning rather than producing an ungrounded poster.

The prompt wording lives in app/services/infographic_prompt.py, which adapts
density, vocabulary and closing strips by grade band. Nothing grade- or
subject-specific belongs in this file.

Default scope is the first-cut rollout: Grades 5-12, Science and Maths.
Subject naming is NOT uniform across grades — Grade 5 has EVS rather than
Science, and Grades 11-12 split Science into Physics/Chemistry/Biology. That
map is DEFAULT_SCOPE below.

Usage:
    cd backend
    # Everything in scope, into a dated folder
    python3 scripts/prepare_gpt55_infographic_prompts.py

    # One grade / subject
    python3 scripts/prepare_gpt55_infographic_prompts.py --grade "Grade 8" --subject Science

    # Preview counts without writing anything
    python3 scripts/prepare_gpt55_infographic_prompts.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.infographic_prompt import build_infographic_prompt  # noqa: E402

MODE = "CBSE"

# First-cut rollout scope. Subject names differ by grade — see module docstring.
DEFAULT_SCOPE: dict[str, list[str]] = {
    "Grade 5": ["Maths", "EVS"],
    "Grade 6": ["Maths", "Science"],
    "Grade 7": ["Maths", "Science"],
    "Grade 8": ["Maths", "Science"],
    "Grade 9": ["Maths", "Science"],
    "Grade 10": ["Maths", "Science"],
    "Grade 11": ["Mathematics", "Physics", "Chemistry", "Biology"],
    "Grade 12": ["Mathematics", "Physics", "Chemistry", "Biology"],
}


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def get_authored_chapters(grade: str, subject: str) -> list[str]:
    """Distinct chapters with active authored lesson_cache content."""
    db = get_content_db(grade)
    rows = (
        db.table("lesson_cache")
        .select("chapter")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("mode", MODE)
        .eq("status", "active")
        .execute()
    )
    return sorted({r["chapter"] for r in (rows.data or []) if r.get("chapter")})


def get_chapter_lesson_text(grade: str, subject: str, chapter: str) -> str:
    """Join every authored step of one chapter into a single grounding string."""
    db = get_content_db(grade)
    rows = (
        db.table("lesson_cache")
        .select("step_title, lesson_content, teacher_persona")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .eq("mode", MODE)
        .eq("status", "active")
        .execute()
    )
    # A step can have several persona variants of the same content; keep one per
    # step so the grounding text is not padded with near-duplicates.
    by_step: dict[str, str] = {}
    for r in (rows.data or []):
        content = (r.get("lesson_content") or "").strip()
        if not content:
            continue
        step = r.get("step_title") or ""
        if step not in by_step or not r.get("teacher_persona"):
            by_step[step] = content
    return "\n\n".join(by_step.values())


def run(scope: dict[str, list[str]], output_root: Path, dry_run: bool) -> int:
    """Write one prompt file per chapter. Returns the number written."""
    written = 0
    skipped: list[str] = []
    index_lines = [
        "GPT-5.5 CHAPTER INFOGRAPHIC PROMPTS",
        "=" * 78,
        f"Generated: {date.today().isoformat()}",
        "",
        "WHAT TO DO",
        "-" * 78,
        "For each *_PROMPT.txt file below:",
        "  1. Open it and copy the ENTIRE contents.",
        "  2. Paste into a fresh GPT-5.5 chat session (image generation enabled).",
        "  3. Review the returned poster against the chapter before accepting it —",
        "     see REVIEW GATE below. Regenerate if it fails.",
        "  4. Save the image, and copy the ALT: and CAPTION: lines it returns.",
        "  5. Apply it:",
        "",
        "     cd backend",
        "     python3 scripts/apply_chapter_infographic.py \\",
        '         --image ~/Downloads/<saved-image>.png \\',
        '         --grade "<grade>" --subject "<subject>" \\',
        '         --chapter "<exact chapter string from the prompt>" \\',
        '         --alt "<ALT line>" --caption "<CAPTION line>" \\',
        "         --dry-run",
        "",
        "     Drop --dry-run once the preview looks right.",
        "",
        "REVIEW GATE — do not skip",
        "-" * 78,
        "Generated posters have shipped real errors. Before applying, check:",
        "  [ ] Every panel belongs to THIS chapter (no topics from elsewhere).",
        "  [ ] No meta/study-skills panel.",
        "  [ ] All lettering spelled correctly and legible when enlarged.",
        "  [ ] Formulae, units and numeric values match the chapter.",
        "  [ ] No invented NCERT page/exercise/figure references.",
        "",
        "CHAPTERS",
        "-" * 78,
    ]

    for grade, subjects in scope.items():
        for subject in subjects:
            try:
                chapters = get_authored_chapters(grade, subject)
            except Exception as exc:
                print(f"  ! {grade} / {subject}: lookup failed ({exc})")
                continue

            if not chapters:
                skipped.append(f"{grade} / {subject}: no authored chapters")
                continue

            folder = output_root / _slugify(grade) / _slugify(subject)
            print(f"\n{grade} / {subject} — {len(chapters)} chapter(s)")
            index_lines.append(f"\n{grade} / {subject}  ({len(chapters)})")

            for i, chapter in enumerate(chapters, start=1):
                lesson_text = get_chapter_lesson_text(grade, subject, chapter)
                if not lesson_text.strip():
                    print(f"  · skipped (no authored content): {chapter}")
                    skipped.append(f"{grade} / {subject} / {chapter}: no content")
                    continue

                prompt = build_infographic_prompt(
                    grade=grade, subject=subject, chapter=chapter,
                    chapter_lesson_text=lesson_text,
                )
                filename = f"{i:02d}_{_slugify(chapter)}_PROMPT.txt"
                index_lines.append(f"  {filename}   <- {chapter}")

                if not dry_run:
                    folder.mkdir(parents=True, exist_ok=True)
                    (folder / filename).write_text(prompt, encoding="utf-8")
                written += 1

            print(f"  {'would write' if dry_run else 'wrote'} {len(chapters)} prompt(s)")

    if skipped:
        index_lines += ["", "SKIPPED", "-" * 78] + [f"  {s}" for s in skipped]

    if not dry_run:
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "00_README_and_index.txt").write_text(
            "\n".join(index_lines) + "\n", encoding="utf-8",
        )

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--grade", help='Limit to one grade, e.g. "Grade 8"')
    parser.add_argument("--subject", help='Limit to one subject, e.g. "Science"')
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing")
    args = parser.parse_args()

    if args.grade:
        subjects = [args.subject] if args.subject else DEFAULT_SCOPE.get(args.grade, [])
        if not subjects:
            print(f"No default subjects known for {args.grade}; pass --subject explicitly.")
            return 1
        scope = {args.grade: subjects}
    elif args.subject:
        scope = {g: [args.subject] for g, subs in DEFAULT_SCOPE.items() if args.subject in subs}
        if not scope:
            print(f"Subject {args.subject!r} is not in the default scope.")
            return 1
    else:
        scope = DEFAULT_SCOPE

    output_root = (
        Path(args.output_dir).expanduser() if args.output_dir
        else Path.home() / "Downloads" / f"GPT55_Chapter_Infographic_Prompts_{date.today().isoformat()}"
    )

    print(f"{'DRY RUN — no files written' if args.dry_run else 'Writing prompts'}")
    print(f"Output root: {output_root}")

    written = run(scope, output_root, args.dry_run)

    print(f"\n{'Would write' if args.dry_run else 'Done.'} {written} prompt(s)")
    if not args.dry_run:
        print(f"  {output_root}")
        print("  Start with 00_README_and_index.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
