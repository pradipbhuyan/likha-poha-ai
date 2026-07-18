import json
from app.services.openai_service import ask_llm


QUIZ_SYSTEM = """
You generate CBSE quizzes for the grade requested by the user.

Return ONLY valid JSON.
Do not use markdown.

Schema:
{
  "questions": [
    {
      "id": 1,
      "question": "...",
      "options": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      },
      "answer": "A",
      "explanation": "..."
    }
  ]
}
"""


def generate_quiz(
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    difficulty: str,
    count: int,
    board: str = "CBSE",
):
    """
    Generate a multiple-choice quiz as JSON for the selected topic.

    The service expects valid JSON from the model and returns the parsed question
    list to the quiz route.
    """
    prompt = f"""
Generate {count} MCQs.

Grade: {grade}
Board: {board}
Subject: {subject}
Chapter/Topic: {chapter}
Mode: {mode}
Difficulty: {difficulty}

Rules:
- Do not show answers inside question text.
- Keep each question clear.
- Give exactly 4 options: A, B, C, D.
- Include correct answer key separately.
- Include short explanation separately.

Return ONLY valid JSON.
"""

    raw = ask_llm(QUIZ_SYSTEM, prompt)

    try:
        data = json.loads(raw)
        return data.get("questions", [])
    except Exception:
        return []
