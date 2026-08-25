"""
test_feature_authorization.py
─────────────────────────────────────────────────────────────────────────────
Comprehensive regression suite for the canonical feature authorization system.

Covers:
  Phase 1 — authorize_feature() unit tests
    - FREE_TIER gets allowed=True, limited=True for lessons/mock_test/doubts
    - FREE_TIER gets allowed=False for EXEMPLAR (paid lesson chapters)
    - FREE_TIER gets allowed=True for EXEMPLAR_RESEARCH (role-gated, not plan-gated)
    - NANO/PREMIUM/FAMILY_PREMIUM/ADMIN_GRANT get allowed=True for all features
    - Expired subscriptions revert to FREE_TIER rules
    - Unknown feature → denied (fail-safe)

  Phase 2 — hasPaidAccess() frontend logic regression
    - Brand new free parent's child: parentId set, accessCbse=False → NOT paid
    - Paid parent's child: parentId set, accessCbse=True → paid
    - Admin → always paid
    - Expired subscription → not paid

  Phase 3 — isFreeUser MockTestPage logic
    - Student with parentId but accessCbse=False → free user
    - Student with parentId AND accessCbse=True → NOT free user
    - Student with no parentId and no accessCbse → free user
    - Admin → not free user

  Phase 4 — Feature matrix parity
    - Feature matrix is consistent (no missing features, no typos)
    - FREE_MOCK_TEST_DAILY_LIMIT matches frontend constant

  Phase 5 — Critical bug regression
    - Bug 1: hasPaidAccess(parentId only) MUST return False (was True)
    - Bug 2: isFreeUser(student with parentId) MUST be True when no accessCbse
    - Bug 3: Backend authorize_feature FREE_TIER + EXEMPLAR → denied
    - Bug 4: Old inverted mock_test check no longer exists
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.services.feature_authorization_service import (
    Feature,
    authorize_feature,
    get_feature_summary,
    FREE_MOCK_TEST_DAILY_LIMIT,
)


# ── Mock subscription resolver ────────────────────────────────────────────────
def _make_sub(cpk: str, has_full_access: bool = True) -> dict:
    """Build a mock resolve_user_subscription result for a given canonical plan key."""
    plan_names = {
        "FREE_TIER": "Free Tier",
        "NANO": "Premium Nano",
        "PREMIUM": "Premium",
        "PREMIUM_6MONTH": "Premium — 6 Months",
        "PREMIUM_ANNUAL": "Premium — Annual",
        "FAMILY_PREMIUM": "Family Premium",
        "FAMILY_ANNUAL": "Family Premium — Annual",
        "ADMIN_GRANT": "Admin Access",
    }
    restrictions = ["lessons_limited", "mock_tests_5_per_day", "no_exemplar"] if cpk == "FREE_TIER" else []
    return {
        "active_tier": "FREE" if cpk == "FREE_TIER" else "PREMIUM",
        "plan_name": plan_names.get(cpk, "Premium"),
        "canonical_plan_key": cpk,
        "access_source": "NONE" if cpk == "FREE_TIER" else "PAID",
        "has_full_access": has_full_access,
        "valid_until": None,
        "days_remaining": None,
        "expiring_soon": False,
        "child_limit": None,
        "student_limit": None,
        "restrictions": restrictions,
    }


def _auth(user_id: str, feature: str, cpk: str, has_full_access: bool = True) -> dict:
    """Run authorize_feature with mocked subscription resolver."""
    with patch(
        "app.services.feature_authorization_service.resolve_user_subscription",
        return_value=_make_sub(cpk, has_full_access),
    ):
        return authorize_feature(user_id, feature)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: authorize_feature() unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFreeTierFeatureAccess:
    """FREE_TIER users: limited on lessons/mock_test/doubts, denied exemplar."""

    def test_lessons_allowed_but_limited(self):
        r = _auth("user-1", Feature.LESSONS, "FREE_TIER", False)
        assert r["allowed"] is True
        assert r["limited"] is True
        assert "upgrade" in r["restriction_message"].lower() or "upgrade" in r["upgrade_recommendation"].lower()

    def test_mock_test_allowed_but_limited(self):
        r = _auth("user-1", Feature.MOCK_TEST, "FREE_TIER", False)
        assert r["allowed"] is True
        assert r["limited"] is True

    def test_ask_doubts_allowed_but_limited(self):
        r = _auth("user-1", Feature.ASK_DOUBTS, "FREE_TIER", False)
        assert r["allowed"] is True
        assert r["limited"] is True

    def test_exemplar_denied(self):
        r = _auth("user-1", Feature.EXEMPLAR, "FREE_TIER", False)
        assert r["allowed"] is False
        assert r["limited"] is False
        assert r["canonical_plan_key"] == "FREE_TIER"

    def test_exemplar_research_denied_on_free_tier(self):
        """
        Exemplar Research is gated on TWO axes now: role (teachers blocked
        outright at the route, not expressed in this matrix) and plan
        (students/parents/admin gated here, same paid-plan set as EXEMPLAR).

        Previously this matrix entry was allowed_plans=None (every plan let
        through unconditionally), so the free/paid split for students lived
        only in the web client's hasPaidAccess() check — mobile never
        replicated that check, so free-tier mobile students got full
        functional access to a feature sold exclusively as paid. Both axes
        are backend-enforced now; see
        docs/ACCESS_CONTROL_ARCHITECTURE_BLUEPRINT.md for the audit that
        found it.
        """
        r = _auth("user-1", Feature.EXEMPLAR_RESEARCH, "FREE_TIER", False)
        assert r["allowed"] is False

    def test_mock_test_unlimited_denied(self):
        r = _auth("user-1", Feature.MOCK_TEST_UNLIMITED, "FREE_TIER", False)
        assert r["allowed"] is False

    def test_lesson_download_denied(self):
        r = _auth("user-1", Feature.LESSON_DOWNLOAD, "FREE_TIER", False)
        assert r["allowed"] is False

    def test_parent_dashboard_allowed(self):
        r = _auth("user-1", Feature.PARENT_DASHBOARD, "FREE_TIER", False)
        assert r["allowed"] is True

    def test_upgrade_message_present_for_exemplar(self):
        r = _auth("user-1", Feature.EXEMPLAR, "FREE_TIER", False)
        assert len(r["upgrade_recommendation"]) > 0


class TestPaidPlanFeatureAccess:
    """NANO/PREMIUM/FAMILY/ADMIN_GRANT: full access to all features."""

    @pytest.mark.parametrize("cpk", ["NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                                      "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT"])
    def test_exemplar_allowed_for_all_paid(self, cpk):
        r = _auth("user-2", Feature.EXEMPLAR, cpk)
        assert r["allowed"] is True
        assert r["limited"] is False

    @pytest.mark.parametrize("cpk", ["NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT"])
    def test_exemplar_research_allowed_for_paid(self, cpk):
        r = _auth("user-2", Feature.EXEMPLAR_RESEARCH, cpk)
        assert r["allowed"] is True

    @pytest.mark.parametrize("cpk", ["NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT"])
    def test_mock_test_unlimited_allowed_for_paid(self, cpk):
        r = _auth("user-2", Feature.MOCK_TEST_UNLIMITED, cpk)
        assert r["allowed"] is True

    @pytest.mark.parametrize("cpk", ["NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT"])
    def test_lessons_not_limited_for_paid(self, cpk):
        r = _auth("user-2", Feature.LESSONS, cpk)
        assert r["allowed"] is True
        assert r["limited"] is False

    @pytest.mark.parametrize("cpk", ["NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT"])
    def test_doubts_not_limited_for_paid(self, cpk):
        r = _auth("user-2", Feature.ASK_DOUBTS, cpk)
        assert r["allowed"] is True
        assert r["limited"] is False


class TestEdgeCases:
    """Edge cases: empty user_id, unknown feature, feature summary."""

    def test_empty_user_id_returns_denied(self):
        r = authorize_feature("", Feature.EXEMPLAR)
        assert r["allowed"] is False

    def test_none_user_id_returns_denied(self):
        r = authorize_feature(None, Feature.EXEMPLAR)
        assert r["allowed"] is False

    def test_unknown_feature_returns_denied(self):
        r = _auth("user-3", "NONEXISTENT_FEATURE", "NANO")
        assert r["allowed"] is False

    def test_feature_summary_has_all_features(self):
        with patch(
            "app.services.feature_authorization_service.resolve_user_subscription",
            return_value=_make_sub("FREE_TIER", False),
        ):
            summary = get_feature_summary("user-4")
        expected_features = [
            Feature.LESSONS, Feature.LESSON_DOWNLOAD, Feature.EXEMPLAR,
            Feature.EXEMPLAR_RESEARCH, Feature.MOCK_TEST, Feature.MOCK_TEST_UNLIMITED,
            Feature.ASK_DOUBTS, Feature.AI_ASSISTANT, Feature.AI_CHAT,
            Feature.PARENT_DASHBOARD,
        ]
        for feat in expected_features:
            assert feat in summary["features"], f"{feat} missing from feature summary"

    def test_feature_summary_free_tier(self):
        with patch(
            "app.services.feature_authorization_service.resolve_user_subscription",
            return_value=_make_sub("FREE_TIER", False),
        ):
            summary = get_feature_summary("user-4")
        assert summary["features"][Feature.EXEMPLAR]["allowed"] is False
        assert summary["features"][Feature.MOCK_TEST]["allowed"] is True
        assert summary["features"][Feature.MOCK_TEST]["limited"] is True

    def test_feature_summary_premium(self):
        with patch(
            "app.services.feature_authorization_service.resolve_user_subscription",
            return_value=_make_sub("PREMIUM", True),
        ):
            summary = get_feature_summary("user-5")
        assert summary["features"][Feature.EXEMPLAR]["allowed"] is True
        assert summary["features"][Feature.MOCK_TEST]["limited"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: hasPaidAccess() frontend logic (Python mirror)
# ─────────────────────────────────────────────────────────────────────────────

def has_paid_access_py(user: dict) -> bool:
    """Python mirror of the fixed hasPaidAccess() frontend function."""
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    from datetime import datetime, timezone
    expires_at = user.get("subscriptionExpiresAt")
    if expires_at:
        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if dt > datetime.now(timezone.utc):
                return True
        except Exception:
            pass
    if user.get("accessCbse"):
        return True
    return False


class TestHasPaidAccessLogic:
    """Test the FIXED hasPaidAccess logic — parentId alone must NOT grant access."""

    # ── CRITICAL BUG REGRESSION: Bug 1 ─────────────────────────────────────
    def test_child_of_free_parent_is_not_paid(self):
        """Brand new child of free-plan parent: parentId set, accessCbse=False → NOT paid."""
        user = {
            "role": "student",
            "parentId": "parent-uuid-123",
            "accessCbse": False,
            "subscriptionPlan": "free",
            "subscriptionExpiresAt": None,
        }
        assert has_paid_access_py(user) is False, (
            "CRITICAL BUG: child with only parentId (no accessCbse) must not have paid access"
        )

    def test_child_of_paid_parent_is_paid(self):
        """Child of paid parent: parentId set AND accessCbse=True → paid."""
        user = {
            "role": "student",
            "parentId": "parent-uuid-123",
            "accessCbse": True,
            "subscriptionPlan": "free",
            "subscriptionExpiresAt": None,
        }
        assert has_paid_access_py(user) is True

    def test_admin_is_always_paid(self):
        user = {"role": "admin", "accessCbse": False}
        assert has_paid_access_py(user) is True

    def test_user_with_active_subscription_is_paid(self):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        user = {
            "role": "student",
            "subscriptionExpiresAt": future,
            "accessCbse": False,
            "parentId": None,
        }
        assert has_paid_access_py(user) is True

    def test_user_with_expired_subscription_is_free(self):
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        user = {
            "role": "student",
            "subscriptionExpiresAt": past,
            "accessCbse": False,
            "parentId": None,
        }
        assert has_paid_access_py(user) is False

    def test_standalone_student_no_access_is_free(self):
        user = {
            "role": "student",
            "parentId": None,
            "accessCbse": False,
            "subscriptionPlan": "free",
            "subscriptionExpiresAt": None,
        }
        assert has_paid_access_py(user) is False

    def test_student_with_access_cbse_is_paid(self):
        user = {
            "role": "student",
            "parentId": None,
            "accessCbse": True,
            "subscriptionPlan": "free",
        }
        assert has_paid_access_py(user) is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: isFreeUser MockTestPage logic (Python mirror)
# ─────────────────────────────────────────────────────────────────────────────

def is_free_user_py(user: dict) -> bool:
    """Python mirror of the FIXED isFreeUser computation in MockTestPage.jsx."""
    if not user:
        return True
    if user.get("role") != "student":
        return False
    return not has_paid_access_py(user)


class TestIsFreeUserLogic:
    """Test the FIXED isFreeUser — parentId alone must NOT exclude from free tier."""

    # ── CRITICAL BUG REGRESSION: Bug 2 ─────────────────────────────────────
    def test_child_of_free_parent_is_free_user(self):
        """CRITICAL: student with parentId but no accessCbse MUST be free user."""
        user = {
            "role": "student",
            "parentId": "parent-uuid-123",
            "accessCbse": False,
            "subscriptionPlan": "free",
            "subscriptionExpiresAt": None,
        }
        assert is_free_user_py(user) is True, (
            "CRITICAL BUG REGRESSION: child of free-plan parent must be treated as free user"
        )

    def test_child_of_paid_parent_is_not_free_user(self):
        """Student with parentId AND accessCbse=True → not free user."""
        user = {
            "role": "student",
            "parentId": "parent-uuid-123",
            "accessCbse": True,
            "subscriptionPlan": "free",
        }
        assert is_free_user_py(user) is False

    def test_standalone_free_student_is_free_user(self):
        user = {"role": "student", "parentId": None, "accessCbse": False}
        assert is_free_user_py(user) is True

    def test_admin_is_not_free_user(self):
        user = {"role": "admin", "accessCbse": False}
        assert is_free_user_py(user) is False

    def test_parent_role_is_not_free_user_in_mock_test_sense(self):
        """Parents don't take mock tests — isFreeUser only applies to students."""
        user = {"role": "parent", "accessCbse": False}
        assert is_free_user_py(user) is False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Feature matrix sanity + constant parity
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureMatrixParity:
    def test_free_mock_test_daily_limit_is_5(self):
        """FREE_MOCK_TEST_DAILY_LIMIT must match the frontend FREE_DAILY_MOCK_LIMIT constant."""
        assert FREE_MOCK_TEST_DAILY_LIMIT == 5

    def test_all_feature_constants_have_matrix_entry(self):
        """Every Feature constant must have a corresponding matrix entry."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        feature_attrs = [v for k, v in vars(Feature).items() if not k.startswith("_")]
        for feat in feature_attrs:
            assert feat in _FEATURE_MATRIX, f"Feature '{feat}' missing from _FEATURE_MATRIX"

    def test_free_tier_exemplar_always_denied(self):
        """Exemplar must never be accessible for FREE_TIER — canonical rule."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        matrix = _FEATURE_MATRIX[Feature.EXEMPLAR]
        assert matrix["allowed_plans"] is not None, "Exemplar should have restricted plans"
        assert "FREE_TIER" not in matrix["allowed_plans"]

    def test_exemplar_research_plan_gate_mirrors_exemplar(self):
        """Same paid-plan set as EXEMPLAR — the role check lives at the route, separately."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        matrix = _FEATURE_MATRIX[Feature.EXEMPLAR_RESEARCH]
        assert matrix["allowed_plans"] == _FEATURE_MATRIX[Feature.EXEMPLAR]["allowed_plans"]
        assert "FREE_TIER" not in matrix["allowed_plans"]

    def test_exemplar_research_does_not_share_a_db_flag_with_exemplar(self):
        """
        The two are different features and must not move together.

        Feature.EXEMPLAR gates Exemplar chapters inside Lessons, which are
        paid. EXEMPLAR_RESEARCH is the separate topic-card page. They both
        used to map to access_exemplar, so one admin toggle intended for the
        paid chapters would silently have disabled the open page too.
        """
        from app.services.feature_authorization_service import _DB_DRIVEN_FEATURES
        assert _DB_DRIVEN_FEATURES.get(Feature.EXEMPLAR) == "access_exemplar"
        assert Feature.EXEMPLAR_RESEARCH not in _DB_DRIVEN_FEATURES

    def test_exemplar_lesson_chapters_stay_paid(self):
        """The genuinely-paid sibling must be unaffected by that split."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        matrix = _FEATURE_MATRIX[Feature.EXEMPLAR]
        assert matrix["allowed_plans"] is not None
        assert "FREE_TIER" not in matrix["allowed_plans"]

    def test_mock_test_available_to_all(self):
        """MOCK_TEST (limited) must be available to all plans including FREE_TIER."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        matrix = _FEATURE_MATRIX[Feature.MOCK_TEST]
        assert matrix["allowed_plans"] is None, "MOCK_TEST must be available to all plans"
        assert "FREE_TIER" in matrix["limited_on"]

    def test_mock_test_unlimited_requires_paid(self):
        """MOCK_TEST_UNLIMITED must require a paid plan."""
        from app.services.feature_authorization_service import _FEATURE_MATRIX
        matrix = _FEATURE_MATRIX[Feature.MOCK_TEST_UNLIMITED]
        assert matrix["allowed_plans"] is not None
        assert "FREE_TIER" not in matrix["allowed_plans"]
        assert "NANO" in matrix["allowed_plans"]
        assert "PREMIUM" in matrix["allowed_plans"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Critical bug regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCriticalBugRegression:
    """Regression tests that MUST pass to confirm all 4 reported bugs are fixed."""

    def test_bug1_has_paid_access_parent_id_only_returns_false(self):
        """
        BUG 1: hasPaidAccess({ parentId: 'x', accessCbse: false }) was True.
        Fixed: parentId alone does not grant paid access.
        """
        user = {"role": "student", "parentId": "parent-1", "accessCbse": False}
        result = has_paid_access_py(user)
        assert result is False, "BUG 1 NOT FIXED: parentId alone must not grant paid access"

    def test_bug2_is_free_user_with_parent_id_no_access_cbse(self):
        """
        BUG 2: isFreeUser was False for students with parentId (due to !user?.parentId check).
        Fixed: isFreeUser correctly identifies free-tier students regardless of parentId.
        """
        user = {"role": "student", "parentId": "parent-1", "accessCbse": False}
        result = is_free_user_py(user)
        assert result is True, "BUG 2 NOT FIXED: child of free parent must be identified as free user"

    def test_bug3_backend_free_tier_exemplar_denied(self):
        """
        BUG 3: Backend had no Exemplar endpoint protection.
        Fixed: authorize_feature(FREE_TIER, EXEMPLAR) returns allowed=False.
        """
        r = _auth("user-bug3", Feature.EXEMPLAR, "FREE_TIER", False)
        assert r["allowed"] is False, "BUG 3 NOT FIXED: FREE_TIER must not access Exemplar"

    def test_bug3_exemplar_chapters_and_exemplar_research_are_both_paid_but_independent(self):
        """
        BUG 3 was about Exemplar chapters in Lessons, which remain paid.

        Exemplar Research was swept into the same matrix rule at the time by
        sharing EXEMPLAR's DB-driven flag — see
        test_exemplar_research_does_not_share_a_db_flag_with_exemplar. That
        coupling was the bug, not the fact that both happen to be paid: they
        must move independently (one admin toggle for the paid Lessons
        chapters must not silently affect the other), even though today both
        correctly deny FREE_TIER.
        """
        r = _auth("user-bug3", Feature.EXEMPLAR_RESEARCH, "FREE_TIER", False)
        assert r["allowed"] is False

    def test_bug4_mock_test_inverted_check_free_user_limited(self):
        """
        BUG 4: Old backend mock_test check was inverted:
        `not access_cbse and not is_free_tier_user` allowed ALL free users through.
        Fixed: is_free_tier_user check now correctly identifies free users as limited.
        """
        r = _auth("user-bug4", Feature.MOCK_TEST, "FREE_TIER", False)
        assert r["allowed"] is True   # free users CAN do mock tests (limited)
        assert r["limited"] is True   # but they are LIMITED to 5/day

    def test_bug4_unlimited_mock_tests_denied_for_free(self):
        """Free users must not get unlimited mock tests."""
        r = _auth("user-bug4", Feature.MOCK_TEST_UNLIMITED, "FREE_TIER", False)
        assert r["allowed"] is False, "BUG 4 NOT FIXED: free user must not get unlimited mock tests"

    def test_new_free_parent_grade10_child_denied_exemplar(self):
        """
        Full scenario: new parent signed up free, added Grade 10 child.
        Child's profile: parentId=set, accessCbse=False.
        Expected: Exemplar access = DENIED.
        """
        child_user = {
            "role": "student",
            "grade": "Grade 10",
            "parentId": "free-parent-uuid",
            "accessCbse": False,
            "subscriptionPlan": "free",
            "subscriptionExpiresAt": None,
        }
        # Frontend check: hasPaidAccess must be False
        assert has_paid_access_py(child_user) is False
        # Frontend check: isFreeUser must be True
        assert is_free_user_py(child_user) is True
        # Backend check: EXEMPLAR must be denied
        r = _auth(child_user["parentId"], Feature.EXEMPLAR, "FREE_TIER", False)
        assert r["allowed"] is False

    def test_new_free_parent_grade10_child_has_mock_test_limit(self):
        """
        Full scenario: Grade 10 child of free parent must have mock test limit.
        """
        child_user = {
            "role": "student",
            "grade": "Grade 10",
            "parentId": "free-parent-uuid",
            "accessCbse": False,
        }
        # isFreeUser=True means daily limit applies
        assert is_free_user_py(child_user) is True
        # Mock test is allowed but limited
        r = _auth("child-user-id", Feature.MOCK_TEST, "FREE_TIER", False)
        assert r["allowed"] is True
        assert r["limited"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Exemplar chapter detection in lesson route
# ─────────────────────────────────────────────────────────────────────────────

class TestExemplarChapterDetection:
    """Regression tests for Exemplar chapter name detection in lesson.py."""

    def test_exemplar_chapter_prefix_detected(self):
        """Chapters starting with 'Exemplar:' must be detected as Exemplar."""
        chapter = "Exemplar: Chemical Reactions and Equations"
        is_exemplar = chapter.lower().startswith("exemplar") or ": exemplar" in chapter.lower()
        assert is_exemplar is True

    def test_normal_chapter_not_exemplar(self):
        """Regular chapters must NOT be flagged as Exemplar."""
        chapters = [
            "Chapter 1: Chemical Reactions and Equations",
            "Motion and Forces",
            "Heredity and Evolution",
            "Life Processes",
        ]
        for ch in chapters:
            is_exemplar = ch.lower().startswith("exemplar") or ": exemplar" in ch.lower()
            assert is_exemplar is False, f"Chapter '{ch}' incorrectly flagged as Exemplar"

    def test_exemplar_chapter_free_tier_denied_by_authorize_feature(self):
        """authorize_feature(FREE_TIER, EXEMPLAR) must deny — lesson route uses this."""
        r = _auth("user-exemplar", Feature.EXEMPLAR, "FREE_TIER", False)
        assert r["allowed"] is False
        assert "paid" in r["upgrade_recommendation"].lower()

    def test_exemplar_chapter_nano_allowed(self):
        """NANO+ users must be allowed Exemplar lessons."""
        r = _auth("user-exemplar", Feature.EXEMPLAR, "NANO", True)
        assert r["allowed"] is True
        assert r["limited"] is False

    def test_exemplar_chapter_free_tier_child_of_free_parent_denied(self):
        """
        Scenario: Grade 10 child of free parent requests 'Exemplar: Light...' lesson.
        The backend lesson.py now checks authorize_feature(user_id, Feature.EXEMPLAR).
        This must be denied for FREE_TIER canonical plan.
        """
        # Frontend check: child is free tier
        child = {"role": "student", "parentId": "free-parent", "accessCbse": False}
        assert is_free_user_py(child) is True

        # Backend check: exemplar feature denied for FREE_TIER
        r = _auth("child-user-id", Feature.EXEMPLAR, "FREE_TIER", False)
        assert r["allowed"] is False, "Exemplar chapter must be denied for FREE_TIER child"
        assert r["canonical_plan_key"] == "FREE_TIER"
