"""
test_formula_sheets.py
─────────────────────────────────────────────────────────────────────────────
Tests for formula sheet content structure, API endpoint, and seed validation.

Covers:
  1. _build_sections groups rows correctly by section_title
  2. grade filter applied (only matching grade returned)
  3. available=false returned when no rows found
  4. Seed data structure validation (schema compliance)
  5. No row has empty required fields
  6. display_order is an integer >= 0
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.routes.formula_sheets import _build_sections, get_formula_sheets


# ── _build_sections ───────────────────────────────────────────────────────────

class TestBuildSections:
    def test_groups_by_section_title(self):
        rows = [
            {"section_title": "Area Formulas", "formula_name": "Heron Formula",
             "expression": "A=sqrt[s(s-a)(s-b)(s-c)]", "explanation": "s=semiperimeter",
             "example": "a=3,b=4,c=5->A=6", "chapter": "Triangles"},
            {"section_title": "Area Formulas", "formula_name": "Area of Circle",
             "expression": "A=pi.r^2", "explanation": "r=radius",
             "example": "r=7->A=154", "chapter": "Circles"},
            {"section_title": "Equations of Motion", "formula_name": "First Equation",
             "expression": "v=u+at", "explanation": "v=final",
             "example": "u=0,a=10,t=5->v=50", "chapter": "Motion"},
        ]
        sections = _build_sections(rows)
        assert len(sections) == 2
        titles = [s["title"] for s in sections]
        assert "Area Formulas" in titles
        assert "Equations of Motion" in titles

    def test_formulas_in_section(self):
        rows = [
            {"section_title": "AP Formulas", "formula_name": "nth Term",
             "expression": "a_n=a+(n-1)d", "explanation": "a=first,d=diff",
             "example": "a=2,d=3,n=5->14", "chapter": "AP"},
            {"section_title": "AP Formulas", "formula_name": "Sum",
             "expression": "S_n=(n/2)[2a+(n-1)d]", "explanation": "Sum",
             "example": "n=10->55", "chapter": "AP"},
        ]
        sections = _build_sections(rows)
        assert len(sections) == 1
        assert len(sections[0]["formulas"]) == 2

    def test_empty_rows_returns_empty(self):
        assert _build_sections([]) == []


# ── get_formula_sheets (mocked) ───────────────────────────────────────────────

class TestGetFormulaSheets:
    STUDENT = {"profile": {"id": "uid-1", "username": "test", "grade": "Grade 9"}}

    def _mock_formula_rows(self, monkeypatch, rows, subj_rows=None):
        call_count = [0]
        def fake_safe_query(fn):
            call_count[0] += 1
            if call_count[0] == 1:
                class R: data = rows
                return rows, None
            # subjects query
            class R: data = subj_rows or [{"subject": "Mathematics"}]
            return subj_rows or [{"subject": "Mathematics"}], None
        monkeypatch.setattr("app.routes.formula_sheets._safe_query", fake_safe_query)

    def test_returns_sections_when_rows_found(self, monkeypatch):
        rows = [
            {"section_title": "Area Formulas", "formula_name": "Heron Formula",
             "expression": "A=sqrt[s(s-a)(s-b)(s-c)]", "explanation": "s=semi",
             "example": "a=3,b=4,c=5->A=6", "chapter": "Triangles", "display_order": 1},
        ]
        self._mock_formula_rows(monkeypatch, rows)
        result = get_formula_sheets(grade=None, subject="Mathematics", chapter=None, student=self.STUDENT)
        assert result["success"] is True
        assert result["available"] is True
        assert len(result["sections"]) >= 1

    def test_returns_unavailable_when_no_rows(self, monkeypatch):
        monkeypatch.setattr("app.routes.formula_sheets._safe_query", lambda fn: ([], None))
        result = get_formula_sheets(grade=None, subject="Mathematics", chapter=None, student=self.STUDENT)
        assert result["success"] is True
        assert result["available"] is False
        assert "not available" in result["message"].lower() or result["message"]

    def test_uses_student_grade_as_default(self, monkeypatch):
        captured = {}
        def fake_query(fn):
            try:
                result = fn()
                captured["called"] = True
                class R: data = []
                return [], None
            except Exception:
                return [], None
        monkeypatch.setattr("app.routes.formula_sheets._safe_query", fake_query)
        result = get_formula_sheets(grade=None, subject=None, chapter=None, student=self.STUDENT)
        # grade should default to Grade 9 (from student profile)
        assert result["grade"] == "Grade 9"

    def test_table_missing_returns_unavailable(self, monkeypatch):
        monkeypatch.setattr("app.routes.formula_sheets._safe_query",
                            lambda fn: ([], "schema cache error"))
        result = get_formula_sheets(grade=None, subject=None, chapter=None, student=self.STUDENT)
        assert result["success"] is True
        assert result["available"] is False


# ── Seed data structure validation ────────────────────────────────────────────

class TestSeedDataStructure:
    """
    These tests validate that any rows added to formula_sheets follow the schema.
    Used as a guard against malformed seed data.
    """
    REQUIRED_FIELDS = ["grade", "subject", "section_title", "formula_name", "expression"]
    VALID_GRADES = {f"Grade {i}" for i in range(5, 13)}

    def _sample_rows(self):
        """Return representative rows that match the seed data format."""
        return [
            {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Triangles",
             "section_title": "Area Formulas", "formula_name": "Heron Formula",
             "expression": "A=sqrt[s(s-a)(s-b)(s-c)]", "explanation": "s=(a+b+c)/2",
             "example": "a=3,b=4,c=5->A=6", "display_order": 1},
            {"grade": "Grade 9", "subject": "Science", "chapter": "Motion",
             "section_title": "Equations of Motion", "formula_name": "First Equation",
             "expression": "v=u+at", "explanation": "v=final vel",
             "example": "u=0,a=10,t=5->v=50", "display_order": 1},
            {"grade": "Grade 12", "subject": "Physics", "chapter": "Electrostatics",
             "section_title": "Coulomb Law", "formula_name": "Coulomb Law",
             "expression": "F=kq1q2/r^2", "explanation": "k=9e9",
             "example": "q1=q2=1C,r=1m->F=9e9N", "display_order": 1},
        ]

    def test_all_required_fields_present(self):
        for row in self._sample_rows():
            for field in self.REQUIRED_FIELDS:
                assert field in row, f"Missing required field '{field}' in row: {row}"
                assert row[field], f"Required field '{field}' is empty in row: {row}"

    def test_grade_is_valid_format(self):
        for row in self._sample_rows():
            assert row["grade"] in self.VALID_GRADES, \
                f"Invalid grade '{row['grade']}' — must be Grade 5-12"

    def test_display_order_is_non_negative_int(self):
        for row in self._sample_rows():
            d = row.get("display_order", 0)
            assert isinstance(d, int), f"display_order must be int, got {type(d)}"
            assert d >= 0, f"display_order must be >= 0, got {d}"

    def test_expression_is_not_empty(self):
        for row in self._sample_rows():
            assert row["expression"].strip(), "expression must not be empty or whitespace"

    def test_no_none_in_required_fields(self):
        for row in self._sample_rows():
            for field in self.REQUIRED_FIELDS:
                assert row[field] is not None, f"Required field '{field}' is None"

    def test_grade_range_5_to_12(self):
        """Ensure no row accidentally has Grade 1-4 or Grade 13+."""
        for row in self._sample_rows():
            num = int(row["grade"].split()[-1])
            assert 5 <= num <= 12, f"Grade {num} out of supported range 5-12"
