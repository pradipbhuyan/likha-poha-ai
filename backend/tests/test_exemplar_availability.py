"""
test_exemplar_availability.py
══════════════════════════════
Covers the Exemplar Research availability lookup that lets the topic grid mark
cards with no authored content.

168 topic cards ship in ExemplarResearchPage.jsx against 132 authored
explanations. 36 of that gap can never close — NCERT never published Exemplar
books for three of the fourteen sections — so those cards are permanently
unfillable rather than pending. Before this, a student discovered that one
click at a time, several dead cards in a row in an affected section.

Run with:
    cd backend && python -m pytest tests/test_exemplar_availability.py -v
"""

import pytest
from fastapi.routing import APIRoute

from app.main import app
from app.services.auth_service import get_current_user
from app.services.exemplar_research_bank_service import (
    get_available_topics,
    get_exemplar_explanation,
)


class TestAvailabilityAgreesWithTheExplainPath:
    """
    The grid's answer must match what a click actually does.

    A cheaper existence check that disagreed would be worse than no check: it
    would either grey out working cards or leave dead ones looking live.
    """

    @pytest.mark.parametrize("grade,subject,topic", [
        ("Grade 8", "Maths", "Squares and Square Roots"),
        ("Grade 10", "Science", "Definitely Not A Real Topic"),
        ("Grade 12", "Physics", "Also Not Real"),
    ])
    def test_matches_get_exemplar_explanation(self, grade, subject, topic):
        expected = get_exemplar_explanation(grade, subject, topic) is not None
        assert get_available_topics(grade, subject, [topic])[topic] is expected

    def test_authored_topic_reports_available(self):
        result = get_available_topics("Grade 8", "Maths", ["Squares and Square Roots"])
        assert result["Squares and Square Roots"] is True

    def test_unauthored_topic_reports_unavailable(self):
        result = get_available_topics("Grade 8", "Maths", ["No Such Topic Exists Here"])
        assert result["No Such Topic Exists Here"] is False


class TestAvailabilityShape:

    def test_every_topic_asked_about_is_answered(self):
        topics = ["Squares and Square Roots", "Nonsense One", "Nonsense Two"]
        result = get_available_topics("Grade 8", "Maths", topics)
        assert set(result) == set(topics)
        assert all(isinstance(v, bool) for v in result.values())

    def test_empty_topic_list_is_fine(self):
        assert get_available_topics("Grade 8", "Maths", []) == {}

    def test_unknown_grade_or_subject_reports_all_unavailable(self):
        result = get_available_topics("Grade 99", "Astrology", ["Anything"])
        assert result == {"Anything": False}


class TestAvailabilityRoute:

    def _route(self):
        for r in app.routes:
            if isinstance(r, APIRoute) and r.path == "/api/teacher/exemplar-research/availability":
                return r
        raise AssertionError("availability route is not registered")

    def test_requires_authentication(self):
        guards = set()

        def walk(dependant):
            if dependant.call is not None:
                guards.add(dependant.call)
            for sub in dependant.dependencies:
                walk(sub)

        for sub in self._route().dependant.dependencies:
            walk(sub)

        assert get_current_user in guards, (
            "the availability route must require authentication, matching the "
            "explain route it describes"
        )

    def test_topic_list_is_capped(self, monkeypatch):
        """A malformed or hostile request must not walk the whole bank."""
        from app.routes import teacher as teacher_route
        from app.routes.teacher import (
            ExemplarAvailabilityRequest,
            get_exemplar_research_availability,
        )

        # Role check now needs a real profile lookup — a student profile
        # passes straight through to the availability logic under test.
        # require_feature() also needs a real plan lookup (a fake user id
        # fails DB resolution and defaults to FREE_TIER, now correctly
        # denied) — stub it out since this test is about the topic cap, not
        # entitlement.
        monkeypatch.setattr(teacher_route, "get_user_profile", lambda uid: {"role": "student"})
        monkeypatch.setattr(teacher_route, "require_feature", lambda *a, **k: None)

        result = get_exemplar_research_availability(
            ExemplarAvailabilityRequest(
                grade="Grade 8", subject="Maths",
                topics=[f"topic-{i}" for i in range(500)],
            ),
            user=type("U", (), {"id": "test-user"})(),
        )
        assert len(result["available"]) == 200

    def test_blank_and_non_string_topics_are_dropped(self, monkeypatch):
        from app.routes import teacher as teacher_route
        from app.routes.teacher import (
            ExemplarAvailabilityRequest,
            get_exemplar_research_availability,
        )

        monkeypatch.setattr(teacher_route, "get_user_profile", lambda uid: {"role": "student"})
        monkeypatch.setattr(teacher_route, "require_feature", lambda *a, **k: None)

        result = get_exemplar_research_availability(
            ExemplarAvailabilityRequest(
                grade="Grade 8", subject="Maths",
                topics=["Squares and Square Roots", "", "   "],
            ),
            user=type("U", (), {"id": "test-user"})(),
        )
        assert list(result["available"]) == ["Squares and Square Roots"]

    def test_teacher_is_blocked_from_availability_check(self, monkeypatch):
        """Exemplar Research is a student-only feature — a teacher calling
        the availability endpoint must get the same 403 as the explain route."""
        from fastapi import HTTPException
        from app.routes import teacher as teacher_route
        from app.routes.teacher import (
            ExemplarAvailabilityRequest,
            get_exemplar_research_availability,
        )

        monkeypatch.setattr(teacher_route, "get_user_profile", lambda uid: {"role": "teacher"})

        with pytest.raises(HTTPException) as exc_info:
            get_exemplar_research_availability(
                ExemplarAvailabilityRequest(
                    grade="Grade 8", subject="Maths",
                    topics=["Squares and Square Roots"],
                ),
                user=type("U", (), {"id": "test-teacher"})(),
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["feature"] == "EXEMPLAR_RESEARCH"

    def test_free_tier_student_is_blocked_from_availability_check(self, monkeypatch):
        """
        Exemplar Research is a paid, student-only feature — a free-tier
        student must be denied here too, not just teachers.

        Previously this route never checked student plan at all (only role),
        so a free-tier student's request sailed through unconditionally —
        the actual open door behind mobile's free-tier leak (mobile's own
        client-side entitlement flag was separately broken, but even a
        correct client would have had nothing backend-side stopping a direct
        API call). See docs/ACCESS_CONTROL_ARCHITECTURE_BLUEPRINT.md.
        """
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.routes import teacher as teacher_route
        from app.routes.teacher import (
            ExemplarAvailabilityRequest,
            get_exemplar_research_availability,
        )

        monkeypatch.setattr(teacher_route, "get_user_profile", lambda uid: {"role": "student"})

        with patch(
            "app.services.feature_authorization_service.resolve_user_subscription",
            return_value={"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier",
                          "has_full_access": False, "restrictions": []},
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_exemplar_research_availability(
                    ExemplarAvailabilityRequest(
                        grade="Grade 8", subject="Maths",
                        topics=["Squares and Square Roots"],
                    ),
                    user=type("U", (), {"id": "test-free-student"})(),
                )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["feature"] == "EXEMPLAR_RESEARCH"

    def test_paid_student_is_allowed_through_availability_check(self, monkeypatch):
        """The other half of the same gate — a paid student must not be denied."""
        from unittest.mock import patch
        from app.routes import teacher as teacher_route
        from app.routes.teacher import (
            ExemplarAvailabilityRequest,
            get_exemplar_research_availability,
        )

        monkeypatch.setattr(teacher_route, "get_user_profile", lambda uid: {"role": "student"})

        with patch(
            "app.services.feature_authorization_service.resolve_user_subscription",
            return_value={"canonical_plan_key": "PREMIUM", "plan_name": "Premium",
                          "has_full_access": True, "restrictions": []},
        ):
            result = get_exemplar_research_availability(
                ExemplarAvailabilityRequest(
                    grade="Grade 8", subject="Maths",
                    topics=["Squares and Square Roots"],
                ),
                user=type("U", (), {"id": "test-paid-student"})(),
            )
        assert result["available"] == {"Squares and Square Roots": True}


def test_the_gap_this_exists_for_is_real():
    """
    Sanity check on the premise: the bank genuinely holds fewer explanations
    than the UI has cards, so the grid needs to say which is which.
    """
    from pathlib import Path

    bank = Path(__file__).resolve().parents[1] / "app" / "data" / "exemplar_research_bank"
    authored = len(list(bank.rglob("*.json")))

    assert authored > 0, "bank is empty — availability would mark everything dead"
    assert authored < 168, (
        "if every one of the 168 cards is authored this signalling is moot; "
        "revisit whether the grid still needs it"
    )
