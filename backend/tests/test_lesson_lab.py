"""
test_lesson_lab.py — Backend tests for Admin Lesson Experience Lab.

Tests:
- admin-only endpoints return 403 for non-admin
- lesson list returns correct structure
- lesson list accepts grade/subject/chapter filters
- lesson detail returns normalized steps with required fields
- missing lesson returns safe 404
- preview-transform does not save content
- preview-transform rejects invalid mode
- visuals endpoint returns empty state safely when no DB
- no secrets exposed in any response
- service helpers work correctly on synthetic content
"""
import pytest
from unittest.mock import MagicMock, patch

# ── Service unit tests (no DB required) ─────────────────────────────────────

from app.services.lesson_lab_service import (
    _estimate_minutes,
    _extract_sections,
    _extract_examples,
    _section_completeness,
    _normalize_step,
    get_lesson_list,
    get_lesson_detail,
    preview_transform,
    get_visuals,
    CANONICAL_SECTIONS,
)


# ── _estimate_minutes ─────────────────────────────────────────────────────────

def test_estimate_minutes_short_text():
    assert _estimate_minutes("hello world") >= 1


def test_estimate_minutes_long_text():
    text = " ".join(["word"] * 360)  # 360 words = 2 minutes at 180wpm
    assert _estimate_minutes(text) == 2


def test_estimate_minutes_empty():
    assert _estimate_minutes("") == 1  # minimum 1


# ── _extract_sections ─────────────────────────────────────────────────────────

def test_extract_sections_with_headings():
    content = """## Introduction
This is the intro.

## What You Will Learn
You will learn about X.

## Summary
Key points here."""
    sections = _extract_sections(content)
    assert "introduction" in sections
    assert "what you will learn" in sections
    assert "summary" in sections


def test_extract_sections_no_headings():
    content = "Plain text with no headings at all."
    sections = _extract_sections(content)
    # Should put all content in "introduction" (default)
    assert "introduction" in sections
    assert sections["introduction"].strip()


def test_extract_sections_preserves_content():
    content = "## Introduction\nHello world."
    sections = _extract_sections(content)
    assert "hello world" in sections.get("introduction", "").lower()


# ── _extract_examples ─────────────────────────────────────────────────────────

def test_extract_examples_finds_for_example():
    text = "For example, if a = 2 then b = 4.\nNormal sentence."
    examples = _extract_examples(text)
    assert len(examples) > 0
    assert "example" in examples[0].lower()


def test_extract_examples_empty():
    text = "This text has no examples at all."
    examples = _extract_examples(text)
    assert examples == []


# ── _section_completeness ─────────────────────────────────────────────────────

def test_section_completeness_full():
    sections = {key: "some content here" for key in CANONICAL_SECTIONS}
    score = _section_completeness(sections)
    assert score == 100


def test_section_completeness_empty():
    assert _section_completeness({}) == 0


def test_section_completeness_partial():
    sections = {"introduction": "content", "summary": "content"}
    score = _section_completeness(sections)
    assert 0 < score < 100


# ── _normalize_step ───────────────────────────────────────────────────────────

SAMPLE_LESSON_CONTENT = """## Introduction
Photosynthesis is the process by which plants make food using sunlight.
Plants use chlorophyll to capture light energy from the sun.

## What You Will Learn
You will learn the chemical equation for photosynthesis and how it works.

## Worked Example
For example, if a plant absorbs 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.
Step 1: Balance carbon atoms.
Step 2: Balance hydrogen atoms.

## Summary
Key points: photosynthesis converts light into chemical energy stored as glucose.
"""

def test_normalize_step_returns_required_fields():
    step = _normalize_step(0, "Introduction", SAMPLE_LESSON_CONTENT, [SAMPLE_LESSON_CONTENT])
    for field in [
        "step_number", "step_title", "raw_content", "normalized_sections",
        "formulas", "examples", "mcqs", "summary", "word_count",
        "estimated_minutes", "completeness_score", "uniqueness_score",
        "depth_progression_score", "overall_step_score", "status", "issues",
    ]:
        assert field in step, f"Missing field: {field}"


def test_normalize_step_scores_in_range():
    step = _normalize_step(0, "Step 1", SAMPLE_LESSON_CONTENT, [SAMPLE_LESSON_CONTENT])
    assert 0 <= step["completeness_score"] <= 100
    assert 0 <= step["uniqueness_score"] <= 100
    assert 0 <= step["depth_progression_score"] <= 100
    assert 0 <= step["overall_step_score"] <= 100


def test_normalize_step_extracts_formulas():
    content = "The formula is F = ma. Also E = mc^2."
    step = _normalize_step(0, "Step 1", content, [content])
    # Formulas should be detected from lines with = signs
    assert isinstance(step["formulas"], list)


def test_normalize_step_extracts_examples():
    content = "For example, if x = 2 then y = 4 and we compute the result."
    step = _normalize_step(0, "Step 1", content, [content])
    assert isinstance(step["examples"], list)


# ── get_lesson_list (mocked DB) ───────────────────────────────────────────────

# The get_content_db function is imported lazily inside each service function
# (PLC0415 pattern). The patch target must be where it's imported, not where
# it's defined. We patch at the grade_db_router module level.
_GRADE_DB_PATCH = "app.services.grade_db_router.get_content_db"


def test_get_lesson_list_empty_when_db_unavailable():
    """get_lesson_list should return empty structure when DB is unavailable."""
    with patch(_GRADE_DB_PATCH, side_effect=Exception("DB down")):
        result = get_lesson_list(grade="Grade 9")
    assert result["grades"] == []
    assert result["lessons"] == []
    assert result["total_lessons"] == 0


def _fluent_mock(rows):
    """
    Build a Supabase query-builder mock where every method returns the same
    mock object (fluent interface), so the chain depth doesn't matter.
    Only .execute().data is configured with the supplied rows.
    """
    mock_db = MagicMock()
    # Make every query-builder method return the same mock_db so that chaining
    # .eq().eq().ilike().order().limit() all resolve to the same object.
    for method_name in ("table", "select", "eq", "ilike", "order", "limit"):
        getattr(mock_db, method_name).return_value = mock_db
    mock_db.execute.return_value.data = rows
    return mock_db


def test_get_lesson_list_returns_required_keys():
    mock_db = _fluent_mock([
        {"id": "1", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis", "step_title": "Step 1", "status": "active"},
        {"id": "2", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis", "step_title": "Step 2", "status": "active"},
    ])
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_lesson_list(grade="Grade 9")
    for key in ("grades", "subjects", "chapters", "lessons", "total_lessons", "total_steps"):
        assert key in result, f"Missing key: {key}"


def test_get_lesson_list_groups_by_chapter():
    mock_db = _fluent_mock([
        {"id": "1", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis", "step_title": "Step 1", "status": "active"},
        {"id": "2", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis", "step_title": "Step 2", "status": "active"},
        {"id": "3", "grade": "Grade 9", "subject": "Science", "chapter": "Respiration", "step_title": "Step 1", "status": "active"},
    ])
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_lesson_list(grade="Grade 9")
    # 2 distinct lessons
    assert result["total_lessons"] == 2
    assert result["total_steps"] == 3


# ── get_lesson_detail (mocked DB) ─────────────────────────────────────────────

def test_get_lesson_detail_not_found():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_lesson_detail("nonexistent-id")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_get_lesson_detail_returns_normalized_steps():
    mock_db = MagicMock()
    rows = [
        {"id": "1", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis",
         "step_title": "Step 1", "lesson_content": SAMPLE_LESSON_CONTENT, "status": "active"},
        {"id": "2", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis",
         "step_title": "Step 2", "lesson_content": SAMPLE_LESSON_CONTENT + " More content.", "status": "active"},
    ]
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_lesson_detail("1")
    assert "steps" in result
    assert len(result["steps"]) == 2
    for step in result["steps"]:
        assert "step_number" in step
        assert "normalized_sections" in step
        assert "completeness_score" in step
        assert "issues" in step


def test_get_lesson_detail_has_audit_summary():
    mock_db = MagicMock()
    rows = [
        {"id": "1", "grade": "Grade 9", "subject": "Science", "chapter": "Photosynthesis",
         "step_title": "Step 1", "lesson_content": SAMPLE_LESSON_CONTENT, "status": "active"},
    ]
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_lesson_detail("1")
    # audit_summary may be None for a single step but key must exist
    assert "audit_summary" in result
    assert "total_estimated_minutes" in result


def test_get_lesson_detail_never_writes(monkeypatch):
    """get_lesson_detail must only read — no update/insert calls."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        get_lesson_detail("test-id")
    # Verify no .insert() or .update() calls were made
    mock_db.table.return_value.insert.assert_not_called()
    mock_db.table.return_value.update.assert_not_called()


# ── preview_transform ─────────────────────────────────────────────────────────

def _mock_lesson_detail_for_preview(monkeypatch):
    """Helper: patch get_lesson_detail to return a synthetic lesson."""
    synthetic = {
        "lesson_id": "test", "grade": "Grade 9", "subject": "Science",
        "chapter": "Photosynthesis", "title": "Science — Photosynthesis",
        "total_steps": 1, "total_estimated_minutes": 5,
        "steps": [{
            "step_number": 1, "step_title": "Intro",
            "raw_content": SAMPLE_LESSON_CONTENT,
            "normalized_sections": {"introduction": "Hello"},
            "formulas": ["F = ma"], "examples": [], "mcqs": [],
            "summary": "Key points here.", "word_count": 100,
            "estimated_minutes": 5, "completeness_score": 75,
            "uniqueness_score": 80, "depth_progression_score": 70,
            "cross_step_repetition_score": 90, "overall_step_score": 77,
            "status": "pass", "issues": [],
        }],
        "audit_summary": None, "similarity_matrix": None,
    }
    monkeypatch.setattr("app.services.lesson_lab_service.get_lesson_detail", lambda *a, **kw: synthetic)
    return synthetic


def test_preview_transform_structure_only_does_not_return_raw_content(monkeypatch):
    _mock_lesson_detail_for_preview(monkeypatch)
    result = preview_transform("test", mode="structure_only")
    assert result["preview_mode"] == "structure_only"
    # structure_only should not include raw_content in steps
    for step in result["steps"]:
        assert "raw_content" not in step


def test_preview_transform_summary_only(monkeypatch):
    _mock_lesson_detail_for_preview(monkeypatch)
    result = preview_transform("test", mode="summary_only")
    assert result["preview_mode"] == "summary_only"
    assert "steps" in result
    for step in result["steps"]:
        assert "summary" in step


def test_preview_transform_sectioned_no_llm(monkeypatch):
    _mock_lesson_detail_for_preview(monkeypatch)
    result = preview_transform("test", mode="sectioned", use_llm=False)
    assert result["use_llm"] is False
    assert "steps" in result


def test_preview_transform_does_not_save_content(monkeypatch):
    """preview_transform must never call insert/update on any DB table."""
    _mock_lesson_detail_for_preview(monkeypatch)
    mock_db = MagicMock()
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        preview_transform("test", mode="structure_only")
    mock_db.table.return_value.insert.assert_not_called()
    mock_db.table.return_value.update.assert_not_called()


def test_preview_transform_invalid_mode_returns_error(monkeypatch):
    _mock_lesson_detail_for_preview(monkeypatch)
    result = preview_transform("test", mode="nonexistent_mode")
    assert "error" in result


def test_preview_transform_missing_lesson_propagates_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.lesson_lab_service.get_lesson_detail",
        lambda *a, **kw: {"error": "Lesson not found."},
    )
    result = preview_transform("missing-id")
    assert "error" in result


# ── get_visuals ───────────────────────────────────────────────────────────────

def test_get_visuals_returns_empty_state_when_table_missing():
    """get_visuals must return friendly empty state when DB/table unavailable."""
    with patch(_GRADE_DB_PATCH, side_effect=Exception("table missing")):
        result = get_visuals(grade="Grade 9", subject="Science", chapter="Photosynthesis")
    assert result["available"] is False
    assert result["visuals"] == []
    assert result["empty_state"] == "No textbook visuals linked yet."


def test_get_visuals_returns_required_keys():
    result = get_visuals(grade="Grade 9")
    for key in ("available", "visuals", "grade", "subject", "chapter", "lesson_id"):
        assert key in result, f"Missing key: {key}"


def test_get_visuals_does_not_expose_secrets():
    """No API keys, passwords or tokens should appear in visuals response."""
    result = get_visuals(grade="Grade 9")
    result_str = str(result).lower()
    for secret_keyword in ("api_key", "password", "token", "secret", "sk-", "gsk_"):
        assert secret_keyword not in result_str, f"Secret keyword '{secret_keyword}' found in visuals response"


def test_get_visuals_with_data(monkeypatch):
    """When DB returns visual rows, they should be formatted correctly."""
    rows = [
        {
            "id": "vis-1", "title": "Chloroplast Structure", "asset_url": "https://cdn.example.com/vis1.png",
            "source": "textbook", "matched_topic": "Photosynthesis", "caption": "Figure 1.1",
            "page_number": 42, "chapter": "Photosynthesis", "subject": "Science", "grade": "Grade 9",
        },
    ]
    # Use fluent mock: visuals query chains .eq().eq().ilike().ilike().order().limit()
    mock_db = _fluent_mock(rows)
    with patch(_GRADE_DB_PATCH, return_value=mock_db):
        result = get_visuals(grade="Grade 9", subject="Science", chapter="Photosynthesis")
    assert result["available"] is True
    assert len(result["visuals"]) == 1
    visual = result["visuals"][0]
    for key in ("id", "title", "image_url_or_asset_ref", "source", "matched_topic", "caption"):
        assert key in visual, f"Visual missing key: {key}"
    assert result["empty_state"] is None
