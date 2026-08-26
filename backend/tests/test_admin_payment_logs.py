"""
Tests for GET /api/admin-control/payment-logs (app/routes/admin_payment_logs.py).

Covers:
  - require_admin dependency is present on the route
  - Happy path: payments enriched with profile data, summary stats, 12-month trend
  - Empty payment table
  - subscription_payments query failure → safe empty response
  - profiles batch lookup failure → falls back to metadata, doesn't crash
  - Metadata fallback for username/email when no matching profile
  - failure_reason extraction from metadata (failure_reason then error)
  - created_at/verified_at truncated to 19 chars (drop fractional seconds/tz)
  - monthly_revenue only counts the current month; total_revenue counts all paid
  - active_paid_users dedupes by email
  - plan_distribution groups by plan_key, "unknown" fallback
  - 12-month trend has exactly 12 buckets, current month bucket picks up current payments
  - Payments with no parent_id are skipped in the profile batch lookup
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import app.routes.admin_payment_logs as admin_payment_logs_route
from app.routes.admin_payment_logs import get_payment_logs

ADMIN_CONTEXT = {"profile": {"id": "admin-1", "role": "admin"}}


class FakeTable:
    """Minimal fake for admin_client.table(name).select(...)... .execute()."""

    def __init__(self, data_by_table, exceptions_by_table=None):
        self._data_by_table = data_by_table
        self._exceptions_by_table = exceptions_by_table or {}
        self._name = None

    def __call__(self, name):
        self._name = name
        return self

    def select(self, *_a, **_kw):
        return self

    def order(self, *_a, **_kw):
        return self

    def in_(self, *_a, **_kw):
        return self

    def execute(self):
        if self._name in self._exceptions_by_table:
            raise self._exceptions_by_table[self._name]

        class R:
            data = self._data_by_table.get(self._name, [])
        return R()


def _make_client(payments=None, profiles=None, raise_on=None):
    table = FakeTable(
        {"subscription_payments": payments or [], "profiles": profiles or []},
        exceptions_by_table={t: Exception("boom") for t in (raise_on or [])},
    )

    class FakeClient:
        def table(self, name):
            return table(name)

    return FakeClient()


def _payment(**overrides):
    base = {
        "id": "pay-1",
        "razorpay_order_id": "order_1",
        "razorpay_payment_id": "rzp_1",
        "status": "paid",
        "plan_key": "starter",
        "amount": 299,
        "currency": "INR",
        "parent_id": "parent-1",
        "created_at": "2026-01-15T10:00:00.123456+00:00",
        "verified_at": "2026-01-15T10:01:00.123456+00:00",
        "metadata": {},
    }
    base.update(overrides)
    return base


# ── Route requires admin ──────────────────────────────────────────────────────

def test_payment_logs_requires_admin():
    """get_payment_logs function signature has the admin dependency."""
    sig = inspect.signature(get_payment_logs)
    assert "admin" in sig.parameters


# ── Empty / failure paths ─────────────────────────────────────────────────────

def test_empty_payments_table_returns_empty_lists(monkeypatch):
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=[], profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    assert result["success"] is True
    assert result["payments"] == []
    assert result["summary"]["total_transactions"] == 0
    assert result["summary"]["monthly_revenue"] == 0
    assert result["summary"]["total_revenue"] == 0
    assert result["summary"]["active_paid_users"] == 0
    assert len(result["trends"]) == 12


def test_subscription_payments_query_failure_returns_safe_empty_response(monkeypatch):
    """A DB error on the payments table itself must not raise — the route degrades gracefully."""
    monkeypatch.setattr(
        admin_payment_logs_route, "admin_client",
        _make_client(payments=[], profiles=[], raise_on=["subscription_payments"]),
    )

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    assert result == {"success": True, "payments": [], "summary": {}, "trends": []}


def test_profiles_batch_lookup_failure_falls_back_to_metadata(monkeypatch):
    """If the profiles join fails, payments must still be enriched from metadata, not crash."""
    payments = [_payment(parent_id="parent-1", metadata={"signup_role": "meta-user", "signup_email": "meta@test.com"})]
    monkeypatch.setattr(
        admin_payment_logs_route, "admin_client",
        _make_client(payments=payments, profiles=[], raise_on=["profiles"]),
    )

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    assert result["success"] is True
    assert len(result["payments"]) == 1
    assert result["payments"][0]["username"] == "meta-user"
    assert result["payments"][0]["email"] == "meta@test.com"


# ── Enrichment ─────────────────────────────────────────────────────────────────

def test_payment_enriched_with_profile_data(monkeypatch):
    payments = [_payment(parent_id="parent-1")]
    profiles = [{"id": "parent-1", "username": "priya", "email": "priya@test.com", "grade": "Grade 9", "board": "CBSE"}]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=profiles))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    row = result["payments"][0]
    assert row["username"] == "priya"
    assert row["email"] == "priya@test.com"
    assert row["grade"] == "Grade 9"
    assert row["order_id"] == "order_1"
    assert row["payment_id"] == "rzp_1"
    assert row["amount"] == 299
    assert row["status"] == "paid"


def test_payment_with_no_parent_id_uses_metadata_fallback_and_dash(monkeypatch):
    """A payment with no parent_id can't be profile-joined — must fall back gracefully, not KeyError."""
    payments = [_payment(parent_id=None, metadata={})]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    row = result["payments"][0]
    assert row["username"] == "—"
    assert row["email"] == "—"
    assert row["grade"] == "—"


def test_payment_with_no_parent_id_excluded_from_profile_batch_lookup(monkeypatch):
    """Payments with parent_id=None must not appear in the profiles .in_() batch lookup set."""
    payments = [_payment(parent_id=None), _payment(id="pay-2", parent_id="parent-2")]
    captured_ids = {}

    class TrackingTable(FakeTable):
        def in_(self, col, ids):
            captured_ids["ids"] = ids
            return super().in_(col, ids)

    table = TrackingTable({"subscription_payments": payments, "profiles": []})

    class FakeClient:
        def table(self, name):
            return table(name)

    monkeypatch.setattr(admin_payment_logs_route, "admin_client", FakeClient())

    get_payment_logs(admin=ADMIN_CONTEXT)

    assert captured_ids["ids"] == ["parent-2"]


def test_failure_reason_prefers_failure_reason_over_error(monkeypatch):
    payments = [_payment(status="failed", metadata={"failure_reason": "card declined", "error": "generic"})]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)
    assert result["payments"][0]["failure_reason"] == "card declined"


def test_failure_reason_falls_back_to_error_field(monkeypatch):
    payments = [_payment(status="failed", metadata={"error": "signature mismatch"})]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)
    assert result["payments"][0]["failure_reason"] == "signature mismatch"


def test_timestamps_truncated_to_19_chars(monkeypatch):
    """created_at/verified_at drop fractional seconds and timezone suffix for display."""
    payments = [_payment(
        created_at="2026-01-15T10:00:00.123456+00:00",
        verified_at="2026-01-15T10:01:00.999999+00:00",
    )]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)
    row = result["payments"][0]
    assert row["created_at"] == "2026-01-15T10:00:00"
    assert row["verified_at"] == "2026-01-15T10:01:00"


# ── Summary stats ──────────────────────────────────────────────────────────────

def test_total_revenue_sums_all_paid_regardless_of_month(monkeypatch):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=200)
    payments = [
        _payment(id="p1", status="paid", amount=100, created_at=now.isoformat()),
        _payment(id="p2", status="paid", amount=200, created_at=old.isoformat()),
        _payment(id="p3", status="failed", amount=999, created_at=now.isoformat()),
    ]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    # total_revenue: only paid payments count, regardless of month (100 + 200)
    assert result["summary"]["total_revenue"] == 300
    assert result["summary"]["total_transactions"] == 2
    assert result["summary"]["failed_transactions"] == 1


def test_monthly_revenue_only_counts_current_month(monkeypatch):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=200)  # a different month for sure
    payments = [
        _payment(id="p1", status="paid", amount=100, created_at=now.isoformat()),
        _payment(id="p2", status="paid", amount=200, created_at=old.isoformat()),
    ]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    assert result["summary"]["monthly_revenue"] == 100
    assert result["summary"]["total_revenue"] == 300


def test_active_paid_users_dedupes_by_email(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    payments = [
        _payment(id="p1", status="paid", parent_id="parent-1", created_at=now),
        _payment(id="p2", status="paid", parent_id="parent-1", created_at=now),  # same parent, second payment
        _payment(id="p3", status="paid", parent_id="parent-2", created_at=now),
    ]
    profiles = [
        {"id": "parent-1", "username": "a", "email": "a@test.com", "grade": None, "board": None},
        {"id": "parent-2", "username": "b", "email": "b@test.com", "grade": None, "board": None},
    ]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=profiles))

    result = get_payment_logs(admin=ADMIN_CONTEXT)
    assert result["summary"]["active_paid_users"] == 2


def test_plan_distribution_groups_by_plan_key_with_unknown_fallback(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    payments = [
        _payment(id="p1", status="paid", plan_key="starter", created_at=now),
        _payment(id="p2", status="paid", plan_key="starter", created_at=now),
        _payment(id="p3", status="paid", plan_key="family_premium", created_at=now),
        _payment(id="p4", status="paid", plan_key=None, created_at=now),
    ]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)
    dist = result["summary"]["plan_distribution"]
    assert dist["starter"] == 2
    assert dist["family_premium"] == 1
    assert dist["unknown"] == 1


# ── 12-month trend ─────────────────────────────────────────────────────────────

def test_trend_has_exactly_12_months_each_with_required_keys(monkeypatch):
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=[], profiles=[]))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    assert len(result["trends"]) == 12
    for bucket in result["trends"]:
        assert set(bucket.keys()) == {"month", "label", "revenue", "users"}


def test_trend_current_month_bucket_picks_up_current_payment(monkeypatch):
    now = datetime.now(timezone.utc)
    payments = [_payment(status="paid", amount=499, parent_id="parent-1", created_at=now.isoformat())]
    profiles = [{"id": "parent-1", "username": "u", "email": "u@test.com", "grade": None, "board": None}]
    monkeypatch.setattr(admin_payment_logs_route, "admin_client", _make_client(payments=payments, profiles=profiles))

    result = get_payment_logs(admin=ADMIN_CONTEXT)

    this_month_label = now.strftime("%Y-%m")
    current_bucket = next(b for b in result["trends"] if b["month"] == this_month_label)
    assert current_bucket["revenue"] == 499
    assert current_bucket["users"] == 1
    # The current month must be the LAST bucket (most recent, per the range(11, -1, -1) order)
    assert result["trends"][-1]["month"] == this_month_label
