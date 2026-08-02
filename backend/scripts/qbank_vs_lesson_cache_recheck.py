#!/usr/bin/env python3
"""
Re-check sampled question_bank content against lesson_cache (the actual
current authoritative content source per user confirmation), instead of
raw rag_chunks (which is known-stale/corrupted for several Grade 12
subjects and is no longer what lessons/Ask Doubt-via-lesson_cache serve).

READ-ONLY. Reuses the exact same chapters flagged in the earlier
rag_chunks-based sample so the before/after comparison is apples-to-apples.
"""
from __future__ import annotations
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.auth_service import admin_client

BOARD = "CBSE"
random.seed(42)

# Same chapters flagged as "mismatched vs rag_chunks" in the earlier sample.
RECHECK_PLAN = [
    ("Grade 12", "History", "Chapter 4: Thinkers, Beliefs and Buildings: Cultural Developments"),
    ("Grade 12", "History", "Chapter 2: Kings, Farmers and Towns: Early States and Economies"),
    ("Grade 12", "History", "Chapter 1: Bricks, Beads and Bones: The Harappan Civilisation"),
    ("Grade 12", "Political Science", "Chapter 4: International Organisations"),
    ("Grade 12", "Political Science", "Chapter 10: Politics of Planned Development"),
    ("Grade 12", "Political Science", "Chapter 3: Contemporary South Asia"),
    ("Grade 12", "Political Science", "Chapter 13: The Crisis of Democratic Order"),
    ("Grade 12", "Political Science", "Chapter 5: Security in the Contemporary World"),
    ("Grade 12", "Chemistry", "Chapter 3: Chemical Kinetics"),
    ("Grade 12", "Chemistry", "Chapter 1: Solutions"),
    ("Grade 12", "Chemistry", "Chapter 6: Haloalkanes and Haloarenes"),
    ("Grade 12", "Chemistry", "Chapter 2: Electrochemistry"),
    ("Grade 11", "Biology", "Chapter 13: Plant Growth and Development"),
    ("Grade 11", "Biology", "Chapter 12: Respiration in Plants"),
]


def fetch_all(qb, page=1000):
    rows, start = [], 0
    while True:
        r = qb().range(start, start + page - 1).execute()
        d = r.data or []
        rows.extend(d)
        if len(d) < page:
            break
        start += page
    return rows


def get_lesson_text(grade, subject, chapter, max_chars=1500):
    rows = fetch_all(lambda: admin_client.table("lesson_cache").select("step_title,lesson_content")
                      .eq("grade", grade).eq("subject", subject).eq("chapter", chapter)
                      .eq("status", "active").eq("mode", "CBSE"))
    if not rows:
        return None
    # "Concept introduction" step gives the clearest topic-identity signal
    intro = next((r for r in rows if r["step_title"] == "Concept introduction"), rows[0])
    return intro["lesson_content"][:max_chars]


def get_sample_questions(grade, subject, chapter, n=2):
    rows = fetch_all(lambda: admin_client.table("question_bank").select("question,answer,explanation,difficulty")
                      .eq("grade", grade).eq("subject", subject).eq("chapter", chapter).eq("board", BOARD))
    if not rows:
        return []
    return random.sample(rows, min(n, len(rows)))


def main():
    for grade, subject, chapter in RECHECK_PLAN:
        print(f"\n{'=' * 90}\n{grade} / {subject} / {chapter}\n{'=' * 90}")
        lesson_text = get_lesson_text(grade, subject, chapter)
        if lesson_text is None:
            print("  [NO lesson_cache content found for this exact chapter string]")
            continue
        print(f"--- lesson_cache 'Concept introduction' (first 1500 chars) ---")
        print(lesson_text)
        print(f"\n--- sampled bank questions ---")
        for q in get_sample_questions(grade, subject, chapter):
            print(f"\n  [{q['difficulty']}] {q['question']}")
            print(f"    Answer: {q['answer']}")
            print(f"    Explanation: {q['explanation']}")


if __name__ == "__main__":
    main()
