"""
Tests for tech debt backlog: creation from feedback, listing, approve/reject.
"""
import pytest

from app.routes.tech_debt import (
    TechDebtCreateIn, TechDebtUpdateIn, VALID_STATUSES, _TIER_DEFAULT_SCORE,
)


class TestTechDebtCreateValidation:
    def test_valid_title(self):
        m = TechDebtCreateIn(title="Fix crash on submit")
        assert m.title == "Fix crash on submit"

    def test_blank_title_raises(self):
        with pytest.raises(Exception):
            TechDebtCreateIn(title="   ")

    def test_title_is_trimmed(self):
        m = TechDebtCreateIn(title="  Fix crash  ")
        assert m.title == "Fix crash"

    def test_source_feedback_ids_default_empty(self):
        m = TechDebtCreateIn(title="Manual entry")
        assert m.source_feedback_ids == []

    def test_source_feedback_ids_accepted(self):
        m = TechDebtCreateIn(title="Bundled bug", source_feedback_ids=["a", "b", "c"])
        assert m.source_feedback_ids == ["a", "b", "c"]

    def test_valid_tier_override(self):
        m = TechDebtCreateIn(title="Manual", criticality_tier_override="high")
        assert m.criticality_tier_override == "high"

    def test_invalid_tier_override_raises(self):
        with pytest.raises(Exception):
            TechDebtCreateIn(title="Manual", criticality_tier_override="urgent")

    def test_all_tier_overrides_accepted(self):
        for tier in _TIER_DEFAULT_SCORE:
            m = TechDebtCreateIn(title="Manual", criticality_tier_override=tier)
            assert m.criticality_tier_override == tier


class TestTechDebtUpdateValidation:
    def test_valid_status(self):
        m = TechDebtUpdateIn(status="approved")
        assert m.status == "approved"

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            TechDebtUpdateIn(status="archived")

    def test_all_valid_statuses_accepted(self):
        for s in VALID_STATUSES:
            m = TechDebtUpdateIn(status=s)
            assert m.status == s

    def test_rejection_reason_optional_at_model_level(self):
        # The handler enforces "required when rejecting" — the model itself
        # just carries the field so a reject without a reason can be validated once.
        m = TechDebtUpdateIn(status="rejected")
        assert m.rejection_reason is None
