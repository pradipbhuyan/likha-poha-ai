"""
Lesson Plan Quality Checks
=============================================================================
Deterministic, rule-based quality-control pass for authored lesson-plan
markdown, run by scripts/ingest_gpt55_lesson_plan_output.py before a GPT-5.5
authored handout is written into app/data/lesson_plan_bank/. This is the
"post-generation validation" step referenced in
docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md — the authoring prompt in
app/services/lesson_plan_pedagogy.py asks the model to follow these rules,
this module checks that it actually did.

Nothing here is grade/subject/chapter-specific; the same checks run for
every handout, using grade_band()/GRADE_BAND_TEACHER_TALK_CAP_MINUTES from
lesson_plan_pedagogy.py to adapt the teacher-talk cap by grade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.lesson_plan_pedagogy import (
    DURATION_MAX_MINUTES,
    DURATION_MIN_MINUTES,
    GRADE_BAND_TEACHER_TALK_CAP_MINUTES,
    grade_band,
)

REQUIRED_H2_HEADINGS = [
    "## Lesson Overview",
    "## Learning Objectives",
    "## Prerequisites",
    "## Materials & Resources",
    "## Lesson Plan (Step-by-Step)",
    "## Homework Assignment",
    "## Differentiation Strategies",
    "## Common Misconceptions to Address",
]

BANNED_DIFFERENTIATION_LABELS = [
    re.compile(r"\bslow learners?\b", re.IGNORECASE),
    re.compile(r"\bweak students?\b", re.IGNORECASE),
    re.compile(r"\bdull students?\b", re.IGNORECASE),
]

VAGUE_OBJECTIVE_PATTERNS = [
    re.compile(r"\bunderstand everything about\b", re.IGNORECASE),
    re.compile(r"\bbecome familiar with\b", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s*(Know|Learn)\b", re.IGNORECASE | re.MULTILINE),
]

STAGE_HEADING_RE = re.compile(r"^###\s+(.*?)\s*\(.*?(\d+)\s*minutes?\)\s*$", re.MULTILINE)
NUMBERED_LINE_RE = re.compile(r"^\s*\d+\.\s+\S", re.MULTILINE)
SKIP_CORE_CONTENT_RE = re.compile(r"\b(skip|skipping|omit|omitting|remove|removing)\b", re.IGNORECASE)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "to", "for", "with",
    "students", "student", "will", "be", "able", "this", "that", "their", "its",
    "one", "using", "use", "based", "from", "into", "about", "core", "lesson",
}


@dataclass
class QualityIssue:
    severity: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.message}"


def _section(markdown: str, heading: str) -> str:
    """Return the body text of one '## Heading' section, up to the next
    '## ' heading (or end of string). Empty string if heading is absent."""
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL
    )
    m = pattern.search(markdown)
    return m.group(1) if m else ""


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def check_lesson_plan_markdown(markdown: str, grade: str, subject: str) -> list[QualityIssue]:
    """Run the deterministic quality-control pass over one authored lesson
    plan's markdown. Returns a list of QualityIssue (possibly empty)."""
    issues: list[QualityIssue] = []
    markdown = markdown or ""

    # -- Required structure -------------------------------------------------
    for heading in REQUIRED_H2_HEADINGS:
        if not re.search(rf"^{re.escape(heading)}\s*$", markdown, re.MULTILINE):
            issues.append(QualityIssue("error", f"Missing required section heading: {heading!r}"))

    # -- Objective count & phrasing -----------------------------------------
    objectives_body = _section(markdown, "## Learning Objectives")
    objective_lines = NUMBERED_LINE_RE.findall(objectives_body)
    n_objectives = len(objective_lines)
    if n_objectives < 2:
        issues.append(QualityIssue("error", f"Only {n_objectives} core learning objective(s) found; need 2-4."))
    elif n_objectives > 4:
        issues.append(QualityIssue("error", f"{n_objectives} core learning objectives found; max is 4 (prefer depth over breadth)."))

    for pattern in VAGUE_OBJECTIVE_PATTERNS:
        if pattern.search(objectives_body):
            issues.append(QualityIssue("warning", "A learning objective uses vague phrasing (e.g. 'know', 'learn', 'understand everything about')."))
            break

    # -- Timing ---------------------------------------------------------------
    lesson_flow = _section(markdown, "## Lesson Plan (Step-by-Step)")
    stage_minutes: dict[str, int] = {}
    for name, minutes in STAGE_HEADING_RE.findall(lesson_flow):
        stage_minutes[name.strip().lower()] = int(minutes)

    total_minutes = sum(stage_minutes.values())
    if total_minutes == 0:
        issues.append(QualityIssue("error", "Could not find any '### Stage (N minutes)' headings under Lesson Plan (Step-by-Step)."))
    elif not (DURATION_MIN_MINUTES - 3 <= total_minutes <= DURATION_MAX_MINUTES + 3):
        issues.append(QualityIssue(
            "error",
            f"Stage minutes sum to {total_minutes}, outside the "
            f"{DURATION_MIN_MINUTES}-{DURATION_MAX_MINUTES} minute period.",
        ))

    direct_instruction_minutes = next(
        (m for name, m in stage_minutes.items() if "direct instruction" in name), None
    )
    band = grade_band(grade)
    talk_cap = GRADE_BAND_TEACHER_TALK_CAP_MINUTES[band]
    if direct_instruction_minutes is not None and direct_instruction_minutes > talk_cap:
        severity = "error" if band == "1-2" and direct_instruction_minutes > talk_cap + 2 else "warning"
        issues.append(QualityIssue(
            severity,
            f"Direct Instruction is {direct_instruction_minutes} min, above the "
            f"~{talk_cap} min uninterrupted-teacher-talk guideline for grade band {band}.",
        ))

    practice_minutes = sum(
        m for name, m in stage_minutes.items()
        if "guided practice" in name or "student activity" in name
    )
    if direct_instruction_minutes is not None and practice_minutes < direct_instruction_minutes:
        issues.append(QualityIssue(
            "warning",
            f"Guided Practice + Student Activity ({practice_minutes} min) is less than "
            f"Direct Instruction ({direct_instruction_minutes} min) — practice should usually get at least as much time.",
        ))

    # -- Differentiation ------------------------------------------------------
    diff_body = _section(markdown, "## Differentiation Strategies")
    for pattern in BANNED_DIFFERENTIATION_LABELS:
        if pattern.search(diff_body):
            issues.append(QualityIssue("error", f"Differentiation Strategies uses a banned label matching {pattern.pattern!r}."))

    support_match = re.search(
        r"\*\*For students needing additional support:?\*\*(.*?)(?=\n-\s*\*\*|\Z)", diff_body, re.DOTALL | re.IGNORECASE
    )
    if support_match:
        if SKIP_CORE_CONTENT_RE.search(support_match.group(1)):
            issues.append(QualityIssue(
                "warning",
                "The 'students needing additional support' bullet reads like it removes core content "
                "(contains 'skip'/'omit'/'remove') instead of scaffolding it.",
            ))
    else:
        issues.append(QualityIssue("error", "Missing 'For students needing additional support:' bullet in Differentiation Strategies."))

    if not re.search(r"\*\*For students ready for extension:?\*\*", diff_body, re.IGNORECASE):
        issues.append(QualityIssue("error", "Missing 'For students ready for extension:' bullet in Differentiation Strategies."))

    # -- Assessment alignment (heuristic) -------------------------------------
    assessment_body = _section(markdown, "## Lesson Plan (Step-by-Step)")
    closure_match = re.search(r"###\s*Assessment.*?(?=^###\s|\Z)", assessment_body, re.MULTILINE | re.DOTALL)
    closure_text = closure_match.group(0) if closure_match else ""
    if closure_text:
        objective_words = _significant_words(objectives_body)
        closure_words = _significant_words(closure_text)
        if objective_words and not (objective_words & closure_words):
            issues.append(QualityIssue(
                "warning",
                "Assessment & Closure shares no significant keywords with Learning Objectives — "
                "check it isn't assessing a side topic instead of the core lesson.",
            ))
    else:
        issues.append(QualityIssue("warning", "Could not find an 'Assessment & Closure' stage to check against the objectives."))

    # -- Misconceptions ---------------------------------------------------------
    misconceptions_body = _section(markdown, "## Common Misconceptions to Address")
    n_misconceptions = len(NUMBERED_LINE_RE.findall(misconceptions_body))
    if n_misconceptions > 4:
        issues.append(QualityIssue("warning", f"{n_misconceptions} misconceptions listed; keep it to 1-3 genuinely meaningful ones."))

    return issues


def has_errors(issues: list[QualityIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)
