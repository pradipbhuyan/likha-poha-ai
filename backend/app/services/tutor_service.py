
import os as _os
from app.services.openai_service import DEFAULT_TEXT_MODEL, ask_llm, PREWARM_TEXT_MODEL
from app.services.rag_service import search_textbook_content, strip_chapter_number_prefix
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
- The "Quick check question" section MUST always use MCQ (4 options A/B/C/D)
  or True/False format. NEVER use open-ended descriptive questions in this
  section — students cannot type free-form answers on mobile.
  Format MCQ like this (EXACTLY — no bold, no extra lines):

  <Question text here>

  A) <option>
  B) <option>
  C) <option>
  D) <option>

  Answer: <correct option key, e.g. B>

  Explanation: <one or two sentences explaining why the answer is correct>

  For True/False format use EXACTLY:

  <Statement here — must be answerable as True or False>

  A) True
  B) False

  Answer: <A or B>

  Explanation: <one or two sentences>

  Rules for Quick check question:
  - The question must directly test a key concept from THIS lesson step only.
    Do NOT ask about topics from other chapters or steps.
  - The question MUST be completely self-contained. A student must be able to
    answer it from the question text alone — no data table, no figure, no
    external context required.
  - NEVER write "The following data shows...", "Using the data above...",
    "Refer to the table...", or any phrase that implies a separate data source.
    If numerical data is needed, embed it directly in the question sentence.
    WRONG: "The following data shows speed values: 10, 20, 30. Calculate..."
    RIGHT: "A car travels at 20 m/s for 5 seconds. Calculate the distance."
  - NEVER ask the student to "identify each", "classify the following list",
    or "state whether each of the following is X or Y" for a list of items.
    Ask about ONE specific concept, value, or scenario only.
  - All 4 MCQ options must be plausible (avoid obviously wrong options).
  - The correct answer MUST appear as one of the labelled options.
  - The Answer line MUST be exactly: "Answer: X" where X is A, B, C, or D.
  - Explanation must be present and explain why the answer is correct.
  - For Maths/Science, prefer MCQ. For True/False, the statement must be clear.
- The "Worked example" section MUST begin with "Question: <data> <task instruction>"
  where the task instruction tells the student what to DO (e.g.
  "Find the value of x.", "Calculate the area.", "Explain why this happens.").
  This is the problem being solved, NOT a conversational prompt.
  NEVER use "Draw a pictograph", "Draw a graph", "Sketch a diagram", or any
  task that requires the student to produce visual or physical output.
- Do not add a "Quick check question:" line inside any other section or after a visual.
- Sections other than "Worked example" and "Quick check question" must end with a
  statement or instruction, not a question.
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

MATH RULES — CRITICAL, FOLLOW EXACTLY:
- Every mathematical expression, formula, variable, or number-with-operator MUST be wrapped in $...$.
- Inline formulas MUST use single dollar delimiters: $x^2 + 4x + 4$
- Display formulas MUST use double dollar delimiters on their own line:

$$
(a + b)^2 = a^2 + 2ab + b^2
$$

- NEVER write any math expression inside normal parentheses ().
  These are WRONG and will break rendering:
  Bad: (x^2 + 4x + 4), (a + b)^2, (x - 2)(x + 2), (\\frac{p}{q})
  Bad: writing a superscript like x^2 x 2 — that is meaningless
  Bad: using $$ inside () like (x - 2$$x + 2) — NEVER do this
  Good: $x^2 + 4x + 4$, $(a + b)^2$, $(x - 2)(x + 2)$

- To write factored expressions like (x-2)(x+3), ALWAYS use:
  $(x - 2)(x + 3)$ — NOT (x - 2)(x + 3) in plain text

- To write a fraction, ALWAYS use LaTeX:
  Good: $\\frac{x^2 - 4}{x^2 - 9}$
  Never: \\frac{x^2 - 4}{x^2 - 9} or (\\frac{x^2-4}{x^2-9})

- NEVER repeat a variable twice like "x^2 x 2" — write it as $x^2$ only.

- If an inline formula starts with a number, add a space after the opening dollar:
  Bad: $10 - 2 \\times 4 = 2$
  Good: $ 10 - 2 \\times 4 = 2 $

- LaTeX examples for common algebra patterns:
  $(a + b)^2 = a^2 + 2ab + b^2$
  $(a - b)^2 = a^2 - 2ab + b^2$
  $(a + b)(a - b) = a^2 - b^2$
  $\\frac{x^2 - 4}{x - 2} = x + 2$
  $(x + 2)(x - 3)$
  $x^2 + 5x + 6$
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

# ── Feature flag — set ENABLE_TYPED_LESSONS=false in Railway to roll back ────
_TYPED_LESSONS_ENABLED = _os.getenv("ENABLE_TYPED_LESSONS", "true").lower() != "false"


# ── Chapter-type detection ────────────────────────────────────────────────────
_PROSE_KEYWORDS = {
    "letter", "story", "tale", "prose", "novel", "chapter", "lesson",
    "portrait", "diary", "journey", "adventure", "tiger", "glimpse",
    "memorable", "road", "fun", "tusker", "madam", "virtually true",
    "christmas", "thief", "sermon", "hack driver", "bholi", "book",
    "footprints", "flamingo", "honeydew", "beehive", "first flight",
    "vistas", "hornbill", "kaleidoscope", "the last lesson", "a letter",
    "nelson mandela", "two stories", "from the diary", "glimpses of india",
    "mijbil the otter", "madam rides the bus", "the hundred dresses",
}
_POEM_KEYWORDS = {
    "poem", "poetry", "sonnet", "ballad", "ode", "rhyme", "verse",
    "dust of snow", "fire and ice", "a tiger in the zoo", "how to tell",
    "the ball poem", "amanda", "animals", "the trees", "fog",
    "the tale of custard", "for anne gregory", "god made the country",
    # ── Grade 5 Santoor English poems (confirmed from RAG content) ──────────
    "papa's spectacles", "spectacles",  # Chapter 1
    "the rainbow",                       # Chapter 3
    "the frog",                          # Chapter 5
    "vocation",                          # Chapter 9
}
_GRAMMAR_KEYWORDS = {
    "grammar", "tense", "voice", "reported speech", "narration",
    "active", "passive", "clause", "conjunction", "preposition",
    "article", "adjective", "adverb", "punctuation", "sentence",
    "determiners", "modals", "subject-verb", "parts of speech",
}

def _extract_step_number(step_title: str, grade: str = "") -> int:
    """
    Map a lesson step_title to the correct PROSE_LITERATURE_SYSTEM / POEM_SYSTEM
    section number (1-5), taking the grade's step count into account.

    Each grade band has a different number of steps; mapping must be proportional
    so that every grade distributes evenly across the 5-section prose/poem system.

    Grade 1-3  (3 steps): Introduction → 1, Let's Practice → 3, Quick Review → 5
    Grade 4-5  (3 steps): What We Learn → 1, Worked Examples → 2, Recap → 5
    Grade 6-8  (4 steps): Concept intro → 1, Core explanation → 2,
                           Worked examples → 3, Revision and recap → 5
    Grade 9+   (5-6 steps): keyword-based fallback — works for all named steps
    """
    lower = (step_title or "").lower().strip()
    grade_lower = (grade or "").lower().strip()

    # ── Grade 4/5: 3 steps → map proportionally across 5-section prose system ──
    if grade_lower in ("grade 4", "grade 5"):
        _G45 = {
            "what we learn": 1,       # Overview / Context
            "worked examples": 2,     # Paragraph/Section Breakdown (story walkthrough)
            "recap": 5,               # CBSE-style Questions and Revision
        }
        if lower in _G45:
            return _G45[lower]
        return 1  # fallback

    # ── Grade 1/2/3: 3 steps → same proportional mapping ─────────────────────
    if grade_lower in ("grade 1", "grade 2", "grade 3"):
        _G13 = {
            "introduction": 1,        # Overview
            "let's practice": 3,      # Characters & Theme (simple identification)
            "quick review": 5,        # Summary / Q&A
        }
        if lower in _G13:
            return _G13[lower]
        return 1

    # ── Grade 6/7/8: 4 steps → skip step 4 (Literary Devices) ───────────────
    if grade_lower in ("grade 6", "grade 7", "grade 8"):
        _G68 = {
            "concept introduction": 1,
            "core explanation": 2,
            "worked examples": 3,
            "revision and recap": 5,
        }
        if lower in _G68:
            return _G68[lower]

    # ── Grade 9+ / fallback: keyword-based mapping ───────────────────────────
    import re as _step_re  # noqa: PLC0415
    m = _step_re.search(r'\b([1-5])\b', str(step_title or ''))
    if m:
        return int(m.group(1))
    if any(k in lower for k in ['overview', 'introduction', 'intro', 'concept', 'context', 'background', 'what we learn']):
        return 1
    if any(k in lower for k in ['paragraph', 'paraphrase', 'breakdown', 'stanza', 'section', 'explanation', 'core']):
        return 2
    if any(k in lower for k in ['character', 'theme', 'message', 'moral', 'analysis', 'example', 'examples', 'worked']):
        return 3
    if any(k in lower for k in ['device', 'literary', 'poetic', 'style', 'rhyme', 'vocabulary']):
        return 4
    if any(k in lower for k in ['question', 'answer', 'cbse', 'exam', 'practice', 'summary', 'recap', 'review', 'revision']):
        return 5
    return 1


def detect_chapter_type(subject: str, chapter: str) -> str:
    """
    Classify the chapter as 'prose', 'poem', 'grammar', or 'default'.

    Used to route lesson generation to the correct subject-type prompt.
    Returns 'default' for Science, Maths, SOF, and any non-English chapter.

    Rollback: set ENABLE_TYPED_LESSONS=false — this function's result is ignored.
    """
    if not subject or "english" not in subject.lower():
        return "default"

    chapter_lower = (chapter or "").lower()
    subject_lower = subject.lower()

    # Grammar subjects/chapters
    if any(kw in chapter_lower for kw in _GRAMMAR_KEYWORDS):
        return "grammar"
    if "grammar" in subject_lower:
        return "grammar"

    # Poem detection
    if any(kw in chapter_lower for kw in _POEM_KEYWORDS):
        return "poem"

    # Prose detection
    if any(kw in chapter_lower for kw in _PROSE_KEYWORDS):
        return "prose"

    # Default for English chapters we can't classify (treat as prose)
    return "prose"


# ── TTS pre-cleanup filter ────────────────────────────────────────────────────
import re as _re_tts

def clean_for_tts(text: str) -> str:
    """
    Strip markdown symbols the TTS engine would read aloud literally.

    Applied BEFORE sending lesson text to audio generation.
    The prompt fix (TUTOR_SYSTEM_TTS) handles 90% of cases at the source;
    this filter is the safety net for whatever slips through.

    Rollback: this function is always safe to call — worst case it returns
    the original text unchanged.
    """
    if not text:
        return text
    t = text
    # Underscores used for fill-in-the-blank → "blank"
    t = _re_tts.sub(r'_{2,}', 'blank', t)
    # Asterisks (bold/italic markers)
    t = _re_tts.sub(r'\*+', '', t)
    # Markdown headings (#, ##, ###) → just the text
    t = _re_tts.sub(r'^#{1,6}\s+', '', t, flags=_re_tts.MULTILINE)
    # Backticks
    t = t.replace('`', '')
    # LaTeX math delimiters (read the content, not the delimiters)
    t = _re_tts.sub(r'\$\$(.+?)\$\$', r'\1', t, flags=_re_tts.DOTALL)
    t = _re_tts.sub(r'\$(.+?)\$', r'\1', t)
    # e.g. → "for example"
    t = _re_tts.sub(r'\be\.g\.\b', 'for example', t, flags=_re_tts.IGNORECASE)
    # i.e. → "that is"
    t = _re_tts.sub(r'\bi\.e\.\b', 'that is', t, flags=_re_tts.IGNORECASE)
    # % → "percent"
    t = t.replace('%', ' percent')
    # = → "equals" only in isolated positions
    t = _re_tts.sub(r'\s=\s', ' equals ', t)
    # Remove leftover markdown link syntax
    t = _re_tts.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    return t


# ── Prose / Literature system prompt ─────────────────────────────────────────
PROSE_LITERATURE_SYSTEM = """
You are an expert CBSE English Literature teacher for Class 6 to Class 10 students.

You are teaching a PROSE chapter (story, letter, travelogue, biography excerpt, or play).
Your job is NOT to teach grammar — you are teaching the literary content of this specific chapter.

STEP-BY-STEP STRUCTURE — follow exactly based on which step is requested:

STEP 1 (Overview / Context):
- Title, author, and type of prose (story / letter / travelogue / etc.)
- Brief context: when and where is the story set, what is the situation
- First impression and tone of the chapter
- What students should look for as they read

STEP 2 (Paragraph / Section Breakdown with Paraphrasing):
- Go through the chapter passage by passage (or paragraph by paragraph)
- Paraphrase each section in simple modern English
- Highlight key events, turning points, or important lines from the text
- Explain the significance of each section for the story's progression

STEP 3 (Characters and Theme — CRITICAL FOR CBSE EXAMS):
- Detailed character analysis: personality, motivation, role, development
- Central theme(s) of the chapter: state them clearly and explain with textual evidence
- Sub-themes and moral lessons
- How characters embody or contrast the theme
- This section earns the most marks in CBSE English exams

STEP 4 (Literary Devices and Language):
- Identify literary devices used: metaphor, simile, personification, alliteration, irony, symbolism etc.
- Quote the exact line from the text and name the device
- Explain what effect the device creates on the reader
- Vocabulary: important words with meaning and usage in context

STEP 5 (CBSE-style Questions and Answers):
- 2 short-answer questions (2-3 marks each) with model answers
- 1 long-answer / value-based question (5 marks) with model answer
- 1 extract-based question with line reference and explanation
- All questions must be in CBSE exam format

RULES:
- Always use the uploaded RAG textbook content as the primary source.
- Never teach grammar concepts inside a Prose lesson step.
- Write for TTS narration: no underscores, no markdown symbols, no asterisks.
  Write "blank" instead of underscores. Write headings as plain text.
- Use simple, clear English appropriate for the grade.
- Every answer must be directly supported by the text.
"""

POEM_SYSTEM = """
You are an expert CBSE English Literature teacher for Class 6 to Class 10 students.

You are teaching a POEM.

STEP-BY-STEP STRUCTURE:

STEP 1 (Introduction):
- Poet's name, type of poem, central idea in one paragraph
- Tone, mood, and setting of the poem

STEP 2 (Stanza-by-Stanza Explanation):
- Explain each stanza in simple prose
- Paraphrase the poet's meaning line by line where needed
- Highlight important images and feelings expressed

STEP 3 (Theme and Message):
- Central theme stated clearly
- Sub-themes and the poet's message
- How the poem relates to real life or human values

STEP 4 (Poetic Devices and Rhyme Scheme):
- Identify devices: metaphor, simile, personification, alliteration, assonance, imagery, symbolism
- Quote the exact line and name the device
- Explain the effect on the reader
- Rhyme scheme notation (ABAB / AABB etc.)

STEP 5 (CBSE-style Questions and Answers):
- 2 reference-to-context (extract) questions with model answers
- 1 appreciation / value-based question
- 1 short note on the poem's central idea
- All in CBSE exam format

RULES:
- Never teach grammar inside a Poem lesson.
- Write for TTS narration: no underscores, no markdown symbols, no asterisks.
- Use the uploaded RAG textbook content as the primary source.
"""

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
    cache_only: bool = False,
    force_refresh: bool = False,
):
    """
    Generate one focused lesson step using RAG when uploaded context exists.

    Cache-first: checks lesson_cache before calling the LLM. On cache hit the
    lesson is returned instantly with zero token cost. On cache miss the LLM
    generates as normal and the result is stored for future requests.

    Pass force_refresh=True to bypass the cache entirely and regenerate fresh.
    The new content overwrites the existing cache entry so future requests are
    served the corrected version (used by the "Refresh lesson" button).

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
    # force_refresh=True skips ALL cache lookups so the lesson regenerates
    # from RAG + LLM and overwrites the existing (potentially stale) cache entry.
    cached = None if force_refresh else get_cached_lesson(cache_key, grade=grade)

    # Fallback 1 (PERSONA): prewarm stores lessons with teacher_persona="".
    # Fallback 1 (PERSONA): prewarm stores lessons with teacher_persona="".
    # Try the empty-persona key when the request has a non-empty persona.
    # Skip all fallbacks when force_refresh is active.
    if not cached and not force_refresh and (teacher_persona or "").strip():
        fallback_key = make_lesson_cache_key(
            board=board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=mode,
            step_title=step_title,
            teacher_persona="",
        )
        cached = get_cached_lesson(fallback_key, grade=grade)

    # Fallback 2 (SOURCE-PREFIX): the lesson cache may have been built before
    # multi-book display prefixes were introduced (e.g. "Text Book - Chapter 7").
    # Try the same lookups with the source prefix stripped from the chapter name.
    stripped_chapter = _strip_chapter_source_prefix(chapter)
    if not cached and not force_refresh and stripped_chapter and stripped_chapter != chapter:
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
        cached = get_cached_lesson(stripped_key, grade=grade)

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
            cached = get_cached_lesson(stripped_empty_key, grade=grade)

    # Fallback 3 (TEXT SEARCH): the cache key is a hash so prefix mismatches
    # between prewarm time and request time produce different hashes even for
    # the same chapter.  As a last resort, query the lesson_cache table by the
    # core chapter text (ilike) so 'Economics - Chapter 1: Development' and
    # 'Text Book - Chapter 1: Development' both resolve to the same row.
    if not cached and not force_refresh:
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

    # Free-trial offer users are limited to pre-warmed content only.
    # If the lesson is not in the cache, do NOT call the LLM — return a
    # clear message so the user knows the content will be available soon.
    if cache_only:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(
            status_code=403,
            detail=(
                "🔒 This lesson step is being prepared and will be available shortly. "
                "All other chapters are available now. "
                "To generate any lesson on demand, upgrade to a paid plan."
            ),
        )

    rag_query = f"""
    {grade} {subject} {chapter}
    Current lesson step: {step_title}
    Find textbook explanation, definitions, examples, formulas, important points.
    """

    # ── Hybrid match_count to reduce Supabase egress without quality loss ──
    # Language/literature subjects need more context for long prose passages.
    # Hard sciences at Grade 11-12 benefit from extra chunks for long chapters.
    # All others (Maths/Science Gr 5-10) are well-served by 8 focused chunks.
    _subj_lower = (subject or "").lower()
    _is_language = any(s in _subj_lower for s in ("english", "hindi", "sanskrit"))
    _is_long_subject = any(s in _subj_lower for s in ("physics", "chemistry", "mathematics", "biology"))
    _is_grade_1112 = grade in ("Grade 11", "Grade 12")
    if _is_language:
        _lesson_match_count = 12  # prose chapters need more context
    elif _is_long_subject and _is_grade_1112:
        _lesson_match_count = 10  # long Gr 11-12 chapters
    else:
        _lesson_match_count = 8   # Gr 5-10 Science/Maths + all others

    rag_results = search_textbook_content(
        query=rag_query,
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=_lesson_match_count,
    )

    # Fallback 1: no chapter filter (broadens to all subject content)
    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            board=board,
            grade=grade,
            subject=subject,
            chapter=None,
            match_count=_lesson_match_count,
        )

    # Fallback 2: strip numeric chapter prefix (e.g. "1. Papa's Spectacles"
    # → "Papa's Spectacles") to handle uploads stored without the number prefix.
    if not rag_results and chapter:
        _stripped_num = strip_chapter_number_prefix(chapter)
        if _stripped_num and _stripped_num != chapter:
            rag_results = search_textbook_content(
                query=rag_query,
                board=board,
                grade=grade,
                subject=subject,
                chapter=_stripped_num,
                match_count=_lesson_match_count,
            )

    source_type = "RAG" if rag_results else "LLM"

    # ── Anti-hallucination guard for language & literature subjects ───────────
    # English, Hindi, Sanskrit and Social Science chapters contain specific
    # story/passage text that the LLM does NOT know accurately.
    # If RAG returns 0 results for these subjects, do NOT let the LLM generate
    # an answer from parametric memory — it will fabricate story content.
    # Instead, return a clear "content not available" response so the student
    # is not given wrong information.
    #
    # Example of harm avoided: for "Grade 5 English / Papa's Spectacles / Worked Examples"
    # with no RAG context, the LLM invented a completely wrong story with
    # a dustbin, father's anger, and hugging — none of which exists in the book.
    _STORY_DEPENDENT_SUBJECTS = {
        "english", "hindi", "sanskrit",
        "social science", "social studies", "history", "geography",
        "economics", "civics", "political science",
    }
    _subject_lower = (subject or "").lower()
    if not rag_results and any(s in _subject_lower for s in _STORY_DEPENDENT_SUBJECTS):
        _no_content_msg = (
            f"📚 **Textbook content not yet available**\n\n"
            f"The lesson content for **{chapter}** ({subject}, {grade}) has not been "
            f"uploaded to our knowledge base yet.\n\n"
            f"This lesson requires the actual NCERT textbook passage to answer accurately. "
            f"Without it, the AI cannot give you a reliable answer and will not guess.\n\n"
            f"**What you can do:**\n"
            f"- Read the relevant passage/story in your NCERT textbook\n"
            f"- Ask your teacher for help with this chapter\n"
            f"- Come back soon — we are regularly adding more content\n\n"
            f"_We apologise for the inconvenience. Accuracy is more important than speed._"
        )
        # Do NOT cache NO_CONTENT responses — once the admin uploads RAG content,
        # the next request should try fresh and find the uploaded material.
        # Caching NO_CONTENT would permanently block RAG from being picked up.
        return {
            "lesson": _no_content_msg,
            "source_type": "NO_CONTENT",
            "sources": [],
            "textbook_visuals": [],
            "practice_questions": [],
            "from_cache": False,
        }
    # ── End anti-hallucination guard ─────────────────────────────────────────

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
- If approved visual aids are listed, weave them logically into the lesson
  with a short instruction such as "Look at the visual aid below..." only
  when the visual supports the current idea. Never use the phrase "textbook visual".
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
- Start the worked example with "Question: <complete problem statement>".
  The question must be COMPLETE and self-contained — include both the data AND
  the task instruction (e.g. "Find the area of a rectangle with length 8 cm and
  breadth 5 cm." or "Calculate the speed of a car that travels 120 km in 2 hours.").
  A student must be able to attempt it with no other context.
- After the question, show the solution step-by-step starting with "Step 1:".
- Explain the reasoning behind each step.
- Explain why each formula or method is used.
- Include conceptual interpretation of the final answer.

WORKED EXAMPLE RESTRICTIONS — PLATFORM CONSTRAINTS:
- NEVER ask the student to draw, sketch, construct a diagram, draw a graph,
  draw a pictograph, make a table, or produce any visual/physical output.
  Students CANNOT draw or submit visual work on this platform.
- Worked examples must be answerable in TEXT only — calculations, explanations,
  short written answers, or multiple-choice style.
- The worked example MUST be relevant to the current subject. For Science:
  use experiments, observations, calculations, or reasoning questions.
  Do NOT use Maths data handling questions (pictographs, bar charts) inside
  a Science lesson — those belong only in Maths.
- For Grade 9 Science "Exploration" chapter: use examples about scientific
  method, hypotheses, observations, measurements, or simple calculations —
  NOT data visualization tasks.

Before explaining, identify the textbook coverage being used:
- Key concepts covered
- Important examples or activities — list these in ascending order (Example 1.1, 1.2, 1.3 — never reverse order)
- Important exam/reasoning points

Then teach the lesson in depth.

End with a short next-step instruction, not a question. The only student-facing
question should be inside the "Quick check question" section.
"""

    # ── Select system prompt based on chapter type (Phase 1) ──────────────────
    # Rollback: set ENABLE_TYPED_LESSONS=false in Railway to revert to TUTOR_SYSTEM
    _step_num = _extract_step_number(step_title, grade)  # computed for ALL subjects now
    if _TYPED_LESSONS_ENABLED:
        _chapter_type = detect_chapter_type(subject, chapter)
        if _chapter_type == "prose":
            _system = PROSE_LITERATURE_SYSTEM
            prompt = f"You are teaching STEP {_step_num} of a Prose/Literature lesson.\n\n" + prompt
        elif _chapter_type == "poem":
            _system = POEM_SYSTEM
            prompt = f"You are teaching STEP {_step_num} of a Poem lesson.\n\n" + prompt
        else:
            _system = TUTOR_SYSTEM
    else:
        _system = TUTOR_SYSTEM

    # ── Quick Check gate: suppress for Steps 1 and 2 ─────────────────────────
    # Quick Check questions require the student to have learned the core
    # concept first.  Steps 1 and 2 are introductory; self-check only
    # appears from Step 3 onwards across ALL subject types.
    if _step_num <= 2:
        prompt += (
            "\n\nCRITICAL RULE FOR THIS STEP: "
            f"This is Step {_step_num} (an introductory step). "
            "Do NOT include a 'Quick check question' section in this lesson. "
            "Quick check questions are reserved for Step 3 and beyond. "
            "End this lesson with the Summary or a next-step instruction instead."
        )

    # ── New Words vocabulary (Step 1 only, English/Hindi subjects) ───────────
    # Vocabulary must be extracted ONLY from the textbook/RAG context provided
    # in the prompt — not invented by the LLM from general knowledge.
    _VOCAB_SUBJECTS = {"english", "hindi"}
    _is_vocab_subject = any(s in (subject or "").lower() for s in _VOCAB_SUBJECTS)
    if _step_num == 1 and _is_vocab_subject and textbook_context:
        prompt += (
            "\n\nMANDATORY NEW WORDS SECTION FOR STEP 1 (LANGUAGE/LITERATURE CHAPTERS):\n"
            "Place this section JUST BEFORE the Summary section (at the end of the lesson, "
            "after the main explanation but before the closing Summary).\n\n"
            "Use this exact heading:\n"
            "## New Words\n"
            "### Vocabulary from the chapter\n\n"
            "Rules for the New Words section:\n"
            "1. EXTRACT 5-8 WORDS ONLY from the TEXTBOOK CONTEXT provided above. "
            "   Do NOT use words from your general knowledge — only words that APPEAR "
            "   in the uploaded textbook passage.\n"
            "2. For each word, provide: the WORD in bold, then ' — ' then the meaning "
            "   AS USED IN THIS SPECIFIC TEXT (not a dictionary definition).\n"
            "   Example format:\n"
            "   **spectacles** — another word for glasses that help you see clearly\n"
            "   **misplaced** — lost or put in the wrong place by mistake\n"
            "3. Choose words that are unusual, subject-specific, or likely to be new "
            "   to students at this grade level.\n"
            "4. NEVER invent words or meanings. Every word MUST appear in the textbook "
            "   context above. If the textbook context has fewer than 5 new words, "
            "   include only those that appear.\n"
            "5. The New Words section goes ABOVE the Summary — not at the beginning. "
            "   Lesson structure: [Introduction] → [Main explanation] → [New Words] → [Summary]"
        )

    lesson = ask_llm(
        _system,
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

    # Doubts are narrow/specific — 6 targeted chunks is always sufficient.
    # This is the biggest egress saving: doubts are frequent and short-context.
    rag_results = search_textbook_content(
        query=rag_query,
        board=board,
        grade=grade,
        subject=subject if subject else None,
        chapter=chapter if chapter else None,
        match_count=6,
    )

    if not rag_results:
        rag_results = search_textbook_content(
            query=rag_query,
            board=board,
            grade=grade,
            subject=None,
            chapter=None,
            match_count=6,
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

MATH RULES — CRITICAL, FOLLOW EXACTLY:
- Every mathematical expression MUST be wrapped in $...$ (inline) or $$...$$ (display).
- NEVER write math inside plain parentheses ().
- Bad: (x^2 + 4x + 4), (a + b)^2, (x - 2)(x + 2), (\\frac{{p}}{{q}})
- Good: $x^2 + 4x + 4$, $(a + b)^2$, $(x - 2)(x + 2)$, $\\frac{{p}}{{q}}$
- NEVER use $$ inside () like (x - 2$$x + 2) — that is broken syntax.
- NEVER repeat a variable like "x^2 x 2" — write $x^2$ only.
- Factored products: $(x - 2)(x + 3)$ — always inside $ not plain text.
- Fractions: $\\frac{{x^2 - 4}}{{x - 2}}$ — always LaTeX.
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
    # Skip off-topic / current-affairs questions — they contain stale data and
    # must never be cached.
    try:
        from app.services.doubt_kb_service import store_in_doubt_kb  # noqa: PLC0415
        from app.services.academic_guardrail_service import is_non_academic_question  # noqa: PLC0415
        if not is_non_academic_question(question):
            # Also log to unanswered_questions so admin can review and improve DKB quality
            try:
                from app.services.auth_service import admin_client as _sb_log  # noqa: PLC0415
                _sb_log.table("unanswered_questions").insert({
                    "question": question[:500],
                    "source": "doubt",
                    "grade": grade,
                    "subject": subject,
                    "chapter": chapter if chapter else None,
                    "mode": mode,
                    "username": username,
                    "status": "pending",
                }).execute()
            except Exception:
                pass  # Never block doubt delivery
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

    prompt = f"""Grade: {grade} | Subject: {subject} | Chapter: {chapter} | Step: {step_title}

Student question: {question}

Relevant textbook context:
{textbook_context if textbook_context else "Use the lesson content and your knowledge of the NCERT curriculum."}

Current lesson content (for context):
{lesson[:1200] if lesson else "Not provided."}

RULES:
- Answer the student's question DIRECTLY and SPECIFICALLY.
- Do NOT generate a full lesson structure (no "What you will learn", no "Simple explanation" headings).
- If the question asks to "identify", "list", "find", or "give examples" — provide exactly that with numbered or bullet points.
- If the question asks "why" or "how" — give a clear 3-5 sentence explanation.
- Keep the answer focused and concise — match the length to the question's complexity.
- Use NCERT textbook content and examples from this chapter where possible.
- End with one short follow-up question only if it adds value.
"""

    answer = ask_llm(
        "You are a direct and helpful CBSE tutor. Answer the student's specific question concisely using NCERT content. Do NOT generate lesson structure headings. Give the exact answer asked for.",
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
