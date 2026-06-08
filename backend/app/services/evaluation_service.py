import json
import re

from app.services.openai_service import ask_llm
from app.services.mentor_memory_service import save_mentor_memory


EVALUATOR_SYSTEM = """
You are an expert CBSE examiner and teacher for Class 1 to Class 10 students.

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
- Do not impose pass/fail language.
- Always help the student learn from the attempt.

Output format:

## Score
X/10

## What was correct
- ...

## What can be better
- ...

## Key words to include
- Use bold markdown for important terms, for example **photosynthesis**.
- Include short notes on why each keyword matters.

## Improved answer
Provide a strong model answer suitable for the student's grade.

## One improvement tip
Short actionable advice.
"""


def _is_math_subject(subject: str) -> bool:
    """Identify maths subjects for MCQ-only practice generation."""
    return subject in {"Maths", "Maths Olympiad", "Mathematics"}


def _is_hindi_subject(subject: str) -> bool:
    """Identify Hindi subjects for MCQ-only practice generation."""
    return subject in {"Hindi", "Hindi Olympiad"}


def _extract_json_array(text: str) -> list[dict]:
    """Parse a model response that should contain one JSON array."""
    stripped = text.strip()

    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    start = stripped.find("[")
    end = stripped.rfind("]")

    if start == -1 or end == -1 or end <= start:
        return []

    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    return [item for item in parsed if isinstance(item, dict)]


def _fallback_practice_questions(subject: str) -> list[dict]:
    """Provide structured practice questions if LLM formatting is unusable."""
    if _is_math_subject(subject) or _is_hindi_subject(subject):
        return [
            {
                "type": "mcq",
                "question": "पाठ पढ़ते समय सबसे अच्छा तरीका क्या है?"
                if _is_hindi_subject(subject)
                else "Which option best matches the main idea from this lesson?",
                "options": [
                    "मुख्य विचार समझकर उदाहरण से जोड़ना।"
                    if _is_hindi_subject(subject)
                    else "The concept can be applied using a clear rule or method.",
                    "केवल शीर्षक याद करना।"
                    if _is_hindi_subject(subject)
                    else "The concept only needs memorisation.",
                    "प्रश्न को बिना पढ़े उत्तर चुनना।"
                    if _is_hindi_subject(subject)
                    else "The concept has no examples.",
                    "सबसे लंबा विकल्प चुनना।"
                    if _is_hindi_subject(subject)
                    else "The concept cannot be checked step by step.",
                ],
                "answer": "मुख्य विचार समझकर उदाहरण से जोड़ना।"
                if _is_hindi_subject(subject)
                else "The concept can be applied using a clear rule or method.",
                "explanation": "हिंदी में अच्छा उत्तर मुख्य विचार, पात्र या प्रसंग, और एक छोटा उदाहरण जोड़कर लिखा जाता है।"
                if _is_hindi_subject(subject)
                else "Maths practice should check whether you can identify and apply the method, not only remember a definition.",
                "expected_keywords": ["मुख्य विचार", "उदाहरण", "पूरा वाक्य"]
                if _is_hindi_subject(subject)
                else ["method", "rule", "step"],
            },
            {
                "type": "mcq",
                "question": "हिंदी उत्तर लिखते समय कौन-सी बात सबसे उपयोगी है?"
                if _is_hindi_subject(subject)
                else "What should you do before choosing the final answer in a maths problem?",
                "options": [
                    "स्पष्ट, पूरे वाक्यों में उत्तर लिखना।"
                    if _is_hindi_subject(subject)
                    else "Check the given values and the rule used.",
                    "बहुत छोटे और अधूरे शब्द लिखना।"
                    if _is_hindi_subject(subject)
                    else "Pick the longest option.",
                    "प्रश्न से अलग बात लिखना।"
                    if _is_hindi_subject(subject)
                    else "Skip the working.",
                    "पाठ के संदर्भ को छोड़ देना।"
                    if _is_hindi_subject(subject)
                    else "Ignore units and signs.",
                ],
                "answer": "स्पष्ट, पूरे वाक्यों में उत्तर लिखना।"
                if _is_hindi_subject(subject)
                else "Check the given values and the rule used.",
                "explanation": "उत्तर लिखते समय स्पष्ट वाक्य, पाठ से जुड़ा कारण, और सही शब्द चयन जरूरी होता है।"
                if _is_hindi_subject(subject)
                else "Good maths answers come from checking values, signs, units, and the rule used.",
                "expected_keywords": ["स्पष्ट वाक्य", "कारण", "पाठ"]
                if _is_hindi_subject(subject)
                else ["given values", "rule", "check"],
            },
        ]

    return [
        {
            "type": "mcq",
            "question": "Which option best captures the main idea from this lesson?",
            "options": [
                "The idea explains a key concept and how it is used.",
                "The idea is only a definition to memorise.",
                "The idea is unrelated to examples.",
                "The idea cannot be explained in simple words.",
            ],
            "answer": "The idea explains a key concept and how it is used.",
            "explanation": "A good answer connects the concept with use, example, or reasoning.",
            "expected_keywords": ["concept", "example", "reason"],
        },
        {
            "type": "descriptive",
            "question": "Explain the main concept from this lesson in your own words. Add one example if possible.",
            "expected_keywords": ["concept", "example", "reason"],
        },
    ]


def evaluate_student_answer(
    grade: str,
    question: str,
    student_answer: str,
    ideal_context: str,
    username: str = "unknown",
    mode: str = "CBSE",
    subject: str = "",
    chapter: str = "",
    step_title: str = "",
    question_type: str = "descriptive",
    expected_keywords: list[str] | None = None,
):
    """
    Evaluate a student answer as coaching feedback, not as a progression gate.

    The model returns teacher feedback; the service extracts an X/10 score so
    the lesson page can show a useful practice signal and mentor memory can
    guide future revision.
    """
    expected_keywords = expected_keywords or []
    prompt = f"""
Question:
{question}

Question type:
{question_type}

Student answer:
{student_answer}

Reference lesson/context:
{ideal_context}

Expected keywords if known:
{", ".join(expected_keywords) if expected_keywords else "Infer the important keywords from the lesson context."}

Evaluate the student's answer carefully.

Important:
- Evaluate at the expected level for {grade}.
- Use simpler expectations for Classes 1-5 and stronger exam expectations for Classes 6-10.
- Focus on conceptual understanding.
- Reward partial understanding.
- Correct misconceptions clearly.
- Keep tone encouraging.
- Do not say PASS or FAIL.
- Under "Key words to include", bold every important keyword using markdown.
- Improved answer should be exam-ready and easy to revise.
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

    try:
        memory_answer = (
            f"Practice score: {score}/10. Question type: {question_type}. "
            f"Feedback: {evaluation[:700]}"
        )
        save_mentor_memory(
            username=username,
            grade=grade,
            mode=mode,
            subject=subject,
            chapter=chapter or step_title,
            question=f"Practice: {question}",
            answer=memory_answer,
        )
    except Exception:
        # Practice memory should never block answer evaluation.
        pass

    return {
        "evaluation": evaluation,
        "score": score,
        "passed": passed,
    }
    
def generate_practice_questions(
    grade: str,
    lesson: str,
    chapter: str,
    step_title: str,
    username: str = "unknown",
    subject: str = "",
):
    """
    Generate subject-aware structured practice questions for a lesson step.

    Maths and Hindi receive two MCQs. Science, English, and Social Science
    receive one MCQ plus one descriptive answer prompt with no word limit.
    """
    if _is_math_subject(subject) or _is_hindi_subject(subject):
        pattern_rule = "Create exactly 2 MCQ questions and 0 descriptive questions."
    else:
        pattern_rule = "Create exactly 1 MCQ question and exactly 1 descriptive question."

    prompt = f"""
Create exactly 2 practice questions for a {grade} student.

Chapter:
{chapter}

Subject:
{subject or "Unknown"}

Lesson step:
{step_title}

Lesson content:
{lesson}

Rules:
- Keep wording and difficulty suitable for {grade}.
- Questions should test understanding, not copying.
- {pattern_rule}
- For Hindi, keep the questions and options in Hindi when the lesson context is Hindi.
- MCQ questions must have exactly 4 options.
- MCQ "answer" must exactly match one option.
- MCQ explanation must explain why the answer is right and why a common distractor is wrong.
- Descriptive questions must not mention a word limit.
- Include 3 to 6 expected_keywords for every question.
- Keep questions exam-style and clear.
- Return only valid JSON as an array.

JSON shape:
[
  {{
    "type": "mcq",
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "answer": "...",
    "explanation": "...",
    "expected_keywords": ["...", "..."]
  }},
  {{
    "type": "descriptive",
    "question": "...",
    "expected_keywords": ["...", "..."]
  }}
]
"""

    response = ask_llm(
        EVALUATOR_SYSTEM,
        prompt,
        username=username,
        feature="practice_question_generation",
    )

    questions = _extract_json_array(response)

    if len(questions) < 2:
        questions = _fallback_practice_questions(subject)

    return {
        "questions": questions[:2],
    }
