"""
Tests for user feedback submission + admin triage + eligibility gating.

Covers:
- Feedback type/rating/message validation
- Criticality scoring (type + low-rating bump) and tier derivation
- Rate limit enforced
- Sanitization strips HTML
- Activity-threshold + cooldown eligibility logic
"""
import pytest
from unittest.mock import MagicMock, patch

from app.routes.feedback import (
    FeedbackReportIn, FeedbackUpdateIn,
    compute_criticality, tier_from_score, _sanitize, _check_rate,
    VALID_FEEDBACK_TYPES,
)
from app.services.feedback_eligibility_service import (
    check_eligibility, get_activity_count, ACTIVITY_THRESHOLD, COOLDOWN_DAYS,
)


# ── Unit: validation ─────────────────────────────────────────────────────────

class TestFeedbackValidation:
    def test_valid_feedback_type(self):
        m = FeedbackReportIn(feedback_type="bug", message="Something is broken here.")
        assert m.feedback_type == "bug"

    def test_invalid_feedback_type_raises(self):
        with pytest.raises(Exception):
            FeedbackReportIn(feedback_type="rant", message="This is a message.")

    def test_all_valid_types_accepted(self):
        for t in VALID_FEEDBACK_TYPES:
            m = FeedbackReportIn(feedback_type=t, message="A reasonably long message.")
            assert m.feedback_type == t

    def test_rating_in_range(self):
        m = FeedbackReportIn(feedback_type="praise", rating=5, message="Loving the app!")
        assert m.rating == 5

    def test_rating_out_of_range_raises(self):
        with pytest.raises(Exception):
            FeedbackReportIn(feedback_type="praise", rating=6, message="Too high a rating.")

    def test_rating_optional(self):
        m = FeedbackReportIn(feedback_type="other", message="No rating given here.")
        assert m.rating is None

    def test_empty_message_raises(self):
        with pytest.raises(Exception):
            FeedbackReportIn(feedback_type="other", message="")

    def test_too_short_message_raises(self):
        with pytest.raises(Exception):
            FeedbackReportIn(feedback_type="other", message="hi")

    def test_update_valid_status(self):
        m = FeedbackUpdateIn(status="reviewed")
        assert m.status == "reviewed"

    def test_update_invalid_status_raises(self):
        with pytest.raises(Exception):
            FeedbackUpdateIn(status="archived")


# ── Unit: sanitization ────────────────────────────────────────────────────────

class TestFeedbackSanitization:
    def test_strips_html_tags(self):
        out = _sanitize("<script>alert(1)</script>Nice app")
        assert "<script>" not in out
        assert "Nice app" in out

    def test_none_returns_none(self):
        assert _sanitize(None) is None

    def test_empty_returns_none(self):
        assert _sanitize("") is None

    def test_truncates(self):
        out = _sanitize("a" * 3000, max_len=50)
        assert len(out) <= 50


# ── Unit: criticality scoring ─────────────────────────────────────────────────

class TestCriticalityScoring:
    def test_bug_scores_higher_than_praise(self):
        assert compute_criticality("bug", None) > compute_criticality("praise", None)

    def test_low_rating_bumps_score(self):
        base = compute_criticality("feature_request", None)
        bumped = compute_criticality("feature_request", 1)
        assert bumped > base

    def test_high_rating_no_bump(self):
        base = compute_criticality("feature_request", None)
        with_high = compute_criticality("feature_request", 5)
        assert with_high == base

    def test_tier_thresholds(self):
        assert tier_from_score(80) == "critical"
        assert tier_from_score(55) == "high"
        assert tier_from_score(35) == "medium"
        assert tier_from_score(5) == "low"

    def test_bug_report_is_at_least_high_tier(self):
        assert tier_from_score(compute_criticality("bug", None)) in ("high", "critical")

    def test_praise_is_low_tier(self):
        assert tier_from_score(compute_criticality("praise", 5)) == "low"


# ── Unit: rate limit ───────────────────────────────────────────────────────────

class TestFeedbackRateLimit:
    def test_within_limit_passes(self):
        import app.routes.feedback as mod
        mod._rate.pop("fb-rate-user", None)
        for _ in range(5):
            _check_rate("fb-rate-user")

    def test_over_limit_raises(self):
        import app.routes.feedback as mod
        import time
        from fastapi import HTTPException
        mod._rate["fb-rate-limit-user"] = [time.time()] * 10
        with pytest.raises(HTTPException) as exc:
            _check_rate("fb-rate-limit-user")
        assert exc.value.status_code == 429


# ── Unit: eligibility gating ("serious user") ─────────────────────────────────

class _FakeCountTable:
    def __init__(self, count):
        self._count = count

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        m = MagicMock()
        m.count = self._count
        return m


class _FakeCountClient:
    def __init__(self, counts):
        self._counts = counts

    def table(self, name):
        return _FakeCountTable(self._counts.get(name, 0))


class TestActivityCount:
    def test_sums_lessons_tests_exam_prep(self):
        fake = _FakeCountClient({"student_progress": 2, "test_history": 1, "exam_prep_simulated_tests": 4})
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            assert get_activity_count("alice", "user-1") == 7

    def test_no_username_skips_username_keyed_tables(self):
        fake = _FakeCountClient({"student_progress": 9, "test_history": 9, "exam_prep_simulated_tests": 2})
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            assert get_activity_count(None, "user-1") == 2


class TestEligibility:
    def test_below_threshold_not_eligible(self):
        fake = _FakeCountClient({"student_progress": 0, "test_history": 1, "exam_prep_simulated_tests": 0})
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            result = check_eligibility("user-1", "alice", None)
        assert result["eligible"] is False
        assert result["activity_count"] < ACTIVITY_THRESHOLD

    def test_meets_threshold_no_prior_prompt_is_eligible(self):
        fake = _FakeCountClient({"student_progress": 2, "test_history": 2, "exam_prep_simulated_tests": 0})
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            result = check_eligibility("user-1", "alice", None)
        assert result["eligible"] is True
        assert result["activity_count"] >= ACTIVITY_THRESHOLD

    def test_recent_prompt_blocks_eligibility(self):
        from datetime import datetime, timezone
        fake = _FakeCountClient({"student_progress": 5, "test_history": 5, "exam_prep_simulated_tests": 5})
        recent = datetime.now(timezone.utc).isoformat()
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            result = check_eligibility("user-1", "alice", recent)
        assert result["eligible"] is False
        assert result["cooldown_ok"] is False

    def test_old_prompt_allows_eligibility_again(self):
        from datetime import datetime, timedelta, timezone
        fake = _FakeCountClient({"student_progress": 5, "test_history": 5, "exam_prep_simulated_tests": 5})
        old = (datetime.now(timezone.utc) - timedelta(days=COOLDOWN_DAYS + 1)).isoformat()
        with patch("app.services.feedback_eligibility_service.admin_client", fake):
            result = check_eligibility("user-1", "alice", old)
        assert result["eligible"] is True
        assert result["cooldown_ok"] is True
