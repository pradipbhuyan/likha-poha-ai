#!/usr/bin/env python3
"""
Bulk-patch ```extract-ref``` blocks into every Grade 9 Social Science
(and remaining English) lesson_cache row that cites a specific numbered
NCERT "Questions and activities Q<N>" or "Critical Reflection <roman>.<N>"
reference, using the actual verbatim question/extract text extracted by
scripts/extract_qa_text_for_citations.py into
backend/reports/qa_extraction/*.json.

This is the generalized version of
scripts/patch_extract_refs_g9_english_grandmother.py (which only handled
one chapter) — applies the same fix across every affected Grade 9
Social Science chapter, plus the two remaining English chapters
("The Pot Maker", "Winds of Change") not covered by that first script.

Usage:
    cd backend
    python3 scripts/extract_qa_text_for_citations.py all   # if not already run
    python3 scripts/patch_extract_refs_bulk.py              # dry-run
    python3 scripts/patch_extract_refs_bulk.py --force       # apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.lesson_cache_service import (  # noqa: E402
    make_lesson_cache_key,
    store_lesson_cache,
)

GRADE = "Grade 9"
BOARD = "CBSE"
MODE = "CBSE"

QA_DIR = Path(__file__).resolve().parents[1] / "reports" / "qa_extraction"

# Chapter display name (as stored in lesson_cache.chapter) -> QA json filename
SS_CHAPTER_TO_FILE = {
    "Understanding Social Science": "social_science_understanding_social_science.json",
    "Shaping of the Earth's Surface": "social_science_shaping_of_the_earths_surface.json",
    "Atmosphere and Climate": "social_science_atmosphere_and_climate.json",
    "Early Humans and Beginning of Civilisation": "social_science_early_humans_and_beginning_of_civilisation.json",
    "State and Society up to 1000 CE": "social_science_state_and_society_up_to_1000_ce.json",
    "Democracy": "social_science_democracy.json",
    "Elections": "social_science_elections.json",
    "Building Blocks in Economics: The Problem of Choice": "social_science_building_blocks_in_economics_the_problem_of_choice.json",
    "The Price Puzzle: What Drives the Market": "social_science_the_price_puzzle_what_drives_the_market.json",
}

EN_CHAPTER_TO_FILE = {
    "Chapter 2: The Pot Maker": "english_the_pot_maker.json",
    "Chapter 3: Winds of Change": "english_winds_of_change.json",
}


def parse_numbered_questions(qa_block: str) -> dict[int, str]:
    """Split a 'Questions and activities' block into {number: question_text}.

    Matches lines starting with 'N.' (top-level questions 1-20). Stops
    each question's text at the next top-level 'N.' or end of block.
    Sub-parts (e.g. '7.1', '7.2') are included as part of question 7's
    text since they elaborate the same question.
    """
    # Find all top-level question start positions: "^N. " where N is 1-2 digits
    starts = list(re.finditer(r"(?:^|\n)(\d{1,2})\.\s+", qa_block))
    result: dict[int, str] = {}
    for i, m in enumerate(starts):
        num = int(m.group(1))
        if num > 30:  # guard against stray large numbers being misparsed
            continue
        start_pos = m.start()
        end_pos = starts[i + 1].start() if i + 1 < len(starts) else len(qa_block)
        text = qa_block[start_pos:end_pos].strip()
        # Keep only the FIRST occurrence of a given number (top-level,
        # not a sub-part like "7.1" being mis-split)
        if num not in result:
            result[num] = text
    return result


def load_qa_map(json_path: Path, key: str) -> dict[int, str]:
    if not json_path.exists():
        return {}
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return parse_numbered_questions(data.get(key, ""))


def build_extract_ref_block(citation: str, extract_text: str, note: str) -> str:
    payload = {"citation": citation, "extract_text": extract_text, "note": note}
    return "```extract-ref\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def patch_ss_content(content: str, qa_map: dict[int, str], chapter: str) -> tuple[str, int]:
    insertions = 0

    def replacer(m: re.Match) -> str:
        nonlocal insertions
        full_line = m.group(0)
        tail_start = m.end()
        if "```extract-ref" in content[tail_start:tail_start + 20]:
            return full_line
        num = int(m.group(1))
        text = qa_map.get(num)
        if not text:
            return full_line
        citation = f"NCERT Questions and activities Q{num}"
        block = build_extract_ref_block(citation, text, f"{chapter} — Questions and activities.")
        insertions += 1
        return f"{full_line}\n\n{block}"

    content = re.sub(
        r"^Question:.*?NCERT Questions? and [Aa]ctivities Q(\d{1,2}).*$",
        replacer,
        content,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return content, insertions


def patch_en_content(content: str, qa_map: dict[int, str], chapter: str) -> tuple[str, int]:
    """English chapters cite 'Critical Reflection <roman>.<N>' — the QA map
    here is keyed differently (not numbered questions), so this uses a
    simpler whole-block-per-citation approach: if ANY Critical Reflection
    citation is found and we have SOME extracted block text, attach it.
    Given the low volume (2 chapters), this is intentionally conservative:
    only patches if we have real text for that citation, else skips."""
    insertions = 0
    # For English, qa_map holds {0: full_critical_reflection_block_text}
    full_text = qa_map.get(0, "")
    if not full_text:
        return content, 0

    def replacer(m: re.Match) -> str:
        nonlocal insertions
        full_line = m.group(0)
        tail_start = m.end()
        if "```extract-ref" in content[tail_start:tail_start + 20]:
            return full_line
        citation_match = re.search(r"NCERT Critical Reflection [IVXi]+\.\d+", full_line, re.IGNORECASE)
        if not citation_match:
            return full_line
        citation = citation_match.group(0)
        block = build_extract_ref_block(
            citation, full_text[:2500],
            f"{chapter} — Critical Reflection section (full extract block; see citation for the specific sub-question).",
        )
        insertions += 1
        return f"{full_line}\n\n{block}"

    content = re.sub(
        r"^Question:.*NCERT Critical Reflection [IVXi]+\.\d+.*$",
        replacer,
        content,
        flags=re.MULTILINE,
    )
    return content, insertions


def run(dry_run: bool = True) -> None:
    total = 0

    # ── Social Science ──
    for chapter, filename in SS_CHAPTER_TO_FILE.items():
        qa_map = load_qa_map(QA_DIR / filename, "qa_block")
        rows = (
            admin_client.table("lesson_cache")
            .select("step_title, lesson_content, practice_questions, teacher_persona")
            .eq("grade", GRADE).eq("subject", "Social Science").eq("chapter", chapter)
            .execute().data
        )
        for row in rows:
            patched, n = patch_ss_content(row["lesson_content"], qa_map, chapter)
            if n == 0:
                continue
            total += n
            print(f"  [{'dry-run' if dry_run else 'patch'}] Social Science / {chapter} / {row['step_title']} — {n} block(s)")
            if dry_run:
                continue
            persona = row.get("teacher_persona") or ""
            key = make_lesson_cache_key(board=BOARD, grade=GRADE, subject="Social Science",
                                         chapter=chapter, mode=MODE, step_title=row["step_title"],
                                         teacher_persona=persona)
            store_lesson_cache(cache_key=key, lesson_content=patched, source_type="MANUAL",
                                board=BOARD, grade=GRADE, subject="Social Science", chapter=chapter,
                                mode=MODE, step_title=row["step_title"], teacher_persona=persona,
                                practice_questions=row.get("practice_questions") or [])
        if not dry_run:
            admin_client.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
                "subject", "Social Science").eq("chapter", chapter).eq("mode", MODE).execute()

    # ── English (remaining chapters) ──
    for chapter, filename in EN_CHAPTER_TO_FILE.items():
        json_path = QA_DIR / filename
        if not json_path.exists():
            print(f"  [skip] English / {chapter} — no extraction file")
            continue
        data = json.loads(json_path.read_text(encoding="utf-8"))
        qa_map = {0: data.get("critical_reflection_block", "")}
        rows = (
            admin_client.table("lesson_cache")
            .select("step_title, lesson_content, practice_questions, teacher_persona")
            .eq("grade", GRADE).eq("subject", "English").eq("chapter", chapter)
            .execute().data
        )
        for row in rows:
            patched, n = patch_en_content(row["lesson_content"], qa_map, chapter)
            if n == 0:
                continue
            total += n
            print(f"  [{'dry-run' if dry_run else 'patch'}] English / {chapter} / {row['step_title']} — {n} block(s)")
            if dry_run:
                continue
            persona = row.get("teacher_persona") or ""
            key = make_lesson_cache_key(board=BOARD, grade=GRADE, subject="English",
                                         chapter=chapter, mode=MODE, step_title=row["step_title"],
                                         teacher_persona=persona)
            store_lesson_cache(cache_key=key, lesson_content=patched, source_type="MANUAL",
                                board=BOARD, grade=GRADE, subject="English", chapter=chapter,
                                mode=MODE, step_title=row["step_title"], teacher_persona=persona,
                                practice_questions=row.get("practice_questions") or [])
        if not dry_run:
            admin_client.table("lesson_chapter_doc").delete().eq("grade", GRADE).eq(
                "subject", "English").eq("chapter", chapter).eq("mode", MODE).execute()

    print(f"\nTotal extract-ref blocks {'would be ' if dry_run else ''}inserted: {total}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(dry_run=not args.force)


if __name__ == "__main__":
    main()
