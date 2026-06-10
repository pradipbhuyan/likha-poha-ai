"""
Question Bank Building Script
==============================
Pre-generates mock test questions for all Grade 9 chapters and stores
them in the question_bank table for random sampling.

Run this ONCE when your OpenAI API key is ready and the question_bank table
has been created in Supabase (backend/sql/add_question_bank.sql).

Estimated cost: ~$8.73 for all Grade 9 CBSE + SOF question pools.
Estimated time: ~60 minutes (rate limited to ~0.5 req/sec).

Usage:
    cd backend
    python3 scripts/build_question_bank.py

After completion, all mock test requests will be served from the bank
at zero token cost (random sampling from 50+ questions per chapter).
"""

import sys
import time
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.syllabus import CBSE_9, SOF_9
from app.services.openai_service import ask_llm
from app.services.question_bank_service import add_questions_to_bank, get_questions_from_bank

GRADE = "Grade 9"
BOARD = "CBSE"

# Generate this many questions per chapter/difficulty combination
QUESTIONS_PER_BATCH = 20  # Each LLM call generates 20 questions
BATCHES_PER_CHAPTER = 3   # 3 batches = 60 questions per chapter/difficulty
# Total per chapter/difficulty: 60 questions → C(60,10) = 75 billion unique tests

DIFFICULTIES = ["Easy", "Medium", "Hard"]

# Rate limit: pause between requests to avoid OpenAI rate limit errors
REQUEST_DELAY_SECONDS = 2.0

MOCK_TEST_SYSTEM = """
You create original CBSE mock test questions for exam preparation.
Return ONLY valid JSON array. No markdown. No explanations outside JSON.

JSON schema:
[
  {
    "id": 1,
    "section": "MCQ",
    "question": "...",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "answer": "A",
    "explanation": "...",
    "marks": 1
  }
]
"""


def generate_questions_for_chapter(
    grade: str,
    board: str,
    subject: str,
    chapter: str,
    difficulty: str,
    count: int,
    batch_num: int,
) -> list[dict]:
    """Generate a batch of questions for one chapter/difficulty."""
    prompt = f"""
Create {count} original {difficulty} difficulty MCQ questions for a {grade} {board} {subject} exam.

Chapter: {chapter}
Difficulty: {difficulty}
Batch variation seed: {batch_num}

Rules:
- Every question must be original and different from previous batches.
- Use the batch variation seed to ensure variety.
- Follow {board} exam style for {grade}.
- Each question must have exactly 4 options (A, B, C, D).
- Answer must be one of A, B, C, D.
- Include a clear explanation for every answer.
- Questions should test understanding, not just memorisation.
- Vary question types: direct concept, application, assertion-reason.

Return ONLY a valid JSON array with {count} questions.
"""

    try:
        raw = ask_llm(MOCK_TEST_SYSTEM, prompt, username="bank_builder", feature="question_bank_build")
        raw = raw.strip()
        if raw.startswith("```"):
            import re
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            return []
        data = json.loads(raw[start:end + 1])
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"    ⚠️  Parse error: {e}")
        return []


def build_cbse_bank():
    """Build question bank for all CBSE Grade 9 chapters."""
    total_added = 0
    total_skipped = 0

    for subject, chapters in CBSE_9.items():
        print(f"\n📚 Subject: {subject}")

        for chapter in chapters:
            for difficulty in DIFFICULTIES:
                # Check if bank already has enough questions
                existing = get_questions_from_bank(
                    board=BOARD, grade=GRADE, subject=subject,
                    chapter=chapter, difficulty=difficulty,
                    num_questions=QUESTIONS_PER_BATCH * BATCHES_PER_CHAPTER,
                )
                if existing:
                    print(f"  ⏭  SKIP  {chapter[:40]} [{difficulty}] — bank full")
                    total_skipped += QUESTIONS_PER_BATCH * BATCHES_PER_CHAPTER
                    continue

                for batch in range(1, BATCHES_PER_CHAPTER + 1):
                    print(f"  ⚡ GEN   {chapter[:40]} [{difficulty}] batch {batch}/{BATCHES_PER_CHAPTER}")

                    questions = generate_questions_for_chapter(
                        grade=GRADE, board=BOARD, subject=subject,
                        chapter=chapter, difficulty=difficulty,
                        count=QUESTIONS_PER_BATCH, batch_num=batch,
                    )

                    if questions:
                        add_questions_to_bank(
                            questions=questions,
                            board=BOARD, grade=GRADE, subject=subject,
                            chapter=chapter, difficulty=difficulty,
                            exam_type="General",
                        )
                        total_added += len(questions)
                        print(f"      ✅ Added {len(questions)} questions")
                    else:
                        print(f"      ❌ No questions returned")

                    time.sleep(REQUEST_DELAY_SECONDS)

    return total_added, total_skipped


if __name__ == "__main__":
    total_chapters = sum(len(chapters) for chapters in CBSE_9.values())
    total_batches = total_chapters * len(DIFFICULTIES) * BATCHES_PER_CHAPTER
    estimated_questions = total_batches * QUESTIONS_PER_BATCH

    print("=" * 60)
    print("LikhaPoha AI — Question Bank Builder")
    print("=" * 60)
    print(f"Grade: {GRADE} CBSE")
    print(f"Chapters: {total_chapters}")
    print(f"Difficulties: {', '.join(DIFFICULTIES)}")
    print(f"Questions per chapter/difficulty: {QUESTIONS_PER_BATCH * BATCHES_PER_CHAPTER}")
    print(f"Total questions to generate: ~{estimated_questions}")
    print(f"Estimated cost: ~${total_batches * 0.0054:.2f}")
    print(f"Estimated time: ~{total_batches * REQUEST_DELAY_SECONDS / 60:.0f} minutes")
    print()
    print("Note: Already-populated chapter/difficulty combinations are skipped.")
    print("Run this script again to resume after an interruption.")
    print()

    confirm = input("Type 'yes' to start bank generation: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    print()
    print("--- Building CBSE question bank ---")
    added, skipped = build_cbse_bank()

    print()
    print("=" * 60)
    print("Question bank building complete!")
    print(f"Questions added: {added}")
    print(f"Skipped (already in bank): {skipped}")
    print()
    print("All future CBSE mock test requests will be served from the bank.")
    print("SOF mock tests continue using RAG-based generation (by design).")
    print("=" * 60)
