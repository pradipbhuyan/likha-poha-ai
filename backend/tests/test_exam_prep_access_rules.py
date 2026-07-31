"""
test_exam_prep_access_rules.py
==============================
Comprehensive tests for Grade 11/12 Exam Prep Center access rules:

A. Feature authorization matrix — EXAM_PREP_CENTER / EXAM_PREP_CONTENT
B. Stream-based exam eligibility (JEE→PCM/PCMB, NEET→PCB/PCMB)
C. check_exam_prep_content_access — subscription gate
D. get_access_check_response — canonical frontend response builder

These complement the existing test_exam_prep.py tests.
"""

import pytest
from unittest.mock import patch


# ─────────────────────────────────────────────────────────────────────────────
# A. Feature Authorization Matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureMatrixConstants:
    def test_feature_constants_exist(self):
        from app.services.feature_authorization_service import Feature
        assert Feature.EXAM_PREP_CENTER == "EXAM_PREP_CENTER"
        assert Feature.EXAM_PREP_CONTENT == "EXAM_PREP_CONTENT"

    def test_exam_prep_center_in_matrix(self):
        from app.services.feature_authorization_service import _FEATURE_MATRIX, Feature
        assert Feature.EXAM_PREP_CENTER in _FEATURE_MATRIX
        m = _FEATURE_MATRIX[Feature.EXAM_PREP_CENTER]
        assert m["allowed_plans"] is None        # page visible to all
        assert "FREE_TIER" in m["limited_on"]    # free → preview only
        assert "NANO" in m["limited_on"]          # nano → preview only

    def test_exam_prep_content_premium_only(self):
        from app.services.feature_authorization_service import _FEATURE_MATRIX, Feature
        m = _FEATURE_MATRIX[Feature.EXAM_PREP_CONTENT]
        allowed = m["allowed_plans"]
        assert "NANO" not in allowed       # Nano explicitly excluded per spec
        assert "FREE_TIER" not in allowed
        for plan in ("PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                     "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT"):
            assert plan in allowed, f"{plan} must be in EXAM_PREP_CONTENT allowed_plans"

    def test_exam_prep_content_has_upgrade_message(self):
        from app.services.feature_authorization_service import _FEATURE_MATRIX, Feature
        msg = _FEATURE_MATRIX[Feature.EXAM_PREP_CONTENT]["upgrade_message"]
        assert len(msg) > 10


class TestAuthorizeFeatureExamPrep:
    """Test authorize_feature() for EXAM_PREP_CENTER and EXAM_PREP_CONTENT."""

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_free_center_allowed_limited(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CENTER)
        assert r["allowed"] is True
        assert r["limited"] is True

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_nano_center_allowed_limited(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "NANO", "plan_name": "Nano", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CENTER)
        assert r["allowed"] is True
        assert r["limited"] is True

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_premium_center_allowed_not_limited(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "PREMIUM", "plan_name": "Premium", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CENTER)
        assert r["allowed"] is True
        assert r["limited"] is False

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_free_content_denied(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is False

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_nano_content_denied(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "NANO", "plan_name": "Nano", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is False  # Nano explicitly excluded

    @patch("app.services.feature_authorization_service._get_plan_feature_flag", return_value=True)
    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_premium_content_allowed(self, mock_sub, _mock_flag):
        mock_sub.return_value = {"canonical_plan_key": "PREMIUM", "plan_name": "Premium", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is True
        assert r["limited"] is False

    @patch("app.services.feature_authorization_service._get_plan_feature_flag", return_value=True)
    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_family_premium_content_allowed(self, mock_sub, _mock_flag):
        mock_sub.return_value = {"canonical_plan_key": "FAMILY_PREMIUM", "plan_name": "Family Premium", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is True

    @patch("app.services.feature_authorization_service._get_plan_feature_flag", return_value=True)
    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_admin_grant_content_allowed(self, mock_sub, _mock_flag):
        mock_sub.return_value = {"canonical_plan_key": "ADMIN_GRANT", "plan_name": "Admin", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is True

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_expired_premium_resolves_to_free_denied(self, mock_sub):
        # Subscription resolver handles expiry; expired plans resolve as FREE_TIER
        mock_sub.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier (expired)", "has_full_access": False}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXAM_PREP_CONTENT)
        assert r["allowed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# B. Stream-based exam eligibility
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildExamEligibility:
    def test_pcm_jee_eligible_neet_not(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCM")
        assert e["jee_main"]["eligible"] is True
        assert e["neet_ug"]["eligible"] is False

    def test_pcb_neet_eligible_jee_not(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCB")
        assert e["jee_main"]["eligible"] is False
        assert e["neet_ug"]["eligible"] is True

    def test_pcmb_both_eligible(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCMB")
        assert e["jee_main"]["eligible"] is True
        assert e["neet_ug"]["eligible"] is True

    def test_commerce_neither_eligible(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("Commerce")
        assert e["jee_main"]["eligible"] is False
        assert e["neet_ug"]["eligible"] is False

    def test_humanities_neither_eligible(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("Humanities")
        assert e["jee_main"]["eligible"] is False
        assert e["neet_ug"]["eligible"] is False

    def test_none_stream_neither_eligible(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility(None)
        assert e["jee_main"]["eligible"] is False
        assert e["neet_ug"]["eligible"] is False

    def test_cuet_now_active_for_all_streams(self):
        """CUET UG is now fully active — eligible for all streams, no coming_soon flag."""
        from app.services.exam_prep_service import build_exam_eligibility
        for stream in ("PCM", "PCB", "PCMB", "Commerce", "Humanities", None):
            e = build_exam_eligibility(stream)
            assert e["cuet_ug"]["eligible"] is True, f"CUET should be eligible for stream={stream}"
            assert "coming_soon" not in e["cuet_ug"], f"CUET should not have coming_soon for stream={stream}"

    def test_ineligible_jee_has_math_reason(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCB")
        assert "Mathematics" in e["jee_main"]["reason"]

    def test_ineligible_neet_has_biology_reason(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCM")
        assert "Biology" in e["neet_ug"]["reason"]

    def test_eligible_jee_empty_reason(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("PCM")
        assert e["jee_main"]["reason"] == ""

    def test_lowercase_stream_normalized(self):
        from app.services.exam_prep_service import build_exam_eligibility
        e = build_exam_eligibility("pcm")  # lowercase
        # Should normalize to uppercase and match PCM
        assert e["jee_main"]["eligible"] is True

    def test_global_standardised_tests_eligible_for_all_streams(self):
        """SAT/IELTS/TOEFL have no stream prerequisite — eligible regardless of academic stream."""
        from app.services.exam_prep_service import build_exam_eligibility
        for stream in ("PCM", "PCB", "PCMB", "Commerce", "Humanities", None):
            e = build_exam_eligibility(stream)
            for exam_type in ("sat", "ielts", "toefl_ibt"):
                assert e[exam_type]["eligible"] is True, f"{exam_type} should be eligible for stream={stream}"
                assert e[exam_type]["reason"] == ""


# ─────────────────────────────────────────────────────────────────────────────
# C. check_exam_prep_content_access
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckExamPrepContentAccess:
    def test_admin_always_allowed(self):
        from app.services.exam_prep_service import check_exam_prep_content_access
        p = {"id": "a", "role": "admin", "grade": "Grade 9", "username": "admin"}
        r = check_exam_prep_content_access(p)
        assert r["allowed"] is True

    def test_test_user_always_allowed(self):
        from app.services.exam_prep_service import check_exam_prep_content_access
        p = {"id": "b", "role": "student", "grade": "Grade 9", "username": "akshita.teststudent"}
        r = check_exam_prep_content_access(p)
        assert r["allowed"] is True

    def test_grade10_denied_at_grade_gate(self):
        from app.services.exam_prep_service import check_exam_prep_content_access
        from fastapi import HTTPException
        p = {"id": "c", "role": "student", "grade": "Grade 10", "username": "s10"}
        with pytest.raises(HTTPException) as exc:
            check_exam_prep_content_access(p)
        assert exc.value.status_code == 403
        assert "Grade 11" in str(exc.value.detail)

    def test_parent_denied_at_grade_gate(self):
        from app.services.exam_prep_service import check_exam_prep_content_access
        from fastapi import HTTPException
        p = {"id": "d", "role": "parent", "grade": "Grade 11", "username": "parent1"}
        with pytest.raises(HTTPException) as exc:
            check_exam_prep_content_access(p)
        assert exc.value.status_code == 403

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_free_grade11_denied_restriction_type_free(self, mock_auth):
        mock_auth.return_value = {
            "allowed": False, "canonical_plan_key": "FREE_TIER",
            "plan_name": "Free Tier", "restriction_message": "Upgrade",
            "upgrade_recommendation": "Upgrade to Premium"
        }
        from app.services.exam_prep_service import check_exam_prep_content_access
        from fastapi import HTTPException
        p = {"id": "e", "role": "student", "grade": "Grade 11", "username": "s11free"}
        with pytest.raises(HTTPException) as exc:
            check_exam_prep_content_access(p)
        assert exc.value.status_code == 403
        assert exc.value.detail["restriction_type"] == "free"

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_nano_grade11_denied_restriction_type_nano(self, mock_auth):
        mock_auth.return_value = {
            "allowed": False, "canonical_plan_key": "NANO",
            "plan_name": "Nano", "restriction_message": "...",
            "upgrade_recommendation": "Upgrade"
        }
        from app.services.exam_prep_service import check_exam_prep_content_access
        from fastapi import HTTPException
        p = {"id": "f", "role": "student", "grade": "Grade 11", "username": "s11nano"}
        with pytest.raises(HTTPException) as exc:
            check_exam_prep_content_access(p)
        assert exc.value.detail["restriction_type"] == "nano"
        assert "Nano" in exc.value.detail["message"]

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_premium_grade12_allowed(self, mock_auth):
        mock_auth.return_value = {
            "allowed": True, "limited": False,
            "canonical_plan_key": "PREMIUM", "plan_name": "Premium",
            "restriction_message": "", "upgrade_recommendation": ""
        }
        from app.services.exam_prep_service import check_exam_prep_content_access
        p = {"id": "g", "role": "student", "grade": "Grade 12", "username": "s12premium"}
        r = check_exam_prep_content_access(p)
        assert r["allowed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# D. get_access_check_response — canonical frontend response builder
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAccessCheckResponse:
    def test_admin_full_access(self):
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "admin-id", "role": "admin", "grade": "Grade 9", "username": "admin", "stream": "PCM"}
        r = get_access_check_response("admin-id", p)
        assert r["grade_eligible"] is True
        assert r["has_access"] is True
        assert r["preview_only"] is False
        assert r["reason"] == "admin"
        assert r["exam_eligibility"]["jee_main"]["eligible"] is True

    def test_test_user_full_access(self):
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "t", "role": "student", "grade": "Grade 9", "username": "akshita.teststudent", "stream": "PCB"}
        r = get_access_check_response("t", p)
        assert r["has_access"] is True
        assert r["preview_only"] is False
        assert r["reason"] == "test_user"

    def test_grade10_grade_ineligible(self):
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g10", "role": "student", "grade": "Grade 10", "username": "s10", "stream": None}
        r = get_access_check_response("g10", p)
        assert r["grade_eligible"] is False
        assert r["has_access"] is False
        assert r["reason"] == "grade_ineligible"
        assert r["exam_eligibility"] is None

    def test_parent_grade_ineligible(self):
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "par", "role": "parent", "grade": "Grade 12", "username": "parent", "stream": None}
        r = get_access_check_response("par", p)
        assert r["grade_eligible"] is False

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_grade11_free_preview_only_reason_free(self, mock_auth):
        mock_auth.return_value = {
            "allowed": False, "canonical_plan_key": "FREE_TIER",
            "plan_name": "Free Tier", "upgrade_recommendation": "Upgrade"
        }
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g11f", "role": "student", "grade": "Grade 11", "username": "s11", "stream": "PCM"}
        r = get_access_check_response("g11f", p)
        assert r["grade_eligible"] is True
        assert r["has_access"] is False
        assert r["preview_only"] is True
        assert r["reason"] == "free"
        assert r["exam_eligibility"]["jee_main"]["eligible"] is True

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_grade11_nano_preview_only_reason_nano(self, mock_auth):
        mock_auth.return_value = {
            "allowed": False, "canonical_plan_key": "NANO",
            "plan_name": "Nano", "upgrade_recommendation": "Upgrade"
        }
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g11n", "role": "student", "grade": "Grade 11", "username": "s11n", "stream": "PCB"}
        r = get_access_check_response("g11n", p)
        assert r["has_access"] is False
        assert r["preview_only"] is True
        assert r["reason"] == "nano"

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_grade12_premium_full_access(self, mock_auth):
        mock_auth.return_value = {
            "allowed": True, "limited": False,
            "canonical_plan_key": "PREMIUM", "plan_name": "Premium"
        }
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g12p", "role": "student", "grade": "Grade 12", "username": "s12", "stream": "PCMB"}
        r = get_access_check_response("g12p", p)
        assert r["has_access"] is True
        assert r["preview_only"] is False
        assert r["reason"] == "full_access"
        # PCMB: both JEE and NEET eligible
        assert r["exam_eligibility"]["jee_main"]["eligible"] is True
        assert r["exam_eligibility"]["neet_ug"]["eligible"] is True

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_stream_missing_flagged(self, mock_auth):
        mock_auth.return_value = {
            "allowed": True, "limited": False,
            "canonical_plan_key": "PREMIUM", "plan_name": "Premium"
        }
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g12ns", "role": "student", "grade": "Grade 12", "username": "s12ns", "stream": None}
        r = get_access_check_response("g12ns", p)
        assert r["stream_missing"] is True
        assert r["stream"] is None

    @patch("app.services.feature_authorization_service.authorize_feature")
    def test_stream_set_not_flagged_missing(self, mock_auth):
        mock_auth.return_value = {
            "allowed": True, "limited": False,
            "canonical_plan_key": "PREMIUM", "plan_name": "Premium"
        }
        from app.services.exam_prep_service import get_access_check_response
        p = {"id": "g12s", "role": "student", "grade": "Grade 12", "username": "s12s", "stream": "PCM"}
        r = get_access_check_response("g12s", p)
        assert r["stream_missing"] is False
        assert r["stream"] == "PCM"


# ─────────────────────────────────────────────────────────────────────────────
# E. Regression: existing Grade 5–10 features unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestGrade510Regression:
    """Ensure EXAM_PREP_CONTENT/CENTER additions do not break Grade 5–10 features."""

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_exemplar_still_works_for_nano(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "NANO", "plan_name": "Nano", "has_full_access": True}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.EXEMPLAR)
        assert r["allowed"] is True

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_lessons_still_limited_for_free(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.LESSONS)
        assert r["allowed"] is True
        assert r["limited"] is True

    @patch("app.services.feature_authorization_service.resolve_user_subscription")
    def test_mock_test_still_works_for_free(self, mock_sub):
        mock_sub.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False}
        from app.services.feature_authorization_service import authorize_feature, Feature
        r = authorize_feature("uid", Feature.MOCK_TEST)
        assert r["allowed"] is True   # limited daily
        assert r["limited"] is True

    def test_feature_summary_includes_exam_prep_keys(self):
        """get_feature_summary() must include the new exam prep features."""
        from app.services.feature_authorization_service import get_feature_summary, Feature
        from unittest.mock import patch as _patch
        with _patch("app.services.feature_authorization_service.resolve_user_subscription") as m:
            m.return_value = {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False}
            summary = get_feature_summary("uid")
        assert Feature.EXAM_PREP_CENTER in summary["features"]
        assert Feature.EXAM_PREP_CONTENT in summary["features"]
        # Free tier: EXAM_PREP_CENTER allowed (but limited), EXAM_PREP_CONTENT denied
        assert summary["features"][Feature.EXAM_PREP_CENTER]["allowed"] is True
        assert summary["features"][Feature.EXAM_PREP_CENTER]["limited"] is True
        assert summary["features"][Feature.EXAM_PREP_CONTENT]["allowed"] is False
