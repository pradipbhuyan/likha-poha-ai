
from app.services.openai_service import ask_llm
from app.services.rag_service import search_textbook_content
from app.services.mentor_memory_service import (
    get_recent_mentor_memory,
    build_memory_context,
    save_mentor_memory,
)

from app.services.curriculum_service import (
    build_chapter_outline,
    format_chapter_outline,
)

TUTOR_SYSTEM = """
You are a patient Grade 9 CBSE and SOF Olympiad tutor.

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

DEPTH REQUIREMENTS:
- Teach concepts thoroughly, not superficially.
- Explain WHY, not only WHAT.
- Include conceptual reasoning and scientific logic.
- Use proper textbook terminology naturally.
- Include exam-level conceptual understanding.
- Include important nuances and edge cases when relevant.
- Correct common misconceptions proactively.
- Use real-world intuition and practical interpretation.
- Build understanding progressively from basic to deeper ideas.

FOR SCIENCE:
- Explain mechanisms and cause-effect clearly.
- Explain how and why processes happen.
- Connect concepts with observations and experiments.

FOR MATHEMATICS:
- Explain derivations and reasoning.
- Explain why formulas work.
- Show conceptual meaning behind equations.

FOR OLYMPIAD MODE:
- Increase conceptual rigor significantly.
- Include HOTS reasoning and tricky conceptual patterns.

PEDAGOGY RULES:
- Avoid shallow summaries.
- Avoid generic textbook paraphrasing.
- Explain ideas like an expert teacher teaching a real classroom.
- Every explanation should deepen understanding.

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
- Use Mermaid especially for:
  - science processes
  - systems
  - cycles
  - hierarchies
  - comparisons
  - step-by-step flows
  - cause and effect
  - parts of an object
- Keep Mermaid diagrams simple and educational.
- Use simple Mermaid labels.
- Avoid parentheses, plus signs, minus signs, slashes, and special symbols inside Mermaid node labels.
- Example: use Proton positive, not Proton (+).
- Example: use Electron negative, not Electron (-).
- ALWAYS wrap Mermaid diagrams inside a fenced mermaid code block.
- NEVER output raw graph TD text outside the fenced block.
- Keep every Mermaid node label under 24 characters.
- Use short labels only.
- Use this exact format:

```mermaid
graph TD
A[Start] --> B[Next Step]
B --> C[End]
```

MATH RULES:
- Use LaTeX math for formulas.
- Use this format:

$$
v = u + at
$$
"""


DIAGRAM_HINT = """
Diagram instruction:
If this topic can be understood better visually, include one simple Mermaid diagram.

Good cases for Mermaid:
- science processes
- systems
- cycles
- hierarchies
- comparisons
- step-by-step flows
- cause and effect
- classification

STRICT Mermaid rules:
- ALWAYS wrap Mermaid diagrams inside a fenced mermaid code block.
- NEVER output raw graph TD text outside the fenced block.
- Keep every node label under 24 characters.
- Use short labels like Inertia, Force, Acceleration, Reaction.
- Do not write full sentences inside Mermaid nodes.
- Avoid parentheses, plus signs, minus signs, slashes, and special symbols inside Mermaid labels.
- Use only simple educational flowcharts.
- Use this exact format:

```mermaid
graph TD
A[Start] --> B[Next]
B --> C[End]
```
"""

def ensure_mermaid_fences(text: str) -> str:
    if not text or "graph TD" not in text or "```mermaid" in text:
        return text

    lines = text.split("\n")
    output = []
    in_graph = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("graph TD"):
            output.append("```mermaid")
            output.append(line)
            in_graph = True
            continue

        if in_graph:
            is_graph_line = (
                stripped == ""
                or "-->" in stripped
                or "-.->" in stripped
                or stripped.startswith("subgraph")
                or stripped == "end"
            )

            if is_graph_line:
                output.append(line)
            else:
                output.append("```")
                output.append(line)
                in_graph = False
            continue

        output.append(line)

    if in_graph:
        output.append("```")

    return "\n".join(output)

import re


def sanitize_mermaid(text: str) -> str:
    if "```mermaid" not in text:
        return text

    def clean_line(line: str):
        if "-->" not in line:
            return line

        line = re.sub(r"[(){}:+*/=,]", "", line)

        line = re.sub(
            r"\[(.*?)\]",
            lambda m: "[" + m.group(1)[:22] + "]",
            line,
        )

        return line

    output = []

    for line in text.split("\n"):
        output.append(clean_line(line))

    return "\n".join(output)

def generate_step_lesson(
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
    username: str = "unknown",
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
        match_count=15,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=15,
        )

    source_type = "RAG" if rag_results else "LLM"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    ) if rag_results else ""

    chapter_outline = build_chapter_outline(
        grade=grade,
        subject=subject,
        chapter=chapter,
    )

    chapter_outline_text = format_chapter_outline(
        chapter_outline
    )

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

Textbook chapter outline:
{chapter_outline_text}

Create a focused step-wise lesson only for this sub-topic.
Do not cover unrelated topics.

Textbook coverage rules:
- Use the uploaded textbook context deeply.
- Do not create a shallow summary.
- Extract and teach all important concepts present in the retrieved textbook context.
- Preserve the textbook's learning progression where possible.
- Include important definitions, examples, activities, experiments, observations, conclusions, applications, and review-style questions from the textbook context.
- If the textbook contains "Activity", "Pause and Ponder", "Think as a Scientist", "At a Glance", or review questions, include their learning value in the lesson.
- Explain how each idea connects to the next.
- Do not skip important subtopics from the retrieved textbook context.

Depth instructions:
- Teach this topic in strong conceptual depth.
- Include conceptual intuition and scientific reasoning.
- Explain WHY concepts work.
- Include misconception correction.
- Include exam framing where relevant.
- Include practical interpretation and applications.
- Do not oversimplify important concepts.
- Aim for real classroom-quality teaching.

Use uploaded textbook/RAG context when available.
If RAG context is available, align the explanation with it.
If RAG context is not available, use standard CBSE/SOF knowledge.

{DIAGRAM_HINT}

- Keep every Mermaid node label under 24 characters.
- Use short labels like Inertia, Force, Acceleration, Reaction.
- Do not write full sentences inside Mermaid nodes.

Worked example requirements:
- Solve examples step-by-step.
- Explain the reasoning behind each step.
- Explain why each formula or method is used.
- Include conceptual interpretation of the final answer.

Before explaining, identify the textbook coverage being used:
- Key concepts covered
- Important examples or activities
- Important exam/reasoning points

Then teach the lesson in depth.

End with one small question to check understanding.
"""

    lesson = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="lesson",
    )

    lesson = ensure_mermaid_fences(lesson)
    lesson = sanitize_mermaid(lesson)

    return {
        "lesson": lesson,
        "source_type": source_type,
        "sources": rag_results,
    }


def answer_doubt(
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    question: str,
    username: str = "unknown",
):
    rag_query = f"""
    Student doubt:
    {question}
IMPORTANT:
- The CURRENT student doubt is the highest priority.
- Do NOT continue previous topics unless explicitly asked.
- Ignore older mentor memory if it conflicts with the current doubt.
- Treat each new doubt as a fresh topic unless the student clearly asks for continuation.
- Answer ONLY the current doubt asked above.


    Find any relevant textbook explanation, definition, formula, example, or concept.
    """

    rag_results = search_textbook_content(
        query=rag_query,
        grade=grade,
        subject=subject if subject else None,
        chapter=chapter if chapter else None,
        match_count=15,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            grade=grade,
            subject=None,
            chapter=None,
            match_count=15,
        )

    source_type = "RAG" if rag_results else "LLM"

    textbook_context = "\n\n".join(
        item.get("chunk_text", "")
        for item in rag_results
    ) if rag_results else ""

    memories = get_recent_mentor_memory(
        username=username,
        limit=5,
    )

    memory_context = build_memory_context(memories)

    prompt = f"""
Grade: {grade}
Mode: {mode}
Subject: {subject if subject else "Open doubt"}
Chapter: {chapter if chapter else "Open topic"}

CURRENT STUDENT DOUBT:
{question}

IMPORTANT:
- Answer ONLY the CURRENT STUDENT DOUBT above.
- Do not continue any previous topic.
- Do not answer from earlier conversation memory.
- If the current doubt is "what is matter", answer matter only.
- If the current doubt is "what is cell", answer cell only.

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Explain clearly for a Grade 9 student.

Use uploaded textbook/RAG context when available.
If RAG context is available, align the answer with it.
If RAG context is not available, use standard CBSE/SOF knowledge.

Do not use markdown tables.
Use bullet points instead.

{DIAGRAM_HINT}

- Keep every Mermaid node label under 24 characters.
- Use short labels like Inertia, Force, Acceleration, Reaction.
- Do not write full sentences inside Mermaid nodes.

For formulas:
- Use inline LaTeX like $F = m \times a$
- Use display LaTeX like:

$$
F = m \times a
$$

- Never write formulas inside normal parentheses like:
( F = m \times a )
"""

    answer = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="doubt",
    )

    answer = ensure_mermaid_fences(answer)
    answer = sanitize_mermaid(answer)
    

    save_mentor_memory(
        username=username,
        grade=grade,
        mode=mode,
        subject=subject,
        chapter=chapter,
        question=question,
        answer=answer,
    )

    suggestions = []

    lower_question = question.lower()

    if "formula" in lower_question or "equation" in lower_question:
        suggestions.append("Show a worked example")

    if "diagram" in lower_question or "structure" in lower_question:
        suggestions.append("Explain the structure step-by-step")

    if "not understand" in lower_question or "confused" in lower_question:
        suggestions.append("Explain in simpler language")

    if "why" in lower_question:
        suggestions.append("Give a real-life analogy")

    if not suggestions:
        suggestions = [
            "Give a practice question",
            "Explain step-by-step",
            "Give a real-life example",
        ]


    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
        "mentor_suggestions": suggestions,
    }

def answer_lesson_follow_up(
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    step_title: str,
    lesson: str,
    question: str,
    username: str = "unknown",
):
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
        match_count=10,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=10,
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
- If the answer benefits from a visual, include one Mermaid diagram.
- End with one small check question.

{DIAGRAM_HINT}
- Keep every Mermaid node label under 24 characters.
- Use short labels like Inertia, Force, Acceleration, Reaction.
- Do not write full sentences inside Mermaid nodes.


"""

    answer = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="lesson_followup",
    )

    answer = ensure_mermaid_fences(answer)
    answer = sanitize_mermaid(answer)

    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
    }
