"""
Lesson Plan Lecture Script
=============================================================================
Deterministically extracts a spoken teacher-lecture script from an authored
lesson_plan_bank markdown handout — no LLM call. A lesson plan is a
*planning document* (objectives, differentiation notes, timing labels,
misconceptions) written for the teacher; a lecture script is the subset of
it that would actually be said out loud while teaching. This module picks
out that subset so it can be fed to text-to-speech (see
app/services/tts_service.py's clean_text_for_tts()) without reading
teacher-only notes aloud.

Kept in sync with the lesson plan automatically, since it's derived from it
each time rather than authored separately.
"""

from __future__ import annotations

import re

# Sub-sections of "## Lesson Plan (Step-by-Step)" that are actually spoken
# to the class, in delivery order. Differentiation/Misconceptions/NCERT
# Alignment/Prerequisites/Materials are teacher-only notes and excluded.
LECTURE_SUBSECTIONS = [
    "Introduction & Hook",
    "Direct Instruction",
    "Guided Practice",
    "Student Activity",
    "Assessment & Closure",
]

_STAGE_HEADING_RE = re.compile(
    r"^###\s+(.*?)\s*\(.*?\d+\s*minutes?\)\s*$", re.MULTILINE
)


def _section(markdown: str, heading: str) -> str:
    """Return the body text of one '## Heading' section, up to the next
    '## ' heading (or end of string). Empty string if heading is absent."""
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL
    )
    m = pattern.search(markdown)
    return m.group(1) if m else ""


def _stage(lesson_flow: str, stage_name: str) -> str:
    """Return the body of one '### Stage (N minutes)' sub-section within
    the Lesson Plan (Step-by-Step) body. Empty string if absent."""
    pattern = re.compile(
        rf"^###\s+{re.escape(stage_name)}\s*\(.*?\)\s*$(.*?)(?=^###\s|^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(lesson_flow)
    return m.group(1) if m else ""


def build_lecture_script(lesson_plan_markdown: str) -> str:
    """
    Extract the spoken-to-students portion of an authored lesson plan.

    Returns a markdown string (headings + bullets intact, not yet cleaned
    for TTS) covering Introduction & Hook, Direct Instruction, Guided
    Practice, Student Activity, Assessment & Closure, and Homework
    Assignment — the parts of the plan a teacher would actually say aloud —
    with Prerequisites, Materials & Resources, Differentiation Strategies,
    Common Misconceptions, and NCERT Alignment dropped.
    """
    markdown = lesson_plan_markdown or ""
    lesson_flow = _section(markdown, "## Lesson Plan (Step-by-Step)")

    parts: list[str] = []
    for stage_name in LECTURE_SUBSECTIONS:
        body = _stage(lesson_flow, stage_name).strip()
        if body:
            parts.append(f"## {stage_name}\n{body}")

    homework = _section(markdown, "## Homework Assignment").strip()
    if homework:
        parts.append(f"## Homework Assignment\n{homework}")

    return "\n\n".join(parts).strip()
