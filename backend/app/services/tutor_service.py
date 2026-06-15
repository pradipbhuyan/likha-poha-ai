
from app.services.openai_service import DEFAULT_TEXT_MODEL, ask_llm, PREWARM_TEXT_MODEL
from app.services.rag_service import search_textbook_content
from app.services.rag_visual_service import (
    find_visual_assets_for_question,
    get_lesson_step_visual_assets,
)
from app.services.mentor_memory_service import (
    get_recent_mentor_memory,
    build_memory_context,
    save_mentor_memory,
)
from app.services.curriculum_service import (
    build_chapter_outline,
    format_chapter_outline,
)
import re as _re

from app.services.lesson_cache_service import (
    make_lesson_cache_key,
    get_cached_lesson,
    get_cached_lesson_by_chapter_text,
    store_lesson_cache,
)

# Display-source prefixes added when multiple books are uploaded for one subject.
# The lesson cache may have been built before these prefixes were introduced,
# so we strip them for the fallback lookup.
_CHAPTER_SOURCE_PREFIX_RE = _re.compile(
    r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
    r"History|Geography|Political Science|Economics)\s*[-:]\s*",
    _re.IGNORECASE,
)


def _strip_chapter_source_prefix(chapter: str) -> str:
    """Remove a book-source display prefix from a chapter label for cache fallback."""
    return _CHAPTER_SOURCE_PREFIX_RE.sub("", chapter or "").strip()

TUTOR_SYSTEM = """
	You are a patient CBSE and SOF Olympiad tutor for Class 1 to Class 10 students.

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

	Use language, examples, and depth suitable for the grade provided in the user prompt.

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
- Only the "Quick check question" section may ask a question.
- Do not add a "Quick check question:" line inside any other section or after a visual.
- All other sections must end with a statement or instruction, not a question.
- Do not ask conversational questions such as "Would you like that?" or
  "Should we continue?" because the app will not process those as answers.
- In Summary, tell the student what to do next, for example:
  "Review these key points, then move to the next lesson step when ready."

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
- Do NOT use Mermaid diagrams.
- Use a visual only when it clearly improves learning.
- If a visual is useful, include exactly one fenced visual-json code block.
- Use only facts from the lesson or textbook context. If unsure, skip the visual.
- Keep labels short and complete so students are never shown cut-off text.
- Allowed visual types:
  - flow: sequence or cause-effect
  - steps: ordered method
  - cycle: repeating process
  - compare: two-column comparison
- For flow, steps, and cycle, use this shape:

```visual-json
{"type":"flow","title":"Short title","items":["Short complete label","Short complete label","Short complete label"],"note":"Optional one-line note"}
```

- For compare, use this shape:

```visual-json
{"type":"compare","title":"Short title","columns":["Idea A","Idea B"],"rows":[["Short point","Short point"],["Short point","Short point"]]}
```

- Limits:
  - title under 80 characters
  - each label under 70 characters
  - 2 to 6 items for flow, steps, and cycle
  - 2 columns and 2 to 5 rows for compare

MATH RULES:
- Use LaTeX math for formulas.
- Inline formulas MUST use dollar delimiters, for example $\\frac{p}{q}$ and $q \\neq 0$.
- If an inline formula starts with a number, add a space after the opening dollar.
  Bad: $10 - 2 \\times 4 = 2$
  Good: $ 10 - 2 \\times 4 = 2 $
- Display formulas MUST use double-dollar delimiters.
- Never place LaTeX commands inside normal parentheses.
- Bad: (\\frac{p}{q}), (q \\neq 0), (7 = \\frac{7}{1})
- Good: $\\frac{p}{q}$, $q \\neq 0$, $7 = \\frac{7}{1}$
- Use this display format:

$$
v = u + at
$$
	"""


DIAGRAM_HINT = """
Visual instruction:
Do not use Mermaid.
If this topic can be understood better visually, include one validated
visual-json block only.

Good cases for visual-json:
- science processes
- systems
- cycles
- comparisons
- step-by-step flows
- cause and effect
- classification

STRICT visual-json rules:
- Use only facts from the lesson or textbook context.
- If you are not confident the visual is correct, do not include a visual.
- Keep labels short, complete, and student-safe.
- Do not include cut-off words.
- Do not include more than one visual-json block.
- Use this format for a flow:

```visual-json
{"type":"flow","title":"Short title","items":["Short complete label","Short complete label","Short complete label"],"note":"Optional one-line note"}
```

- Use this format for a comparison:

```visual-json
{"type":"compare","title":"Short title","columns":["Idea A","Idea B"],"rows":[["Short point","Short point"],["Short point","Short point"]]}
```
"""

def ensure_mermaid_fences(text: str) -> str:
    """
    Wrap raw Mermaid graph output in fenced code blocks when the model forgets.

    The React renderer only recognizes Mermaid inside ```mermaid fences, so this
    cleanup keeps diagrams renderable without asking the model again.
    """
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
    """
    Remove Mermaid-breaking punctuation and shorten node labels in diagrams.

    The LLM can produce labels that are valid prose but invalid Mermaid syntax;
    this normalizer protects the frontend diagram renderer from blank/error
    states.
    """
    if "```mermaid" not in text:
        return text

    def clean_line(line: str):
        """Clean one Mermaid edge line without touching non-edge prose."""
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


def remove_mermaid_blocks(text: str) -> str:
    """
    Remove Mermaid output from student-facing answers.

    Visuals are only shown when they arrive as validated visual-json. Mermaid has
    proven too fragile for reliable student learning, so both fenced diagrams
    and loose graph snippets are stripped before returning the answer.
    """
    if not text:
        return text

    without_fenced = re.sub(
        r"```mermaid[\s\S]*?```",
        "",
        text,
        flags=re.IGNORECASE,
    )

    lines = without_fenced.split("\n")
    output = []
    in_loose_graph = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("graph TD") or stripped.startswith("flowchart"):
            in_loose_graph = True
            continue

        if in_loose_graph:
            is_graph_line = (
                stripped == ""
                or "-->" in stripped
                or "-.->" in stripped
                or stripped.startswith("subgraph")
                or stripped == "end"
                or bool(re.match(r"^[A-Za-z0-9_]+\[.*\]$", stripped))
            )

            if is_graph_line:
                continue

            in_loose_graph = False

        output.append(line)

    return "\n".join(output).strip()

def generate_step_lesson(
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
    username: str = "unknown",
    board: str = "CBSE",
    model: str = DEFAULT_TEXT_MODEL,
):
    """
    Generate one focused lesson step using RAG when uploaded context exists.

    Cache-first: checks lesson_cache before calling the LLM. On cache hit the
    lesson is returned instantly with zero token cost. On cache miss the LLM
    generates as normal and the result is stored for future requests.

    Pass model=PREWARM_TEXT_MODEL for offline pre-generation (75% cheaper).
    Live student requests use DEFAULT_TEXT_MODEL for best quality.

    The function first searches exact chapter material, falls back to broader
    subject material, and only then relies on general model knowledge. Returned
    source metadata lets the frontend show whether textbook content was used.
    """
    # ------------------------------------------------------------------ cache
    cache_key = make_lesson_cache_key(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        mode=mode,
        step_title=step_title,
        teacher_persona=teacher_persona or "",
    )
    cached = get_cached_lesson(cache_key)

    # Fallback 1 (PERSONA): prewarm stores lessons with teacher_persona="".
    # Try the empty-persona key when the request has a non-empty persona.
    if not cached and (teacher_persona or "").strip():
        fallback_key = make_lesson_cache_key(
            board=board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=mode,
            step_title=step_title,
            teacher_persona="",
        )
        cached = get_cached_lesson(fallback_key)

    # Fallback 2 (SOURCE-PREFIX): the lesson cache may have been built before
    # multi-book display prefixes were introduced (e.g. "Text Book - Chapter 7").
    # Try the same lookups with the source prefix stripped from the chapter name.
    stripped_chapter = _strip_chapter_source_prefix(chapter)
    if not cached and stripped_chapter and stripped_chapter != chapter:
        # Try stripped chapter with original persona
        stripped_key = make_lesson_cache_key(
            board=board,
            grade=grade,
            subject=subject,
            chapter=stripped_chapter,
            mode=mode,
            step_title=step_title,
            teacher_persona=teacher_persona or "",
        )
        cached = get_cached_lesson(stripped_key)

        # Also try stripped chapter with empty persona
        if not cached and (teacher_persona or "").strip():
            stripped_empty_key = make_lesson_cache_key(
                board=board,
                grade=grade,
                subject=subject,
                chapter=stripped_chapter,
                mode=mode,
                step_title=step_title,
                teacher_persona="",
            )
            cached = get_cached_lesson(stripped_empty_key)

    # Fallback 3 (TEXT SEARCH): the cache key is a hash so prefix mismatches
    # between prewarm time and request time produce different hashes even for
    # the same chapter.  As a last resort, query the lesson_cache table by the
    # core chapter text (ilike) so 'Economics - Chapter 1: Development' and
    # 'Text Book - Chapter 1: Development' both resolve to the same row.
    if not cached:
        cached = get_cached_lesson_by_chapter_text(
            board=board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=mode,
            step_title=step_title,
        )
        if cached:
            # Backfill the primary cache key so future lookups are direct hash
            # hits (avoids repeated ilike queries and ensures the prewarm counter
            # counts this chapter correctly).
            store_lesson_cache(
                cache_key=cache_key,
                lesson_content=cached["lesson_content"],
                source_type=cached.get("source_type", "CACHE"),
                board=board,
                grade=grade,
                subject=subject,
                chapter=chapter,
                mode=mode,
                step_title=step_title,
                teacher_persona=teacher_persona or "",
                practice_questions=cached.get("practice_questions") or [],
            )

    if cached:
        return {
            "lesson": cached["lesson_content"],
            "source_type": cached.get("source_type", "CACHE"),
            "sources": [],
            "textbook_visuals": [],
            "practice_questions": cached.get("practice_questions") or [],
            "from_cache": True,
        }
    # --------------------------------------------------------------- end cache

    rag_query = f"""
    {grade} {subject} {chapter}
    Current lesson step: {step_title}
    Find textbook explanation, definitions, examples, formulas, important points.
    """

    rag_results = search_textbook_content(
        query=rag_query,
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=15,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            board=board,
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
        board=board,
        subject=subject,
        chapter=chapter,
    )

    chapter_outline_text = format_chapter_outline(
        chapter_outline
    )

    textbook_visuals = get_lesson_step_visual_assets(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        lesson_context=textbook_context,
        limit=3,
    )

    textbook_visual_context = "\n".join(
        (
            f"- Page {visual.get('page_number')}: "
            f"{visual.get('caption') or visual.get('title') or visual.get('chapter')}"
        )
        for visual in textbook_visuals
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

Approved textbook visuals available for this exact lesson context:
{textbook_visual_context if textbook_visual_context else "No approved textbook visual assets found."}

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
- If approved textbook visuals are listed, weave them logically into the lesson
  with a short instruction such as "Look at the textbook visual below..." only
  when the visual supports the current idea.
- Do not invent, request, or describe a different image. If no listed visual
  fits the idea being taught, teach normally without mentioning visuals.

	Depth instructions:
	- Teach this topic at the right depth for {grade}.
	- Use simpler words, concrete examples, and shorter steps for Classes 1-5.
	- Use stronger conceptual reasoning and exam framing for Classes 6-10.
	- Include conceptual intuition and scientific reasoning when age-appropriate.
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

End with a short next-step instruction, not a question. The only student-facing
question should be inside the "Quick check question" section.
"""

    lesson = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="lesson",
        model=model,
    )

    lesson = remove_mermaid_blocks(lesson)

    # Store in cache so future requests for the same lesson are free
    store_lesson_cache(
        cache_key=cache_key,
        lesson_content=lesson,
        source_type=source_type,
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        mode=mode,
        step_title=step_title,
        teacher_persona=teacher_persona or "",
    )

    return {
        "lesson": lesson,
        "source_type": source_type,
        "sources": rag_results,
        "textbook_visuals": textbook_visuals,
        "from_cache": False,
    }


def answer_doubt(
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    question: str,
    username: str = "unknown",
    model: str = DEFAULT_TEXT_MODEL,
    board: str = "CBSE",
):
    """
    Answer a student doubt with DKB cache-first, then RAG, then LLM.

    Flow:
    1. Search Doubt Knowledge Base (DKB) by semantic similarity.
       On hit → return cached answer instantly (zero token cost).
    2. On DKB miss → RAG + LLM generation (existing flow).
    3. Auto-store new LLM-generated answer in DKB for future reuse.
    """
    # ----------------------------------------------------------------- DKB
    try:
        from app.services.doubt_kb_service import search_doubt_kb, store_in_doubt_kb  # noqa: PLC0415
        # Strip answer-style instructions appended by buildDoubtPayload on the
        # frontend before doing the DKB embedding lookup.  The appended text
        # ("Preferred answer style: Explain this in simple language first.")
        # changes the embedding enough to drop similarity below the threshold.
        # We search with the clean raw question; the full enriched text is still
        # sent to the LLM if the DKB misses.
        raw_question_for_dkb = question.split("\n\nPreferred answer style:", 1)[0].strip()
        dkb_hit = search_doubt_kb(
            question=raw_question_for_dkb,
            grade=grade,
            # Treat empty string as None so the DKB subject filter is bypassed
            # (user left "Open subject" in the doubt page → search all subjects)
            subject=subject if (subject or "").strip() else None,
            chapter=chapter if (chapter or "").strip() else None,
            mode=mode,
            board=board,
        )
        if dkb_hit:
            save_mentor_memory(
                username=username,
                grade=grade,
                mode=mode,
                subject=subject,
                chapter=chapter,
                question=question,
                answer=dkb_hit["answer"],
            )
            return {
                "answer": dkb_hit["answer"],
                "source_type": "LLM",   # shown to student as normal AI answer
                "sources": [],
                "textbook_visuals": [],
                "mentor_suggestions": [
                    "Give a practice question",
                    "Explain step-by-step",
                    "Give a real-life example",
                ],
            }
    except Exception:
        pass  # DKB unavailable — fall through to LLM
    # -------------------------------------------------------------- end DKB

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
        board=board,
        grade=grade,
        subject=subject if subject else None,
        chapter=chapter if chapter else None,
        match_count=15,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            board=board,
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

	Explain clearly for a {grade} student.

Use uploaded textbook/RAG context when available.
If RAG context is available, align the answer with it.
If RAG context is not available, use standard CBSE/SOF knowledge.

Do not use markdown tables.
Use bullet points instead.

{DIAGRAM_HINT}

For formulas:
- Use inline LaTeX like $F = m \times a$
- Use inline LaTeX like $\\frac{{p}}{{q}}$ and $q \\neq 0$
- If an inline formula starts with a number, write it like $ 10 - 2 \times 4 = 2 $
- Use display LaTeX like:

$$
F = m \times a
$$

- Never write formulas inside normal parentheses like:
( F = m \times a )
- Never write LaTeX commands inside normal parentheses like:
(\\frac{{p}}{{q}}) or (q \\neq 0)
"""

    answer = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="doubt",
        model=model,
    )

    answer = remove_mermaid_blocks(answer)
    textbook_visuals = find_visual_assets_for_question(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        question=question,
    )
    

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


    # Auto-store the new LLM answer in DKB so future identical/similar questions
    # are served instantly without another LLM call.
    try:
        from app.services.doubt_kb_service import store_in_doubt_kb  # noqa: PLC0415
        store_in_doubt_kb(
            question=question,
            answer=answer,
            grade=grade,
            subject=subject,
            chapter=chapter if chapter else None,
            mode=mode,
            board=board,
            source="llm",
        )
    except Exception:
        pass  # DKB store failure must never break doubt delivery

    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
        "textbook_visuals": textbook_visuals,
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
    board: str = "CBSE",
):
    """
    Answer a follow-up about a generated lesson step.

    DKB-first: checks the Doubt Knowledge Base for a pre-answered match before
    calling the LLM.  On a DKB hit the answer is returned instantly at zero
    token cost.  On a miss the existing RAG + LLM flow runs as normal.

    The lesson text and selected chapter are both included so the response stays
    tied to the current screen instead of drifting into a generic explanation.
    """
    # ----------------------------------------------------------------- DKB
    try:
        from app.services.doubt_kb_service import search_doubt_kb, store_in_doubt_kb  # noqa: PLC0415
        dkb_hit = search_doubt_kb(
            question=question,
            grade=grade,
            subject=subject,
            chapter=chapter if chapter else None,
            mode=mode,
            board=board,
        )
        if dkb_hit:
            save_mentor_memory(
                username=username,
                grade=grade,
                mode=mode,
                subject=subject,
                chapter=chapter,
                question=question,
                answer=dkb_hit["answer"],
            )
            return {
                "answer": dkb_hit["answer"],
                "source_type": "LLM",   # shown to student as normal AI answer
                "sources": [],
                "textbook_visuals": [],
            }
    except Exception:
        pass  # DKB unavailable — fall through to LLM
    # -------------------------------------------------------------- end DKB

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
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=10,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            board=board,
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
	You are helping a {grade} student understand a lesson.

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
	- Explain like a friendly tutor using age-appropriate language for {grade}.
- Use bullets if helpful.
- Do not repeat the full lesson.
- If the answer benefits from a visual, include one visual-json block.
- End with one small check question.

{DIAGRAM_HINT}

"""

    answer = ask_llm(
        TUTOR_SYSTEM,
        prompt,
        username=username,
        feature="lesson_followup",
    )

    answer = remove_mermaid_blocks(answer)
    textbook_visuals = find_visual_assets_for_question(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        question=question,
    )

    return {
        "answer": answer,
        "source_type": source_type,
        "sources": rag_results,
        "textbook_visuals": textbook_visuals,
    }
