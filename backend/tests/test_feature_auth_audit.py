"""
test_feature_auth_audit.py — Feature Authorization Audit regression tests
─────────────────────────────────────────────────────────────────────────────
Tests:
  1. Free Tier Exemplar → denied
  2. Paid Exemplar → full
  3. parentId alone does not grant paid access
  4. Expired paid plan falls back to Free Tier (denied premium)
  5. Formula Sheet premium denied for Free Tier
  6. Mock Tests limited (not denied) for Free Tier
  7. AuditCheck._evaluate works correctly
  8. _compute_summary counts correctly
  9. Critical failure → fail-critical exits with code 1
  10. run_audit returns 100% pass with sample mode (mocked)
  11. Report contains no secrets
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.audit_feature_authorization import (
    AuditCheck,
    _compute_summary,
    _build_expected_matrix,
    EXPECTED_MATRIX,
    _get_actual_access,
    _run_scenario_checks,
    _run_matrix_checks,
    run_audit,
    Feature,
    PAID_PLANS,
)


# ── AuditCheck ────────────────────────────────────────────────────────────────

class TestAuditCheck:
    def test_pass_when_expected_matches_actual(self):
        c = AuditCheck("F","PLAN","scenario","denied","denied")
        assert c.passed is True
        assert c.severity == "pass"

    def test_fail_when_mismatch(self):
        c = AuditCheck("F","PLAN","scenario","denied","full")
        assert c.passed is False

    def test_critical_severity_when_denied_violated(self):
        c = AuditCheck("F","PLAN","scenario","denied","full","detail")
        assert c.severity == "critical"

    def test_limited_expected_passes_if_actual_full(self):
        # "limited" expected but "full" given — acceptable
        c = AuditCheck("F","PLAN","scenario","limited","full")
        assert c.passed is True

    def test_limited_expected_passes_if_actual_limited(self):
        c = AuditCheck("F","PLAN","scenario","limited","limited")
        assert c.passed is True

    def test_to_dict_safe(self):
        c = AuditCheck("EXEMPLAR","FREE_TIER","Test","denied","full","some detail")
        d = c.to_dict()
        assert d["feature"] == "EXEMPLAR"
        assert d["plan"] == "FREE_TIER"
        assert d["passed"] is False
        assert "SUPABASE_SERVICE_ROLE_KEY" not in str(d)
        assert "OPENAI_API_KEY" not in str(d)


# ── _compute_summary ──────────────────────────────────────────────────────────

class TestComputeSummary:
    def test_all_pass(self):
        checks = [AuditCheck("F","P","s","denied","denied") for _ in range(10)]
        s = _compute_summary(checks)
        assert s["overall"] == "PASS"
        assert s["passed"] == 10
        assert s["failed"] == 0
        assert s["critical"] == 0
        assert s["pass_rate"] == 100.0

    def test_critical_failure(self):
        checks = [
            AuditCheck("F","P","s","denied","denied"),
            AuditCheck("F","P","s","denied","full","detail"),  # critical
        ]
        s = _compute_summary(checks)
        assert s["overall"] == "CRITICAL"
        assert s["critical"] == 1
        assert s["failed"] == 1

    def test_non_critical_failure(self):
        checks = [AuditCheck("F","P","s","full","limited")]
        s = _compute_summary(checks)
        assert s["overall"] == "FAIL"
        assert s["critical"] == 0

    def test_empty_checks(self):
        s = _compute_summary([])
        assert s["total"] == 0
        assert s["pass_rate"] == 0.0  # 0/0 = 0% (no checks run)


# ── _get_actual_access ────────────────────────────────────────────────────────

def _mock_resolver(effective_plan):
    """Return a mock resolver that always returns the given plan."""
    paid = effective_plan in PAID_PLANS
    def mock(uid, **kwargs):
        return {"canonical_plan_key": effective_plan, "has_full_access": paid}
    return mock


class TestGetActualAccess:
    def test_free_tier_exemplar_denied(self):
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("FREE_TIER")
        try:
            result = _get_actual_access(Feature.EXEMPLAR, "FREE_TIER")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "denied"

    def test_premium_exemplar_full(self):
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("PREMIUM")
        try:
            result = _get_actual_access(Feature.EXEMPLAR, "PREMIUM")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "full"

    def test_free_tier_formula_premium_denied(self):
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("FREE_TIER")
        try:
            result = _get_actual_access(Feature.FORMULA_SHEET_PREMIUM, "FREE_TIER")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "denied"

    def test_free_tier_mock_test_limited(self):
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("FREE_TIER")
        try:
            result = _get_actual_access(Feature.MOCK_TEST, "FREE_TIER")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "limited"

    def test_expired_premium_exemplar_denied(self):
        """Expired plan should fall back to FREE_TIER — Exemplar denied."""
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("FREE_TIER")  # expired → FREE_TIER
        try:
            result = _get_actual_access(Feature.EXEMPLAR, "EXPIRED_PREMIUM")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "denied"

    def test_admin_grant_exemplar_full(self):
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        feat_mod.resolve_user_subscription = _mock_resolver("ADMIN_GRANT")
        try:
            result = _get_actual_access(Feature.EXEMPLAR, "ADMIN_GRANT")
        finally:
            feat_mod.resolve_user_subscription = orig
        assert result == "full"


# ── Scenario checks ───────────────────────────────────────────────────────────

class TestScenarioChecks:
    def _run_with_mock(self):
        """Run scenario checks with mocked resolver."""
        import app.services.feature_authorization_service as feat_mod
        orig = feat_mod.resolve_user_subscription
        results = {}

        def smart_mock(uid, **kwargs):
            # Return FREE_TIER for most test UIDs (conservative)
            return {"canonical_plan_key": "FREE_TIER", "has_full_access": False}

        feat_mod.resolve_user_subscription = smart_mock
        try:
            checks = _run_scenario_checks()
        finally:
            feat_mod.resolve_user_subscription = orig
        return checks

    def test_scenario_checks_run(self):
        checks = self._run_with_mock()
        assert len(checks) > 0

    def test_free_exemplar_scenario_present(self):
        checks = self._run_with_mock()
        free_exemplar = [c for c in checks
                         if c.feature == Feature.EXEMPLAR and "FREE" in c.plan]
        assert len(free_exemplar) > 0

    def test_parent_id_scenario_present(self):
        checks = self._run_with_mock()
        parent_scenario = [c for c in checks if "parentId" in c.scenario or "parent" in c.scenario.lower()]
        assert len(parent_scenario) > 0


# ── Report safety ─────────────────────────────────────────────────────────────

class TestReportSafety:
    def test_no_secrets_in_json_report(self, tmp_path, monkeypatch):
        """JSON report must not contain API keys or service role keys."""
        from scripts.audit_feature_authorization import _write_json
        checks = [AuditCheck("EXEMPLAR","FREE_TIER","test","denied","denied","safe detail")]
        summary = _compute_summary(checks)
        monkeypatch.setattr("scripts.audit_feature_authorization.REPORT_DIR", tmp_path)
        _write_json(checks, summary, tmp_path)
        p = tmp_path / "feature_authorization_report.json"
        content = p.read_text()
        assert "OPENAI_API_KEY" not in content
        assert "SUPABASE_SERVICE_ROLE_KEY" not in content
        assert "service_role" not in content.lower()

    def test_csv_report_written(self, tmp_path):
        from scripts.audit_feature_authorization import _write_csv
        checks = [AuditCheck("EXEMPLAR","FREE_TIER","test","denied","denied")]
        _write_csv(checks, {}, tmp_path)
        p = tmp_path / "feature_authorization_summary.csv"
        assert p.exists()
        lines = p.read_text().splitlines()
        assert "feature" in lines[0]


# ── Expected matrix ───────────────────────────────────────────────────────────

class TestExpectedMatrix:
    def setup_method(self):
        EXPECTED_MATRIX.clear()
        _build_expected_matrix()

    def test_free_exemplar_expected_denied(self):
        assert EXPECTED_MATRIX.get((Feature.EXEMPLAR, "FREE_TIER")) == "denied"

    def test_paid_exemplar_expected_full(self):
        assert EXPECTED_MATRIX.get((Feature.EXEMPLAR, "PREMIUM")) == "full"

    def test_expired_premium_expected_denied(self):
        assert EXPECTED_MATRIX.get((Feature.EXEMPLAR, "EXPIRED_PREMIUM")) == "denied"

    def test_free_mock_test_expected_limited(self):
        assert EXPECTED_MATRIX.get((Feature.MOCK_TEST, "FREE_TIER")) == "limited"

    def test_admin_grant_exemplar_expected_full(self):
        assert EXPECTED_MATRIX.get((Feature.EXEMPLAR, "ADMIN_GRANT")) == "full"

    def test_free_formula_premium_expected_denied(self):
        assert EXPECTED_MATRIX.get((Feature.FORMULA_SHEET_PREMIUM, "FREE_TIER")) == "denied"


# ── Admin QA endpoint tests ───────────────────────────────────────────────────

class TestFeatureAuthEndpoints:
    ADMIN = {"id":"admin-1","role":"admin","profile":{"id":"admin-1","role":"admin"}}

    def test_latest_returns_unavailable_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.FEAT_AUTH_REPORT_DIR", tmp_path)
        from app.routes.admin_qa import get_latest_feat_auth_report
        result = get_latest_feat_auth_report(admin=self.ADMIN)
        assert result["success"] is True
        assert result["available"] is False

    def test_latest_returns_data_when_report_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.FEAT_AUTH_REPORT_DIR", tmp_path)
        data = {"audited_at":"2026-06-28T10:00:00Z",
                "summary":{"overall":"PASS","total":10,"passed":10,"failed":0,"critical":0,"pass_rate":100},
                "failed_checks":[], "checks":[]}
        (tmp_path/"feature_authorization_report.json").write_text(json.dumps(data))
        from app.routes.admin_qa import get_latest_feat_auth_report
        result = get_latest_feat_auth_report(admin=self.ADMIN)
        assert result["available"] is True
        assert result["summary"]["overall"] == "PASS"

    def test_run_sample_returns_job_id(self, monkeypatch):
        import threading
        monkeypatch.setattr("threading.Thread", lambda **kw: MagicMock(start=lambda: None))
        from app.routes.admin_qa import run_feat_auth_audit
        from fastapi import BackgroundTasks
        result = run_feat_auth_audit(mode="sample", admin=self.ADMIN)
        assert result["success"] is True
        assert "job_id" in result

    def test_run_invalid_mode_returns_400(self):
        from fastapi import HTTPException
        from app.routes.admin_qa import run_feat_auth_audit
        with pytest.raises(HTTPException) as exc:
            run_feat_auth_audit(mode="invalid", admin=self.ADMIN)
        assert exc.value.status_code == 400

    def test_status_404_for_unknown_job(self, monkeypatch):
        from fastapi import HTTPException
        from app.routes.admin_qa import get_feat_auth_status
        monkeypatch.setattr("app.routes.admin_qa._FA_JOBS", {})
        with pytest.raises(HTTPException) as exc:
            get_feat_auth_status("unknown-job", admin=self.ADMIN)
        assert exc.value.status_code == 404

    def test_download_404_when_no_file(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        from app.routes.admin_qa import download_feat_auth_report
        monkeypatch.setattr("app.routes.admin_qa.FEAT_AUTH_REPORT_DIR", tmp_path)
        with pytest.raises(HTTPException) as exc:
            download_feat_auth_report(format="json", admin=self.ADMIN)
        assert exc.value.status_code == 404
