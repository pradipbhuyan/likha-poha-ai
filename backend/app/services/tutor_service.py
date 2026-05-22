
from app.services.openai_service import ask_llm
from app.services.rag_service import search_textbook_content


TUTOR_SYSTEM = """
You are a patient GradeCBSE tutor.

Teach only the requested sub-topic.
Do not give the full chapter at once.

Use this structure:
1. What you will learn
2. Simple explanation
3. Step-by-step breakdown
4. Worked example
5. Common mistake
6. Quick check question
7. Summary

Use simple language for a 14-15 year old student.

For Olympiad mode:
- include reasoning
- HOTS thinking
- tricks
- patterns

For Hindi:
- explain in Hindi.

IMPORTANT FORMATTING RULES:
- Do NOT use markdown tables.
- Use bullet points instead of tables.
- Use markdown headings and lists properly.

VISUAL RULES:
- When useful, include Mermaid diagrams.
- Never output Mermaid code unless it is inside a fenced code block.
- Use simple Mermaid labels. Avoid parentheses, plus signs, minus signs, and special symbols inside node labels.
- Example: use Proton positive, not Proton (+).
- Use this exact format:

```mermaid
graph TD
A[Start] --> B[Next Step]
B --> C[End]
```text

MATH RULES:
- Use LaTeX math for formulas.
- Use this format:

$$
v = u + at
$$
"""


def generate_step_lesson(
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
):
    """
    Generate a focused step-wise lesson for a specific sub-topic.
    
    Args:
        grade: Student grade level
        subject: Subject name
        chapter: Chapter name
        mode: Learning mode (standard or olympiad)
        step_title: Current lesson step/sub-topic
        teacher_persona: Optional custom teacher persona
    
    Returns:
        Dictionary with lesson, source_type, and sources
    """
    rag_query = f"""
    Grade 9 {subject} {chapter}
    Current lesson step: {step_title}
    Find textbook explanation, definitions, examples, formulas, important points.
    """

    rag_results = search_textbook_content(
        query=rag_query,
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=5,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=5,
        )

    source_type = "RAG" if rag_results else "LLM"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    ) if rag_results else ""

    prompt = f"""
Grade: {grade}
Mode: {mode}
Subject: {subject}
Chapter: {chapter}
Current sub-topic: {step_title}

Teacher Persona:
{teacher_persona if teacher_persona else "Standard CBSE tutor"}

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Create a focused step-wise lesson only for this sub-topic.
Do not cover unrelated topics.

Use uploaded textbook/RAG context when available.
If RAG context is available, align the explanation with it.
If RAG context is not available, use standard CBSE/SOF knowledge.

End with one small question to check understanding.
"""

    lesson = ask_llm(TUTOR_SYSTEM, prompt)

    return {
        "lesson": lesson,
        "source_type": source_type,
        "sources": rag_results,
    }


def answer_doubt(
    grade: str,
    subject: str,
    chapter: str,
    question: str,
):
    """
    Answer a student's doubt about a topic.
    
    Args:
        grade: Student grade level
        subject: Subject name
        chapter: Chapter name
        question: Student's doubt/question
    
    Returns:
        Dictionary with answer, source_type, and sources
    """
    rag_results = search_textbook_content(
        query=f"{chapter} {question}",
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=3,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=f"{chapter} {question}",
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=3,
        )

    source_type = "RAG" if rag_results else "LLM"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    ) if rag_results else ""

    prompt = f"""
Grade: {grade}
Subject: {subject}
Chapter: {chapter}

Student doubt:
{question}

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Explain step by step.

Use uploaded textbook/RAG context when available.
If RAG context is available, align the answer with it.
If RAG context is not available, use standard CBSE/SOF knowledge.

Do not use markdown tables.
Use bullet points instead.

If useful:
- include Mermaid diagrams
- include LaTeX formulas
- include visual reasoning

For formulas use:

$$
formula
$$
"""

    answer = ask_llm(TUTOR_SYSTEM, prompt)

    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
    }


def answer_lesson_follow_up(
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    step_title: str,
    lesson: str,
    question: str,
):
    """
    Answer a follow-up question about the current lesson.
    
    Args:
        grade: Student grade level
        mode: Learning mode (standard or olympiad)
        subject: Subject name
        chapter: Chapter name
        step_title: Current lesson step
        lesson: Current lesson content
        question: Student's follow-up question
    
    Returns:
        Dictionary with answer, source_type, and sources
    """
    rag_query = f"""
Grade: {grade}
Mode: {mode}
Subject: {subject}
Chapter: {chapter}
Current lesson step: {step_title}
Student follow-up question: {question}
"""

    rag_results = search_textbook_content(
        query=rag_query,
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=3,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=3,
        )

    source_type = "RAG" if rag_results else "LLM"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    ) if rag_results else ""

    prompt = f"""
You are helping a Grade 9 student understand a lesson.

Grade: {grade}
Mode: {mode}
Subject: {subject}
Chapter: {chapter}
Current lesson step: {step_title}

Current lesson content:
{lesson}

Student follow-up question:
{question}

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Answer the follow-up question clearly and briefly.

Rules:
- Use the lesson content as context.
- Use RAG textbook context when available.
- Explain like a friendly tutor.
- Use bullets if helpful.
- Do not repeat the full lesson.
- End with one small check question.
"""

    answer = ask_llm(TUTOR_SYSTEM, prompt)

    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
    }
