#!/usr/bin/env python3
"""
Month 9 — continuing past the original 8-month plan at the same 0.5x-per-
month cadence.

Target: 5.0x session-depth floor across every subject. Sized against
published+draft (non-archived) rows, same rationale as Months 6-8, though
at generation time everything is actually published (0 drafts remain,
following the Month 8 bulk-publish).

JEE Main unlocks for the first time this month — Chemistry (6-question
gap) and Mathematics (9-question gap) are due; Physics's 2-question gap
is deferred, same "1-2 question exceptions" precedent as Months 1 and 3
(not worth a dedicated GPT-5.5 round-trip for two questions). TOEFL
Reading/Listening remain far above every floor this plan has ever set
(6.2-6.9x) and stay untouched.

Generalizes the NEET-only Class-11 topic-grade detection (introduced
Month 5) to JEE Main too: confirmed live via the existing DB rows that
JEE Chemistry/Mathematics/Physics are genuinely mixed Grade 11/12, same
as NEET — both share the same JEE_SUBJECTS-derived topic list
(NEET_PHYSICS = dict(JEE_SUBJECTS["Physics"]), etc., in
exam_prep_service.py), so the same ncert_chapter-parsing logic applies
unchanged, just extended to a second exam_type.

Usage:
    cd backend
    ./venv/bin/python scripts/prepare_exam_prep_month9_prompts.py

Then: run each prompt through GPT-5.5, save as <slug>_questions.json in the
output folder, and ingest with ingest_exam_prep_month9_output.py (dry-run first).
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

OUT_DIR = Path.home() / "Downloads" / "GPT55_ExamPrep_Month9_Prompts"

EXAM_LABELS = {
    "cuet_ug": "CUET UG", "neet_ug": "NEET UG", "jee_main": "JEE Main",
    "sat": "SAT", "ielts": "IELTS", "toefl_ibt": "TOEFL iBT",
}

# Subjects whose topics genuinely mix NCERT Class 11 and Class 12 content
# (confirmed against existing DB grade distributions) — grade is derived
# per-topic for these, flat "Grade 12" for everything else (CUET/SAT/
# IELTS/TOEFL, whose questions are conventionally tagged Grade 12
# regardless of NCERT source class).
PER_TOPIC_GRADE_EXAM_TYPES = {"neet_ug", "jee_main"}

# (exam_type, subject, question_count) — gap to reach 5.0x target_per_session
# (vs published+draft), recomputed live at prompt-generation time (see
# module docstring).
MONTH9_TARGETS: list[tuple[str, str, int]] = [
    ("cuet_ug", "English", 20),
    ("cuet_ug", "Hindi", 20),
    ("cuet_ug", "General Test", 20),
    ("cuet_ug", "Physics (Domain)", 20),
    ("cuet_ug", "Chemistry (Domain)", 20),
    ("cuet_ug", "Mathematics (Domain)", 20),
    ("cuet_ug", "Biology (Domain)", 20),
    ("cuet_ug", "History", 20),
    ("cuet_ug", "Geography", 20),
    ("cuet_ug", "Political Science", 20),
    ("cuet_ug", "Economics", 20),
    ("cuet_ug", "Accountancy", 20),
    ("cuet_ug", "Business Studies", 20),
    ("cuet_ug", "Sociology", 20),
    ("cuet_ug", "Psychology", 20),
    ("cuet_ug", "Legal Studies", 20),
    ("neet_ug", "Physics", 23),
    ("neet_ug", "Chemistry", 23),
    ("neet_ug", "Biology", 45),
    ("jee_main", "Chemistry", 6),
    ("jee_main", "Mathematics", 9),
    ("sat", "Reading & Writing", 25),
    ("sat", "Mathematics", 26),
    ("ielts", "Listening", 13),
    ("ielts", "Reading", 13),
    ("ielts", "Vocabulary & Grammar", 13),
    ("toefl_ibt", "Integrated Skills", 8),
]


def _topic_chapter(t: dict) -> str:
    return t.get("chapter") or t.get("ncert_chapter") or t["name"]


def _topic_weight(t: dict) -> float:
    return float(t.get("weightage_pct") or 1)


def _topic_grade(exam_type: str, t: dict) -> str:
    if exam_type in PER_TOPIC_GRADE_EXAM_TYPES and "Class 11" in t.get("ncert_chapter", ""):
        return "Grade 11"
    return "Grade 12"


def _allocate(total: int, weights: list[float]) -> list[int]:
    """
    Largest-remainder proportional allocation. When total < number of
    topics, only the highest-weighted `total` topics get 1 question each
    and the rest get 0 — triggered this month for JEE Chemistry (6
    questions across 7 topics).
    """
    n = len(weights)
    if total <= 0:
        return [0] * n
    if total >= n:
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
    order = sorted(range(n), key=lambda i: weights[i], reverse=True)
    base = [0] * n
    for i in order[:total]:
        base[i] = 1
    return base


def _existing_question_stems(exam_type: str, subject: str) -> list[str]:
    rows = (
        admin_client.table("exam_prep_questions")
        .select("question_text")
        .eq("exam_type", exam_type).eq("subject", subject)
        .neq("status", "archived")
        .execute().data
    )
    return [r["question_text"] for r in rows if r.get("question_text")]


PROMPT_TEMPLATE = """You are an expert assessment designer and senior question setter for Indian competitive examinations.

Your responsibility is to generate ORIGINAL, HIGH-QUALITY, COMPLETE multiple-choice questions.

Target Exam: {exam_label}
Subject: {subject}
Total questions: {total}
Difficulty mix: 30% Easy, 50% Moderate, 20% Difficult

=== TOPIC BREAKDOWN — WRITE EXACTLY THIS MANY QUESTIONS PER TOPIC ===
{topic_table}
(Total across all topics must equal {total}. Topics not listed above get 0 questions this batch.)

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

E. EXAM STANDARD for {exam_label}: NCERT/curriculum-based conceptual focus, minimal lengthy calculations.

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
    "ncert_reference": "...",
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
        "GPT-5.5 Exam Prep Center authoring — Month 9 (5.0x session-depth floor)",
        "=" * 78,
        "",
        "16 CUET UG subjects, all three NEET UG subjects, JEE Main Chemistry",
        "and Mathematics (first time — Physics's 2-question gap deferred),",
        "both SAT subjects, all three IELTS subjects, and TOEFL Integrated",
        "Skills.",
        "",
        "For each subject below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <slug>_questions.json in this folder.",
        "  4. Once all are done, ingest them all in one command:",
        "",
        "     cd backend",
        f"     ./venv/bin/python scripts/ingest_exam_prep_month9_output.py --dir {OUT_DIR} --dry-run",
        f"     ./venv/bin/python scripts/ingest_exam_prep_month9_output.py --dir {OUT_DIR}",
        "",
        "Subjects:",
    ]

    manifest = []
    for i, (exam_type, subject, total) in enumerate(MONTH9_TARGETS, start=1):
        exam_label = EXAM_LABELS[exam_type]
        topics = ep.EXAM_SUBJECTS_MAP[exam_type][subject]["topics"]
        weights = [_topic_weight(t) for t in topics]
        alloc = _allocate(total, weights)

        included = [(t, a) for t, a in zip(topics, alloc) if a > 0]
        topic_table = "\n".join(
            f"  - {t['name']} ({_topic_chapter(t)}): {a} question(s)"
            for t, a in included
        )
        topic_names = [t["name"] for t, _ in included]

        existing = _existing_question_stems(exam_type, subject)
        existing_questions_block = (
            "\n".join(f"  {n}. {q}" for n, q in enumerate(existing, start=1))
            if existing else "  (none — this subject currently has no existing questions)"
        )

        prompt_text = PROMPT_TEMPLATE.format(
            exam_label=exam_label, subject=subject, total=total, topic_table=topic_table,
            existing_questions_block=existing_questions_block,
        )
        slug = _slugify(f"{exam_type}_{subject}")
        prompt_path = OUT_DIR / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        expected_json = f"{slug}_questions.json"
        manifest.append({
            "index": i,
            "exam_type": exam_type,
            "subject": subject,
            "question_count": total,
            "topics": topic_names,
            "topic_to_chapter": {t["name"]: _topic_chapter(t) for t, _ in included},
            "topic_to_grade": {t["name"]: _topic_grade(exam_type, t) for t, _ in included},
            "expected_json": expected_json,
        })

        print(f"[{i:02d}] {exam_label} / {subject} -> {prompt_path.name} "
              f"({total} questions across {len(included)}/{len(topics)} topics, "
              f"{len(existing)} existing to avoid, {len(prompt_text):,} chars)")

        index_lines.append(f"  [{i:02d}] {exam_label} / {subject}  ({total} questions, {len(included)} topics)")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {expected_json}")

    index_lines.append("")
    index_lines.append("Deferred (needs only 2 questions, not worth a dedicated round-trip): "
                        "JEE Main Physics (gap: 2 questions at 5.0x floor)")

    (OUT_DIR / "00_README_and_index.txt").write_text("\n".join(index_lines), encoding="utf-8")
    (OUT_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_q = sum(t[2] for t in MONTH9_TARGETS)
    print(f"\nDone. {len(MONTH9_TARGETS)} prompts written to {OUT_DIR} ({total_q} questions total once authored).")


if __name__ == "__main__":
    main()
