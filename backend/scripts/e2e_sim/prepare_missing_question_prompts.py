#!/usr/bin/env python3
"""
Phase 3 driver: for every (grade, subject) with genuinely-missing question_bank
chapters (failure_classification.json -> truly_empty_subject_area), call
prepare_gpt55_question_prompts.run() directly (not via CLI) so exact chapter
strings containing commas aren't mangled by naive comma-splitting.

Produces one output folder per (grade, subject), in the priority order from
the approved plan: Hindi, Physics, English (+ Supplementary Reader),
Psychology, then the remaining smaller pockets.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # backend/
sys.path.insert(0, str(HERE.parents[1] / "scripts"))

from prepare_gpt55_question_prompts import run as prepare_run  # noqa: E402

PRIORITY_SUBJECTS = ["Hindi", "Physics", "English", "English Supplementary Reader", "Psychology"]

OUT_ROOT = Path.home() / "Downloads" / "GPT55_Question_Prompts_MissingChapters"


def priority_key(grade_subject):
    grade, subject = grade_subject
    try:
        p = PRIORITY_SUBJECTS.index(subject)
    except ValueError:
        p = len(PRIORITY_SUBJECTS)
    return (p, subject, int(grade.split()[-1]))


def main():
    data = json.load(open(HERE / "failure_classification.json"))
    by_subject = defaultdict(list)
    for item in data["truly_empty_subject_area"]:
        by_subject[(item["grade"], item["subject"])].append(item["chapter"])

    groups = sorted(by_subject.items(), key=lambda kv: priority_key(kv[0]))

    print(f"{len(groups)} (grade,subject) groups to prepare, {sum(len(v) for _, v in by_subject.items())} chapters total\n")

    for i, ((grade, subject), chapters) in enumerate(groups, 1):
        grade_slug = grade.replace(" ", "_")
        subject_slug = subject.replace(" ", "_").replace("/", "-")
        out_dir = OUT_ROOT / f"{i:02d}_{grade_slug}_{subject_slug}"
        print(f"[{i}/{len(groups)}] {grade} / {subject} -- {len(chapters)} chapters -> {out_dir}")
        try:
            prepare_run(
                grade=grade, subject=subject, output_dir=out_dir,
                only_chapters=chapters, questions_per_chapter=30,
            )
        except SystemExit as e:
            print(f"  -> skipped ({e})")
        print()


if __name__ == "__main__":
    main()
