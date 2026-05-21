import json

from app.services.openai_service import ask_llm


MOCK_TEST_SYSTEM = """
You create original Grade 9 SOF Olympiad style mock tests.
Do not copy previous year questions verbatim.
Create questions inspired by common SOF patterns.

Return ONLY valid JSON. No markdown.

JSON schema:
{
  "questions": [
    {
      "id": 1,
      "section": "...",
      "question": "...",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "A",
      "explanation": "...",
      "marks": 1
    }
  ]
}
"""


def generate_olympiad_mock_test(olympiad, num_questions=10, difficulty="Medium"):
    if olympiad == "Science Olympiad":
        pattern = """
Create a Class 9 SOF Science Olympiad style mock test.

Pattern:
- Logical Reasoning: about 20%
- Science: about 70%
- Achievers Section/HOTS: about 10%

Include Physics, Chemistry, Biology, reasoning, application and HOTS.
"""

    elif olympiad == "Maths Olympiad":
        pattern = """
Create a Class 9 SOF Maths Olympiad style mock test.

Pattern:
- Logical Reasoning: about 20%
- Mathematical Reasoning: about 50%
- Everyday Mathematics: about 20%
- Achievers Section/HOTS: about 10%

Include number systems, algebra, geometry, mensuration, statistics, probability, logical puzzles and HOTS.
"""

    elif olympiad == "English Olympiad":
        pattern = """
Create a Class 9 SOF English Olympiad style mock test.

Pattern:
- Word and Structure Knowledge
- Reading
- Spoken and Written Expression
- Achievers Section/HOTS

Include vocabulary, grammar, sentence correction, comprehension, inference, para jumbles and usage.
"""

    else:
        pattern = """
Create a Class 9 SOF Olympiad style mock test.
"""

    prompt = f"""
{pattern}

Difficulty: {difficulty}
Number of questions: {num_questions}

Return only valid JSON.
"""

    raw = ask_llm(MOCK_TEST_SYSTEM, prompt)

    try:
        data = json.loads(raw)
        return data.get("questions", [])
    except Exception:
        return []


def generate_science_olympiad_mock_test(num_questions=10, difficulty="Medium"):
    return generate_olympiad_mock_test(
        "Science Olympiad",
        num_questions,
        difficulty
    )


def generate_maths_olympiad_mock_test(num_questions=10, difficulty="Medium"):
    return generate_olympiad_mock_test(
        "Maths Olympiad",
        num_questions,
        difficulty
    )


def generate_english_olympiad_mock_test(num_questions=10, difficulty="Medium"):
    return generate_olympiad_mock_test(
        "English Olympiad",
        num_questions,
        difficulty
    )


def calculate_score(questions, user_answers):
    total_score = 0
    max_score = 0
    results = []

    for q in questions:
        qid = str(q.get("id"))
        correct = q.get("answer")
        selected = user_answers.get(qid)
        marks = int(q.get("marks", 1))
        max_score += marks

        is_correct = selected == correct
        if is_correct:
            total_score += marks

        results.append({
            "id": q.get("id"),
            "section": q.get("section"),
            "question": q.get("question"),
            "selected": selected,
            "correct": correct,
            "is_correct": is_correct,
            "marks": marks,
            "options": q.get("options", {}),
            "explanation": q.get("explanation", "")
        })

    return total_score, max_score, results

def generate_cbse_mock_test(
    subject,
    chapter,
    exam_type="Class Test",
    num_questions=10,
    difficulty="Medium"
):

    prompt = f"""
Create a CBSE Grade 9 mock test.

Subject: {subject}
Chapter: {chapter}
Exam Type: {exam_type}
Difficulty: {difficulty}
Questions: {num_questions}

Follow CBSE/NCERT style.

For:
- Class Test -> short chapter focused questions
- Mid Term -> moderate difficulty
- Annual Exam -> mixed conceptual and application questions

Include:
- MCQs
- Assertion Reason
- Case based questions where suitable
- Numericals for Maths/Science
- Grammar/Comprehension for English/Hindi

Return ONLY valid JSON.

JSON schema:
{{
  "questions": [
    {{
      "id": 1,
      "section": "...",
      "question": "...",
      "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      }},
      "answer": "A",
      "explanation": "...",
      "marks": 1
    }}
  ]
}}
"""

    raw = ask_llm(MOCK_TEST_SYSTEM, prompt)

    try:
        data = json.loads(raw)
        return data.get("questions", [])
    except Exception:
        return []
