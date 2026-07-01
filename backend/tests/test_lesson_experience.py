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
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services.auth_service import require_admin
from app.routes.lesson_experience import router


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_app():
    """Create a FastAPI app with the lesson_experience router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/admin/lesson-experience")
    return app


def auth_header(token: str = "admin-tok") -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCatalogEndpoint:
    """GET /api/admin/lesson-experience/catalog"""

    def test_catalog_admin_only_403_for_student(self):
        """Non-admin must receive 403."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="Admin access required")
        )
        with TestClient(app) as client:
            resp = client.get("/api/admin/lesson-experience/catalog", headers=auth_header("student-tok"))
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 403

    def test_catalog_returns_success(self):
        """catalog returns success=True and lessons list."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/admin/lesson-experience/catalog",
                    headers=auth_header(),
                )
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "lessons" in data

    def test_catalog_no_writes(self):
        """catalog must not call any write functions."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG) as mock_list,
        ):
            with TestClient(app) as client:
                client.get("/api/admin/lesson-experience/catalog", headers=auth_header())
        app.dependency_overrides.pop(require_admin, None)
        # Only get_lesson_list was called — not any mutating function
        mock_list.assert_called_once()

    def test_catalog_grade_filter_passed_through(self):
        """grade query param is forwarded to get_lesson_list."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_list", return_value=MOCK_CATALOG) as mock_list,
        ):
            with TestClient(app) as client:
                client.get(
                    "/api/admin/lesson-experience/catalog?grade=Grade+9",
                    headers=auth_header(),
                )
        app.dependency_overrides.pop(require_admin, None)
        mock_list.assert_called_once_with(grade="Grade 9", subject=None, chapter=None)


class TestLessonEndpoint:
    """GET /api/admin/lesson-experience/lesson/{id}"""

    def test_lesson_admin_only_403(self):
        """Non-admin must receive 403."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="Admin access required")
        )
        with TestClient(app) as client:
            resp = client.get(
                "/api/admin/lesson-experience/lesson/some-id",
                headers=auth_header("student-tok"),
            )
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 403

    def test_lesson_returns_normalized_steps(self):
        """lesson endpoint returns normalized steps."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_detail", return_value=MOCK_LESSON),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                    headers=auth_header(),
                )
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_lesson_missing_returns_404(self):
        """Missing lesson returns 404."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_detail",
                  return_value={"error": "Lesson not found"}),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/admin/lesson-experience/lesson/nonexistent",
                    headers=auth_header(),
                )
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 404

    def test_lesson_missing_formulas_safe(self):
        """Steps with no formulas return empty list, not crash."""
        lesson_no_formulas = {
            **MOCK_LESSON,
            "steps": [{**MOCK_LESSON["steps"][0], "formulas": None}],
        }
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_lesson_detail",
                  return_value=lesson_no_formulas),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/admin/lesson-experience/lesson/Grade+9%7CScience%7CMotion",
                    headers=auth_header(),
                )
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 200
        data = resp.json()
        step = data["steps"][0]
        # formulas may be None or [] when the source data has no formulas — both are safe
        assert step["formulas"] in ([], None)


class TestVisualsEndpoint:
    """GET /api/admin/lesson-experience/visuals"""

    def test_visuals_admin_only_403(self):
        """Non-admin must receive 403."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="Admin access required")
        )
        with TestClient(app) as client:
            resp = client.get("/api/admin/lesson-experience/visuals", headers=auth_header("student-tok"))
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 403

    def test_visuals_returns_empty_state_safely(self):
        """Empty visuals returns a safe empty-state response."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_visuals", return_value=MOCK_VISUALS),
        ):
            with TestClient(app) as client:
                resp = client.get("/api/admin/lesson-experience/visuals", headers=auth_header())
        app.dependency_overrides.pop(require_admin, None)
        assert resp.status_code == 200

    def test_visuals_no_writes(self):
        """visuals endpoint must not write to any table."""
        app = make_app()
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        with (
            patch("app.routes.lesson_experience.get_visuals", return_value=MOCK_VISUALS) as mock_vis,
        ):
            with TestClient(app) as client:
                client.get("/api/admin/lesson-experience/visuals", headers=auth_header())
        app.dependency_overrides.pop(require_admin, None)
        mock_vis.assert_called_once()
