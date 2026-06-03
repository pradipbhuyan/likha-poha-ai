import re

from app.services.openai_service import ask_llm


EVALUATOR_SYSTEM = """
You are an expert Grade 9 CBSE examiner and teacher.

Your role:
- Evaluate student-written answers.
- Encourage active learning.
- Be constructive and educational.

Evaluation rules:
- Identify correct points.
- Identify missing concepts.
- Identify misconceptions.
- Score fairly.
- Explain how to improve.

Output format:

## Score
X/10

## Verdict
PASS or RETRY

## What was correct
- ...

## Missing or incorrect points
- ...

## Improved answer
If Verdict is PASS, provide a strong model answer suitable for exams.
If Verdict is RETRY, do NOT provide the full model answer. Instead give 3–5 helpful hints only.

## One improvement tip
Short actionable advice.

Scoring rule:
- PASS only if score is 8/10 or higher.
- RETRY if score is below 8/10.
Anti-copy rule:
- If score is below 8/10, never reveal the complete ideal answer.
- Give hints and missing points only.
- Reveal the exam-ready model answer only when the student passes.
"""


def evaluate_student_answer(
    question: str,
    student_answer: str,
    ideal_context: str,
    username: str = "unknown",
):
    """
    Evaluate a written student answer and parse a pass/fail score.

    The model returns teacher feedback; the service extracts an X/10 score so
    the lesson page can decide whether to unlock continuation.
    """
    prompt = f"""
Question:
{question}

Student answer:
{student_answer}

Reference lesson/context:
{ideal_context}

Evaluate the student's answer carefully.

Important:
- Focus on conceptual understanding.
- Reward partial understanding.
- Correct misconceptions clearly.
- Keep tone encouraging.
- Improved answer should be exam-ready.
"""

    evaluation = ask_llm(
        EVALUATOR_SYSTEM,
        prompt,
        username=username,
        feature="answer_evaluation",
    )

    score_match = re.search(r"(\d+)/10", evaluation)

    score = 0

    if score_match:
        score = int(score_match.group(1))

    passed = score >= 8

    return {
        "evaluation": evaluation,
        "score": score,
        "passed": passed,
    }
    
def generate_practice_questions(
    lesson: str,
    chapter: str,
    step_title: str,
    username: str = "unknown",
):
    """
    Generate two written-answer practice questions for a lesson step.

    The output is parsed from a numbered list into plain strings for the
    frontend practice workflow.
    """
    prompt = f"""
Create exactly 2 written-answer practice questions for a Grade 9 student.

Chapter:
{chapter}

Lesson step:
{step_title}

Lesson content:
{lesson}

Rules:
- Questions must require written explanation, not MCQ.
- Questions should test understanding, not copying.
- One question should be concept-based.
- One question should be application/reasoning-based.
- Keep questions exam-style and clear.
- Do not provide answers.
- Return only the two questions as a numbered list.
"""

    response = ask_llm(
        EVALUATOR_SYSTEM,
        prompt,
        username=username,
        feature="practice_question_generation",
    )

    questions = []

    for line in response.split("\n"):
        cleaned = line.strip()

        if cleaned.startswith("1.") or cleaned.startswith("2."):
            questions.append(cleaned[2:].strip())

    if len(questions) < 2:
        questions = [
            "Explain the main concept from this lesson in your own words.",
            "Give one real-life example or application of this concept.",
        ]

    return {
        "questions": questions[:2],
    }
