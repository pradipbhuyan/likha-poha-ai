import json
import re

from app.services.openai_service import ask_llm
from app.services.mentor_memory_service import save_mentor_memory


EVALUATOR_SYSTEM = """
You are a strict but supportive CBSE teacher for Class 1 to Class 10 students.

Your role:
- Give accurate, textbook-grounded coaching feedback on student answers.
- Answers must reference SPECIFIC facts, terms, events, or details from the lesson.
- General knowledge or vague answers that avoid the specific textbook content should be clearly flagged.

Evaluation rules:
- NEVER give a numeric score or rating (no X/10, no percentages, no grades).
- NEVER say PASS, FAIL, or any judgment word.
- Start by highlighting what the student got RIGHT, but only if it is factually correct and textbook-specific.
- Clearly explain what is missing — especially if the answer is too vague or uses only general knowledge.
- Correct any misconceptions firmly but kindly.
- Always end with an encouraging note.
- If the answer contains NO specific textbook details, say so clearly: "Your answer is too general — use specific facts from the chapter."

Output format (use exactly these section headings):

## What you got right
- List specific points the student answered correctly with brief praise.

## What can be improved
- Explain clearly what is missing or could be stronger.
- For each point, say WHY it matters for understanding.
- Use simple language appropriate for the grade.

## Key terms to strengthen your answer
- **term** — short explanation of why this term is important.

## A stronger answer would look like this
Write a model answer at the right level for the student's grade.

## Keep going!
One encouraging sentence to motivate further effort.
"""

MCQ_EVALUATOR_SYSTEM = """
You are a concise CBSE teacher giving instant MCQ feedback to a student.

Rules:
- Be brief. Maximum 5 lines total.
- NEVER say PASS, FAIL, score, or grade.
- Do NOT use section headings or bullet lists.
- Do NOT write a long model answer or lists of key terms.

Format (follow exactly, nothing more):

**✓ Correct!** or **✗ Incorrect — the right answer is: [correct option text]**

One sentence explaining WHY the correct answer is right.

**Exam tip:** If asked as a written question, answer: [one concise sentence using 1–2 key subject terms].
"""


def _is_math_subject(subject: str) -> bool:
    """Identify maths subjects for MCQ-only practice generation."""
    return subject in {"Maths", "Mathematics"}


def _is_hindi_subject(subject: str) -> bool:
    """Identify Hindi subjects for MCQ-only practice generation."""
    return subject == "Hindi"


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


def _keyword_based_evaluation(
    student_answer: str,
    expected_keywords: list[str],
) -> dict:
    """
    Score a descriptive answer by keyword coverage — zero LLM cost.

    Checks how many expected_keywords appear in the student's answer and
    returns a score, coverage feedback, and a template improvement tip.
    Used when expected_keywords are known (from question bank or cached questions).
    """
    answer_lower = student_answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]
    total = len(expected_keywords)

    if total == 0:
        score = 5
    else:
        score = round((len(found) / total) * 10)

    # Stricter: don't award points just for attempting — must cover keywords
    score = max(0, min(10, score))

    lines = []

    if found:
        lines.append("## What you got right")
        for kw in found:
            lines.append(f"- ✅ You included **{kw}** — well done!")
        lines.append("")
    else:
        lines.append("## What you got right")
        lines.append("- You made an attempt — that is the most important first step! Keep going.")
        lines.append("")

    if missing:
        lines.append("## What can be improved")
        for kw in missing:
            lines.append(f"- 📝 Try to also mention **{kw}** — this is an important part of the answer.")
        lines.append("")
    else:
        lines.append("## What can be improved")
        lines.append("- Excellent coverage! Try writing each keyword in a complete sentence to make your answer even stronger.")
        lines.append("")

    lines.append("## Key terms to strengthen your answer")
    for kw in expected_keywords:
        lines.append(f"- **{kw}**")
    lines.append("")

    lines.append("## Keep going!")
    if missing:
        lines.append(f"You are on the right track! Try adding **{missing[0]}** to your next attempt and see how much stronger it sounds.")
    else:
        lines.append("Excellent work! You have included all the key ideas. Keep practising to make your answers even clearer.")

    return {
        "evaluation": "\n".join(lines),
        "score": score,
        "passed": score >= 7,  # Stricter: 70%+ keyword coverage required to pass
    }


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
    correct_answer: str = "",
):
    """
    Evaluate a student answer as coaching feedback, not as a progression gate.

    Keyword-first: when expected_keywords are provided, evaluation is instant
    with zero LLM cost using keyword coverage scoring. Only falls back to LLM
    when no keywords are available (e.g. inline lesson questions).
    """
    expected_keywords = expected_keywords or []

    # -------------------------------------------------- MCQ (instant, no LLM)
    if question_type == "mcq":
        # Use explicit correct_answer if provided; fall back to expected_keywords[0]
        if not correct_answer and expected_keywords:
            correct_answer = expected_keywords[0]
        is_correct = student_answer.strip().lower() == correct_answer.strip().lower()
        score = 10 if is_correct else 0
        # Build feedback from stored explanation — zero LLM cost
        explanation = ideal_context[:300] if ideal_context else ""
        if is_correct:
            feedback = f"**✓ Correct!**\n\n{explanation}" if explanation else "**✓ Correct!**"
        else:
            feedback = f"**✗ Incorrect** — the right answer is: **{correct_answer}**\n\n{explanation}" if explanation else f"**✗ Incorrect** — the right answer is: **{correct_answer}**"
        try:
            save_mentor_memory(
                username=username,
                grade=grade,
                mode=mode,
                subject=subject,
                chapter=chapter or step_title,
                question=f"MCQ: {question}",
                answer=f"Selected: {student_answer}. Correct: {is_correct}.",
            )
        except Exception:
            pass
        return {"evaluation": feedback, "score": score, "passed": is_correct}
    # ---------------------------------------------------- end MCQ

    # ------------------------------------------------- keyword-based (no LLM)
    if question_type == "descriptive" and expected_keywords:
        result = _keyword_based_evaluation(student_answer, expected_keywords)

        try:
            save_mentor_memory(
                username=username,
                grade=grade,
                mode=mode,
                subject=subject,
                chapter=chapter or step_title,
                question=f"Practice: {question}",
                answer=f"Practice score: {result['score']}/10. Keyword feedback.",
            )
        except Exception:
            pass

        return result
    # -------------------------------------------- end keyword-based

    # Fallback: LLM evaluation (inline lesson questions without keywords)
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
        pass

    return {
        "evaluation": evaluation,
        "score": score,
        "passed": passed,
    }
    
def _bank_question_to_practice(q: dict) -> dict:
    """Convert a question_bank row (options as dict, answer as letter) to practice format."""
    opts_dict = q.get("options") or {}
    options_list = [str(opts_dict.get(k, "")) for k in ("A", "B", "C", "D") if k in opts_dict]
    answer_letter = q.get("answer", "A")
    answer_text = str(opts_dict.get(answer_letter, ""))
    return {
        "type": "mcq",
        "question": q.get("question", ""),
        "options": options_list,
        "answer": answer_text,
        "explanation": q.get("explanation", ""),
        "expected_keywords": [],
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
    Generate 2 practice questions for the current lesson step.

    Fast path: search the question bank for this chapter — returns instantly,
    questions are chapter-specific. Falls back to LLM only when the bank has
    fewer than 2 usable questions.

    LLM fallback generates questions directly from the lesson step content so
    they are always relevant to what was just taught.
    """
    # ── Prewarm cache check — highest priority ────────────────────────────────
    # Admin-generated questions from RAG textbook content (via Lesson Prewarm tab)
    # take precedence over the question bank. They are chapter-specific and accurate.
    try:
        from app.services.lesson_cache_service import make_lesson_cache_key, get_cached_lesson  # noqa: PLC0415
        _cache_key = make_lesson_cache_key(
            board="CBSE",
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode="CBSE",
            step_title=step_title,
            teacher_persona="",
        )
        _cached = get_cached_lesson(_cache_key, grade=grade)
        if _cached:
            _prewarm_qs = _cached.get("practice_questions") or []
            if _prewarm_qs and len(_prewarm_qs) >= 1:
                return {"questions": _prewarm_qs}
    except Exception:
        pass
    # ── End prewarm cache check ───────────────────────────────────────────────

    # ── Question bank only — no LLM ───────────────────────────────────────────
    # With 140,000+ questions in the bank, every chapter should have enough.
    # Tries multiple difficulty levels to maximise hit rate.
    # Returns [] if no questions found for this chapter.
    try:
        from app.services.question_bank_service import get_questions_from_bank  # noqa: PLC0415
        # Strip common chapter prefixes that differ between syllabus and bank
        # e.g. "Chapter 6: Measuring Space: Perimeter and Area" → "Measuring Space: Perimeter and Area"
        import re as _re_local  # noqa: PLC0415
        clean_for_bank = _re_local.sub(r"^Chapter\s+\d+\s*:\s*", "", chapter or "", flags=_re_local.IGNORECASE).strip()

        for difficulty_try in ("Medium", "Easy", "Hard", "medium", "easy", "hard"):
            for chapter_try in ([chapter, clean_for_bank] if clean_for_bank != chapter else [chapter]):
                try:
                    bank_qs = get_questions_from_bank(
                        board="CBSE",
                        grade=grade,
                        subject=subject,
                        chapter=chapter_try,
                        difficulty=difficulty_try,
                        num_questions=2,
                        excluded_ids=[],
                    )
                    if bank_qs and len(bank_qs) >= 1:
                        return {"questions": [_bank_question_to_practice(q) for q in bank_qs[:2]]}
                except Exception:
                    continue
    except Exception:
        pass
    # No questions found in bank for this chapter
    return {"questions": []}
