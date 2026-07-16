#!/usr/bin/env python3
"""
generate_formula_prompt.py — Generate exhaustive LLM prompts for CBSE formula seeding.

The original single-shot prompt "Generate ALL formulas for Grade 12 Maths" only returns
5-10 formulas because LLMs summarize. This script generates CHAPTER-SPECIFIC prompts
that reliably return 15-40+ formulas per chapter.

Usage:
    cd backend

    # List available chapters for a grade
    python3 scripts/generate_formula_prompt.py list --grade "Grade 12" --subject "Mathematics"

    # Generate prompt for ONE chapter (recommended workflow)
    python3 scripts/generate_formula_prompt.py prompt --grade "Grade 12" --subject "Mathematics" --chapter "Integrals"

    # Generate prompts for ALL chapters (prints them sequentially)
    python3 scripts/generate_formula_prompt.py all --grade "Grade 12" --subject "Mathematics"

After ChatGPT responds:
    pbpaste | python3 scripts/generate_formula_prompt.py import \
        --grade "Grade 12" --subject "Mathematics" \
        --api http://localhost:8000 --token YOUR_ADMIN_JWT
"""

import argparse
import json
import sys
import os

# ── NCERT Chapter lists by grade/subject ──────────────────────────────────────

CHAPTERS = {
    ("Grade 12", "Mathematics"): [
        "Relations and Functions",
        "Inverse Trigonometric Functions",
        "Matrices",
        "Determinants",
        "Continuity and Differentiability",
        "Application of Derivatives",
        "Integrals",
        "Application of Integrals",
        "Differential Equations",
        "Vector Algebra",
        "Three Dimensional Geometry",
        "Linear Programming",
        "Probability",
    ],
    ("Grade 11", "Mathematics"): [
        "Sets",
        "Relations and Functions",
        "Trigonometric Functions",
        "Principle of Mathematical Induction",
        "Complex Numbers and Quadratic Equations",
        "Linear Inequalities",
        "Permutations and Combinations",
        "Binomial Theorem",
        "Sequences and Series",
        "Straight Lines",
        "Conic Sections",
        "Introduction to Three Dimensional Geometry",
        "Limits and Derivatives",
        "Statistics",
        "Probability",
    ],
    ("Grade 10", "Mathematics"): [
        "Real Numbers",
        "Polynomials",
        "Pair of Linear Equations in Two Variables",
        "Quadratic Equations",
        "Arithmetic Progressions",
        "Triangles",
        "Coordinate Geometry",
        "Introduction to Trigonometry",
        "Some Applications of Trigonometry",
        "Circles",
        "Areas Related to Circles",
        "Surface Areas and Volumes",
        "Statistics",
        "Probability",
    ],
    ("Grade 9", "Mathematics"): [
        "Number Systems",
        "Polynomials",
        "Coordinate Geometry",
        "Linear Equations in Two Variables",
        "Introduction to Euclid's Geometry",
        "Lines and Angles",
        "Triangles",
        "Quadrilaterals",
        "Circles",
        "Heron's Formula",
        "Surface Areas and Volumes",
        "Statistics",
        "Probability",
    ],
}

# ── Schema description ─────────────────────────────────────────────────────────

SCHEMA = """JSON schema for each formula object:
{
  "formula_name": "Short descriptive name (e.g. 'Area of Circle')",
  "expression": "Human-readable expression (e.g. 'A = π r²')",
  "expression_latex": "LaTeX version (e.g. 'A = \\\\pi r^2')",
  "chapter": "Exact chapter name as provided",
  "topic": "Sub-topic or section within the chapter",
  "chapter_order": <integer, chapter number in syllabus>,
  "display_order": <integer, order within chapter starting from 1>,
  "difficulty": "easy | medium | hard",
  "explanation": "One sentence explaining what the formula calculates",
  "variables": "List all variables with meanings (e.g. 'r = radius, A = area')",
  "example": "One worked numerical example (e.g. 'r=7 → A=154 cm²')",
  "memory_tip": "Short mnemonic or memory trick (optional)",
  "tags": ["array", "of", "keywords"]
}"""


def build_prompt(grade: str, subject: str, chapter: str, chapter_order: int) -> str:
    """Build an exhaustive formula-generation prompt for one chapter."""

    return f"""You are generating CBSE NCERT formula data for the Likha Poha AI education platform.

TASK: Generate EVERY formula, identity, theorem, rule, and important result from:
  Grade: {grade}
  Subject: {subject}
  Chapter: {chapter} (Chapter {chapter_order} in NCERT)

CRITICAL RULES:
1. Include EVERY formula — do NOT summarize, do NOT skip, do NOT say "and similar formulas".
2. Each formula must be a SEPARATE JSON object. Never combine multiple formulas into one entry.
3. For chapters with 20+ formulas (like Integrals, Derivatives), include ALL of them.
4. Use the EXACT schema below — every field matters for the database.
5. Output ONLY a valid JSON array. No markdown. No explanation. No code fences.
6. Minimum expected count: at least 15-20 formula objects for most chapters, 30+ for Integrals/Derivatives.

{SCHEMA}

IMPORTANT for {chapter}:
- Include ALL standard results and special cases
- Include proofs/derivation results where CBSE exams test them
- Include both formulas and their conditions/constraints
- Include geometric interpretations where applicable
- Difficulty: mark common exam formulas as "medium", basic definitions as "easy", 
  tricky applications as "hard"

Output ONLY the JSON array starting with [ and ending with ]
"""


def cmd_list(args):
    """List available chapters."""
    key = (args.grade, args.subject)
    chapters = CHAPTERS.get(key)
    if not chapters:
        print(f"No chapter list for {args.grade} / {args.subject}")
        print("Available combinations:")
        for g, s in CHAPTERS:
            print(f"  --grade \"{g}\" --subject \"{s}\"")
        return
    print(f"\nChapters for {args.grade} {args.subject}:")
    for i, ch in enumerate(chapters, 1):
        print(f"  {i:2}. {ch}")
    print(f"\nTotal: {len(chapters)} chapters")
    print(f"\nGenerate a prompt:\n  python3 scripts/generate_formula_prompt.py prompt \\")
    print(f'    --grade "{args.grade}" --subject "{args.subject}" \\')
    print(f'    --chapter "{chapters[0]}"')


def cmd_prompt(args):
    """Print the prompt for one chapter."""
    key = (args.grade, args.subject)
    chapters = CHAPTERS.get(key, [])
    chapter_order = chapters.index(args.chapter) + 1 if args.chapter in chapters else 1

    prompt = build_prompt(args.grade, args.subject, args.chapter, chapter_order)

    print("=" * 72)
    print(f"FORMULA PROMPT — {args.grade} / {args.subject} / {args.chapter}")
    print("=" * 72)
    print()
    print("Paste the text below into ChatGPT (GPT-4o recommended).")
    print("The response will be a JSON array — copy ALL of it.")
    print()
    print("-" * 72)
    print(prompt)
    print("-" * 72)
    print()
    print("After ChatGPT responds, store via:")
    g = args.grade
    s = args.subject
    ch = args.chapter
    print(f'  pbpaste | python3 scripts/generate_formula_prompt.py import \\')
    print(f'    --grade "{g}" --subject "{s}" --chapter "{ch}" \\')
    print(f'    --api http://localhost:8000 --token YOUR_ADMIN_JWT')


def cmd_all(args):
    """Print prompts for ALL chapters."""
    key = (args.grade, args.subject)
    chapters = CHAPTERS.get(key)
    if not chapters:
        print(f"No chapters configured for {args.grade} / {args.subject}")
        return

    print(f"\nGenerating prompts for ALL {len(chapters)} chapters of {args.grade} {args.subject}")
    print("Run each prompt through ChatGPT separately for best results.\n")

    for i, chapter in enumerate(chapters, 1):
        prompt = build_prompt(args.grade, args.subject, chapter, i)
        print("=" * 72)
        print(f"CHAPTER {i}/{len(chapters)}: {chapter}")
        print("=" * 72)
        print(prompt)
        print()


def cmd_import(args):
    """Import JSON from stdin into the formula_sheets table via the API."""
    try:
        import requests as req
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)

    raw = sys.stdin.read().strip()

    # Try to extract JSON array if there's surrounding text
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        print("ERROR: No JSON array found in input. Make sure you copied the full ChatGPT response.")
        sys.exit(1)

    json_text = raw[start:end + 1]

    try:
        formulas = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        print("First 200 chars:", json_text[:200])
        sys.exit(1)

    if not isinstance(formulas, list):
        print("ERROR: Expected a JSON array of formula objects.")
        sys.exit(1)

    print(f"Parsed {len(formulas)} formulas. Importing...")

    payload = {
        "grade": args.grade,
        "subject": args.subject,
        "formulas": formulas,
    }

    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    url = f"{args.api.rstrip('/')}/api/admin/formula-sheets/import"
    resp = req.post(url, json=payload, headers=headers, timeout=60)

    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Import complete:")
        print(f"   Inserted: {result.get('inserted', 0)}")
        print(f"   Updated:  {result.get('updated', 0)}")
        print(f"   Skipped:  {result.get('skipped', 0)}")
        errors = result.get("errors", [])
        if errors:
            print(f"   Errors:   {len(errors)}")
            for e in errors[:5]:
                print(f"     - {e}")
    else:
        print(f"❌ HTTP {resp.status_code}: {resp.text[:500]}")


def main():
    parser = argparse.ArgumentParser(description="Generate formula prompts for CBSE seeding")
    sub = parser.add_subparsers(dest="cmd")

    # list
    p_list = sub.add_parser("list", help="List chapters for a grade/subject")
    p_list.add_argument("--grade", required=True)
    p_list.add_argument("--subject", required=True)

    # prompt
    p_prompt = sub.add_parser("prompt", help="Print prompt for one chapter")
    p_prompt.add_argument("--grade", required=True)
    p_prompt.add_argument("--subject", required=True)
    p_prompt.add_argument("--chapter", required=True)

    # all
    p_all = sub.add_parser("all", help="Print prompts for all chapters")
    p_all.add_argument("--grade", required=True)
    p_all.add_argument("--subject", required=True)

    # import
    p_imp = sub.add_parser("import", help="Import JSON from stdin into the API")
    p_imp.add_argument("--grade", required=True)
    p_imp.add_argument("--subject", required=True)
    p_imp.add_argument("--chapter", help="Chapter name (optional, for logging)")
    p_imp.add_argument("--api", default="http://localhost:8000", help="Backend API base URL")
    p_imp.add_argument("--token", help="Admin JWT token")

    args = parser.parse_args()

    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "prompt":
        cmd_prompt(args)
    elif args.cmd == "all":
        cmd_all(args)
    elif args.cmd == "import":
        cmd_import(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
