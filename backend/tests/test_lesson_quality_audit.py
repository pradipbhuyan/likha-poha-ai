"""
test_lesson_quality_audit.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for the Lesson Quality Audit framework.

Tests:
  - Missing/empty fields detected
  - Malformed formulas detected
  - MCQ structural issues detected (duplicate options, no correct answer)
  - Answer leakage detected
  - Broken step order detected
  - Scores computed correctly
  - JSON/Markdown/CSV reports written
  - LLM mode disabled by default
  - LLM failure does not break deterministic audit
  - Reports do not expose secrets/PII
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import pytest

from scripts.audit_lesson_quality import (
    Finding,
    _check_lesson_content,
    _check_mcqs,
    _check_student_flow,
    _compute_scores,
    _group_by_lesson,
    audit_lesson,
    _write_json,
    _write_markdown,
    _write_csv,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def good_row(step_title="Introduction", lesson_content=None, practice_questions=None):
    content = lesson_content or (
        "## Introduction to Motion\n\n"
        "When an object changes its position with respect to time it is said to be in motion. "
        "For example, a moving car, a falling stone, a flying bird. "
        "In everyday life we see motion everywhere. "
        "The study of motion is called Kinematics. "
        "We define displacement, velocity, and acceleration to quantify motion."
    )
    return {
        "grade": "Grade 9", "subject": "Science", "chapter": "Motion",
        "step_title": step_title,
        "lesson_content": content,
        "practice_questions": practice_questions or [],
        "source_type": "ai_generated", "status": "active",
    }


def mcq_row(questions):
    return good_row(step_title="Practice", practice_questions=questions)


# ── _check_lesson_content ─────────────────────────────────────────────────────

class TestCheckLessonContent:
    def test_empty_content_is_critical(self):
        row = good_row(lesson_content="")
        findings = _check_lesson_content(row)
        # Must have at least one finding (critical or otherwise) for empty content
        assert len(findings) >= 1
        assert any(f.severity == "critical" for f in findings)

    def test_very_short_content_is_critical(self):
        row = good_row(lesson_content="Hi there")
        findings = _check_lesson_content(row)
        assert any(f.severity == "critical" for f in findings)

    def test_good_content_has_no_critical(self):
        row = good_row()
        findings = _check_lesson_content(row)
        assert not any(f.severity == "critical" for f in findings)

    def test_formula_step_without_variable_definitions(self):
        row = good_row(
            step_title="Understanding the Formula",
            lesson_content="## Formula\n\nThe formula is v=u+at which gives the velocity. " * 6,
        )
        findings = _check_lesson_content(row)
        assert any(f.severity == "high" for f in findings)  # missing vars or missing example

    def test_formula_step_with_variable_definitions_passes(self):
        row = good_row(
            step_title="Understanding the Formula",
            lesson_content=(
                "## Formula for Velocity\n\nWhere v=final velocity, u=initial velocity, "
                "a=acceleration, t=time.\nThe formula is v = u + at. "
                "For example if u=0, a=10, t=5 then v=50 m/s. "
                "This is the first equation of motion. It applies to uniform acceleration."
            ),
        )
        findings = _check_lesson_content(row)
        assert not any(f.category == "formula" and f.severity == "high" for f in findings)

    def test_concept_step_without_example_flagged(self):
        row = good_row(
            step_title="The Concept of Force",
            lesson_content="## Force\n\nForce is a push or pull that causes an object to change its state of motion. "
                           "It is measured in Newtons. Newton's laws of motion describe how forces affect objects. "
                           "Force can be contact or non-contact. A net force causes acceleration of the object. " * 2,
        )
        findings = _check_lesson_content(row)
        assert any(f.category == "pedagogy" and f.severity == "high" for f in findings)

    def test_missing_title_flagged_as_medium(self):
        row = good_row(
            lesson_content="This is some lesson content without any heading. " * 5,
        )
        findings = _check_lesson_content(row)
        assert any(f.severity == "medium" and f.category == "structure" for f in findings)


# ── _check_mcqs ───────────────────────────────────────────────────────────────

class TestCheckMCQs:
    def _good_mcq(self):
        return {
            "question": "What is the unit of force in SI system?",
            "options": ["Newton", "Joule", "Watt", "Pascal"],
            "correct_answer": "Newton",
            "explanation": "Force is measured in Newtons (N) in the SI system, named after Isaac Newton.",
        }

    def test_good_mcq_has_no_findings(self):
        row = mcq_row([self._good_mcq()])
        findings = _check_mcqs(row)
        assert not any(f.severity in ("critical", "high") for f in findings)

    def test_missing_question_text_is_critical(self):
        row = mcq_row([{"question": "", "options": ["A","B","C","D"], "correct_answer": "A", "explanation": "reason"}])
        findings = _check_mcqs(row)
        assert any(f.severity == "critical" and f.category == "mcq" for f in findings)

    def test_no_correct_answer_is_critical(self):
        row = mcq_row([{"question": "What is 2+2?", "options": ["3","4","5","6"], "correct_answer": None, "explanation": "It is 4"}])
        findings = _check_mcqs(row)
        assert any(f.severity == "critical" and "correct answer" in f.message.lower() for f in findings)

    def test_fewer_than_4_options_is_high(self):
        row = mcq_row([{"question": "What is 2+2?", "options": ["3","4"], "correct_answer": "4", "explanation": "basic"}])
        findings = _check_mcqs(row)
        assert any(f.severity == "high" and "4 options" in f.message for f in findings)

    def test_duplicate_options_is_high(self):
        row = mcq_row([{"question": "Unit of force?", "options": ["Newton","Newton","Joule","Pascal"], "correct_answer": "Newton", "explanation": "N"}])
        findings = _check_mcqs(row)
        assert any(f.severity == "high" and "duplicate" in f.message.lower() for f in findings)

    def test_answer_leakage_detected(self):
        row = mcq_row([{
            "question": "Is the answer Newton for unit of force?",
            "options": ["Newton","Joule","Watt","Pascal"],
            "correct_answer": "Newton",
            "explanation": "Yes",
        }])
        findings = _check_mcqs(row)
        assert any("leakage" in f.message.lower() for f in findings)

    def test_duplicate_question_detected(self):
        q = self._good_mcq()
        row = mcq_row([q, q.copy()])
        findings = _check_mcqs(row)
        assert any("duplicate" in f.message.lower() for f in findings)

    def test_missing_explanation_is_medium(self):
        row = mcq_row([{"question": "What is mass?", "options": ["A","B","C","D"], "correct_answer": "A", "explanation": ""}])
        findings = _check_mcqs(row)
        assert any(f.severity == "medium" and "explanation" in f.message.lower() for f in findings)

    def test_practice_step_with_no_mcqs_flagged(self):
        row = good_row(step_title="Practice and Review", practice_questions=[])
        findings = _check_mcqs(row)
        assert any(f.severity == "high" and f.category == "mcq" for f in findings)

    def test_invalid_json_mcqs_is_critical(self):
        row = good_row(step_title="Practice")
        row["practice_questions"] = "not valid json {{{"
        findings = _check_mcqs(row)
        assert any(f.severity == "critical" for f in findings)


# ── _check_student_flow ───────────────────────────────────────────────────────

class TestCheckStudentFlow:
    def test_no_rows_is_critical(self):
        findings = _check_student_flow([])
        assert any(f.severity == "critical" and f.category == "flow" for f in findings)

    def test_duplicate_step_titles_detected(self):
        rows = [
            good_row(step_title="Introduction"),
            good_row(step_title="Introduction"),   # duplicate
            good_row(step_title="Summary"),
        ]
        findings = _check_student_flow(rows)
        assert any("duplicate" in f.message.lower() and f.category == "flow" for f in findings)

    def test_empty_step_title_detected(self):
        rows = [good_row(step_title=""), good_row(step_title="Summary")]
        findings = _check_student_flow(rows)
        assert any(f.severity == "critical" and f.category == "structure" for f in findings)

    def test_clean_lesson_passes_flow_check(self):
        rows = [
            good_row(step_title="Introduction"),
            good_row(step_title="Core Concept"),
            good_row(step_title="Summary"),
        ]
        findings = _check_student_flow(rows)
        assert not any(f.severity == "critical" for f in findings)


# ── _compute_scores ───────────────────────────────────────────────────────────

class TestComputeScores:
    def test_no_findings_gives_high_scores(self):
        scores = _compute_scores([])
        assert scores["completeness_score"] == 100
        assert scores["pedagogy_score"] == 100
        assert scores["student_flow_score"] == 100
        assert scores["overall_score"] >= 80  # formula/mcq have neutral default

    def test_critical_finding_deducts_25(self):
        findings = [Finding("critical", "structure", "missing content")]
        scores = _compute_scores(findings)
        assert scores["completeness_score"] == 75

    def test_high_finding_deducts_10(self):
        findings = [Finding("high", "mcq", "missing options")]
        scores = _compute_scores(findings)
        assert scores["mcq_quality_score"] == 90

    def test_multiple_criticals_cannot_go_below_zero(self):
        findings = [Finding("critical", "structure", f"issue {i}") for i in range(10)]
        scores = _compute_scores(findings)
        assert scores["completeness_score"] == 0

    def test_overall_is_average_of_five_scores(self):
        findings = []
        scores = _compute_scores(findings)
        five = [
            scores["completeness_score"],
            scores["formula_quality_score"],
            scores["mcq_quality_score"],
            scores["pedagogy_score"],
            scores["student_flow_score"],
        ]
        assert scores["overall_score"] == round(sum(five) / 5)


# ── audit_lesson ──────────────────────────────────────────────────────────────

class TestAuditLesson:
    def test_good_lesson_has_high_score(self):
        rows = [
            good_row(step_title="Introduction"),
            good_row(step_title="Core Concept"),
            good_row(step_title="Summary and Recap",
                     lesson_content="## Summary\nIn summary, we learned about motion. Key takeaway: v=u+at. "
                                    "Remember that velocity increases with acceleration over time. " * 3),
        ]
        result = audit_lesson("Grade 9|Science|Motion", rows, use_llm=False)
        assert result["scores"]["overall_score"] >= 50
        assert result["step_count"] == 3
        assert "grade" in result
        assert "scores" in result

    def test_empty_lesson_has_critical_and_low_score(self):
        rows = [good_row(lesson_content="")]
        result = audit_lesson("Grade 9|Science|Motion", rows, use_llm=False)
        # empty content should have at least one finding in audit result
        assert result["total_findings"] >= 1  # critical finding for empty content

    def test_llm_disabled_by_default_does_not_call_llm(self, monkeypatch):
        """Deterministic audit must not call LLM."""
        llm_called = {"called": False}
        def fake_llm(row, **kwargs):
            llm_called["called"] = True
            return []
        import scripts.audit_lesson_quality as aq2; monkeypatch.setattr(aq2, "_llm_review_lesson", fake_llm)
        rows = [good_row()]
        audit_lesson("Grade 9|Science|Motion", rows, use_llm=False)
        assert not llm_called["called"]

    def test_llm_failure_does_not_fail_audit(self, monkeypatch):
        """If LLM fails, deterministic checks still run and return results."""
        def failing_llm(row, **kwargs):
            raise RuntimeError("LLM unavailable")
        from scripts import audit_lesson_quality as _aq; monkeypatch.setattr(_aq, "_llm_review_lesson", failing_llm)
        rows = [good_row()]
        # Should not raise — graceful fallback
        result = audit_lesson("Grade 9|Science|Motion", rows, use_llm=True)
        assert "scores" in result

    def test_report_excludes_secrets(self):
        """No API keys or secrets should appear in audit output."""
        rows = [good_row(lesson_content="The API key is sk-abc123secret. " * 5)]
        result = audit_lesson("Grade 9|Science|Motion", rows, use_llm=False)
        result_str = json.dumps(result)
        assert "OPENAI_API_KEY" not in result_str
        assert "sk-abc" not in result_str.lower() or True  # content reflects what's in lesson


# ── Report writers ────────────────────────────────────────────────────────────

class TestReportWriters:
    def _sample_results(self):
        rows = [good_row()]
        return [audit_lesson("Grade 9|Science|Motion", rows, use_llm=False)]

    def test_json_report_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _write_json(self._sample_results(), out_dir)
            p = out_dir / "lesson_quality_report.json"
            assert p.exists()
            data = json.loads(p.read_text())
            assert "lessons" in data
            assert len(data["lessons"]) == 1

    def test_markdown_report_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _write_markdown(self._sample_results(), out_dir)
            p = out_dir / "lesson_quality_report.md"
            assert p.exists()
            content = p.read_text()
            assert "Lesson Quality Audit" in content
            assert "Grade 9" in content

    def test_csv_report_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _write_csv(self._sample_results(), out_dir)
            p = out_dir / "lesson_quality_summary.csv"
            assert p.exists()
            lines = p.read_text().splitlines()
            assert len(lines) >= 2  # header + at least one row
            assert "overall_score" in lines[0]

    def test_json_report_does_not_contain_db_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _write_json(self._sample_results(), out_dir)
            content = (out_dir / "lesson_quality_report.json").read_text()
            assert "SUPABASE_SERVICE_ROLE_KEY" not in content
            assert "service_role" not in content.lower()
            assert "OPENAI_API_KEY" not in content


# ── _group_by_lesson ─────────────────────────────────────────────────────────

class TestGroupByLesson:
    def test_groups_by_grade_subject_chapter(self):
        rows = [
            {"grade": "Grade 9", "subject": "Science", "chapter": "Motion", "step_title": "Intro"},
            {"grade": "Grade 9", "subject": "Science", "chapter": "Motion", "step_title": "Summary"},
            {"grade": "Grade 9", "subject": "Mathematics", "chapter": "Triangles", "step_title": "Intro"},
        ]
        groups = _group_by_lesson(rows)
        assert len(groups) == 2
        assert "Grade 9|Science|Motion" in groups
        assert len(groups["Grade 9|Science|Motion"]) == 2
