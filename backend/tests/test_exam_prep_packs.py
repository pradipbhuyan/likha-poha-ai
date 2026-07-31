"""
test_exam_prep_packs.py
=======================
E2E tests for JEE / NEET / CUET Exam Prep Pack purchase flow.

Covers all possible flows:
  A. Pack prices — public endpoint, no auth
  B. My-packs — grade-gated, admin/test users get all packs
  C. Pack order — grade check, already-owned check, Razorpay order creation
  D. Pack verify — signature verification, activation, idempotency
  E. Admin grant/revoke — admin grants pack manually
  F. Business rules — Free tier students CAN buy packs (no CBSE tier check)
  G. Helper functions — _get_active_packs, _pack_charge, _pack_expires_at

Run: cd backend && python3 -m pytest tests/test_exam_prep_packs.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# Helper fixtures / stubs
# ─────────────────────────────────────────────────────────────────────────────

def _make_profile(grade="Grade 11", role="student", username="test_student"):
    return {"id": "uid-123", "grade": grade, "role": role, "username": username}


def _active_pack_row(exam_type, days_from_now=120):
    exp = (datetime.now(timezone.utc) + timedelta(days=days_from_now)).isoformat()
    return {"exam_type": exam_type, "status": "active", "expires_at": exp}


def _expired_pack_row(exam_type):
    exp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return {"exam_type": exam_type, "status": "active", "expires_at": exp}


# ─────────────────────────────────────────────────────────────────────────────
# A. Pack prices
# ─────────────────────────────────────────────────────────────────────────────

class TestPackPrices:

    def test_pack_prices_returns_six_exams(self):
        from app.routes.exam_prep_packs import PACK_TO_EXAM_TYPE
        assert "jee_main"   in PACK_TO_EXAM_TYPE.values()
        assert "neet_ug"    in PACK_TO_EXAM_TYPE.values()
        assert "cuet_ug"    in PACK_TO_EXAM_TYPE.values()
        assert "sat"        in PACK_TO_EXAM_TYPE.values()
        assert "ielts"      in PACK_TO_EXAM_TYPE.values()
        assert "toefl_ibt"  in PACK_TO_EXAM_TYPE.values()

    def test_pack_prices_plan_keys_correct(self):
        from app.routes.exam_prep_packs import PACK_TO_EXAM_TYPE, EXAM_TYPE_TO_PACK
        for pack_key, exam_type in PACK_TO_EXAM_TYPE.items():
            assert EXAM_TYPE_TO_PACK[exam_type] == pack_key

    def test_pack_charge_no_discount(self):
        from app.routes.exam_prep_packs import _pack_charge
        plan = {"price": 499, "discount_percent": 0}
        assert _pack_charge(plan) == 499

    def test_pack_charge_with_discount(self):
        from app.routes.exam_prep_packs import _pack_charge
        plan = {"price": 499, "discount_percent": 20}
        assert _pack_charge(plan) == 399  # 499 * 0.80 = 399.2 → 399

    def test_pack_charge_100_percent_discount_is_zero(self):
        from app.routes.exam_prep_packs import _pack_charge
        plan = {"price": 499, "discount_percent": 100}
        assert _pack_charge(plan) == 0

    def test_pack_charge_negative_discount_ignored(self):
        from app.routes.exam_prep_packs import _pack_charge
        plan = {"price": 299, "discount_percent": -10}
        assert _pack_charge(plan) == 299

    def test_pack_expires_at_with_duration_days(self):
        from app.routes.exam_prep_packs import _pack_expires_at
        plan = {"duration_days": 120}
        result = _pack_expires_at(plan)
        assert result is not None
        dt = datetime.fromisoformat(result)
        days = (dt - datetime.now(timezone.utc)).days
        assert 119 <= days <= 121

    def test_pack_expires_at_no_duration_returns_none(self):
        from app.routes.exam_prep_packs import _pack_expires_at
        assert _pack_expires_at({}) is None
        assert _pack_expires_at({"duration_days": None}) is None


# ─────────────────────────────────────────────────────────────────────────────
# B. _get_active_packs helper
# ─────────────────────────────────────────────────────────────────────────────

class TestGetActivePacks:

    def test_empty_result_returns_all_inactive(self):
        from app.routes.exam_prep_packs import _get_active_packs, VALID_EXAM_TYPES
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            result = _get_active_packs("uid-123")
        assert result == {
            exam_type: {"active": False, "expires_at": None} for exam_type in VALID_EXAM_TYPES
        }

    def test_active_pack_detected(self):
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": "jee_main", "status": "active", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid-123")
        assert result["jee_main"]["active"] is True
        assert result["neet_ug"]["active"] is False

    def test_expired_pack_marked_inactive(self):
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        rows = [{"exam_type": "neet_ug", "status": "active", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_table = MagicMock()
            mock_ac.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value.data = rows
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            result = _get_active_packs("uid-123")
        assert result["neet_ug"]["active"] is False

    def test_revoked_pack_not_active(self):
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": "cuet_ug", "status": "revoked", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid-123")
        assert result["cuet_ug"]["active"] is False

    def test_db_error_returns_all_inactive(self):
        from app.routes.exam_prep_packs import _get_active_packs
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")
            result = _get_active_packs("uid-123")
        # Should not raise — returns all inactive
        assert all(not v["active"] for v in result.values())

    def test_multiple_packs_mixed_status(self):
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [
            {"exam_type": "jee_main", "status": "active", "expires_at": exp},
            {"exam_type": "neet_ug",  "status": "revoked", "expires_at": exp},
            {"exam_type": "cuet_ug",  "status": "active", "expires_at": exp},
        ]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid-123")
        assert result["jee_main"]["active"] is True
        assert result["neet_ug"]["active"] is False
        assert result["cuet_ug"]["active"] is True


# ─────────────────────────────────────────────────────────────────────────────
# C. Admin gets all packs (no DB check)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminAndTestUserPacks:

    def test_admin_role_gets_all_packs_active(self):
        """Admin users always have all packs active without DB lookup."""
        from app.routes.exam_prep_packs import get_my_packs
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "admin-uid"
        profile = _make_profile(grade="Grade 9", role="admin", username="admin")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile):
            result = get_my_packs(mock_user)
        assert result["grade_eligible"] is True
        assert result["packs"]["jee_main"]["active"] is True
        assert result["packs"]["neet_ug"]["active"] is True
        assert result["packs"]["cuet_ug"]["active"] is True

    def test_test_user_gets_all_packs_active(self):
        """akshita.teststudent always gets all packs."""
        from app.routes.exam_prep_packs import get_my_packs
        mock_user = MagicMock(); mock_user.id = "test-uid"
        profile = _make_profile(grade="Grade 9", role="student", username="akshita.teststudent")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile):
            result = get_my_packs(mock_user)
        assert result["packs"]["jee_main"]["active"] is True

    def test_grade10_student_not_eligible(self):
        """Grade 10 student is not grade-eligible."""
        from app.routes.exam_prep_packs import get_my_packs
        mock_user = MagicMock(); mock_user.id = "g10-uid"
        profile = _make_profile(grade="Grade 10", role="student", username="grade10student")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile):
            result = get_my_packs(mock_user)
        assert result["grade_eligible"] is False
        assert all(not v["active"] for v in result["packs"].values())


# ─────────────────────────────────────────────────────────────────────────────
# D. Pack order creation
# ─────────────────────────────────────────────────────────────────────────────

class TestPackOrderCreation:

    def test_invalid_exam_type_raises_400(self):
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        profile = _make_profile()
        req = PackOrderRequest(exam_type="invalid_exam")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
             patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True):
            with pytest.raises(HTTPException) as exc:
                create_pack_order(req, mock_user)
            assert exc.value.status_code == 400

    def test_grade10_raises_403(self):
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        profile = _make_profile(grade="Grade 10")
        req = PackOrderRequest(exam_type="jee_main")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
             patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True):
            with pytest.raises(HTTPException) as exc:
                create_pack_order(req, mock_user)
            assert exc.value.status_code == 403

    def test_already_owned_pack_raises_409(self):
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        profile = _make_profile()
        req = PackOrderRequest(exam_type="jee_main")
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        active_packs = {"jee_main": {"active": True, "expires_at": exp}, "neet_ug": {"active": False, "expires_at": None}, "cuet_ug": {"active": False, "expires_at": None}}
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
             patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._get_active_packs", return_value=active_packs):
            with pytest.raises(HTTPException) as exc:
                create_pack_order(req, mock_user)
            assert exc.value.status_code == 409

    def test_razorpay_not_configured_raises_503(self):
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackOrderRequest(exam_type="jee_main")
        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=False):
            with pytest.raises(HTTPException) as exc:
                create_pack_order(req, mock_user)
            assert exc.value.status_code == 503

    def test_free_tier_student_can_buy_pack(self):
        """Critical: Free tier students (access_cbse=False) CAN still buy exam prep packs."""
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        mock_user = MagicMock(); mock_user.id = "free-uid"
        # Free tier profile — no access_cbse
        profile = {"id": "free-uid", "grade": "Grade 11", "role": "student",
                   "username": "free_student", "access_cbse": False, "subscription_plan": "free_tier"}
        req = PackOrderRequest(exam_type="jee_main")
        all_inactive = {"jee_main": {"active": False, "expires_at": None},
                        "neet_ug": {"active": False, "expires_at": None},
                        "cuet_ug": {"active": False, "expires_at": None}}
        mock_order = {"id": "order_123", "amount": 499 * 100}
        mock_plan = {"key": "exam_prep_jee", "price": 499, "discount_percent": 0,
                     "label": "JEE Pack", "duration_days": 120}
        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
             patch("app.routes.exam_prep_packs._get_active_packs", return_value=all_inactive), \
             patch("app.routes.exam_prep_packs._get_pack_plan", return_value=mock_plan), \
             patch("app.routes.exam_prep_packs.req_lib") as mock_req, \
             patch("app.routes.exam_prep_packs.admin_client"):
            mock_resp = MagicMock(); mock_resp.status_code = 200; mock_resp.json.return_value = mock_order
            mock_req.post.return_value = mock_resp
            result = create_pack_order(req, mock_user)
        # Should succeed — Free tier CAN buy exam prep packs
        assert result["order_id"] == "order_123"
        assert result["exam_type"] == "jee_main"
        assert result["amount"] == 499


# ─────────────────────────────────────────────────────────────────────────────
# E. Payment verification
# ─────────────────────────────────────────────────────────────────────────────

class TestPackVerification:

    def test_invalid_signature_raises_400(self):
        from app.routes.exam_prep_packs import verify_pack_payment, PackVerifyRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackVerifyRequest(razorpay_order_id="ord_1", razorpay_payment_id="pay_1",
                                razorpay_signature="bad_sig", exam_type="jee_main")
        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._verify_razorpay_signature", return_value=False):
            with pytest.raises(HTTPException) as exc:
                verify_pack_payment(req, mock_user)
            assert exc.value.status_code == 400

    def test_valid_signature_activates_pack(self):
        from app.routes.exam_prep_packs import verify_pack_payment, PackVerifyRequest
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackVerifyRequest(razorpay_order_id="ord_1", razorpay_payment_id="pay_1",
                                razorpay_signature="good_sig", exam_type="jee_main")
        existing_row = {"user_id": "uid", "exam_type": "jee_main", "status": "created",
                        "plan_key": "exam_prep_jee", "razorpay_payment_id": None, "amount_paid": 499}
        mock_plan = {"key": "exam_prep_jee", "price": 499, "duration_days": 120, "label": "JEE Pack"}

        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._verify_razorpay_signature", return_value=True), \
             patch("app.routes.exam_prep_packs._get_pack_plan", return_value=mock_plan), \
             patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            # First query: find the order
            mock_ac.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [existing_row]
            # Update: activate pack
            mock_ac.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            # Audit log insert
            mock_ac.table.return_value.insert.return_value.execute.return_value = MagicMock()

            result = verify_pack_payment(req, mock_user)

        assert result["success"] is True
        assert result["exam_type"] == "jee_main"
        assert result["expires_at"] is not None

    def test_idempotent_already_activated(self):
        from app.routes.exam_prep_packs import verify_pack_payment, PackVerifyRequest
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackVerifyRequest(razorpay_order_id="ord_1", razorpay_payment_id="pay_1",
                                razorpay_signature="good_sig", exam_type="jee_main")
        exp = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat()
        already_active = {"user_id": "uid", "exam_type": "jee_main", "status": "active",
                          "razorpay_payment_id": "pay_1", "expires_at": exp}

        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._verify_razorpay_signature", return_value=True), \
             patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [already_active]
            result = verify_pack_payment(req, mock_user)

        assert result["success"] is True
        assert result.get("idempotent") is True

    def test_order_not_found_raises_404(self):
        from app.routes.exam_prep_packs import verify_pack_payment, PackVerifyRequest
        from fastapi import HTTPException
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackVerifyRequest(razorpay_order_id="ord_1", razorpay_payment_id="pay_1",
                                razorpay_signature="sig", exam_type="neet_ug")

        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._verify_razorpay_signature", return_value=True), \
             patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
            with pytest.raises(HTTPException) as exc:
                verify_pack_payment(req, mock_user)
            assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# F. Business rules
# ─────────────────────────────────────────────────────────────────────────────

class TestBusinessRules:

    def test_pack_access_independent_of_cbse_subscription(self):
        """Pack ownership must NOT depend on CBSE subscription plan."""
        from app.routes.exam_prep_packs import _get_active_packs
        # A Free Tier user (access_cbse=False) with a purchased JEE pack
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": "jee_main", "status": "active", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("free-tier-uid")
        # Must return active regardless of CBSE tier
        assert result["jee_main"]["active"] is True

    def test_pack_expires_after_duration(self):
        """A pack that is expired (status=active but expires_at in past) must be inactive."""
        from app.routes.exam_prep_packs import _get_active_packs
        exp_past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        rows = [{"exam_type": "jee_main", "status": "active", "expires_at": exp_past}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_table = MagicMock()
            mock_ac.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value.data = rows
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            result = _get_active_packs("uid")
        assert result["jee_main"]["active"] is False

    def test_each_pack_is_independent(self):
        """Buying JEE does not affect NEET or CUET status."""
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": "jee_main", "status": "active", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid")
        assert result["jee_main"]["active"] is True
        assert result["neet_ug"]["active"] is False   # independent
        assert result["cuet_ug"]["active"] is False   # independent

    def test_all_six_packs_can_be_active_simultaneously(self):
        """A student can own all 6 packs at the same time."""
        from app.routes.exam_prep_packs import _get_active_packs, VALID_EXAM_TYPES
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": exam_type, "status": "active", "expires_at": exp} for exam_type in VALID_EXAM_TYPES]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid")
        assert all(v["active"] for v in result.values())

    ALL_PACK_KEYS = ("exam_prep_jee", "exam_prep_neet", "exam_prep_cuet",
                      "exam_prep_sat", "exam_prep_ielts", "exam_prep_toefl")

    def test_valid_exam_types(self):
        """jee_main, neet_ug, cuet_ug, sat, ielts, toefl_ibt are the valid exam types."""
        from app.routes.exam_prep_packs import VALID_EXAM_TYPES
        assert VALID_EXAM_TYPES == {"jee_main", "neet_ug", "cuet_ug", "sat", "ielts", "toefl_ibt"}

    def test_plan_keys_match_exam_types(self):
        """exam_prep_<x> pack keys map to their exam_type."""
        from app.routes.exam_prep_packs import PACK_TO_EXAM_TYPE
        assert PACK_TO_EXAM_TYPE["exam_prep_jee"] == "jee_main"
        assert PACK_TO_EXAM_TYPE["exam_prep_neet"] == "neet_ug"
        assert PACK_TO_EXAM_TYPE["exam_prep_cuet"] == "cuet_ug"
        assert PACK_TO_EXAM_TYPE["exam_prep_sat"] == "sat"
        assert PACK_TO_EXAM_TYPE["exam_prep_ielts"] == "ielts"
        assert PACK_TO_EXAM_TYPE["exam_prep_toefl"] == "toefl_ibt"

    def test_subscription_plan_defaults_have_pack_keys(self):
        """subscription_plans.py must contain all 6 exam prep pack keys."""
        from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS
        for key in self.ALL_PACK_KEYS:
            assert key in DEFAULT_SUBSCRIPTION_PLANS

    def test_pack_plan_has_exam_type_field(self):
        """Each exam prep pack plan must have exam_type field."""
        from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_jee"]["exam_type"] == "jee_main"
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_neet"]["exam_type"] == "neet_ug"
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_cuet"]["exam_type"] == "cuet_ug"
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_sat"]["exam_type"] == "sat"
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_ielts"]["exam_type"] == "ielts"
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_toefl"]["exam_type"] == "toefl_ibt"

    def test_pack_plans_not_cbse_access(self):
        """Exam prep packs must NOT set access_cbse=True."""
        from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS
        for key in self.ALL_PACK_KEYS:
            assert DEFAULT_SUBSCRIPTION_PLANS[key]["access_cbse"] is False, f"{key} must not grant CBSE access"

    def test_pack_plans_have_prices(self):
        """Each pack must have a non-zero price."""
        from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS
        for key in self.ALL_PACK_KEYS:
            assert DEFAULT_SUBSCRIPTION_PLANS[key]["price"] > 0, f"{key} must have a price"

    def test_pack_plans_have_duration_days(self):
        """Each pack must have a positive duration_days."""
        from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS
        for key in self.ALL_PACK_KEYS:
            assert DEFAULT_SUBSCRIPTION_PLANS[key].get("duration_days", 0) > 0, f"{key} must have duration_days"

    def test_grade11_and_grade12_both_eligible(self):
        """Both Grade 11 and Grade 12 students should be grade_eligible."""
        from app.routes.exam_prep_packs import get_my_packs
        for grade in ("Grade 11", "Grade 12"):
            mock_user = MagicMock(); mock_user.id = "uid"
            profile = _make_profile(grade=grade)
            exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            rows = [{"exam_type": "jee_main", "status": "active", "expires_at": exp}]
            with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
                 patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
                mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
                result = get_my_packs(mock_user)
            assert result["grade_eligible"] is True, f"{grade} should be eligible"

    def test_parent_role_not_eligible(self):
        """Parents cannot purchase exam prep packs."""
        from app.routes.exam_prep_packs import get_my_packs
        mock_user = MagicMock(); mock_user.id = "parent-uid"
        profile = _make_profile(grade="Grade 11", role="parent", username="parent1")
        with patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile):
            result = get_my_packs(mock_user)
        assert result["grade_eligible"] is False


# ─────────────────────────────────────────────────────────────────────────────
# H. SAT / IELTS / TOEFL — same purchase flow as JEE/NEET/CUET
# ─────────────────────────────────────────────────────────────────────────────

class TestGlobalExamPacks:

    @pytest.mark.parametrize("exam_type,pack_key,price", [
        ("sat", "exam_prep_sat", 599),
        ("ielts", "exam_prep_ielts", 599),
        ("toefl_ibt", "exam_prep_toefl", 599),
    ])
    def test_order_creation_succeeds_for_global_exams(self, exam_type, pack_key, price):
        from app.routes.exam_prep_packs import create_pack_order, PackOrderRequest
        mock_user = MagicMock(); mock_user.id = "uid"
        profile = _make_profile()
        req = PackOrderRequest(exam_type=exam_type)
        all_inactive = {"jee_main": {"active": False, "expires_at": None},
                        "neet_ug": {"active": False, "expires_at": None},
                        "cuet_ug": {"active": False, "expires_at": None},
                        "sat": {"active": False, "expires_at": None},
                        "ielts": {"active": False, "expires_at": None},
                        "toefl_ibt": {"active": False, "expires_at": None}}
        mock_order = {"id": "order_456", "amount": price * 100}
        mock_plan = {"key": pack_key, "price": price, "discount_percent": 0,
                     "label": f"{exam_type} Pack", "duration_days": 180}
        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs.get_user_profile", return_value=profile), \
             patch("app.routes.exam_prep_packs._get_active_packs", return_value=all_inactive), \
             patch("app.routes.exam_prep_packs._get_pack_plan", return_value=mock_plan), \
             patch("app.routes.exam_prep_packs.req_lib") as mock_req, \
             patch("app.routes.exam_prep_packs.admin_client"):
            mock_resp = MagicMock(); mock_resp.status_code = 200; mock_resp.json.return_value = mock_order
            mock_req.post.return_value = mock_resp
            result = create_pack_order(req, mock_user)
        assert result["order_id"] == "order_456"
        assert result["exam_type"] == exam_type
        assert result["amount"] == price

    @pytest.mark.parametrize("exam_type,pack_key", [
        ("sat", "exam_prep_sat"),
        ("ielts", "exam_prep_ielts"),
        ("toefl_ibt", "exam_prep_toefl"),
    ])
    def test_verify_activates_global_exam_pack(self, exam_type, pack_key):
        from app.routes.exam_prep_packs import verify_pack_payment, PackVerifyRequest
        mock_user = MagicMock(); mock_user.id = "uid"
        req = PackVerifyRequest(razorpay_order_id="ord_1", razorpay_payment_id="pay_1",
                                razorpay_signature="good_sig", exam_type=exam_type)
        existing_row = {"user_id": "uid", "exam_type": exam_type, "status": "created",
                        "plan_key": pack_key, "razorpay_payment_id": None, "amount_paid": 599}
        mock_plan = {"key": pack_key, "price": 599, "duration_days": 180, "label": f"{exam_type} Pack"}

        with patch("app.routes.exam_prep_packs._razorpay_configured", return_value=True), \
             patch("app.routes.exam_prep_packs._verify_razorpay_signature", return_value=True), \
             patch("app.routes.exam_prep_packs._get_pack_plan", return_value=mock_plan), \
             patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [existing_row]
            mock_ac.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            mock_ac.table.return_value.insert.return_value.execute.return_value = MagicMock()
            result = verify_pack_payment(req, mock_user)

        assert result["success"] is True
        assert result["exam_type"] == exam_type
        assert result["expires_at"] is not None

    def test_global_exam_packs_independent_of_entrance_exam_packs(self):
        """Owning a SAT pack must not imply JEE/NEET/CUET access, and vice versa."""
        from app.routes.exam_prep_packs import _get_active_packs
        exp = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        rows = [{"exam_type": "sat", "status": "active", "expires_at": exp}]
        with patch("app.routes.exam_prep_packs.admin_client") as mock_ac:
            mock_ac.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            result = _get_active_packs("uid")
        assert result["sat"]["active"] is True
        assert result["jee_main"]["active"] is False
        assert result["ielts"]["active"] is False
        assert result["toefl_ibt"]["active"] is False
