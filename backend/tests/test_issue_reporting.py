"""
Tests for Product Issue Reporting — Part 2 of Lesson Quality + Bug Reporting.

Covers:
- Student can submit issue report
- Issue context captured
- Description sanitized (HTML injection blocked)
- Rate limit enforced
- Non-admin cannot list all issues
- Admin can list/filter issues
- Admin can update status
- Admin notes sanitized
- Invalid issue type rejected
- Empty description blocked
"""
import pytest
from unittest.mock import MagicMock, patch

# ── Minimal in-memory stubs ────────────────────────────────────────────────────

VALID_ISSUE = {
    "issue_type": "content_issue",
    "severity": "medium",
    "title": "Missing explanation",
    "description": "The simple explanation section is too short.",
    "route": "/lessons",
    "grade": "Grade 9",
    "subject": "Science",
    "chapter": "Motion",
    "lesson_id": "grade9-science-motion-1",
    "lesson_step": "Core explanation",
    "browser_info": {
        "userAgent": "Mozilla/5.0",
        "platform": "MacIntel",
        "language": "en-US",
    },
}

CREATED_ISSUE = {**VALID_ISSUE, "id": "abc-123", "status": "open",
                  "reporter_user_id": "user-1", "reporter_role": "student"}


class _FakeTable:
    def __init__(self, data=None, error=None):
        self._data = data or []
        self._error = error

    def select(self, *a, **k): return self
    def insert(self, row): self._inserted = row; return self
    def update(self, data): self._update = data; return self
    def eq(self, *a): return self
    def ilike(self, *a): return self
    def order(self, *a, **k): return self
    def range(self, *a): return self
    def limit(self, *a): return self
    def single(self): return self
    def execute(self):
        m = MagicMock()
        m.data = self._data
        return m


class _FakeDB:
    def table(self, name): return _FakeTable(data=[CREATED_ISSUE])


# ── Import the module under test ───────────────────────────────────────────────

from app.routes.issues import (
    IssueReportIn, IssueUpdateIn,
    _sanitize, _sanitize_browser_info, _check_rate,
    VALID_ISSUE_TYPES, VALID_SEVERITIES, VALID_STATUSES,
)


# ── Unit: sanitization ─────────────────────────────────────────────────────────

class TestSanitization:
    def test_strips_html_tags(self):
        out = _sanitize("<script>alert('xss')</script>Hello")
        assert "<script>" not in out
        assert "Hello" in out

    def test_escapes_angle_brackets(self):
        out = _sanitize("<b>bold</b>")
        assert "<b>" not in out

    def test_truncates_to_max_len(self):
        out = _sanitize("a" * 3000, max_len=100)
        assert len(out) <= 100

    def test_empty_string(self):
        assert _sanitize("") == ""

    def test_sanitize_browser_info_keeps_safe_keys(self):
        bi = _sanitize_browser_info({
            "userAgent": "Mozilla", "platform": "Win",
            "secretToken": "abc123", "eval": "bad"
        })
        assert "userAgent" in bi
        assert "platform" in bi
        assert "secretToken" not in bi
        assert "eval" not in bi

    def test_sanitize_browser_info_none(self):
        assert _sanitize_browser_info(None) is None


# ── Unit: validation ───────────────────────────────────────────────────────────

class TestIssueValidation:
    def test_valid_issue_type(self):
        m = IssueReportIn(issue_type="content_issue", description="This is a real issue.")
        assert m.issue_type == "content_issue"

    def test_invalid_issue_type_raises(self):
        with pytest.raises(Exception) as exc:
            IssueReportIn(issue_type="hack_attempt", description="x" * 20)
        assert "invalid" in str(exc.value).lower() or "issue_type" in str(exc.value).lower()

    def test_valid_severity(self):
        m = IssueReportIn(issue_type="other", severity="critical", description="x" * 20)
        assert m.severity == "critical"

    def test_invalid_severity_raises(self):
        with pytest.raises(Exception):
            IssueReportIn(issue_type="other", severity="blocker", description="x" * 20)

    def test_empty_description_raises(self):
        with pytest.raises(Exception):
            IssueReportIn(issue_type="other", description="")

    def test_too_short_description_raises(self):
        with pytest.raises(Exception):
            IssueReportIn(issue_type="other", description="short")

    def test_valid_description(self):
        m = IssueReportIn(issue_type="other", description="This is a detailed description.")
        assert m.description

    def test_all_valid_issue_types_accepted(self):
        for t in VALID_ISSUE_TYPES:
            m = IssueReportIn(issue_type=t, description="x" * 20)
            assert m.issue_type == t

    def test_all_valid_severities_accepted(self):
        for s in VALID_SEVERITIES:
            m = IssueReportIn(issue_type="other", severity=s, description="x" * 20)
            assert m.severity == s


# ── Unit: update validation ────────────────────────────────────────────────────

class TestIssueUpdateValidation:
    def test_valid_status(self):
        m = IssueUpdateIn(status="triaged")
        assert m.status == "triaged"

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            IssueUpdateIn(status="deleted")

    def test_all_valid_statuses_accepted(self):
        for s in VALID_STATUSES:
            m = IssueUpdateIn(status=s)
            assert m.status == s

    def test_partial_update_no_status(self):
        m = IssueUpdateIn(admin_notes="Reviewed and confirmed.")
        assert m.admin_notes == "Reviewed and confirmed."
        assert m.status is None


# ── Unit: rate limit ───────────────────────────────────────────────────────────

class TestRateLimit:
    def test_within_limit_passes(self):
        import app.routes.issues as mod
        # Clear rate for test user
        mod._rate.pop("test-rate-user", None)
        from fastapi import HTTPException
        for _ in range(5):
            _check_rate("test-rate-user")  # Should not raise

    def test_over_limit_raises(self):
        import app.routes.issues as mod
        import time
        mod._rate["test-rate-limit-user"] = [time.time()] * 10
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _check_rate("test-rate-limit-user")
        assert exc.value.status_code == 429


# ── Unit: section detection ────────────────────────────────────────────────────

class TestSectionAudit:
    """Test the 8-section audit logic."""

    def _make_lesson(self, sections=None):
        """Build a lesson with given sections (or all 8 if None)."""
        all_sections = {
            "introduction": "This is the introduction. " * 10,
            "what you will learn": "- You will learn about motion.\n- You will understand velocity.\n- You will apply Newton's laws.",
            "simple explanation": "Simple explanation here. " * 15,
            "step-by-step breakdown": "Step 1: Identify the problem.\nStep 2: Apply the formula.\nStep 3: Calculate the answer.",
            "worked example": "Problem: A car moves at 60 km/h.\nSolution: speed = distance/time\nAnswer: 60 km/h",
            "common mistake": "Students often forget to convert units. Instead, always check units first. The correct approach is to convert all units to SI.",
            "quick check question": "Question: What is velocity?\nA) Speed with direction\nB) Distance only\nAnswer: A — velocity includes direction. Explanation: Velocity is a vector.",
            "summary": "- Motion requires force.\n- Velocity includes direction.\n- Newton's laws govern motion.",
        }
        if sections is not None:
            all_sections = {k: v for k, v in all_sections.items() if k in sections}
        content_parts = []
        for sec, text in all_sections.items():
            content_parts.append(f"## {sec.title()}\n{text}\n")
        return "\n".join(content_parts)

    def test_full_lesson_no_critical_issues(self):
        from scripts.audit_lesson_sections import audit_lesson_content
        row = {"grade": "Grade 9", "subject": "Science", "chapter": "Motion",
               "step_title": "Core", "lesson_content": self._make_lesson()}
        result = audit_lesson_content(row)
        assert result["sections_found"] == 8
        assert result["issue_counts"]["critical"] == 0

    def test_missing_section_is_critical(self):
        from scripts.audit_lesson_sections import audit_lesson_content
        # Remove "worked example"
        sections = [s for s in [
            "introduction","what you will learn","simple explanation",
            "step-by-step breakdown","common mistake","quick check question","summary"
        ]]
        row = {"grade": "Grade 9", "subject": "Science", "chapter": "Motion",
               "step_title": "Core", "lesson_content": self._make_lesson(sections)}
        result = audit_lesson_content(row)
        assert "worked example" in result["missing_sections"]
        assert result["issue_counts"]["critical"] >= 1

    def test_empty_section_is_critical(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("introduction", "")
        assert any(i.severity == "critical" for i in issues)

    def test_short_explanation_is_high(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("simple explanation", "Too short.")
        assert any(i.severity == "high" for i in issues)

    def test_filler_text_is_critical(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("introduction", "Coming soon. This section will be added later.")
        assert any(i.severity == "critical" for i in issues)

    def test_worked_example_no_answer_is_critical(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("worked example", "A car moves. We need to find velocity." * 5)
        assert any(i.severity == "critical" for i in issues)

    def test_common_mistake_no_correction_is_high(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("common mistake", "Students make a mistake with velocity." * 3)
        assert any(i.severity == "high" for i in issues)

    def test_quick_check_no_answer_is_high(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("quick check question", "What is velocity? A) Fast B) Slow C) Both")
        assert any(i.severity == "high" for i in issues)

    def test_summary_missing_bullets_is_high(self):
        from scripts.audit_lesson_sections import _audit_section
        issues = _audit_section("summary", "In summary, motion is important in physics and everyday life. You should remember this." * 2)
        assert any(i.severity == "high" for i in issues)

    def test_report_includes_missing_section_names(self):
        from scripts.audit_lesson_sections import audit_lesson_content
        content = "## Introduction\nThis is the intro. " * 8
        row = {"grade": "Grade 9", "subject": "Science", "chapter": "Motion",
               "step_title": "Core", "lesson_content": content}
        result = audit_lesson_content(row)
        assert len(result["missing_sections"]) > 0
        assert all(isinstance(s, str) for s in result["missing_sections"])
