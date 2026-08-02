#!/usr/bin/env python3
"""
Fix legacy text-only extract-ref popups for Grade 12 Physics.

Unlike Psychology/English (where all citations for a chapter sit on one
"Review Questions" page), Physics worked examples/exercises are scattered
throughout each chapter's own numbered Example/Exercise. This script:

  1. For each citation fence (e.g. "NCERT Example 4.2" or
     "NCERT Exercise 8.1"), searches that chapter's rag_visual_assets
     nearby_text for the matching "Example N.N" / "EXAMPLE N.N" or the
     citation's own extract_text substring to find the correct page.
  2. Falls back to a substring match of extract_text if the citation
     label itself isn't found verbatim (exercise text is sometimes
     reproduced without a printed "Exercise N.N" label on the page).
  3. Converts {"citation", "extract_text", "note"} to
     {"citation", "page_number", "asset_url"} using the found page.

Usage:
    cd backend
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_grade12_physics.py --dry-run
    ./venv/bin/python3 scripts/fix_legacy_text_extract_refs_grade12_physics.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

CHAPTER_DOCUMENT_IDS: dict[str, int] = {
    "Chapter 1: Electric Charges and Fields": 1208,
    "Chapter 2: Electrostatic Potential and Capacitance": 1209,
    "Chapter 3: Current Electricity": 1210,
    "Chapter 4: Moving Charges and Magnetism": 1211,
    "Chapter 5: Magnetism and Matter": 1212,
    "Chapter 6: Electromagnetic Induction": 1213,
    "Chapter 7: Alternating Current": 1214,
    "Chapter 8: Electromagnetic Waves": 1215,
    "Chapter 9: Ray Optics and Optical Instruments": 1216,
    "Chapter 10: Wave Optics": 1217,
}

EXTRACT_RE = re.compile(r"```extract-ref\n(.*?)\n```", re.DOTALL)
EXAMPLE_NUM_RE = re.compile(r"Example\s*(\d+\.\d+)", re.IGNORECASE)


def _extract_number(citation: str) -> str | None:
    """Pull '4.2' out of 'NCERT Example 4.2' or 'NCERT Exercise 8.1'."""
    m = re.search(r"(\d+\.\d+)", citation or "")
    return m.group(1) if m else None


def find_page_for_citation(document_id: int, citation: str, extract_text: str) -> tuple[int, str] | None:
    """Return (page_number, asset_url) best matching this citation."""
    res = (
        admin_client.table("rag_visual_assets")
        .select("page_number, asset_url, nearby_text")
        .eq("document_id", document_id)
        .order("page_number")
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None

    number = _extract_number(citation)

    # Strategy 1: look for the exact "N.N" number near the word Example/
    # Exercise on the page (covers both "Example 4.2" and "EXAMPLE 4.2").
    if number:
        pattern = re.compile(
            rf"(Example|Exercise)\s*{re.escape(number)}\b", re.IGNORECASE
        )
        for row in rows:
            text = row.get("nearby_text") or ""
            if pattern.search(text):
                return row["page_number"], row["asset_url"]

    # Strategy 2: fall back to a substantial substring of the extract_text
    # itself (first ~40 chars, to tolerate OCR/whitespace differences).
    snippet = (extract_text or "")[:40].strip()
    if len(snippet) >= 15:
        for row in rows:
            text = row.get("nearby_text") or ""
            if snippet in text:
                return row["page_number"], row["asset_url"]

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    total_fixed = 0
    total_missing = 0

    for chapter, document_id in CHAPTER_DOCUMENT_IDS.items():
        res = (
            admin_client.table("lesson_cache")
            .select("id, step_title, lesson_content")
            .eq("grade", "Grade 12")
            .eq("subject", "Physics")
            .eq("chapter", chapter)
            .execute()
        )

        for row in res.data:
            content = row["lesson_content"]
            changed = False

            def _replace(m: re.Match) -> str:
                nonlocal changed, total_fixed, total_missing
                raw = m.group(1)
                try:
                    payload = json.loads(raw)
                except Exception:
                    return m.group(0)
                if "asset_url" in payload:
                    return m.group(0)
                citation = payload.get("citation", "")
                extract_text = payload.get("extract_text", "")

                found = find_page_for_citation(document_id, citation, extract_text)
                if not found:
                    print(f"  [MISS] {chapter} | {citation} -> no matching page found")
                    total_missing += 1
                    return m.group(0)

                page, asset_url = found
                new_payload = {
                    "citation": citation,
                    "page_number": page,
                    "asset_url": asset_url,
                }
                changed = True
                total_fixed += 1
                new_json = json.dumps(new_payload, ensure_ascii=False)
                return f"```extract-ref\n{new_json}\n```"

            new_content = EXTRACT_RE.sub(_replace, content)

            if changed:
                print(f"[{'DRY' if args.dry_run else 'LIVE'}] {chapter} | {row['step_title']} -> updating")
                if not args.dry_run:
                    admin_client.table("lesson_cache").update(
                        {"lesson_content": new_content}
                    ).eq("id", row["id"]).execute()

    print(f"\nTotal fixed: {total_fixed}, total missing/skip: {total_missing}")

    if not args.dry_run and total_fixed > 0:
        for chapter in CHAPTER_DOCUMENT_IDS:
            admin_client.table("lesson_chapter_doc").delete().eq(
                "grade", "Grade 12"
            ).eq("subject", "Physics").eq("chapter", chapter).execute()
        print("Invalidated lesson_chapter_doc cache for all touched chapters.")


if __name__ == "__main__":
    main()
