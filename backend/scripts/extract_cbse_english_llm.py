#!/usr/bin/env python3
"""
LLM-assisted structural extraction for CBSE English sample papers.

Regex-based extraction (extract_cbse_sample_paper.py) works well for
Maths/Science/Social Science, which have one flat, sequentially-numbered
question list. English doesn't: each passage/extract is a top-level
question containing multiple roman-numeral sub-parts (I, II, III...) that
reset per passage, mixed with inconsistent numbering styles (some top-level
markers use a period, some don't) and OR-choices between whole literature
extracts (each with its own roman-numeral sub-parts). Regex parsing hit
diminishing returns chasing each new one-off quirk; an LLM reading the text
semantically handles this structure far more reliably.

question_number convention for nested sub-parts:
  - Simple passage sub-question: "{top_level}.{ROMAN}" e.g. "1.II"
  - Literature extract-choice sub-question: "{top_level}.{A|B}.{ROMAN}"
    e.g. "6.A.III" (extract A's part III) vs "6.B.III" (extract B's part III)
  - A question with no sub-parts (rare in this paper, but handled): plain
    "{top_level}"

Usage:
    cd backend
    .venv/bin/python3 scripts/extract_cbse_english_llm.py \\
        --pdf /path/to/EnglishL-SQP.pdf \\
        --grade "Grade 10" --subject "English" \\
        --academic-year "2025-26" --source-subject-code EnglishL \\
        --output questions_extracted.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypdf

from app.services.grade_db_router import get_content_db
from app.services.openai_service import get_effective_settings, force_refresh_settings
from openai import OpenAI

BOARD = "CBSE"

SYSTEM_PROMPT = """You extract the structured question list from an official CBSE English sample question paper's raw text (extracted from a PDF, so spacing/line-breaks may be imperfect).

Return ONLY a JSON array, no markdown fences, no commentary. Each element:
{
  "question_number": "...",
  "section": "A"|"B"|"C",
  "question_type": "mcq"|"short_answer"|"long_answer"|"case_study",
  "marks": <integer>,
  "question_text": "...",
  "options": [...],
  "diagram_dependent": true|false
}

question_number rules (CRITICAL — this paper nests differently from other subjects):
- Each reading passage / grammar block / literature extract is a top-level numbered
  question (1, 2, 3, ...) containing multiple roman-numeral sub-parts (I, II, III, IV...)
  that restart at I for each new top-level question. Every sub-part becomes its OWN
  array element with question_number = "{top_level}.{ROMAN}", e.g. "1.I", "1.II", "3.VII".
- If a top-level question offers an OR-choice between two entire extracts (commonly
  labelled A and B, each with its own independent roman-numeral sub-parts), use
  question_number = "{top_level}.{A|B}.{ROMAN}", e.g. "6.A.I", "6.A.II", "6.B.I", "6.B.II".
- Do not skip, renumber, or merge sub-parts. Preserve the exact roman numerals printed.

question_text rules:
- For the FIRST sub-part of each top-level question, prepend the full passage/extract
  text (the reading passage, the extract quote, etc.) before the sub-part's own
  question, since a student answering only that row needs the passage to be
  self-contained. Subsequent sub-parts of the same top-level question do NOT need
  the passage repeated — just their own question text.
- For the grammar section, each roman-numeral sub-part is usually a standalone
  gap-fill / transformation / error-correction task — question_text is just that
  task's own instruction and sentence.

question_type / options rules:
- "mcq": if the sub-part offers 2+ lettered/labelled choices to pick from — put the
  choice texts in "options" (exactly as printed, no letter prefix in the option text
  itself).
- "short_answer": everything else (open-ended, fill-in-blank, error-correction,
  transformation) — options should be an empty array.
- marks: use the number printed next to that specific sub-part (usually 1, sometimes
  2). If truly not printed for a sub-part, use 1.

diagram_dependent: true only if the sub-part explicitly requires seeing a table,
image, or figure that isn't reproducible as plain text (rare in this paper — most
"tables" are simple option grids that ARE representable as text options).

Do not invent content. If a sub-part's text is genuinely unclear from the raw
extraction, still include it with your best-effort question_text rather than
dropping it — dropping questions is worse than an imperfect transcription."""


def extract_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def strip_page_furniture(text: str) -> str:
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text)
    text = re.sub(
        r"\*Please note that the assessment scheme.*?2025-26", "", text, flags=re.DOTALL
    )
    return text


def extract_questions_via_llm(full_text: str, subject_label: str) -> list[dict]:
    # Called directly (bypassing ask_llm's provider-of-the-moment routing) —
    # this is a one-shot, large single call (big prompt, big expected JSON
    # response) where reliability matters more than speed. Tried three
    # candidates head-to-head on this exact workload: Venice's
    # e2ee-gpt-oss-20b-p timed out twice (>10min); Ollama Cloud's gpt-oss:20b
    # "succeeded" but returned an empty/degenerate response (~200 completion
    # tokens for what should be thousands); Venice's gemini-3-5-flash-lite
    # completed in ~200s with a correct, well-formed, schema-matching
    # response. Pin to that regardless of whatever provider is globally
    # configured right now (other concurrent jobs are actively changing it).
    force_refresh_settings()
    venice_key = get_effective_settings().get("venice_api_key")
    client = OpenAI(api_key=venice_key, base_url="https://api.venice.ai/api/v1", timeout=300.0, max_retries=0)

    user_prompt = (
        f"Here is the raw extracted text of a CBSE Class X {subject_label} sample "
        f"question paper (2025-26). Extract the structured question list per the "
        f"schema and rules above.\n\n{full_text}"
    )
    resp = client.chat.completions.create(
        model="gemini-3-5-flash-lite",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        max_tokens=24000,
    )
    raw = resp.choices[0].message.content or ""
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in LLM response (len={len(raw)}): {raw[:300]!r}")
    return json.loads(raw[start:end + 1])


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-assisted extraction for CBSE English sample papers")
    parser.add_argument("--pdf", help="Source PDF (mutually exclusive with --from-json)")
    parser.add_argument("--from-json", help="Load already-extracted/corrected questions JSON instead of calling the LLM")
    parser.add_argument("--subject-label", default="English", help="Human label used in the LLM prompt, e.g. 'English Language and Literature'")
    parser.add_argument("--grade", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--subject-variant", default="")
    parser.add_argument("--academic-year", required=True)
    parser.add_argument("--source-subject-code", required=True)
    parser.add_argument("--question-paper-url", default="")
    parser.add_argument("--marking-scheme-url", default="")
    parser.add_argument("--source-page-url", default="")
    parser.add_argument("--create-paper", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="questions_extracted.json")
    args = parser.parse_args()

    if args.from_json:
        questions = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        pdf_name = Path(args.from_json).name
    elif args.pdf:
        pdf_path = Path(args.pdf)
        pages = extract_pages(pdf_path)
        full_text = strip_page_furniture("\n".join(pages))
        print(f"Extracted {len(full_text)} chars from {len(pages)} pages, calling LLM...")
        questions = extract_questions_via_llm(full_text, args.subject_label)
        pdf_name = pdf_path.name
    else:
        print("Pass either --pdf or --from-json")
        sys.exit(1)

    by_type: dict[str, int] = {}
    for q in questions:
        by_type[q.get("question_type", "?")] = by_type.get(q.get("question_type", "?"), 0) + 1

    print(f"Extracted {len(questions)} question rows from {pdf_name}")
    print(f"  By type: {by_type}")

    Path(args.output).write_text(json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote {args.output}")

    if args.dry_run:
        print("[dry-run] skipping DB writes")
        return

    db = get_content_db(args.grade)

    if args.create_paper:
        # If this paper already exists and is "active" (fully answered), a
        # re-run (e.g. to patch one question) must not downgrade its status
        # back to pending_answers and hide it from students again.
        already_active = (
            db.table("board_sample_papers")
            .select("status")
            .eq("board", BOARD).eq("academic_year", args.academic_year)
            .eq("grade", args.grade).eq("source_subject_code", args.source_subject_code)
            .execute()
        )
        preserve_status = (
            already_active.data[0]["status"]
            if already_active.data and already_active.data[0]["status"] == "active"
            else "pending_answers"
        )
        result = (
            db.table("board_sample_papers")
            .upsert({
                "board": BOARD,
                "academic_year": args.academic_year,
                "grade": args.grade,
                "subject": args.subject,
                "subject_variant": args.subject_variant,
                "source_subject_code": args.source_subject_code,
                "question_paper_url": args.question_paper_url,
                "marking_scheme_url": args.marking_scheme_url,
                "source_page_url": args.source_page_url,
                # Not "active" yet — the paper's questions have no answers,
                # unless this is a re-run on an already-answered paper.
                "status": preserve_status,
            }, on_conflict="board,academic_year,grade,source_subject_code")
            .execute()
        )
        paper_id = result.data[0]["id"]
        print(f"  Paper row: {paper_id}")
    else:
        existing = (
            db.table("board_sample_papers")
            .select("id")
            .eq("board", BOARD).eq("academic_year", args.academic_year)
            .eq("grade", args.grade).eq("source_subject_code", args.source_subject_code)
            .execute()
        )
        if not existing.data:
            print("  [error] no existing paper row found — pass --create-paper")
            sys.exit(1)
        paper_id = existing.data[0]["id"]

    stored = 0
    for q in questions:
        db.table("board_sample_paper_questions").upsert({
            "paper_id": paper_id,
            "question_number": str(q["question_number"]),
            "section": q.get("section", "A"),
            "question_type": q.get("question_type", "short_answer"),
            "marks": q.get("marks", 1),
            "question_text": q.get("question_text", ""),
            "options": q.get("options", []),
            "diagram_dependent": q.get("diagram_dependent", False),
            "status": "extracted",
        }, on_conflict="paper_id,question_number").execute()
        stored += 1
    print(f"  Upserted {stored} question rows (status=extracted, no answers yet)")


if __name__ == "__main__":
    main()
