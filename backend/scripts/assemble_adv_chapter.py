#!/usr/bin/env python3
"""
Assemble a GPT-5.5-style chapter JSON (manifest + 5 lesson markdown files)
from plain files on disk, avoiding manual JSON string-escaping of large
markdown blocks (which is error-prone when authoring by hand / via tools
that write JSON directly).

Directory layout expected, given --dir /path/to/chapter_dir:
    manifest.json                 (the "manifest" object, raw JSON)
    01_concept_introduction.md
    02_core_explanation.md
    03_worked_examples.md
    04_exam_style_problems.md
    05_revision_and_recap.md

Output: writes {"manifest": {...}, "lessons": {...}} to --output.

Usage:
    python3 scripts/assemble_adv_chapter.py --dir gpt_output/adv_maths_01_sets --output gpt_output/adv_maths_01_sets.json
"""
import argparse
import json
from pathlib import Path

STEP_FILES = [
    ("Concept introduction", "01_concept_introduction.md"),
    ("Core explanation", "02_core_explanation.md"),
    ("Worked examples", "03_worked_examples.md"),
    ("Exam-style problems", "04_exam_style_problems.md"),
    ("Revision and recap", "05_revision_and_recap.md"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    chapter_dir = Path(args.dir)
    manifest_path = chapter_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.json not found in {chapter_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    lessons = {}
    for step_title, filename in STEP_FILES:
        fpath = chapter_dir / filename
        if not fpath.exists():
            raise SystemExit(f"Missing lesson file: {fpath}")
        content = fpath.read_text(encoding="utf-8").strip()
        if len(content) < 200:
            raise SystemExit(f"Lesson file {fpath} looks too short ({len(content)} chars)")
        lessons[step_title] = content

    output = {"manifest": manifest, "lessons": lessons}
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
