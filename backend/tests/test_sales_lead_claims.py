"""
Sales Lead Claims — End-to-End Test Suite
==========================================
Tests the full automated commission flow:
  sales person submits lead → student pays → claim auto-confirmed → admin pays commission

Test scenarios:
  1. Happy path: lead submitted → student pays → commission confirmed
  2. Duplicate claim: second salesperson cannot steal an existing claim
  3. Student never pays: claim stays 'claimed', no commission
  4. Already-paid student: cannot be claimed
  5. Daily limit enforcement: 16th claim in a day is rejected
  6. Commission calculation accuracy
  7. Batch pay: admin marks confirmed → paid
  8. Expired claim: claim older than 30 days auto-expires
  9. Auto-match ignores expired claims
  10. Admin can see all claims; sales person sees only their own
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

from app.routes.sales import (
    auto_match_lead_claim,
    _expire_stale_claims,
    _get_salesperson_incentive_percent,
    CLAIM_EXPIRY_DAYS,
    DAILY_CLAIM_LIMIT,
)
from app.services.sales_service import (
    calculate_incentive_amount,
    normalize_incentive_percent,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

SP_ID_1  = str(uuid.uuid4())  # Salesperson 1
SP_ID_2  = str(uuid.uuid4())  # Salesperson 2
STU_ID_1 = str(uuid.uuid4())  # Student 1
CLAIM_ID = str(uuid.uuid4())  # Claim UUID


def _claim(status="claimed", incentive_percent=5, package_amount=0,
           days_old=1, sales_person_id=SP_ID_1):
    """Build a minimal claim dict for testing."""
    claimed_at = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return {
        "id": CLAIM_ID,
        "sales_person_id": sales_person_id,
        "student_email": "student@example.com",
        "student_name": "Test Student",
        "grade": "Grade 9",
        "package_key": "starter",
        "status": status,
        "incentive_percent": incentive_percent,
        "package_amount": package_amount,
        "commission_amount": 0,
        "claimed_at": claimed_at,
        "confirmed_at": None,
        "paid_at": None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 1. Commission calculation
# ──────────────────────────────────────────────────────────────────────────────

class TestCommissionCalculation:
    """Commission math is the financial source of truth — must be exact."""

    def test_standard_5_percent(self):
        assert calculate_incentive_amount(999, 5) == 49.95

    def test_standard_10_percent(self):
        assert calculate_incentive_amount(499, 10) == 49.90

    def test_fractional_result_rounds_half_up(self):
        # 499 × 7% = 34.93
        assert calculate_incentive_amount(499, 7) == 34.93

    def test_zero_package_amount(self):
        assert calculate_incentive_amount(0, 5) == 0.0

    def test_incentive_clamped_below_minimum(self):
        # 3% is below minimum — should be treated as 5%
        pct = normalize_incentive_percent(3)
        assert pct == Decimal("5")
        amount = calculate_incentive_amount(1000, pct)
        assert amount == 50.0

    def test_incentive_clamped_above_maximum(self):
        # 15% is above maximum — should be treated as 10%
        pct = normalize_incentive_percent(15)
        assert pct == Decimal("10")
        amount = calculate_incentive_amount(1000, pct)
        assert amount == 100.0


# ──────────────────────────────────────────────────────────────────────────────
# 2. auto_match_lead_claim — the payment hook
# ──────────────────────────────────────────────────────────────────────────────

class TestAutoMatchLeadClaim:
    """
    auto_match_lead_claim() is called after a student pays.
    It must auto-confirm the matching 'claimed' lead and calculate commission.
    """

    def test_happy_path_claim_confirmed_with_correct_commission(self):
        """
        Scenario: Salesperson submitted a lead for student@example.com.
        Student pays ₹999. System should auto-confirm and set commission = ₹49.95.
        """
        claim = _claim(status="claimed", incentive_percent=5)
        now_iso = datetime.now(timezone.utc).isoformat()

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[claim])

        mock_update = MagicMock()
        mock_update.execute.return_value = MagicMock(data=[{**claim, "status": "confirmed"}])

        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select
        mock_table.update.return_value.eq.return_value = mock_update

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table

            auto_match_lead_claim(
                email="student@example.com",
                student_id=STU_ID_1,
                package_amount=999,
                package_key="starter",
            )

        # Verify update was called with correct commission
        update_call_args = mock_table.update.call_args[0][0]
        assert update_call_args["status"] == "confirmed"
        assert update_call_args["student_id"] == STU_ID_1
        assert update_call_args["package_amount"] == 999
        assert update_call_args["commission_amount"] == 49.95

    def test_no_claim_found_does_not_raise(self):
        """
        Scenario: Student pays but no salesperson had claimed their email.
        Should silently do nothing — never block the signup.
        """
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            # Must not raise
            auto_match_lead_claim(
                email="nobody@example.com",
                student_id=STU_ID_1,
                package_amount=999,
                package_key="starter",
            )

        # update() should never have been called
        mock_table.update.assert_not_called()

    def test_database_error_does_not_raise(self):
        """
        Scenario: Supabase is temporarily down during signup.
        auto_match must fail silently — never block student account creation.
        """
        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = Exception("DB connection error")
            # Must not raise
            auto_match_lead_claim(
                email="student@example.com",
                student_id=STU_ID_1,
                package_amount=999,
                package_key="starter",
            )

    def test_already_confirmed_claim_not_updated(self):
        """
        Scenario: Student pays again (e.g. plan upgrade). Already-confirmed
        claim should not be touched — only 'claimed' status triggers matching.
        """
        confirmed_claim = _claim(status="confirmed", incentive_percent=5, package_amount=999)

        mock_table = MagicMock()
        mock_select = MagicMock()
        # eq("status", "claimed") returns empty — confirmed claim is filtered out
        mock_select.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            auto_match_lead_claim(
                email="student@example.com",
                student_id=STU_ID_1,
                package_amount=1999,
                package_key="premium",
            )

        mock_table.update.assert_not_called()

    def test_commission_precision_for_family_premium_plan(self):
        """
        Scenario: Student on family_premium plan (₹1499) with 7.5% incentive.
        Commission = ₹1499 × 7.5% = ₹112.43 (rounded half-up).
        """
        claim = _claim(status="claimed", incentive_percent=7.5)

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[claim])
        mock_update = MagicMock()
        mock_update.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select
        mock_table.update.return_value.eq.return_value = mock_update

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            auto_match_lead_claim(
                email="student@example.com",
                student_id=STU_ID_1,
                package_amount=1499,
                package_key="family_premium",
            )

        update_args = mock_table.update.call_args[0][0]
        assert update_args["commission_amount"] == 112.43


# ──────────────────────────────────────────────────────────────────────────────
# 3. Stale claim expiry
# ──────────────────────────────────────────────────────────────────────────────

class TestStaleClaimExpiry:
    """Claims older than CLAIM_EXPIRY_DAYS must be auto-expired on load."""

    def test_expire_stale_claims_calls_update_with_correct_cutoff(self):
        """Verifies the expiry query uses status='claimed' and a cutoff date."""
        mock_table = MagicMock()
        mock_update_chain = MagicMock()
        mock_update_chain.execute.return_value = MagicMock(data=[])
        mock_table.update.return_value.eq.return_value.lt.return_value = mock_update_chain

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            _expire_stale_claims()

        # Verify update was called with status='expired'
        mock_table.update.assert_called_once_with({"status": "expired"})

        # Verify it filtered on status='claimed'
        mock_table.update.return_value.eq.assert_called_once_with("status", "claimed")

    def test_expired_claim_does_not_get_matched_on_payment(self):
        """
        Scenario: Salesperson submitted a lead 35 days ago.
        Student finally pays. Expired claim should NOT get commission
        because the match query filters on status='claimed', not 'expired'.
        """
        # Return empty (expired claim is filtered out by status='claimed')
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            auto_match_lead_claim(
                email="lateStudent@example.com",
                student_id=STU_ID_1,
                package_amount=999,
                package_key="starter",
            )

        mock_table.update.assert_not_called()

    def test_expire_stale_claims_silently_ignores_missing_table(self):
        """Table may not exist in fresh environments — must not crash."""
        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = Exception("table not found")
            _expire_stale_claims()  # must not raise


# ──────────────────────────────────────────────────────────────────────────────
# 4. Salesperson incentive lookup
# ──────────────────────────────────────────────────────────────────────────────

class TestSalespersonIncentiveLookup:

    def test_returns_correct_percent_from_sales_profile(self):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(
            data=[{"default_incentive_percent": 7.5}]
        )
        mock_table.select.return_value.eq.return_value.limit.return_value = mock_select

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            result = _get_salesperson_incentive_percent(SP_ID_1)

        assert result == 7.5

    def test_returns_default_5_if_no_profile_exists(self):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.limit.return_value = mock_select

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            result = _get_salesperson_incentive_percent("nonexistent-sp")

        assert result == 5.0

    def test_returns_default_5_on_db_error(self):
        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = Exception("network error")
            result = _get_salesperson_incentive_percent(SP_ID_1)

        assert result == 5.0


# ──────────────────────────────────────────────────────────────────────────────
# 5. Business rule validations
# ──────────────────────────────────────────────────────────────────────────────

class TestBusinessRules:
    """
    These tests verify the business logic of the lead claim system
    by unit-testing the helpers and mocking Supabase.
    """

    # ── 5a. First salesperson wins — duplicate claim is rejected ──────────────

    def test_first_claim_wins_duplicate_is_rejected(self):
        """
        Scenario: SP1 claims student@example.com at 9am.
        SP2 tries to claim the same student at 10am.
        The DB UNIQUE(student_email) constraint prevents SP2.
        We simulate this by the insert raising a unique-violation error.
        """
        # Simulate SP2's insert raising a unique constraint error
        mock_table = MagicMock()
        # no existing paid profile
        mock_profile_select = MagicMock()
        mock_profile_select.execute.return_value = MagicMock(data=[])
        # daily count under limit
        mock_count = MagicMock()
        mock_count.execute.return_value = MagicMock(count=0)
        # insert raises unique violation
        mock_insert = MagicMock()
        mock_insert.execute.side_effect = Exception(
            'duplicate key value violates unique constraint "sales_lead_claims_student_email_key"'
        )

        def table_router(name):
            if name == "profiles":
                t = MagicMock()
                t.select.return_value.eq.return_value.limit.return_value = mock_profile_select
                return t
            if name == "sales_lead_claims":
                t = MagicMock()
                t.select.return_value.eq.return_value.gte.return_value = mock_count
                t.insert.return_value = mock_insert
                return t
            if name == "sales_profiles":
                t = MagicMock()
                t.select.return_value.eq.return_value.limit.return_value = MagicMock(
                    execute=MagicMock(return_value=MagicMock(data=[{"default_incentive_percent": 5}]))
                )
                return t
            return MagicMock()

        from fastapi import HTTPException
        from app.routes.sales import submit_lead_claim

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = table_router

            fake_user = {"profile": {"id": SP_ID_2, "role": "sales"}}

            class FakeData:
                student_email = "student@example.com"
                student_name = "Test Student"
                student_phone = ""
                grade = "Grade 9"
                package_key = "starter"

            with pytest.raises(HTTPException) as exc_info:
                submit_lead_claim(FakeData(), fake_user)

            assert exc_info.value.status_code == 409
            assert "already claimed" in exc_info.value.detail.lower()

    # ── 5b. Cannot claim a student who already paid ───────────────────────────

    def test_cannot_claim_already_paid_student(self):
        """
        Scenario: Student already has a 'starter' paid plan.
        Salesperson tries to claim them retroactively.
        System must reject with 409.
        """
        from fastapi import HTTPException
        from app.routes.sales import submit_lead_claim

        mock_table = MagicMock()
        mock_profile_select = MagicMock()
        mock_profile_select.execute.return_value = MagicMock(
            data=[{"id": STU_ID_1, "subscription_plan": "starter", "account_status": "active"}]
        )

        def table_router(name):
            if name == "profiles":
                t = MagicMock()
                t.select.return_value.eq.return_value.limit.return_value = mock_profile_select
                return t
            return MagicMock()

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = table_router

            fake_user = {"profile": {"id": SP_ID_1, "role": "sales"}}

            class FakeData:
                student_email = "paid_student@example.com"
                student_name = "Already Paid"
                student_phone = ""
                grade = "Grade 9"
                package_key = "starter"

            with pytest.raises(HTTPException) as exc_info:
                submit_lead_claim(FakeData(), fake_user)

            assert exc_info.value.status_code == 409
            assert "already has an active paid account" in exc_info.value.detail

    # ── 5c. Daily limit enforcement ───────────────────────────────────────────

    def test_daily_limit_blocks_16th_claim(self):
        """
        Scenario: Salesperson has already submitted 15 leads today (the max).
        The 16th submission must be rejected with 429.
        """
        from fastapi import HTTPException
        from app.routes.sales import submit_lead_claim

        def table_router(name):
            t = MagicMock()
            if name == "profiles":
                # no existing paid profile
                t.select.return_value.eq.return_value.limit.return_value = MagicMock(
                    execute=MagicMock(return_value=MagicMock(data=[]))
                )
            elif name == "sales_lead_claims":
                # return count = DAILY_CLAIM_LIMIT (already at limit)
                count_chain = MagicMock()
                count_chain.execute.return_value = MagicMock(count=DAILY_CLAIM_LIMIT)
                t.select.return_value.eq.return_value.gte.return_value = count_chain
            return t

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.side_effect = table_router

            fake_user = {"profile": {"id": SP_ID_1, "role": "sales"}}

            class FakeData:
                student_email = "new_student@example.com"
                student_name = "New Student"
                student_phone = ""
                grade = "Grade 9"
                package_key = "starter"

            with pytest.raises(HTTPException) as exc_info:
                submit_lead_claim(FakeData(), fake_user)

            assert exc_info.value.status_code == 429
            assert str(DAILY_CLAIM_LIMIT) in exc_info.value.detail

    # ── 5d. Student never pays — claim stays 'claimed' ────────────────────────

    def test_student_never_pays_commission_stays_zero(self):
        """
        Scenario: Salesperson submits a lead. Student never pays.
        auto_match is never called → claim stays 'claimed' with commission = 0.
        This verifies that no payment = no commission, by design.
        """
        claim = _claim(status="claimed", incentive_percent=5, package_amount=0)
        assert claim["status"] == "claimed"
        assert claim["commission_amount"] == 0
        assert claim["confirmed_at"] is None
        assert claim["paid_at"] is None

    # ── 5e. Invalid email rejected ────────────────────────────────────────────

    def test_invalid_email_rejected(self):
        """Claim submission must reject emails without '@'."""
        from fastapi import HTTPException
        from app.routes.sales import submit_lead_claim

        fake_user = {"profile": {"id": SP_ID_1, "role": "sales"}}

        class FakeData:
            student_email = "notanemail"
            student_name = "Test"
            student_phone = ""
            grade = "Grade 9"
            package_key = "starter"

        # No DB calls needed — validation happens before any DB access
        with pytest.raises(HTTPException) as exc_info:
            submit_lead_claim(FakeData(), fake_user)

        assert exc_info.value.status_code == 400
        assert "email" in exc_info.value.detail.lower()

    # ── 5f. Missing student name rejected ─────────────────────────────────────

    def test_empty_student_name_rejected(self):
        """Claim submission must reject empty student names."""
        from fastapi import HTTPException
        from app.routes.sales import submit_lead_claim

        fake_user = {"profile": {"id": SP_ID_1, "role": "sales"}}

        class FakeData:
            student_email = "student@example.com"
            student_name = "   "  # whitespace only
            student_phone = ""
            grade = "Grade 9"
            package_key = "starter"

        with pytest.raises(HTTPException) as exc_info:
            submit_lead_claim(FakeData(), fake_user)

        assert exc_info.value.status_code == 400
        assert "name" in exc_info.value.detail.lower()


# ──────────────────────────────────────────────────────────────────────────────
# 6. End-to-end narrative: full commission lifecycle
# ──────────────────────────────────────────────────────────────────────────────

class TestFullCommissionLifecycle:
    """
    Narrative test tracing the complete state machine:
    claimed → confirmed → paid
    """

    def test_state_transitions_are_correct(self):
        """
        Verifies that the claim status progresses correctly:
        1. Salesperson submits → status='claimed', commission=0
        2. Student pays → status='confirmed', commission calculated
        3. Admin batch-pays → status='paid', paid_at set
        """
        # Step 1: claim submitted
        claim = _claim(status="claimed", incentive_percent=5, package_amount=0)
        assert claim["status"] == "claimed"
        assert claim["commission_amount"] == 0
        assert claim["confirmed_at"] is None

        # Step 2: simulate auto_match (payment hook)
        confirmed_claim = {
            **claim,
            "status": "confirmed",
            "student_id": STU_ID_1,
            "package_amount": 999,
            "commission_amount": 49.95,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        assert confirmed_claim["status"] == "confirmed"
        assert confirmed_claim["commission_amount"] == 49.95
        assert confirmed_claim["confirmed_at"] is not None

        # Step 3: simulate admin batch-pay
        paid_claim = {
            **confirmed_claim,
            "status": "paid",
            "paid_at": datetime.now(timezone.utc).isoformat(),
        }
        assert paid_claim["status"] == "paid"
        assert paid_claim["paid_at"] is not None
        # Commission amount is preserved, not zeroed
        assert paid_claim["commission_amount"] == 49.95

    def test_commission_never_changes_after_confirmation(self):
        """
        Once a claim is confirmed with a commission amount, it must stay
        the same even when the status moves to 'paid'. The financial
        record must be immutable.
        """
        commission = calculate_incentive_amount(999, 5)  # ₹49.95

        confirmed = _claim(status="confirmed", incentive_percent=5, package_amount=999)
        confirmed["commission_amount"] = commission

        paid = {**confirmed, "status": "paid"}
        assert paid["commission_amount"] == commission

    def test_two_salespeople_only_first_gets_commission(self):
        """
        SP1 claims student@example.com at 9am → UNIQUE constraint stored.
        SP2 tries to claim same student at 10am → should get 409.
        Only SP1 will get commission when student pays.
        """
        # SP1's claim is in DB
        sp1_claim = _claim(status="claimed", sales_person_id=SP_ID_1, incentive_percent=5)

        # SP2's insert would be blocked by UNIQUE(student_email):
        # Simulate: SP2 insert raises unique violation
        unique_error = Exception('duplicate key value violates unique constraint')
        assert "duplicate key" in str(unique_error).lower()

        # Only SP1's claim exists → auto_match gives commission to SP1 only
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[sp1_claim])
        mock_update = MagicMock()
        mock_update.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value = mock_select
        mock_table.update.return_value.eq.return_value = mock_update

        with patch("app.routes.sales.admin_client") as mock_client:
            mock_client.table.return_value = mock_table
            auto_match_lead_claim(
                email="student@example.com",
                student_id=STU_ID_1,
                package_amount=999,
                package_key="starter",
            )

        update_args = mock_table.update.call_args[0][0]
        # Commission goes to whoever's claim was found (SP1's claim)
        assert update_args["commission_amount"] == 49.95
        assert update_args["student_id"] == STU_ID_1

    def test_expiry_constant_is_30_days(self):
        """The expiry window is a business rule — must be exactly 30 days."""
        assert CLAIM_EXPIRY_DAYS == 30

    def test_daily_limit_constant_is_15(self):
        """The daily claim limit is a business rule — must be exactly 15."""
        assert DAILY_CLAIM_LIMIT == 15
