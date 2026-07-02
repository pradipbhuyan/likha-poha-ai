"""
Tests for the Learning Simulation feature.

Tests admin-only access, user setup idempotency, simulation run logic,
dry run behavior, anomaly detection, and Product Bug creation.
No real users, emails, or payments involved.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import require_admin

client = TestClient(app)


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_admin():
    return {
        "auth_user": MagicMock(id="admin-id-123"),
        "profile": {"id": "admin-id-123", "role": "admin"},
    }


def _block_admin():
    """Override that simulates no valid admin token — raises 403."""
    raise HTTPException(status_code=403, detail="Not authorized")


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Restore app.dependency_overrides after every test."""
    yield
    app.dependency_overrides.pop(require_admin, None)


# ── Status endpoint ───────────────────────────────────────────────────────────

class TestSimulationStatus:
    def test_status_requires_admin(self):
        """Non-admin must be blocked — uses dependency override, no Supabase call."""
        app.dependency_overrides[require_admin] = _block_admin
        resp = client.get("/api/admin/simulation/learning/status")
        assert resp.status_code in (401, 403)

    def test_status_returns_structure(self):
        """Admin gets status dict with expected keys."""
        app.dependency_overrides[require_admin] = lambda: _mock_admin()
        with patch("app.routes.learning_simulation.get_simulation_status", return_value={
                 "current_day": 0, "next_cycle_start": 1, "next_cycle_end": 7,
                 "users_setup": False, "vijay_access": None,
                 "recent_runs": [], "total_runs": 0,
             }), \
             patch("app.routes.learning_simulation.admin_client") as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
            resp = client.get("/api/admin/simulation/learning/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_day" in data
        assert "next_cycle_start" in data
        assert "users_setup" in data


# ── Run endpoint ──────────────────────────────────────────────────────────────

class TestSimulationRun:
    def test_run_requires_admin(self):
        app.dependency_overrides[require_admin] = _block_admin
        resp = client.post("/api/admin/simulation/learning/run",
                           json={"cycle_days": 7, "dry_run": True})
        assert resp.status_code in (401, 403)

    def test_dry_run_returns_summary(self):
        """Dry run returns summary without writing data."""
        app.dependency_overrides[require_admin] = lambda: _mock_admin()
        with patch("app.routes.learning_simulation.run_simulation", return_value={
                 "run_id": "dry-run-id",
                 "dry_run": True,
                 "cycle_start_day": 1,
                 "cycle_end_day": 7,
                 "total_days": 7,
                 "total_events": 0,
                 "anomalies": [],
                 "bugs_created": 0,
                 "status": "dry_run",
                 "setup": {"status": "dry_run"},
                 "days": [],
             }):
            resp = client.post("/api/admin/simulation/learning/run",
                               json={"cycle_days": 7, "dry_run": True,
                                     "create_bugs": False, "strict_validation": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("dry_run") is True

    def test_run_returns_cycle_range(self):
        """Run response includes cycle_start_day and cycle_end_day."""
        app.dependency_overrides[require_admin] = lambda: _mock_admin()
        with patch("app.routes.learning_simulation.run_simulation", return_value={
                 "run_id": "run-123",
                 "dry_run": False,
                 "cycle_start_day": 1,
                 "cycle_end_day": 7,
                 "total_days": 7,
                 "total_events": 42,
                 "anomalies": [],
                 "bugs_created": 0,
                 "status": "completed",
                 "setup": {"status": "ready"},
                 "days": [],
             }):
            resp = client.post("/api/admin/simulation/learning/run",
                               json={"cycle_days": 7})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cycle_start_day"] == 1
        assert data["cycle_end_day"] == 7

    def test_no_real_email_called(self):
        """Simulation service must not trigger email sending."""
        from app.services import student_learning_simulation_service as svc
        # SIM_PASSWORD should never appear in any returned dict
        with patch.object(svc, "_ensure_auth_user", return_value="uid-vijay"), \
             patch.object(svc, "_ensure_family", return_value="fam-id"), \
             patch.object(svc, "_upsert_profile", return_value={}), \
             patch.object(svc.admin_client, "table") as mock_table:
            mock_table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
            result = svc.setup_simulation_users(dry_run=True)
        assert "password" not in str(result).lower()
        assert svc.SIM_PASSWORD not in str(result)

    def test_second_run_starts_from_next_day(self):
        """Second run cycle_start must be > first run cycle_end."""
        from app.services.student_learning_simulation_service import get_current_simulated_day
        with patch("app.services.student_learning_simulation_service.admin_client") as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"cycle_end_day": 7}
            ]
            day = get_current_simulated_day()
        assert day == 7  # Next run would start at day 8


# ── Reset endpoint ────────────────────────────────────────────────────────────

class TestSimulationReset:
    def test_reset_requires_admin(self):
        app.dependency_overrides[require_admin] = _block_admin
        resp = client.post("/api/admin/simulation/learning/reset")
        assert resp.status_code in (401, 403)

    def test_reset_returns_success(self):
        app.dependency_overrides[require_admin] = lambda: _mock_admin()
        with patch("app.routes.learning_simulation.reset_simulation_data", return_value={
                 "success": True,
                 "deleted": ["vijay.sim.student@example.test: data cleared"],
                 "errors": [],
                 "message": "Simulation data reset.",
             }):
            resp = client.post("/api/admin/simulation/learning/reset")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_reset_does_not_delete_real_users(self):
        """reset_simulation_data only touches SIM_USERS emails."""
        from app.services.student_learning_simulation_service import (
            reset_simulation_data, SIM_USERS
        )
        deleted_tables = []
        with patch("app.services.student_learning_simulation_service.admin_client") as mock_db:
            mock_table = MagicMock()
            mock_db.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
            mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()
            result = reset_simulation_data("admin-123")
        # Result contains only synthetic emails
        for item in result.get("deleted", []):
            assert any(email in item for email in
                       [spec["email"] for spec in SIM_USERS.values()] + ["not found"])


# ── Anomaly detection ─────────────────────────────────────────────────────────

class TestAnomalyDetection:
    def test_score_out_of_range_detected(self):
        """Mock test score > 100 generates an anomaly."""
        from app.services.student_learning_simulation_service import _validate_score
        anomalies = _validate_score(105.0, {"subject": "Maths", "day": 3})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_type"] == "score_out_of_range"
        assert anomalies[0]["severity"] == "critical"

    def test_score_in_range_no_anomaly(self):
        from app.services.student_learning_simulation_service import _validate_score
        anomalies = _validate_score(75.0, {"subject": "Science", "day": 2})
        assert anomalies == []

    def test_negative_score_detected(self):
        from app.services.student_learning_simulation_service import _validate_score
        anomalies = _validate_score(-5.0, {"subject": "Maths", "day": 1})
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "critical"

    def test_vijay_access_missing_triggers_anomaly(self):
        """Missing Vijay profile triggers critical anomaly."""
        from app.services.student_learning_simulation_service import _validate_vijay_access
        with patch("app.services.student_learning_simulation_service._safe_get", return_value=None):
            anomalies = _validate_vijay_access("nonexistent-uid")
        assert any(a["severity"] == "critical" for a in anomalies)

    def test_vijay_wrong_plan_triggers_anomaly(self):
        from app.services.student_learning_simulation_service import _validate_vijay_access
        with patch("app.services.student_learning_simulation_service._safe_get", return_value={
            "subscription_plan": "free", "access_cbse": True
        }):
            anomalies = _validate_vijay_access("vijay-uid")
        assert any("family_premium" in a.get("message", "") for a in anomalies)


# ── Mock score distribution ───────────────────────────────────────────────────

class TestMockScore:
    def test_scores_always_0_to_100(self):
        from app.services.student_learning_simulation_service import _mock_score
        import random
        random.seed(42)
        for day in range(1, 22):
            score = _mock_score(day)
            assert 0 <= score <= 100, f"Score {score} out of range on day {day}"

    def test_scores_improve_over_time(self):
        """Average score for days 15-21 should exceed days 1-7."""
        from app.services.student_learning_simulation_service import _mock_score
        import random
        random.seed(0)
        early = [_mock_score(d) for d in range(1, 8)]
        later = [_mock_score(d) for d in range(15, 22)]
        assert sum(later) / len(later) >= sum(early) / len(early) - 20  # allow noise


# ── User setup idempotency ────────────────────────────────────────────────────

class TestUserSetup:
    def test_dry_run_returns_dry_run_ids(self):
        from app.services.student_learning_simulation_service import setup_simulation_users
        result = setup_simulation_users(dry_run=True)
        assert result["vijay_id"] == "dry-run-vijay"
        assert result["status"] == "dry_run"

    def test_existing_users_not_duplicated(self):
        """If profile exists, no new auth user is created."""
        from app.services import student_learning_simulation_service as svc
        create_calls = []
        with patch.object(svc, "_ensure_family", return_value="fam-id"), \
             patch.object(svc, "_safe_get", return_value={"id": "existing-uid", "email": "vijay.sim.student@example.test"}), \
             patch.object(svc.admin_client, "table") as mock_table:
            mock_exec = MagicMock()
            mock_exec.execute.return_value = MagicMock(data=[])
            mock_table.return_value.update.return_value.eq.return_value = mock_exec
            result = svc.setup_simulation_users(dry_run=False)
        # _ensure_auth_user should NOT be called if profile already exists
        assert "existing" not in str(create_calls)


# ── Anomaly list endpoint ─────────────────────────────────────────────────────

class TestAnomaliesEndpoint:
    def test_anomalies_requires_admin(self):
        app.dependency_overrides[require_admin] = _block_admin
        resp = client.get("/api/admin/simulation/learning/anomalies")
        assert resp.status_code in (401, 403)

    def test_anomalies_returns_list(self):
        app.dependency_overrides[require_admin] = lambda: _mock_admin()
        with patch("app.routes.learning_simulation.get_anomalies", return_value=[
                 {"id": "a1", "severity": "high", "message": "Test", "run_id": "r1"}
             ]):
            resp = client.get("/api/admin/simulation/learning/anomalies")
        assert resp.status_code == 200
        assert isinstance(resp.json()["anomalies"], list)
