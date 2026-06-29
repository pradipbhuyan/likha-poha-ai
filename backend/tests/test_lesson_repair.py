"""
test_lesson_repair.py — Backend tests for the Admin Lesson Repair workflow.

Covers:
- Admin-only enforcement on all endpoints
- Repair task creation from audit report
- Missing/empty/placeholder section detection
- LLM invalid JSON fails safely (original untouched)
- Validation blocks bad repair draft
- Valid repair draft becomes ready_for_review
- Publish impossible without approval
- Report download works
- No secrets exposed in responses
- Job progress counter updates
- Role conflict (approved → published flow)
"""
import json
import uuid
from types import SimpleNamespace
from fastapi.testclient import TestClient

import pytest

from app.main import app
from app.services.auth_service import get_current_user, require_admin


# ── Helpers ───────────────────────────────────────────────────────────────────

ADMIN_ID = "admin-test-0001"


def _make_admin():
    return {
        "id": ADMIN_ID,
        "email": "admin@test.com",
        "profile": {"id": ADMIN_ID, "email": "admin@test.com", "role": "admin"},
    }


def _make_student():
    # Must be a valid UUID to avoid Supabase type errors during auth lookup
    return SimpleNamespace(id="00000000-0000-0000-0000-000000000099", email="student@test.com")


def _make_audit_report(failed_lessons=None):
    """Create a minimal fake audit report with controllable failures."""
    if failed_lessons is None:
        failed_lessons = [_make_failed_lesson()]
    return {
        "audited_at": "2026-06-29T10:00:00+00:00",
        "summary": {
            "lessons_audited": len(failed_lessons),
            "critical_issues": sum(l.get("issue_counts", {}).get("critical", 0) for l in failed_lessons),
            "avg_overall_score": 40,
            "overall": "CRITICAL",
        },
        "lessons": failed_lessons,
    }


def _make_failed_lesson(grade="Grade 9", subject="Science", chapter="Matter", step_title="States"):
    return {
        "grade": grade, "subject": subject, "chapter": chapter, "step_title": step_title,
        "sections_found": 3, "sections_total": 8,
        "missing_sections": ["introduction", "simple_explanation", "common_mistake", "summary", "quick_check_question"],
        "section_results": {},
        "scores": {"section_presence_score": 37, "section_depth_score": 25, "overall_lesson_score": 31},
        "issue_counts": {"critical": 5, "high": 3, "total": 8},
        "all_issues": [
            {"severity": "critical", "section": "introduction", "issue": "Section 'introduction' is missing."},
            {"severity": "critical", "section": "simple_explanation", "issue": "Section 'simple_explanation' is missing."},
            {"severity": "high", "section": "worked_example", "issue": "Worked example missing final answer."},
        ],
        "audited_at": "2026-06-29T10:00:00+00:00",
    }


# ── validate_repaired_draft tests ─────────────────────────────────────────────

class TestValidateRepairedDraft:
    """Unit tests for the validation logic (no HTTP, pure function calls)."""

    def test_valid_draft_passes(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "grade": "Grade 9", "subject": "Science", "chapter": "Matter",
            "step_title": "States of Matter",
            "sections": {
                "introduction": "Matter is everything around us and has mass and volume. " * 20,  # 200+ words
                "what_you_will_learn": [
                    "Identify and differentiate between the three states of matter: solid, liquid, and gas",
                    "Explain the key physical properties of solids, liquids, and gases using particle theory",
                    "Describe how matter changes its state with changes in temperature and pressure",
                    "Apply knowledge of state changes to explain everyday phenomena in the physical world",
                ],
                "simple_explanation": ("In science, matter refers to anything that has mass and takes up space. "
                                       "Matter exists in three common states: solid, liquid, and gas. "
                                       "The behaviour of matter depends on the arrangement and energy of its particles. "
                                       "In solids, particles are tightly packed and vibrate in fixed positions. "
                                       "In liquids, particles are close together but can move around each other. "
                                       "In gases, particles are far apart and move freely in all directions. ") * 3,
                "step_by_step_breakdown": [
                    "Step 1: Observe a solid object — it has a fixed shape and a definite volume that does not change.",
                    "Step 2: Observe a liquid — it has a fixed volume but takes the shape of whatever container it is placed in.",
                    "Step 3: Observe a gas — it has neither fixed shape nor fixed volume and expands to fill all available space.",
                    "Step 4: Heat the solid and observe it melt into a liquid as particles gain energy to move freely.",
                ],
                "worked_example": {
                    "problem": "A piece of ice at -10°C is placed in a hot room at 25°C. Describe all the state changes that occur.",
                    "solution_steps": [
                        "Step 1: The ice (solid) absorbs heat energy and its temperature rises from -10°C to 0°C.",
                        "Step 2: At 0°C (melting point), the ice melts into liquid water as particles gain enough energy to move.",
                        "Step 3: The liquid water absorbs more heat and its temperature rises from 0°C to 100°C.",
                        "Step 4: At 100°C (boiling point), the water evaporates into steam (gas) as particles escape the liquid.",
                    ],
                    "final_answer": "Ice melts to water at 0°C, then water evaporates to steam at 100°C. Two state changes occur.",
                },
                "common_mistake": {
                    "mistake": "Students confuse melting point with boiling point and use the terms interchangeably.",
                    "why_wrong": "Melting point and boiling point are two completely different temperatures that represent different state changes.",
                    "correction": "Melting point is the temperature at which a solid changes to a liquid; boiling point is when a liquid changes to a gas.",
                },
                "quick_check_question": {
                    "question": "Which state of matter has a definite shape and a definite volume? A) Gas  B) Liquid  C) Solid  D) Plasma",
                    "answer": "C) Solid",
                    "explanation": "Solids have tightly packed particles that vibrate in fixed positions, giving them both a definite shape and a definite volume.",
                },
                "summary": [
                    "Matter exists in three common states: solid, liquid, and gas, each with unique particle arrangements.",
                    "State changes such as melting and evaporation occur at specific temperatures called melting point and boiling point.",
                    "Particles in different states have different energy levels: gases have the most energy, solids the least.",
                    "Understanding states of matter helps explain everyday phenomena like ice melting and water boiling.",
                ],
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is True, f"Expected valid but got issues: {result['issues']}"
        assert result["critical_count"] == 0
        assert result["section_compliance"] == 100

    def test_missing_section_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "introduction": "Some intro text. " * 10,
                # missing all other sections
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is False
        assert result["critical_count"] > 0
        assert "what_you_will_learn" in result["missing_sections"]

    def test_empty_section_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {"sections": {"introduction": "", "what_you_will_learn": [], "simple_explanation": ""}}
        result = validate_repaired_draft(draft)
        assert result["valid"] is False
        assert result["critical_count"] > 0

    def test_filler_text_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "introduction": "Coming soon - content TBD",
                "what_you_will_learn": ["obj1", "obj2", "obj3"],
                "simple_explanation": "Lorem ipsum placeholder",
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is False

    def test_too_short_section_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "introduction": "Short.",  # way under 80 words
                "what_you_will_learn": ["a", "b", "c"],
                "simple_explanation": "Also short.",
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is False

    def test_worked_example_missing_answer_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "worked_example": {
                    "problem": "Solve this problem.",
                    "solution_steps": ["Step 1", "Step 2"],
                    # missing final_answer
                }
            }
        }
        result = validate_repaired_draft(draft)
        assert not result["valid"]
        sections_with_issues = [i["section"] for i in result["issues"]]
        assert "worked_example" in sections_with_issues

    def test_insufficient_objectives_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "what_you_will_learn": ["only one objective"],  # < 3
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is False

    def test_insufficient_steps_fails(self):
        from app.services.lesson_repair_service import validate_repaired_draft
        draft = {
            "sections": {
                "step_by_step_breakdown": ["Only one step"],  # < 3
            }
        }
        result = validate_repaired_draft(draft)
        assert result["valid"] is False


# ── extract_failed_lessons tests ──────────────────────────────────────────────

class TestExtractFailedLessons:
    def test_extracts_lessons_with_critical_issues(self):
        from app.services.lesson_repair_service import extract_failed_lessons
        report = _make_audit_report([
            _make_failed_lesson(),
            {"grade": "Grade 9", "subject": "Maths", "chapter": "Algebra", "step_title": "Equations",
             "issue_counts": {"critical": 0, "high": 0, "total": 0}, "all_issues": [],
             "scores": {"overall_lesson_score": 95}},
        ])
        failed = extract_failed_lessons(report)
        assert len(failed) == 1
        assert failed[0]["subject"] == "Science"

    def test_grade_filter_works(self):
        from app.services.lesson_repair_service import extract_failed_lessons
        report = _make_audit_report([
            _make_failed_lesson(grade="Grade 9"),
            _make_failed_lesson(grade="Grade 10", subject="Maths"),
        ])
        failed = extract_failed_lessons(report, grade="Grade 9")
        assert len(failed) == 1
        assert failed[0]["grade"] == "Grade 9"

    def test_sample_limits_results(self):
        from app.services.lesson_repair_service import extract_failed_lessons
        lessons = [_make_failed_lesson(step_title=f"Step {i}") for i in range(20)]
        report = _make_audit_report(lessons)
        failed = extract_failed_lessons(report, sample=True, sample_size=5)
        assert len(failed) <= 5


# ── LLM repair safety tests ───────────────────────────────────────────────────

class TestLlmRepairSafety:
    def test_invalid_json_returns_error_not_exception(self, monkeypatch):
        """LLM returning non-JSON must not raise — returns {success: False}."""
        from app.services.lesson_repair_service import run_llm_repair

        def fake_ask_llm(*a, **kw):
            return "This is not JSON at all!"

        monkeypatch.setattr("app.services.openai_service.ask_llm", fake_ask_llm)

        result = run_llm_repair(_make_failed_lesson())
        assert result["success"] is False
        assert result["draft"] is None
        assert "invalid JSON" in result["error"] or "JSON" in result["error"]

    def test_missing_sections_key_returns_error(self, monkeypatch):
        """LLM returning JSON without 'sections' key must return error."""
        from app.services.lesson_repair_service import run_llm_repair

        def fake_ask_llm(*a, **kw):
            return '{"grade": "9", "no_sections_here": {}}'

        monkeypatch.setattr("app.services.openai_service.ask_llm", fake_ask_llm)

        result = run_llm_repair(_make_failed_lesson())
        assert result["success"] is False
        assert "sections" in result["error"].lower()

    def test_llm_exception_returns_error_not_raise(self, monkeypatch):
        """LLM network error must not propagate — returns {success: False}."""
        from app.services.lesson_repair_service import run_llm_repair

        def fake_ask_llm(*a, **kw):
            raise ConnectionError("Network timeout")

        monkeypatch.setattr("app.services.openai_service.ask_llm", fake_ask_llm)

        result = run_llm_repair(_make_failed_lesson())
        assert result["success"] is False
        assert result["draft"] is None


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestRepairEndpoints:
    """HTTP endpoint tests for the admin lesson repair API."""

    def setup_method(self):
        """Override auth dependencies before each test."""
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_non_admin_cannot_access_repair_endpoints(self, monkeypatch):
        """All repair endpoints must return 403 for non-admin users."""
        import app.services.auth_service as auth_svc

        # Remove admin override so real require_admin runs
        app.dependency_overrides.pop(require_admin, None)

        # Mock get_user_profile to return a student profile (not admin)
        monkeypatch.setattr(
            auth_svc,
            "get_user_profile",
            lambda user_id: {"id": user_id, "role": "student", "family_id": None},
        )

        with TestClient(app) as client:
            app.dependency_overrides[get_current_user] = lambda: _make_student()
            resp = client.get("/api/admin/qa/lesson-repair/latest",
                              headers={"Authorization": "Bearer fake"})
            # require_admin raises 403 for non-admin role
            assert resp.status_code == 403

        app.dependency_overrides.pop(get_current_user, None)

    def test_latest_returns_200(self, monkeypatch):
        """GET /latest returns 200 with audit_report_meta or null."""
        import app.routes.lesson_repair as lr
        monkeypatch.setattr(lr, "load_latest_audit_report", lambda: None)

        with TestClient(app) as client:
            resp = client.get("/api/admin/qa/lesson-repair/latest",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_history_returns_list(self, monkeypatch):
        """GET /history returns jobs list (may be empty)."""
        import app.routes.lesson_repair as lr
        monkeypatch.setattr(lr, "_db_list_jobs", lambda limit=20: [])

        with TestClient(app) as client:
            resp = client.get("/api/admin/qa/lesson-repair/history",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert "jobs" in resp.json()

    def test_run_requires_existing_audit_report(self, monkeypatch):
        """POST /run returns 422 when no audit report exists."""
        import app.routes.lesson_repair as lr
        monkeypatch.setattr(lr, "load_latest_audit_report", lambda: None)

        with TestClient(app) as client:
            resp = client.post("/api/admin/qa/lesson-repair/run",
                               json={"mode": "sample"},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 422
        assert "audit" in resp.json()["detail"].lower()

    def test_run_invalid_mode_returns_400(self, monkeypatch):
        """POST /run returns 400 for invalid mode."""
        import app.routes.lesson_repair as lr
        monkeypatch.setattr(lr, "load_latest_audit_report", lambda: _make_audit_report())

        with TestClient(app) as client:
            resp = client.post("/api/admin/qa/lesson-repair/run",
                               json={"mode": "invalid_mode"},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 400

    def test_status_404_for_unknown_job(self):
        """GET /status/{job_id} returns 404 for unknown job."""
        fake_id = str(uuid.uuid4())
        import app.routes.lesson_repair as lr
        # Clear in-memory jobs so no accidental match
        lr._REPAIR_JOBS.clear()

        with TestClient(app) as client:
            resp = client.get(f"/api/admin/qa/lesson-repair/status/{fake_id}",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 404

    def test_approve_requires_ready_for_review_status(self, monkeypatch):
        """POST /approve returns 422 if task is not in ready_for_review."""
        import app.routes.lesson_repair as lr
        task_id = str(uuid.uuid4())
        lr._REPAIR_TASKS[task_id] = {
            "id": task_id, "job_id": "job-1", "status": "queued",
            "grade": "Grade 9", "subject": "Science",
        }

        with TestClient(app) as client:
            resp = client.post(f"/api/admin/qa/lesson-repair/task/{task_id}/approve",
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 422
        lr._REPAIR_TASKS.pop(task_id, None)

    def test_publish_requires_approved_status(self, monkeypatch):
        """POST /publish returns 422 if task is not approved."""
        import app.routes.lesson_repair as lr
        task_id = str(uuid.uuid4())
        lr._REPAIR_TASKS[task_id] = {
            "id": task_id, "job_id": "job-1", "status": "ready_for_review",
            "repaired_content_json": {"sections": {}},
        }

        with TestClient(app) as client:
            resp = client.post(f"/api/admin/qa/lesson-repair/task/{task_id}/publish",
                               headers={"Authorization": "Bearer fake-admin"})
        # publish_repaired_task checks status == 'approved'
        assert resp.status_code == 422
        assert "approved" in resp.json()["detail"].lower()
        lr._REPAIR_TASKS.pop(task_id, None)

    def test_response_does_not_expose_admin_id(self, monkeypatch):
        """Job response must not contain requested_by_admin_id."""
        import app.routes.lesson_repair as lr
        job_id = str(uuid.uuid4())
        lr._REPAIR_JOBS[job_id] = {
            "id": job_id, "status": "completed",
            "requested_by_admin_id": "super-secret-admin-id",
            "mode": "sample", "total_tasks": 5,
        }

        with TestClient(app) as client:
            resp = client.get(f"/api/admin/qa/lesson-repair/status/{job_id}",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "requested_by_admin_id" not in data.get("job", {})
        lr._REPAIR_JOBS.pop(job_id, None)

    def test_report_download_json(self, monkeypatch):
        """GET /report?format=json returns valid JSON."""
        import app.routes.lesson_repair as lr
        job_id = str(uuid.uuid4())
        lr._REPAIR_JOBS[job_id] = {
            "id": job_id, "status": "completed", "mode": "sample",
            "total_tasks": 2, "completed_tasks": 2, "failed_tasks": 0,
            "approved_tasks": 1, "published_tasks": 1,
        }
        monkeypatch.setattr(lr, "_db_get_tasks", lambda job_id, status=None: [])

        with TestClient(app) as client:
            resp = client.get(f"/api/admin/qa/lesson-repair/report?job_id={job_id}&format=json",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        parsed = json.loads(resp.content)
        assert "job" in parsed
        lr._REPAIR_JOBS.pop(job_id, None)

    def test_cancel_queued_job(self, monkeypatch):
        """POST /job/{job_id}/cancel cancels a queued job."""
        import app.routes.lesson_repair as lr
        job_id = str(uuid.uuid4())
        lr._REPAIR_JOBS[job_id] = {
            "id": job_id, "status": "queued", "mode": "sample",
        }
        monkeypatch.setattr(lr, "_db_update_job", lambda jid, updates: True)

        with TestClient(app) as client:
            resp = client.post(f"/api/admin/qa/lesson-repair/job/{job_id}/cancel",
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert lr._REPAIR_JOBS[job_id]["status"] == "cancelled"
        lr._REPAIR_JOBS.pop(job_id, None)


# ── publish_repaired_task safety ──────────────────────────────────────────────

class TestPublishSafety:
    def test_publish_without_approval_returns_error(self):
        from app.services.lesson_repair_service import publish_repaired_task
        task = {"status": "ready_for_review", "repaired_content_json": {"sections": {}}}
        result = publish_repaired_task(task)
        assert result["success"] is False
        assert "approved" in result["message"].lower()

    def test_publish_without_repaired_content_returns_error(self):
        from app.services.lesson_repair_service import publish_repaired_task
        task = {"status": "approved", "repaired_content_json": None}
        result = publish_repaired_task(task)
        assert result["success"] is False

    def test_publish_without_cache_id_returns_error(self):
        from app.services.lesson_repair_service import publish_repaired_task
        task = {
            "status": "approved",
            "repaired_content_json": {"sections": {"introduction": "text"}},
            "original_lesson_cache_id": None,
        }
        result = publish_repaired_task(task)
        assert result["success"] is False
        assert "lesson_cache" in result["message"].lower() or "ID" in result["message"]
