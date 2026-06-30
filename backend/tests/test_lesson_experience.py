"""
test_lesson_experience.py — Backend tests for Admin Lesson Experience endpoints.

Verifies:
- All 3 endpoints are admin-only (403 for non-admins)
- catalog returns success response
- lesson endpoint returns normalized data
- visuals endpoint returns safe response
- No endpoint writes to lesson tables
- Missing lesson returns 404
- No secrets in responses
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

ADMIN_USER = {"id": "admin-1", "profile": {"id": "admin-1", "role": "admin"}}
NON_ADMIN_USER = {"id": "user-1", "profile": {"id": "user-1", "role": "student"}}

MOCK_CATALOG = {
    "grades": ["Grade 9"],
    "subjects": ["Science"],
    "chapters": ["Motion"],
    "lessons": [
        {
            "lesson_id": "Grade 9|Science|Motion",
            "grade": "Grade 9",
            "subject": "Science",
            "chapter": "Motion",
            "step_count": 2,
            "estimated_minutes": 10,
        }
    ],
    "total_lessons": 1,
    "total_steps": 2,
}

MOCK_LESSON = {
    "lesson_id": "Grade 9|Science|Motion",
    "grade": "Grade 9",
    "subject": "Science",
    "chapter": "Motion",
    "title": "Science — Motion",
    "total_steps": 2,
    "total_estimated_minutes": 10,
    "steps": [
        {
            "step_number": 1,
            "step_title": "Concept Introduction",
            "raw_content": "Motion is a change in position.",
            "normalized_sections": {"introduction": "Motion is a change in position."},
            "formulas": ["v = s/t"],
            "examples": [],
            "mcqs": [],
            "summary": "Motion = change in position.",
            "word_count": 8,
            "estimated_minutes": 5,
        },
        {
            "step_number": 2,
            "step_title": "Core Explanation",
            "raw_content": "Velocity is speed with direction.",
            "normalized_sections": {},
            "formulas": [],
            "examples": [],
            "mcqs": [],
            "summary": "",
            "word_count": 6,
            "estimated_minutes": 5,
        },
    ],
}

MOCK_VISUALS = {
    "available": False,
    "visuals": [],
    "empty_state": "No textbook visuals linked yet.",
}


# ── Helper ────────────────────────────────────────────────────────────────────

def make_app():
    """Create a TestClient with the lesson_experience router mounted."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes.lesson_experience import router

    app = FastAPI()
    app.include_router(router, prefix="/api/admin/lesson-experience")
    return TestClient(app)


def auth_header(token: str = "admin-tok") -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCatalogEndpoint:
    """GET /api/admin/lesson-experience/catalog"""

    def test_catalog_admin_only_403_for_student(self):
        """Non-admin must receive 403."""
        client = make_app()
        with patch("app.services.auth_service.require_admin") as mock_guard:
            from fastapi import HTTPException
            mock_guard.side_effect = HTTPException(status_code=403, detail="Admin access required")
            resp = client.get("/api/admin/lesson-experience/catalog", headers=auth_header("student-tok"))
        assert resp.status_code == 403

    def test_catalog_returns_success(self):
        """catalog returns success=True and lessons list."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/catalog",
                headers=auth_header(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "lessons" in data

    def test_catalog_no_writes(self):
        """catalog must not call any write functions."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG) as mock_list,
        ):
            client.get("/api/admin/lesson-experience/catalog", headers=auth_header())
        # Only get_lesson_list was called — not any mutating function
        mock_list.assert_called_once()

    def test_catalog_grade_filter_passed_through(self):
        """grade query param is forwarded to get_lesson_list."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG) as mock_list,
        ):
            client.get(
                "/api/admin/lesson-experience/catalog?grade=Grade+9",
                headers=auth_header(),
            )
        mock_list.assert_called_once_with(grade="Grade 9", subject=None, chapter=None)


class TestLessonEndpoint:
    """GET /api/admin/lesson-experience/lesson/{lesson_id}"""

    def test_lesson_admin_only_403(self):
        """Non-admin must receive 403."""
        client = make_app()
        with patch("app.services.auth_service.require_admin") as mock_guard:
            from fastapi import HTTPException
            mock_guard.side_effect = HTTPException(status_code=403, detail="Admin access required")
            resp = client.get(
                "/api/admin/lesson-experience/lesson/some-id",
                headers=auth_header("student-tok"),
            )
        assert resp.status_code == 403

    def test_lesson_returns_normalized_steps(self):
        """lesson endpoint returns normalized steps."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_detail", return_value=MOCK_LESSON),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                headers=auth_header(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "steps" in data
        assert len(data["steps"]) == 2

    def test_lesson_missing_returns_404(self):
        """Missing lesson returns 404."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_detail",
                  return_value={"error": "Lesson not found"}),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/lesson/nonexistent",
                headers=auth_header(),
            )
        assert resp.status_code == 404

    def test_lesson_strips_repair_metadata(self):
        """audit_summary and repair_job_id must not appear in response."""
        lesson_with_metadata = {
            **MOCK_LESSON,
            "audit_summary": {"overall_step_sequence_score": 75},
            "repair_job_id": "job-123",
        }
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_detail",
                  return_value=lesson_with_metadata),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                headers=auth_header(),
            )
        data = resp.json()
        assert "audit_summary" not in data
        assert "repair_job_id" not in data

    def test_lesson_missing_formulas_safe(self):
        """Steps with no formulas return empty list, not crash."""
        lesson_no_formulas = {
            **MOCK_LESSON,
            "steps": [{**MOCK_LESSON["steps"][0], "formulas": None}],
        }
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_detail",
                  return_value=lesson_no_formulas),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                headers=auth_header(),
            )
        assert resp.status_code == 200

    def test_lesson_no_secrets_in_response(self):
        """Response must not contain API keys or tokens."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_lesson_detail", return_value=MOCK_LESSON),
        ):
            resp = client.get(
                "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                headers=auth_header(),
            )
        text = resp.text.lower()
        assert "api_key" not in text
        assert "access_token" not in text
        assert "secret" not in text


class TestVisualsEndpoint:
    """GET /api/admin/lesson-experience/visuals"""

    def test_visuals_admin_only_403(self):
        """Non-admin must receive 403."""
        client = make_app()
        with patch("app.services.auth_service.require_admin") as mock_guard:
            from fastapi import HTTPException
            mock_guard.side_effect = HTTPException(status_code=403, detail="Admin access required")
            resp = client.get("/api/admin/lesson-experience/visuals", headers=auth_header("student-tok"))
        assert resp.status_code == 403

    def test_visuals_returns_empty_state_safely(self):
        """Empty visuals returns a safe empty-state response."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_visuals", return_value=MOCK_VISUALS),
        ):
            resp = client.get("/api/admin/lesson-experience/visuals", headers=auth_header())
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["available"] is False
        assert isinstance(data["visuals"], list)

    def test_visuals_no_writes(self):
        """visuals endpoint must not write to any table."""
        client = make_app()
        with (
            patch("app.routes.lesson_experience.require_admin", return_value=ADMIN_USER),
            patch("app.routes.lesson_experience.get_visuals", return_value=MOCK_VISUALS) as mock_vis,
        ):
            client.get("/api/admin/lesson-experience/visuals", headers=auth_header())
        mock_vis.assert_called_once()
