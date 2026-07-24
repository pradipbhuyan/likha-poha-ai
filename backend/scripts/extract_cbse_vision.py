#!/usr/bin/env python3
"""
Vision-based CBSE SQP extractor for papers where pypdf emits garbled text
(custom math/Hindi fonts) or where questions are embedded as images.

Renders each PDF page as a JPEG image via PyMuPDF, then sends it to the
NVIDIA NIM vision model (microsoft/phi-4-multimodal-instruct) to extract
questions in structured JSON.  Falls back to nvidia/llama-3.2-11b-vision-instruct
if the primary model is unavailable.

Usage:
    cd backend
    .venv/bin/python3 scripts/extract_cbse_vision.py \\
        --pdf scripts/cbse_pilot_data/g12_2024-25_Maths-SQP.pdf \\
        --grade "Grade 12" --subject "Mathematics" \\
        --academic-year "2024-25" --source-subject-code Maths \\
        --output scripts/cbse_pilot_data/g12_2024-25_Maths.json \\
        --dry-run

    # Drop --dry-run and add --create-paper + URL args to upload to Supabase.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # PyMuPDF
from openai import OpenAI

from app.services.grade_db_router import get_content_db
from app.services.openai_service import get_effective_settings, NVIDIA_BASE_URL

BOARD = "CBSE"

# Vision models to try (in order) — confirmed available on NVIDIA NIM free tier
VISION_MODELS = [
    "meta/llama-3.2-11b-vision-instruct",
    "microsoft/phi-3-vision-128k-instruct",
    "meta/llama-3.2-90b-vision-instruct",
]

SYSTEM_PROMPT = """You are a CBSE exam question extractor. You will be given an image of a page 
from a CBSE sample question paper. Extract ALL questions visible on this page.

Return a JSON array. Each element must have exactly these fields:
{
  "question_number": <integer>,
  "section": "<single uppercase letter A-E>",
  "question_type": "<one of: mcq, assertion_reason, short_answer, long_answer, case_study>",
  "marks": <integer 1-5>,
  "question_text": "<full question text including any sub-parts, NOT including option labels>",
  "options": ["<option A text>", "<option B text>", "<option C text>", "<option D text>"] or [],
  "diagram_dependent": <true or false>
}

Rules:
- question_type is determined by marks: 1=mcq or assertion_reason, 2-3=short_answer, 4=case_study, 5=long_answer
- For mcq/assertion_reason, options MUST have exactly 4 strings (the option text WITHOUT the (A)(B)(C)(D) labels)
- For non-mcq questions, options = []
- diagram_dependent = true if the question cannot be answered without seeing a figure/diagram/graph
- If a question is an Assertion-Reason type, set question_type to assertion_reason
- Include ALL questions on the page including case-study sub-parts as separate entries if numbered
- If no questions are visible on this page (e.g. cover page, instructions only), return []
- Return ONLY valid JSON — no markdown, no explanation"""


def render_page_as_jpeg(page: fitz.Page, dpi: int = 200) -> bytes:
    """Render a PDF page to JPEG bytes at the given DPI."""
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return pix.tobytes("jpeg", jpg_quality=85)


def extract_questions_from_image(
    image_bytes: bytes,
    client: OpenAI,
    model: str,
    page_num: int,
    max_retries: int = 3,
) -> list[dict]:
    """Send a page image to the vision model and parse the returned JSON."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64}"

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Extract all questions from this page (page {page_num + 1}) of the CBSE sample paper. Return ONLY a JSON array.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()

            if not raw or raw == "[]":
                return []

            # Fix unescaped backslashes in LaTeX math notation that the model
            # emits as raw \frac, \sqrt, \pi etc. — invalid in JSON strings.
            # Strategy: replace lone backslashes (not already \\) with \\
            raw_fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
            try:
                questions = json.loads(raw_fixed)
            except json.JSONDecodeError:
                questions = json.loads(raw)  # fallback to original if fix made things worse
            if not isinstance(questions, list):
                print(f"  [warn] Page {page_num+1}: model returned non-list, skipping")
                return []

            # Validate and normalise each question
            cleaned = []
            for q in questions:
                try:
                    q_num = int(q.get("question_number", 0))
                    if q_num <= 0:
                        continue
                    marks = int(q.get("marks", 1))
                    opts = q.get("options") or []
                    cleaned.append({
                        "question_number": q_num,
                        "section": str(q.get("section", "A")).upper()[:1],
                        "question_type": str(q.get("question_type", "short_answer")),
                        "marks": marks,
                        "question_text": str(q.get("question_text", "")).strip(),
                        "options": [str(o).strip() for o in opts] if opts else [],
                        "diagram_dependent": bool(q.get("diagram_dependent", False)),
                    })
                except (ValueError, TypeError):
                    continue
            return cleaned

        except json.JSONDecodeError as e:
            print(f"  [warn] Page {page_num+1} attempt {attempt+1}: JSON parse error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                wait = 10 * (attempt + 1)
                print(f"  [rate-limit] Page {page_num+1}: waiting {wait}s...")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                print(f"  [warn] Page {page_num+1} attempt {attempt+1}: {err[:120]}")
                time.sleep(3)
            else:
                print(f"  [error] Page {page_num+1}: {err[:200]}")
    return []


def get_vision_client_and_model(settings: dict) -> tuple[OpenAI, str]:
    """Build the NVIDIA NIM client. Use the first model in VISION_MODELS — no probe,
    since NVIDIA NIM's model-list endpoint confirms availability; probing with a
    synthetic tiny JPEG caused false 404/410 errors on older probe bytes."""
    nvidia_key = settings.get("nvidia_api_key") or ""
    if not nvidia_key:
        raise RuntimeError("No NVIDIA API key found in settings. Configure it in Admin → AI.")
    client = OpenAI(api_key=nvidia_key, base_url=NVIDIA_BASE_URL, timeout=60.0)
    model = VISION_MODELS[0]
    print(f"  Using vision model: {model}")
    return client, model


def extract_pdf_with_vision(pdf_path: Path, dpi: int = 200) -> list[dict]:
    """Extract all questions from a PDF using page-by-page vision extraction."""
    settings = get_effective_settings()
    client, model = get_vision_client_and_model(settings)

    doc = fitz.open(str(pdf_path))
    all_questions: dict[int, dict] = {}  # keyed by question_number, last write wins

    print(f"  Processing {len(doc)} pages with vision model {model}...")

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_bytes = render_page_as_jpeg(page, dpi=dpi)
        print(f"  Page {page_num+1}/{len(doc)}: {len(image_bytes)//1024}KB", end="", flush=True)

        page_questions = extract_questions_from_image(image_bytes, client, model, page_num)
        print(f" → {len(page_questions)} questions")

        for q in page_questions:
            qn = q["question_number"]
            # If we already have this question, keep the one with more content
            if qn not in all_questions or len(q["question_text"]) > len(all_questions[qn]["question_text"]):
                all_questions[qn] = q

        # Small delay to avoid rate-limiting
        if page_num < len(doc) - 1:
            time.sleep(1)

    doc.close()
    return sorted(all_questions.values(), key=lambda q: q["question_number"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Vision-based CBSE SQP extractor")
    parser.add_argument("--pdf", required=True)
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
    parser.add_argument("--output", default="questions_extracted_vision.json")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    print(f"Extracting (vision): {pdf_path.name}")

    questions = extract_pdf_with_vision(pdf_path, dpi=args.dpi)

    # Remove null bytes just in case
    for q in questions:
        q["question_text"] = q["question_text"].replace("\x00", "")
        q["options"] = [o.replace("\x00", "") for o in q["options"]]

    by_type: dict[str, int] = {}
    diagram_count = 0
    for q in questions:
        by_type[q["question_type"]] = by_type.get(q["question_type"], 0) + 1
        if q["diagram_dependent"]:
            diagram_count += 1

    print(f"Parsed {len(questions)} questions from {pdf_path.name}")
    print(f"  By type: {by_type}")
    print(f"  Flagged diagram-dependent: {diagram_count}")
    print(f"  Sections seen: {sorted(set(q['section'] for q in questions))}")

    Path(args.output).write_text(json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote {args.output}")

    if args.dry_run:
        print("[dry-run] skipping DB writes")
        return

    db = get_content_db(args.grade)

    paper_id = None
    if args.create_paper:
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
                "status": "pending_answers",
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
            "question_number": q["question_number"],
            "section": q["section"],
            "question_type": q["question_type"],
            "marks": q["marks"],
            "question_text": q["question_text"],
            "options": q["options"],
            "diagram_dependent": q["diagram_dependent"],
            "status": "extracted",
        }, on_conflict="paper_id,question_number").execute()
        stored += 1
    print(f"  Upserted {stored} question rows (status=extracted, no answers yet)")


if __name__ == "__main__":
    main()
