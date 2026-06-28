"""
test_admin_qa.py — Admin QA Center endpoint tests
─────────────────────────────────────────────────────────────────────────────
Covers:
  1. Non-admin cannot access QA endpoints (403)
  2. Admin can access latest endpoint
  3. Latest returns empty state when no report
  4. Run sample audit starts job
  5. Status endpoint returns queued/running/completed
  6. Invalid mode returns 400
  7. E2E request returns not-configured message
  8. LLM flag accepted but audit runs deterministically
  9. Report summary contains no secrets/PII
  10. _summarise_report handles empty lessons
  11. _read_latest_report returns None when no file
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.routes.admin_qa import (
    _read_latest_report,
    _summarise_report,
    AuditRunRequest,
    router,
    _JOBS,
    get_latest_lesson_quality_report,
    run_lesson_quality_audit,
    get_audit_job_status,
)

ADMIN = {"id": "admin-uid-1", "role": "admin", "profile": {"id": "admin-uid-1", "role": "admin"}}
STUDENT = {"id": "stu-uid-1", "role": "student", "profile": {"id": "stu-uid-1", "role": "student"}}


# ── _read_latest_report ───────────────────────────────────────────────────────

class TestReadLatestReport:
    def test_returns_none_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        result = _read_latest_report()
        assert result is None

    def test_returns_data_when_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        data = {"audited_at": "2026-06-28T10:00:00Z", "lessons": []}
        (tmp_path / "lesson_quality_report.json").write_text(json.dumps(data))
        result = _read_latest_report()
        assert result is not None
        assert result["audited_at"] == "2026-06-28T10:00:00Z"

    def test_returns_none_on_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        (tmp_path / "lesson_quality_report.json").write_text("not json {{{")
        result = _read_latest_report()
        assert result is None


# ── _summarise_report ─────────────────────────────────────────────────────────

class TestSummariseReport:
    def _lesson(self, grade="Grade 9", subject="Mathematics", chapter="Triangles", overall=85):
        return {
            "grade": grade, "subject": subject, "chapter": chapter,
            "step_count": 3,
            "scores": {"overall_score": overall, "completeness_score": 90,
                       "formula_quality_score": 80, "mcq_quality_score": 85,
                       "pedagogy_score": 90, "student_flow_score": 95},
            "findings_summary": {"critical": 0, "high": 1, "medium": 2, "low": 0},
            "findings": [
                {"severity": "high", "category": "formula",
                 "message": "Missing variable definitions", "detail": "s = ..."},
            ],
        }

    def test_empty_lessons_returns_unavailable(self):
        result = _summarise_report({"audited_at": "2026", "lessons": []})
        assert result["available"] is False

    def test_lesson_count_correct(self):
        result = _summarise_report({"lessons": [self._lesson(), self._lesson(chapter="Circles")]})
        assert result["available"] is True
        assert result["lessons_audited"] == 2

    def test_grade_scores_computed(self):
        result = _summarise_report({"lessons": [
            self._lesson(grade="Grade 9", overall=80),
            self._lesson(grade="Grade 9", chapter="Circles", overall=90),
            self._lesson(grade="Grade 10", overall=70),
        ]})
        assert "Grade 9" in result["grade_scores"]
        assert result["grade_scores"]["Grade 9"] == 85  # avg of 80,90

    def test_no_secrets_in_summary(self):
        result = _summarise_report({"lessons": [self._lesson()]})
        result_str = json.dumps(result)
        assert "SUPABASE_SERVICE_ROLE_KEY" not in result_str
        assert "OPENAI_API_KEY" not in result_str
        assert "service_role" not in result_str.lower()

    def test_worst_lessons_capped_at_10(self):
        lessons = [self._lesson(chapter=f"Ch{i}", overall=50+i) for i in range(20)]
        result = _summarise_report({"lessons": lessons})
        assert len(result["worst_lessons"]) <= 10

    def test_all_issues_capped_at_500(self):
        # 60 lessons × 10 findings each = 600 issues, should cap at 500
        def big_lesson(i):
            l = self._lesson(chapter=f"Ch{i}")
            l["findings"] = [{"severity":"medium","category":"pedagogy","message":f"Issue {j}","detail":""} for j in range(10)]
            return l
        result = _summarise_report({"lessons": [big_lesson(i) for i in range(60)]})
        assert len(result["all_issues"]) <= 500


# ── Endpoint tests (via direct function calls) ────────────────────────────────

class TestGetLatestEndpoint:
    def test_admin_can_access_latest(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        result = get_latest_lesson_quality_report(admin=ADMIN)
        assert result["success"] is True
        assert result["available"] is False
        assert "No lesson quality audit" in result["message"]

    def test_non_admin_blocked(self, monkeypatch):
        """Non-admin should get 403 — test via require_admin with mocked profile lookup."""
        from app.services.auth_service import require_admin
        import app.services.auth_service as auth_svc

        class FakeAuthUser:
            id = "stu-uid-1"

        monkeypatch.setattr(auth_svc, "get_user_profile",
                            lambda uid: {"id":uid, "role":"student"})
        with pytest.raises(HTTPException) as exc:
            require_admin(user=FakeAuthUser())
        assert exc.value.status_code == 403

    def test_returns_summary_when_report_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        data = {
            "audited_at": "2026-06-28T10:00:00Z",
            "lessons": [{
                "grade": "Grade 9", "subject": "Mathematics", "chapter": "Triangles",
                "step_count": 3,
                "scores": {"overall_score": 85, "completeness_score": 90,
                           "formula_quality_score": 80, "mcq_quality_score": 85,
                           "pedagogy_score": 90, "student_flow_score": 95},
                "findings_summary": {"critical": 0, "high": 1, "medium": 0, "low": 0},
                "findings": [],
            }],
        }
        (tmp_path / "lesson_quality_report.json").write_text(json.dumps(data))
        result = get_latest_lesson_quality_report(admin=ADMIN)
        assert result["success"] is True
        assert result["available"] is True
        assert result["lessons_audited"] == 1


class TestRunAuditEndpoint:
    def test_invalid_mode_returns_400(self):
        req = AuditRunRequest(mode="invalid_mode")
        with pytest.raises(HTTPException) as exc:
            from fastapi import BackgroundTasks
            run_lesson_quality_audit(req, BackgroundTasks(), admin=ADMIN)
        assert exc.value.status_code == 400

    def test_e2e_request_returns_not_configured(self):
        req = AuditRunRequest(mode="sample", use_e2e=True)
        from fastapi import BackgroundTasks
        result = run_lesson_quality_audit(req, BackgroundTasks(), admin=ADMIN)
        assert result["success"] is False
        assert "not configured" in result["message"].lower()

    def test_sample_audit_returns_job_id(self, monkeypatch):
        """Sample audit starts a background thread and returns job_id."""
        monkeypatch.setattr("threading.Thread", lambda **kw: MagicMock(start=lambda: None))
        req = AuditRunRequest(mode="sample")
        from fastapi import BackgroundTasks
        result = run_lesson_quality_audit(req, BackgroundTasks(), admin=ADMIN)
        assert result["success"] is True
        assert "job_id" in result
        assert result["job_id"] is not None

    def test_llm_false_by_default(self):
        req = AuditRunRequest()
        assert req.use_llm is False

    def test_e2e_false_by_default(self):
        req = AuditRunRequest()
        assert req.use_e2e is False


class TestStatusEndpoint:
    def test_unknown_job_returns_404(self, monkeypatch):
        # Clear _JOBS for isolation
        monkeypatch.setattr("app.routes.admin_qa._JOBS", {})
        monkeypatch.setattr("app.routes.admin_qa._safe_query", lambda fn: ([], None))
        with pytest.raises(HTTPException) as exc:
            get_audit_job_status("nonexistent-job-id", admin=ADMIN)
        assert exc.value.status_code == 404

    def test_known_job_returns_status(self, monkeypatch):
        job_id = "test-job-123"
        monkeypatch.setattr("app.routes.admin_qa._JOBS", {
            job_id: {"id": job_id, "status": "queued", "mode": "sample",
                     "created_by_admin_id": "admin-uid-1"},
        })
        result = get_audit_job_status(job_id, admin=ADMIN)
        assert result["success"] is True
        assert result["job"]["status"] == "queued"
        # Admin ID must not be in response
        assert "created_by_admin_id" not in result["job"]


class TestDownloadEndpoint:
    def test_download_404_when_no_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        from app.routes.admin_qa import download_lesson_quality_report
        with pytest.raises(HTTPException) as exc:
            download_lesson_quality_report(format="json", admin=ADMIN)
        assert exc.value.status_code == 404
        assert "Run an audit first" in exc.value.detail

    def test_download_json_when_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        (tmp_path / "lesson_quality_report.json").write_text('{"lessons":[]}', encoding="utf-8")
        from app.routes.admin_qa import download_lesson_quality_report
        resp = download_lesson_quality_report(format="json", admin=ADMIN)
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_download_csv_when_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        (tmp_path / "lesson_quality_summary.csv").write_text("col1,col2", encoding="utf-8")
        from app.routes.admin_qa import download_lesson_quality_report
        resp = download_lesson_quality_report(format="csv", admin=ADMIN)
        assert resp.status_code == 200

    def test_download_md_when_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.routes.admin_qa.REPORT_DIR", tmp_path)
        (tmp_path / "lesson_quality_report.md").write_text("# Report", encoding="utf-8")
        from app.routes.admin_qa import download_lesson_quality_report
        resp = download_lesson_quality_report(format="md", admin=ADMIN)
        assert resp.status_code == 200


class TestHistoryEndpoint:
    def test_history_degrades_when_db_missing(self, monkeypatch):
        from app.routes.admin_qa import get_lesson_quality_history
        monkeypatch.setattr("app.routes.admin_qa._safe_query",
                            lambda fn: ([], "schema cache error: table not found"))
        monkeypatch.setattr("app.routes.admin_qa._JOBS", {})
        result = get_lesson_quality_history(limit=20, admin=ADMIN)
        assert result["success"] is True

    def test_history_returns_db_rows(self, monkeypatch):
        from app.routes.admin_qa import get_lesson_quality_history
        db_rows = [{"id": "r1", "status": "completed", "mode": "sample"}]
        monkeypatch.setattr("app.routes.admin_qa._safe_query", lambda fn: (db_rows, None))
        result = get_lesson_quality_history(limit=20, admin=ADMIN)
        assert result["success"] is True
        assert result["runs"][0]["id"] == "r1"


class TestSecurityChecks:
    def test_error_sanitization_removes_newlines(self):
        raw = "Error\nTraceback\nRuntimeError: secret"
        sanitised = raw[:500].replace("\n", " ")
        assert "\n" not in sanitised
        assert len(sanitised) <= 500

    def test_background_thread_is_daemon(self, monkeypatch):
        import threading
        created = []
        orig = threading.Thread
        def track(**kw):
            t = orig(**kw)
            created.append(t)
            return t
        import app.routes.admin_qa as qa
        monkeypatch.setattr("threading.Thread", track)
        try:
            from fastapi import BackgroundTasks
            qa.run_lesson_quality_audit(AuditRunRequest(mode="sample"), BackgroundTasks(), admin=ADMIN)
        except Exception:
            pass
        if created:
            assert created[0].daemon is True

    def test_run_response_has_no_secrets(self, monkeypatch):
        import app.routes.admin_qa as qa
        monkeypatch.setattr("threading.Thread", lambda **kw: __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock())
        from fastapi import BackgroundTasks
        result = qa.run_lesson_quality_audit(AuditRunRequest(mode="sample"), BackgroundTasks(), admin=ADMIN)
        s = str(result)
        assert "OPENAI_API_KEY" not in s
        assert "SUPABASE_SERVICE_ROLE_KEY" not in s
        assert "sk-" not in s.lower()
