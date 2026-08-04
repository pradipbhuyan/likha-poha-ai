#!/usr/bin/env python3
"""
Month 2 of the 8-month Exam Prep Center question-bank release plan.

Target: 1.5x session-depth floor across every subject. Recomputed live
against the current database (not the original report's stale estimate) —
Month 1 already closed the below-1.0x gap for 8 CUET subjects, so this
month's gap looks different: all 15 CUET subjects need topping up (the 8
Month-1 subjects landed exactly at 1.0x = 40, so each needs another 20;
Biology (Domain)/History/Legal Studies were the Month-1 leftovers, deferred
then because they only needed 1-2 questions — now genuinely due for volume).
No other exam (JEE/NEET/SAT/IELTS/TOEFL) needs anything this month; all are
already comfortably above 1.5x.

Same pattern as Month 1: one prompt per SUBJECT (not per topic), with a
per-topic question-count table embedded (weightage-proportional, largest-
remainder rounding), plus every existing question for that subject listed
as a "do not repeat" block. See prepare_exam_prep_month1_prompts.py for the
full rationale.

Usage:
    cd backend
    ./venv/bin/python scripts/prepare_exam_prep_month2_prompts.py

Then: run each prompt through GPT-5.5, save as <slug>_questions.json in the
output folder, and ingest with ingest_exam_prep_month2_output.py (dry-run first).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # backend/

import app.services.exam_prep_service as ep  # noqa: E402
from app.services.auth_service import admin_client  # noqa: E402

OUT_DIR = Path.home() / "Downloads" / "GPT55_ExamPrep_Month2_Prompts"

# (subject, question_count, grade) — gap to reach 1.5x target_per_session,
# recomputed live at prompt-generation time (see module docstring).
MONTH2_TARGETS: list[tuple[str, int, str]] = [
    ("Biology (Domain)", 22, "Grade 12"),
    ("History", 21, "Grade 12"),
    ("Legal Studies", 21, "Grade 12"),
    ("Hindi", 20, "Grade 12"),
    ("General Test", 20, "Grade 12"),
    ("Physics (Domain)", 20, "Grade 12"),
    ("Mathematics (Domain)", 20, "Grade 12"),
    ("Economics", 20, "Grade 12"),
    ("Accountancy", 20, "Grade 12"),
    ("Business Studies", 20, "Grade 12"),
    ("Psychology", 20, "Grade 12"),
    ("Chemistry (Domain)", 19, "Grade 12"),
    ("Geography", 12, "Grade 12"),
    ("Sociology", 12, "Grade 12"),
    ("English", 11, "Grade 12"),
]


def _allocate(total: int, weights: list[int]) -> list[int]:
    """Largest-remainder proportional allocation, minimum 1 per topic."""
    n = len(weights)
    raw = [total * w / sum(weights) for w in weights]
    base = [max(1, int(x)) for x in raw]
    diff = total - sum(base)
    order = sorted(range(n), key=lambda i: (raw[i] - int(raw[i])), reverse=True)
    i = 0
    while diff > 0:
        base[order[i % n]] += 1
        diff -= 1
        i += 1
    while diff < 0:
        idx = max(range(n), key=lambda i: base[i])
        base[idx] -= 1
        diff += 1
    return base


def _existing_question_stems(subject: str) -> list[str]:
    """Every existing question's text for this CUET subject (excluding
    archived rows), embedded in the prompt so GPT-5.5 knows what's already
    in the bank and must not repeat or lightly reword."""
    rows = (
        admin_client.table("exam_prep_questions")
        .select("question_text")
        .eq("exam_type", "cuet_ug").eq("subject", subject)
        .neq("status", "archived")
        .execute().data
    )
    return [r["question_text"] for r in rows if r.get("question_text")]


PROMPT_TEMPLATE = """You are an expert assessment designer and senior question setter for Indian competitive examinations.

Your responsibility is to generate ORIGINAL, HIGH-QUALITY, COMPLETE multiple-choice questions for a CUET UG domain-subject paper.

Target Exam: CUET UG
Subject: {subject}
Grade: {grade}
Total questions: {total}
Difficulty mix: 30% Easy, 50% Moderate, 20% Difficult

=== TOPIC BREAKDOWN — WRITE EXACTLY THIS MANY QUESTIONS PER TOPIC ===
{topic_table}
(Total across all topics must equal {total}.)

=== EXISTING QUESTIONS ALREADY IN THE BANK FOR THIS SUBJECT — DO NOT REPEAT ===
{existing_questions_block}
Every question you write must test a DIFFERENT fact, concept, or angle than
every question listed above. A reworded, renumbered, or parameter-changed
version of any of them (e.g. same concept with different numbers, or the
same fact asked from the opposite direction) still counts as a repeat and
must be avoided.

=== ABSOLUTE REQUIREMENTS ===

A. EVERY QUESTION MUST HAVE ALL 4 OPTIONS (A, B, C, D)
   - All 4 options must be populated with meaningful, distinct content.
   - No "All of the above" / "None of the above".

B. EVERY QUESTION MUST HAVE A COMPLETE EXPLANATION
   - Explain WHY the correct answer is correct (show the full working).
   - CRITICAL: the explanation's final stated conclusion must name the SAME
     letter as "correct_option". Double check this before outputting —
     mismatches between the two are the most common defect in past batches.

C. NO DUPLICATE CONCEPTS WITHIN A TOPIC OR AGAINST THE EXISTING BANK
   - Each question within the same topic MUST test a different sub-concept.
   - No question may duplicate or closely paraphrase anything in the "existing questions" list above.

D. DIFFICULTY CALIBRATION:
   - Easy: Direct single-concept, one formula/fact, answer in <=2 steps.
   - Moderate: Two-step reasoning, one small calculation, conceptual application.
   - Hard: Multi-concept integration, non-obvious approach, requires analysis.

E. EXAM STANDARD: Conceptual focus. NCERT-based. Minimal lengthy calculations. Domain-paper standard.

F. OPTION QUALITY:
   - 3 plausible distractors — wrong answers that arise from common mistakes.
   - Randomize which letter (A/B/C/D) is correct across the batch.

G. SELF-CHECK before outputting each question:
   - Exactly 4 non-empty, distinct options?
   - Is the correct answer definitely correct?
   - Does the explanation's conclusion name the same letter as correct_option?
   - Is all numerical/factual data consistent (no contradictions)?
   If any check fails, rewrite before outputting.

=== OUTPUT FORMAT ===

Return ONLY a JSON array, nothing else — no markdown fences, no commentary.
Each element must follow this EXACT shape, and MUST include a "topic" field
set to exactly one of the topic names listed above (so questions can be
matched back to their topic):

[
  {{
    "topic": "<one of the topic names above, exactly>",
    "question_text": "...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_option": "B",
    "detailed_explanation": "Full step-by-step reasoning for the correct answer.",
    "solution_steps": ["Step 1 ...", "Step 2 ...", "Step 3 ..."],
    "formula_used": "...",
    "ncert_reference": "NCERT {grade} — <chapter for this topic>",
    "difficulty": "medium",
    "subtopic": "..."
  }}
]

Generate exactly {total} questions now, distributed per the topic breakdown table above.
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "GPT-5.5 Exam Prep Center authoring — Month 2 (1.5x session-depth floor, all CUET)",
        "=" * 78,
        "",
        "For each subject below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <slug>_questions.json in this folder.",
        "  4. Once all are done, ingest them all in one command:",
        "",
        "     cd backend",
        f"     ./venv/bin/python scripts/ingest_exam_prep_month2_output.py --dir {OUT_DIR} --dry-run",
        f"     ./venv/bin/python scripts/ingest_exam_prep_month2_output.py --dir {OUT_DIR}",
        "",
        "Subjects:",
    ]

    manifest = []
    for i, (subject, total, grade) in enumerate(MONTH2_TARGETS, start=1):
        topics = ep.CUET_SUBJECTS[subject]["topics"]
        weights = [t["weightage_pct"] for t in topics]
        alloc = _allocate(total, weights)

        topic_table = "\n".join(
            f"  - {t['name']} ({t['chapter']}): {a} question(s)"
            for t, a in zip(topics, alloc)
        )
        topic_names = [t["name"] for t in topics]

        existing = _existing_question_stems(subject)
        existing_questions_block = (
            "\n".join(f"  {n}. {q}" for n, q in enumerate(existing, start=1))
            if existing else "  (none — this subject currently has no existing questions)"
        )

        prompt_text = PROMPT_TEMPLATE.format(
            subject=subject, grade=grade, total=total, topic_table=topic_table,
            existing_questions_block=existing_questions_block,
        )
        slug = _slugify(f"cuet_ug_{subject}")
        prompt_path = OUT_DIR / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        expected_json = f"{slug}_questions.json"
        manifest.append({
            "index": i,
            "exam_type": "cuet_ug",
            "subject": subject,
            "grade": grade,
            "question_count": total,
            "topics": topic_names,
            "topic_to_chapter": {t["name"]: t["chapter"] for t in topics},
            "expected_json": expected_json,
        })

        print(f"[{i:02d}] CUET UG / {subject} -> {prompt_path.name} "
              f"({total} questions across {len(topics)} topics, {len(existing)} existing to avoid, "
              f"{len(prompt_text):,} chars)")

        index_lines.append(f"  [{i:02d}] {subject}  ({total} questions, {len(topics)} topics)")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {expected_json}")

    (OUT_DIR / "00_README_and_index.txt").write_text("\n".join(index_lines), encoding="utf-8")
    (OUT_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_q = sum(t[1] for t in MONTH2_TARGETS)
    print(f"\nDone. {len(MONTH2_TARGETS)} prompts written to {OUT_DIR} ({total_q} questions total once authored).")


if __name__ == "__main__":
    main()
