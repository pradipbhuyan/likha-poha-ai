import json
import uuid
from datetime import date

from app.services.openai_service import ask_llm
from app.services.openai_service import DEFAULT_TEXT_MODEL
from app.services.rag_service import search_textbook_content
from app.services.sof_catalog_service import (
    get_sof_exam_paper_chapters,
    get_sof_support_chapters,
)
from app.services.question_bank_service import (
    get_questions_from_bank,
    add_questions_to_bank,
)


MOCK_TEST_SYSTEM = """
You create original CBSE and SOF mock tests for the grade requested by the user.

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


def build_rag_context(items, label="RAG"):
    """
    Format retrieved RAG chunks with source metadata for prompt injection.

    The section labels let the model distinguish chapter content, exercises,
    model papers, and answer explanations when composing SOF questions.
    """
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
RAG Section: {label}
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
    """
    Gather all RAG material needed for a high-quality SOF mock test.

    Chapter content teaches concepts, exercise content informs practice style,
    model papers shape exam patterns, and answer-key sections improve
    explanations.
    """
    context_parts = []

    if chapter:
        chapter_items = search_textbook_content(
            query=(
                f"{chapter} SOF chapter concepts definitions examples "
                "formulas important points"
            ),
            grade=grade,
            subject=olympiad,
            chapter=chapter,
            match_count=10,
        )

        exercise_items = search_textbook_content(
            query=(
                f"{chapter} SOF exercise practice questions solved examples "
                "answer explanations"
            ),
            grade=grade,
            subject=olympiad,
            chapter=chapter,
            match_count=10,
        )

        chapter_context = build_rag_context(
            chapter_items,
            label="SOF chapter content",
        )
        exercise_context = build_rag_context(
            exercise_items,
            label="SOF chapter exercises",
        )

        if chapter_context:
            context_parts.append(chapter_context)

        if exercise_context:
            context_parts.append(exercise_context)

    model_paper_items = []

    for paper_chapter in get_sof_exam_paper_chapters(olympiad):
        paper_items = search_textbook_content(
            query=(
                f"{paper_chapter} SOF workbook paper mock test questions "
                f"pattern difficulty sample questions answer explanations {olympiad}"
            ),
            grade=grade,
            subject=olympiad,
            chapter=paper_chapter,
            match_count=8,
        )
        model_paper_items.extend(paper_items)

    support_items = []

    for support_chapter in get_sof_support_chapters(olympiad):
        support_items.extend(
            search_textbook_content(
                query=(
                    f"{support_chapter} SOF workbook answer key hints "
                    f"explanations solutions reasoning {olympiad}"
                ),
                grade=grade,
                subject=olympiad,
                chapter=support_chapter,
                match_count=8,
            )
        )

    model_paper_items.extend(
        search_textbook_content(
            query=(
                f"uploaded SOF mock test paper model paper sample paper "
                f"section pattern question difficulty answer explanations {olympiad}"
            ),
            grade=grade,
            subject=olympiad,
            chapter=None,
            match_count=10,
        )
    )

    model_paper_context = build_rag_context(
        model_paper_items,
        label="SOF uploaded mock or model test papers",
    )

    if model_paper_context:
        context_parts.append(model_paper_context)

    support_context = build_rag_context(
        support_items,
        label="SOF workbook answer keys and explanations",
    )

    if support_context:
        context_parts.append(support_context)

    return "\n\n".join(context_parts)


def create_generation_variant(username="admin"):
    """
    Create a per-request seed so repeated mock tests differ on the same day.

    The seed is included in the LLM prompt, not used for deterministic random
    generation, because the model itself performs the question generation.
    """
    return f"{username}-{date.today().isoformat()}-{uuid.uuid4().hex[:8]}"


def validate_sof_rag_context(rag_context, olympiad, chapter):
    """
    Ensure SOF mock tests are generated only from uploaded RAG material.

    This protects the product promise that SOF mock tests are grounded in the
    uploaded workbook/exercise/model-paper content.
    """
    if rag_context.strip():
        return

    chapter_text = f" - {chapter}" if chapter else ""

    raise ValueError(
        f"No RAG content found for {olympiad}{chapter_text}. "
        "Upload SOF chapter pages, exercises, or mock test papers before "
        "generating an SOF mock test."
    )


def generate_olympiad_mock_test(
    olympiad,
    num_questions=10,
    difficulty="Medium",
    chapter=None,
    grade="Grade 9",
    username="admin",
    model=DEFAULT_TEXT_MODEL,
):
    """
    Generate an original SOF mock test grounded in uploaded RAG context.

    Bank-first: if question bank already contains questions for this chapter
    and difficulty, serve them instantly at zero token cost.
    Falls back to RAG + LLM generation only when the bank is empty.
    Explanations may add wider model knowledge, but every question must be
    inspired by uploaded SOF content so the test stays aligned with the workbook.
    """
    # ------------------------------------------------------------------ bank
    bank_questions = get_questions_from_bank(
        board="CBSE",
        grade=grade,
        subject=olympiad,
        chapter=chapter or "",
        difficulty=difficulty,
        num_questions=num_questions,
        exam_type="General",
    )
    if bank_questions:
        return bank_questions
    # --------------------------------------------------------------- end bank

    if olympiad == "Science Olympiad":
        pattern = f"""
Create a {grade} SOF Science Olympiad style mock test.

Pattern:
- Logical Reasoning: about 20%
- Science: about 70%
- Achievers Section/HOTS: about 10%

Include Physics, Chemistry, Biology, reasoning, application and HOTS.
"""

    elif olympiad == "Maths Olympiad":
        pattern = f"""
Create a {grade} SOF Maths Olympiad style mock test.

Pattern:
- Logical Reasoning: about 20%
- Mathematical Reasoning: about 50%
- Everyday Mathematics: about 20%
- Achievers Section/HOTS: about 10%

Include number systems, algebra, geometry, mensuration, statistics, probability, logical puzzles and HOTS.
"""

    elif olympiad == "English Olympiad":
        pattern = f"""
Create a {grade} SOF English Olympiad style mock test.

Pattern:
- Word and Structure Knowledge
- Reading
- Spoken and Written Expression
- Achievers Section/HOTS

Include vocabulary, grammar, sentence correction, comprehension, inference, para jumbles and usage.
"""

    else:
        pattern = f"""
Create a {grade} SOF Olympiad style mock test.
"""

    rag_context = get_sof_rag_context(
        olympiad=olympiad,
        chapter=chapter,
        grade=grade,
    )

    validate_sof_rag_context(rag_context, olympiad, chapter)

    generation_variant = create_generation_variant(username=username)

    prompt = f"""
{pattern}

Grade: {grade}
Olympiad: {olympiad}
Chapter: {chapter or "Mixed SOF syllabus"}
Difficulty: {difficulty}
Number of questions: {num_questions}
Generation variation seed: {generation_variant}

Use the RAG context below as the mandatory source material.

Rules:
- Every question must be based on a concept, example, pattern, or exercise present in the uploaded RAG context.
- Use SOF chapter RAG content for tested concepts.
- Use SOF exercise RAG content for practice-question style and common traps.
- Use SOF workbook/mock/model test paper RAG content for exam pattern, section mix, wording style, difficulty and option design.
- Use uploaded SOF answer keys, hints, and explanations to improve answer reasoning.
- Do not introduce unrelated syllabus areas that are not supported by RAG.
- Do not copy exact questions from the RAG context.
- Create fresh original questions inspired by the uploaded SOF material.
- Use the generation variation seed to make this test different from other tests generated today.
- Keep questions suitable for {grade}.
- Every question must have 4 options.
- Every answer must be one of A, B, C or D.
- Explanations must first use the uploaded RAG concept that supports the answer.
- Explanations may then add wider conceptual clarification, reasoning shortcuts, and common-mistake notes from general LLM knowledge.
- Include a clear explanation for every answer.

RAG CONTEXT:
{rag_context[:14000]}

Return only valid JSON.
"""

    raw = ask_llm(
        MOCK_TEST_SYSTEM,
        prompt,
        username=username,
        feature="sof_mock_test",
        model=model,
    )

    try:
        data = json.loads(raw)
        questions = data.get("questions", [])
    except Exception:
        return []

    # Store newly generated questions in the bank for future zero-cost requests
    if questions:
        add_questions_to_bank(
            questions=questions,
            board="CBSE",
            grade=grade,
            subject=olympiad,
            chapter=chapter or "",
            difficulty=difficulty,
            exam_type="General",
        )

    return questions


def generate_science_olympiad_mock_test(
    num_questions=10,
    difficulty="Medium",
    chapter=None,
):
    """Convenience wrapper for Science Olympiad mock-test generation."""
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
    """Convenience wrapper for Maths Olympiad mock-test generation."""
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
    """Convenience wrapper for English Olympiad mock-test generation."""
    return generate_olympiad_mock_test(
        "English Olympiad",
        num_questions,
        difficulty,
        chapter,
    )


def calculate_score(questions, user_answers):
    """
    Score submitted mock-test answers and return per-question result metadata.

    The frontend uses the result list to show selected answer, correct answer,
    explanations, and marks after submission.
    """
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
    grade,
    subject,
    chapter,
    exam_type="Class Test",
    num_questions=10,
    difficulty="Medium",
    board="CBSE",
):
    """
    Generate a CBSE mock test.

    Bank-first: checks the question_bank before calling the LLM. On bank hit
    returns a random sample instantly with zero token cost. On bank miss the
    LLM generates as normal and the result is added to the bank.
    """
    # ------------------------------------------------------------------ bank
    bank_questions = get_questions_from_bank(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        difficulty=difficulty,
        num_questions=num_questions,
        exam_type=exam_type,
    )
    if bank_questions:
        return bank_questions
    # --------------------------------------------------------------- end bank

    prompt = f"""
Create a {board} {grade} mock test.

Grade: {grade}
Board: {board}
Subject: {subject}
Chapter: {chapter}
Exam Type: {exam_type}
Difficulty: {difficulty}
Questions: {num_questions}

Follow {board} textbook and exam style.

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
        questions = data.get("questions", [])
    except Exception:
        return []

    # Store new LLM questions in bank for future requests
    add_questions_to_bank(
        questions=questions,
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter or "",
        difficulty=difficulty,
        exam_type=exam_type,
    )

    return questions
