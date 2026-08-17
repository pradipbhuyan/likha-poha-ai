"""
Exemplar Research Bank Service
================================
Pre-authored NCERT Exemplar topic explanations stored as static JSON files
on disk — one per (grade, subject, topic), mirroring lesson_plan_bank_service.py
(same slugify rule, same grade/subject folder layout). Keyed by TOPIC rather
than chapter because a handful of topic cards share a chapter (e.g. Grade 8
Maths "Squares and Square Roots" / "Cubes and Cube Roots" both live under
chapter "Square-Square Root and Cube-Cube Root") and each card gets its own
authored content — see docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §4.

Design principles:
- get_exemplar_explanation() returns None when no explanation has been
  authored yet for a topic, so the caller reports a friendly "still being
  prepared" message — there is no live LLM fallback (Exemplar Research used
  to call /api/doubt/answer live; that path is being retired in favour of
  this pre-authored bank).
- Populate via: backend/scripts/prepare_gpt55_exemplar_explanation_prompts.py
  + backend/scripts/ingest_gpt55_exemplar_research_output.py
"""

from pathlib import Path

import json

from app.services.lesson_plan_bank_service import _slugify

_BANK_ROOT = Path(__file__).resolve().parents[1] / "data" / "exemplar_research_bank"


def _explanation_path(grade: str, subject: str, topic: str) -> Path:
    return _BANK_ROOT / _slugify(grade) / _slugify(subject) / f"{_slugify(topic)}.json"


def _read_explanation(path: Path) -> str | None:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        markdown = data.get("explanation_markdown")
        return markdown if markdown and markdown.strip() else None
    except Exception:
        return None


def get_exemplar_explanation(grade: str, subject: str, topic: str) -> str | None:
    """
    Look up the pre-authored Exemplar explanation for a topic card.

    Tries the topic string as given first, then falls back to a substring
    scan over every explanation filename in the subject's folder (in case of
    minor topic-title drift between the frontend and the authored file) —
    the same fallback shape lesson_plan_bank_service.get_lesson_plan() uses,
    minus the chapter-name-prefix tiers that don't apply to topic strings.

    Returns None if no explanation has been authored for this topic yet.
    """
    markdown = _read_explanation(_explanation_path(grade, subject, topic))
    if markdown:
        return markdown

    topic_slug = _slugify(topic)
    if not topic_slug:
        return None

    subject_dir = _BANK_ROOT / _slugify(grade) / _slugify(subject)
    try:
        if not subject_dir.is_dir():
            return None
        for candidate in subject_dir.glob("*.json"):
            if topic_slug in candidate.stem or candidate.stem in topic_slug:
                markdown = _read_explanation(candidate)
                if markdown:
                    return markdown
    except Exception:
        return None

    return None


def get_available_topics(grade: str, subject: str, topics: list[str]) -> dict[str, bool]:
    """
    Report which of the given topic cards have authored content.

    Lets the grid mark the ones that will come back empty, instead of a student
    discovering it a click at a time. 168 topic cards ship in the UI against 132
    authored explanations, and 36 of the gap can never be closed — NCERT never
    published Exemplar books for three of the fourteen sections, so those cards
    are permanently unfillable rather than merely pending.

    Deliberately answers by calling get_exemplar_explanation() rather than by a
    cheaper existence check on the filename. The answer must agree exactly with
    what happens when the card is clicked, including the substring fallback for
    topic-title drift — a faster check that disagreed would be worse than none,
    because it would mark good cards dead or dead cards good.
    """
    return {
        topic: get_exemplar_explanation(grade, subject, topic) is not None
        for topic in topics
    }
