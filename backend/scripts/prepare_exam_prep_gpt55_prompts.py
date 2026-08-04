#!/usr/bin/env python3
"""
Phase 1 driver for the Exam Prep Center coverage review: prepare GPT-5.5
authoring prompts for the three genuine zero-coverage gaps confirmed after
careful chapter-name normalization (see the coverage review artifact):

  - NEET UG Biology: 9 chapters with zero questions (50% of NEET's marks)
  - CUET UG Chemistry (Domain): 0 questions, 7 priority topics
  - CUET UG Legal Studies: 0 questions, 5 priority topics

Mirrors the CBSE question_bank GPT-5.5 handoff pattern used earlier this
session (prepare_gpt55_question_prompts.py): generate one prompt file per
target, write to a Downloads folder, human runs each through GPT-5.5, saves
the JSON response, then ingest_exam_prep_gpt55_output.py imports the results
via the platform's own validated admin_import_bulk() path (including the
subject/EXAM_SUBJECTS_MAP mapping-integrity check).

The prompt template mirrors run_prewarm_job()'s proven system/user prompt
(app/services/exam_prep_service.py) — the exact mechanism that produced the
existing 1,843 published questions — so authoring style and difficulty
calibration stay consistent with the rest of the bank.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # backend/

OUT_DIR = Path.home() / "Downloads" / "GPT55_ExamPrep_Prompts"

# (exam_type, exam_label, subject, chapter, topic, grade, question_count)
TARGETS: list[tuple[str, str, str, str, str, str, int]] = [
    # ── NEET UG Biology — 9 genuinely zero-coverage chapters ──────────────────
    ("neet_ug", "NEET UG", "Biology", "Anatomy of Flowering Plants", "Anatomy of Flowering Plants", "Grade 11", 15),
    ("neet_ug", "NEET UG", "Biology", "Biological Classification", "Biological Classification", "Grade 11", 15),
    ("neet_ug", "NEET UG", "Biology", "Locomotion and Movement", "Locomotion and Movement", "Grade 11", 15),
    ("neet_ug", "NEET UG", "Biology", "Microbes in Human Welfare", "Microbes in Human Welfare", "Grade 12", 15),
    ("neet_ug", "NEET UG", "Biology", "Mineral Nutrition", "Mineral Nutrition", "Grade 11", 15),
    ("neet_ug", "NEET UG", "Biology", "Reproductive Health", "Reproductive Health", "Grade 12", 15),
    ("neet_ug", "NEET UG", "Biology", "Sexual Reproduction in Flowering Plants", "Sexual Reproduction in Flowering Plants", "Grade 12", 15),
    ("neet_ug", "NEET UG", "Biology", "Structural Organisation in Animals", "Structural Organisation in Animals", "Grade 11", 15),
    ("neet_ug", "NEET UG", "Biology", "Transport in Plants", "Transport in Plants", "Grade 11", 15),
    # ── CUET UG Chemistry (Domain) — 7 priority topics, 0 questions ───────────
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Chemical Bonding and Molecular Structure", "Chemical Bonding", "Grade 11", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Electrochemistry", "Electrochemistry", "Grade 12", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Haloalkanes and Haloarenes", "Organic Mechanisms", "Grade 12", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Equilibrium", "Equilibrium", "Grade 11", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Coordination Compounds", "Coordination Compounds", "Grade 12", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "Aldehydes, Ketones and Carboxylic Acids", "Organic Compounds", "Grade 12", 6),
    ("cuet_ug", "CUET UG", "Chemistry (Domain)", "p-Block Elements", "p-Block Elements", "Grade 12", 6),
    # ── CUET UG Legal Studies — 5 priority topics, 0 questions ────────────────
    ("cuet_ug", "CUET UG", "Legal Studies", "Nature of Law", "Nature of Law", "Grade 11", 8),
    ("cuet_ug", "CUET UG", "Legal Studies", "Constitution as the Supreme Law", "Indian Constitution", "Grade 11", 8),
    ("cuet_ug", "CUET UG", "Legal Studies", "Judiciary", "Judiciary System", "Grade 12", 8),
    ("cuet_ug", "CUET UG", "Legal Studies", "Criminal Justice System", "Criminal & Civil Law", "Grade 12", 8),
    ("cuet_ug", "CUET UG", "Legal Studies", "International Law", "International Law", "Grade 12", 8),
]

PROMPT_TEMPLATE = """You are an expert assessment designer and senior question setter for Indian competitive examinations.

Your responsibility is to generate ORIGINAL, HIGH-QUALITY, COMPLETE multiple-choice questions.

Target Exam: {exam_label}
Subject: {subject}
Chapter: {chapter}
Topic focus: {topic}
Grade: {grade}
Number of questions: {question_count}
Difficulty mix: 30% Easy, 50% Moderate, 20% Difficult

=== ABSOLUTE REQUIREMENTS ===

A. EVERY QUESTION MUST HAVE ALL 4 OPTIONS (A, B, C, D)
   - All 4 options must be populated with meaningful, distinct content.
   - No "All of the above" / "None of the above".

B. EVERY QUESTION MUST HAVE A COMPLETE EXPLANATION
   - Explain WHY the correct answer is correct (show the full working).

C. NO DUPLICATE CONCEPTS
   - Each question MUST test a DIFFERENT concept/formula/idea within {chapter}.
   - Do NOT ask two questions that test the same formula with different numbers.

D. DIFFICULTY CALIBRATION:
   - Easy: Direct single-concept, one formula/fact, answer in <=2 steps.
   - Moderate: Two-step reasoning, one small calculation, conceptual application.
   - Hard: Multi-concept integration, non-obvious approach, requires analysis.

E. EXAM STANDARD for {exam_label}:
   {exam_standard}

F. OPTION QUALITY:
   - 3 plausible distractors — wrong answers that arise from common mistakes.
   - Randomize which letter (A/B/C/D) is correct across the batch.

G. SELF-CHECK before outputting each question:
   - Exactly 4 non-empty, distinct options?
   - Is the correct answer definitely correct?
   - Is the explanation complete?
   - Is the concept unique in this batch?
   - Is all numerical/factual data consistent (no contradictions)?
   If any check fails, rewrite before outputting.

=== OUTPUT FORMAT ===

Return ONLY a JSON array, nothing else — no markdown fences, no commentary.
Each element must follow this EXACT shape:

[
  {{
    "question_text": "...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_option": "B",
    "detailed_explanation": "Full step-by-step reasoning for the correct answer.",
    "solution_steps": ["Step 1 ...", "Step 2 ...", "Step 3 ..."],
    "formula_used": "...",
    "ncert_reference": "NCERT {grade} — {chapter}",
    "difficulty": "medium",
    "subtopic": "..."
  }}
]

Generate exactly {question_count} questions now, following the format above precisely.
"""

_EXAM_STANDARD = {
    "neet_ug": "NCERT-centric. Biology: exact NCERT terminology. Conceptual clarity over tricks.",
    "cuet_ug": "Conceptual focus. NCERT-based. Minimal lengthy calculations. Domain-paper standard.",
}


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index_lines = [
        "GPT-5.5 Exam Prep Center authoring — Phase 1 zero-coverage gaps",
        "=" * 78,
        "",
        "For each chapter/topic below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <slug>_questions.json in this folder.",
        "  4. Once all are done, ingest them all in one command:",
        "",
        "     cd backend",
        f"     ./venv/bin/python scripts/ingest_exam_prep_gpt55_output.py --dir {OUT_DIR} --dry-run",
        f"     ./venv/bin/python scripts/ingest_exam_prep_gpt55_output.py --dir {OUT_DIR}",
        "",
        "All imports land as status=draft (admin_import_bulk's own behavior) —",
        "nothing goes live to students until explicitly published after review.",
        "",
        "Targets:",
    ]

    manifest = []
    for i, (exam_type, exam_label, subject, chapter, topic, grade, qcount) in enumerate(TARGETS, start=1):
        prompt_text = PROMPT_TEMPLATE.format(
            exam_label=exam_label, subject=subject, chapter=chapter, topic=topic,
            grade=grade, question_count=qcount,
            exam_standard=_EXAM_STANDARD.get(exam_type, "NCERT-based conceptual standard."),
        )
        slug = _slugify(f"{exam_type}_{subject}_{chapter}")
        prompt_path = OUT_DIR / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        expected_json = f"{slug}_questions.json"
        manifest.append({
            "index": i,
            "exam_type": exam_type,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,
            "grade": grade,
            "question_count": qcount,
            "expected_json": expected_json,
        })

        print(f"[{i:02d}] {exam_label} / {subject} / {chapter} -> {prompt_path.name} "
              f"({qcount} questions, {len(prompt_text):,} chars)")

        index_lines.append(f"  [{i:02d}] {exam_label} / {subject} / {chapter}  ({qcount} questions)")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {expected_json}")

    (OUT_DIR / "00_README_and_index.txt").write_text("\n".join(index_lines), encoding="utf-8")
    (OUT_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_q = sum(t[6] for t in TARGETS)
    print(f"\nDone. {len(TARGETS)} prompts written to {OUT_DIR} ({total_q} questions total once authored).")


if __name__ == "__main__":
    main()
