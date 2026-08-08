"""
Lesson Plan Bank Service
=========================
Pre-authored, duration-agnostic lesson-plan handouts stored as static JSON
files on disk — one per (grade, subject, chapter), mirroring the
chapter_manifests/ convention in chapter_doc_service.py (same slugify rule,
same grade/subject/chapter folder layout).

Design principles:
- get_lesson_plan() returns None when no handout has been authored yet for
  a chapter, so the caller reports a friendly "still being prepared" message
  — there is no live LLM fallback.
- Populate via: docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md +
  backend/scripts/prepare_gpt55_lesson_plan_prompts.py +
  backend/scripts/ingest_gpt55_lesson_plan_output.py
"""

import json
import re
from pathlib import Path

from app.services.mock_test_service import normalize_chapter_core, strip_source_display_prefix

_BANK_ROOT = Path(__file__).resolve().parents[1] / "data" / "lesson_plan_bank"


def _slugify(text: str) -> str:
    """Same slugify rule as chapter_doc_service._slugify_for_manifest()."""
    text = re.sub(r"[^\w\s-]", "", (text or "").lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def _handout_path(grade: str, subject: str, chapter: str) -> Path:
    return _BANK_ROOT / _slugify(grade) / _slugify(subject) / f"{_slugify(chapter)}.json"


def _read_handout(path: Path) -> str | None:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        markdown = data.get("lesson_plan_markdown")
        return markdown if markdown and markdown.strip() else None
    except Exception:
        return None


def get_lesson_plan(grade: str, subject: str, chapter: str) -> str | None:
    """
    Look up the pre-authored lesson-plan handout for a chapter.

    Tries, in order: (1) the chapter string as given, (2) with the
    book-source display prefix stripped, (3) with every known prefix style
    stripped down to a bare "core" title, (4) a substring scan over every
    handout filename in the subject's folder for one containing that core
    title — the same fallback tiers question_bank_service.py's chapter
    matching uses, adapted for file lookups instead of DB queries.

    Returns None if no handout has been authored for this chapter yet.
    """
    markdown = _read_handout(_handout_path(grade, subject, chapter))
    if markdown:
        return markdown

    stripped = strip_source_display_prefix(chapter)
    if stripped and stripped != chapter:
        markdown = _read_handout(_handout_path(grade, subject, stripped))
        if markdown:
            return markdown

    core = normalize_chapter_core(chapter)
    if core and core not in (chapter, stripped):
        markdown = _read_handout(_handout_path(grade, subject, core))
        if markdown:
            return markdown

    if not core:
        return None

    subject_dir = _BANK_ROOT / _slugify(grade) / _slugify(subject)
    try:
        if not subject_dir.is_dir():
            return None
        core_slug = _slugify(core)
        for candidate in subject_dir.glob("*.json"):
            if core_slug and core_slug in candidate.stem:
                markdown = _read_handout(candidate)
                if markdown:
                    return markdown
    except Exception:
        return None

    return None
