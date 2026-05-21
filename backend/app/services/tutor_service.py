from app.services.openai_service import ask_llm
from app.services.rag_service import search_textbook_content


TUTOR_SYSTEM = """
You are a patient Grade 9 CBSE tutor.

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
- Wrap Mermaid diagrams exactly like this:

```mermaid
graph TD
A[Start] --> B[Next Step]
B --> C[End]
"""


def generate_step_lesson(
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
):
 
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

    source_type = "LLM"

    if rag_results:
        source_type = "RAG"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    )

    prompt = f"""
Grade: {grade}
Mode: {mode}
Subject: {subject}
Chapter: {chapter}
Current sub-topic: {step_title}

Teacher Persona:
{teacher_persona}

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
    
    source_type = "LLM"

    if rag_results:
        source_type = "RAG"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    )

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

