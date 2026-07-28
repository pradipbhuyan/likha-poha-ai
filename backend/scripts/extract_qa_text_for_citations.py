#!/usr/bin/env python3
"""
Extract "Questions and Activities" (Social Science) and "Critical
Reflection" (English) source text from NCERT PDFs, per chapter, and
write structured JSON so a human/LLM can review before building the
extract-ref patch. Writes one JSON file per chapter to
backend/reports/qa_extraction/<subject>_<chapter_slug>.json

This does NOT touch lesson_cache — it's a read-only extraction step.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parents[1] / "reports" / "qa_extraction"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SS_CHAPTERS = [
    (1, "Understanding Social Science"),
    (2, "Shaping of the Earth's Surface"),
    (3, "Atmosphere and Climate"),
    (4, "Early Humans and Beginning of Civilisation"),
    (5, "State and Society up to 1000 CE"),
    (6, "Democracy"),
    (7, "Elections"),
    (8, "Building Blocks in Economics: The Problem of Choice"),
    (9, "The Price Puzzle: What Drives the Market"),
]

EN_CHAPTERS = [
    (2, "The Pot Maker"),
    (3, "Winds of Change"),
]


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def extract_full_text(pdf_path: Path) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [p.extract_text(layout=False) or "" for p in pdf.pages]
    return "\n".join(pages)


def extract_qa_block(full_text: str) -> str:
    """Grab everything from 'QUESTIONS AND ACTIVITIES' (case-insens.) to
    the next chapter marker or end of text."""
    m = re.search(r"QUESTIONS AND ACTIVITIES", full_text, re.IGNORECASE)
    if not m:
        return ""
    tail = full_text[m.start():]
    # Stop at the next "Chapter N.indd" OCR artifact repeated block, or
    # end of text — keep generous length since exact stop point varies.
    return tail[:6000]


def extract_critical_reflection_block(full_text: str) -> str:
    m = re.search(r"Critical Reflection", full_text, re.IGNORECASE)
    if not m:
        return ""
    return full_text[m.start():m.start() + 6000]


def main() -> None:
    subject_filter = sys.argv[1] if len(sys.argv) > 1 else "all"

    if subject_filter in ("all", "social_science"):
        pdf_dir = REPO_ROOT / "RAG DB" / "Social Science"
        for num, name in SS_CHAPTERS:
            pdf_path = pdf_dir / f"iest1{num:02d}.pdf"
            if not pdf_path.exists():
                print(f"[skip] {name}: {pdf_path} not found")
                continue
            full_text = extract_full_text(pdf_path)
            qa_text = extract_qa_block(full_text)
            out_path = OUT_DIR / f"social_science_{_slugify(name)}.json"
            out_path.write_text(
                json.dumps({"chapter": name, "qa_block": qa_text}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[ok] {name}: wrote {len(qa_text)} chars -> {out_path.name}")

    if subject_filter in ("all", "english"):
        pdf_dir = REPO_ROOT / "RAG DB" / "English"
        for num, name in EN_CHAPTERS:
            pdf_path = pdf_dir / f"iebe1{num:02d}.pdf"
            if not pdf_path.exists():
                print(f"[skip] {name}: {pdf_path} not found")
                continue
            full_text = extract_full_text(pdf_path)
            cr_text = extract_critical_reflection_block(full_text)
            out_path = OUT_DIR / f"english_{_slugify(name)}.json"
            out_path.write_text(
                json.dumps({"chapter": name, "critical_reflection_block": cr_text}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[ok] {name}: wrote {len(cr_text)} chars -> {out_path.name}")


if __name__ == "__main__":
    main()
