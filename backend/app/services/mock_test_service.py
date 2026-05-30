import json

from app.services.openai_service import ask_llm
from app.services.rag_service import search_textbook_content


MOCK_TEST_SYSTEM = """
You create original Grade 9 mock tests.

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


def get_sof_model_papers(olympiad):
    if olympiad == "Science Olympiad":
        return [
            "SOF-ISO Model Test Paper-1",
            "SOF-ISO Model Test Paper-2",
        ]

    if olympiad == "Maths Olympiad":
        return [
            "SOF-IMO Model Test Paper-1",
            "SOF-IMO Model Test Paper-2",
        ]

    if olympiad == "English Olympiad":
        return [
            "SOF-IEO Model Test Paper-1",
            "SOF-IEO Model Test Paper-2",
        ]

    return []


def build_rag_context(items):
    if not items:
        return ""

    chunks = []

    for item in items:
        text = item.get("chunk_text", "")

        document = item.get("document") or {}

        title = document.get("title", "")
        subject = document.get("subject", "")
        chapter = document.get("chapter", "")

        chunks.append(
            f"""
Source: {title}
Subject: {subject}
Chapter: {chapter}

{text}
"""
        )

    return "\n\n".join(chunks)


def get_sof_rag_context(
    olympiad,
    chapter=None,
    grade="Grade 9",
):
    rag_items = []

    if chapter:
        rag_items.extend(
            search_textbook_content(
                query=f"Important concepts, examples and practice questions from {chapter}",
                grade=grade,
                subject=olympiad,
                chapter=chapter,
                match_count=8,
            )
        )

    for paper_chapter in get_sof_model_papers(olympiad):
        rag_items.extend(
            search_textbook_content(
                query=f"SOF question pattern difficulty sample questions for {olympiad}",
                grade=grade,
                subject=olympiad,
                chapter=paper_chapter,
                match_count=5,
            )
        )

    return build_rag_context(rag_items)


def generate_olympiad_mock_test(
    olympiad,
    num_questions=10,
    difficulty="Medium",
    chapter=None,
    grade="Grade 9",
):
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

    rag_context = get_sof_rag_context(
        olympiad=olympiad,
        chapter=chapter,
        grade=grade,
    )


    prompt = f"""
{pattern}

Grade: {grade}
Olympiad: {olympiad}
Chapter: {chapter or "Mixed SOF syllabus"}
Difficulty: {difficulty}
Number of questions: {num_questions}

Use the RAG context below.

Rules:
- Use chapter RAG content for concepts.
- Use SOF model test paper RAG content for question style, difficulty and pattern.
- Do not copy exact questions from the RAG context.
- Create fresh original questions inspired by the uploaded SOF material.
- Keep questions suitable for Grade 9.
- Every question must have 4 options.
- Every answer must be one of A, B, C or D.
- Include a clear explanation.

RAG CONTEXT:
{rag_context[:14000]}

Return only valid JSON.
"""

    raw = ask_llm(
        MOCK_TEST_SYSTEM,
        prompt,
        username="admin",
        feature="sof_mock_test",
    )

    try:
        data = json.loads(raw)
        return data.get("questions", [])
    except Exception:
        return []


def generate_science_olympiad_mock_test(
    num_questions=10,
    difficulty="Medium",
    chapter=None,
):
    return generate_olympiad_mock_test(
        "Science Olympiad",
        num_questions,
        difficulty,
        chapter,
    )


def generate_maths_olympiad_mock_test(
    num_questions=10,
    difficulty="Medium",
    chapter=None,
):
    return generate_olympiad_mock_test(
        "Maths Olympiad",
        num_questions,
        difficulty,
        chapter,
    )


def generate_english_olympiad_mock_test(
    num_questions=10,
    difficulty="Medium",
    chapter=None,
):
    return generate_olympiad_mock_test(
        "English Olympiad",
        num_questions,
        difficulty,
        chapter,
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

    raw = ask_llm(
        MOCK_TEST_SYSTEM,
        prompt,
        username="admin",
        feature="cbse_mock_test",
    )

    try:
        data = json.loads(raw)
        return data.get("questions", [])
    except Exception:
        return []