"""
Tests for the teacher-private lesson-plan edit/save/revert endpoints
(/api/teacher/lesson-plan/save, /generate, /revert).

These endpoints let a teacher save their own edited copy of a lesson plan
without ever touching the shared, system-generated lesson_plan_bank/*.json
file — see app/services/teacher_lesson_plan_service.py and
migrations/20260809_teacher_lesson_plan_edits.sql.

Mirrors the mocking style in test_teacher_tools.py: monkeypatch the
service-layer functions imported into app.routes.teacher (a Supabase-backed
service, no local equivalent to exercise directly).
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user
import app.routes.teacher as teacher_route

FAKE_TEACHER_A = SimpleNamespace(id="teacher-aaa", email="a@example.com")
FAKE_TEACHER_B = SimpleNamespace(id="teacher-bbb", email="b@example.com")


def _client_as(monkeypatch, user):
    monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


class _FakeStore:
    """In-memory stand-in for the teacher_lesson_plan_edits table, keyed
    exactly like the real (teacher_id, grade, subject, chapter) unique
    constraint, so tests can verify per-teacher isolation without touching
    Supabase."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}

    def key(self, teacher_id, grade, subject, chapter):
        return (teacher_id, grade, subject, chapter)

    def get(self, teacher_id, grade, subject, chapter):
        return self.rows.get(self.key(teacher_id, grade, subject, chapter))

    def save(self, teacher_id, grade, subject, chapter, markdown):
        if not (markdown or "").strip():
            return {"success": False, "error": "Lesson plan content cannot be empty."}
        row = {"lesson_plan_markdown": markdown, "updated_at": "2026-08-09T00:00:00Z"}
        self.rows[self.key(teacher_id, grade, subject, chapter)] = row
        return {"success": True, "edit": row}

    def delete(self, teacher_id, grade, subject, chapter):
        self.rows.pop(self.key(teacher_id, grade, subject, chapter), None)
        return {"success": True}


@pytest.fixture
def fake_store(monkeypatch):
    store = _FakeStore()
    monkeypatch.setattr(teacher_route, "get_teacher_edit", store.get)
    monkeypatch.setattr(teacher_route, "save_teacher_edit", store.save)
    monkeypatch.setattr(teacher_route, "delete_teacher_edit", store.delete)
    return store


CHAPTER_ARGS = {"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy"}


class TestSaveAndFetchOwnEdit:
    def test_save_then_generate_returns_the_teachers_own_edit(self, monkeypatch, fake_store):
        client = _client_as(monkeypatch, FAKE_TEACHER_A)
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        with client as c:
            save_resp = c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## My Custom Plan\n- edited by teacher A"},
                headers={"Authorization": "Bearer fake"},
            )
            assert save_resp.status_code == 200
            assert save_resp.json()["success"] is True

            gen_resp = c.post("/api/teacher/lesson-plan/generate", json=CHAPTER_ARGS,
                               headers={"Authorization": "Bearer fake"})
            data = gen_resp.json()
            assert data["success"] is True
            assert data["is_teacher_edited"] is True
            assert "edited by teacher A" in data["lesson_plan"]
        app.dependency_overrides.clear()

    def test_empty_markdown_is_rejected(self, monkeypatch, fake_store):
        client = _client_as(monkeypatch, FAKE_TEACHER_A)
        with client as c:
            resp = c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "   "},
                headers={"Authorization": "Bearer fake"},
            )
            assert resp.status_code == 400
        app.dependency_overrides.clear()


class TestPerTeacherIsolation:
    """The core requirement: a saved edit must be visible ONLY to the
    teacher who saved it. Another teacher requesting the exact same
    grade/subject/chapter must still get the shared system version, never
    another teacher's private edit."""

    def test_teacher_b_does_not_see_teacher_as_saved_edit(self, monkeypatch, fake_store):
        # Teacher A saves a private edit.
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
        with TestClient(app) as c:
            c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## Private to Teacher A"},
                headers={"Authorization": "Bearer fake"},
            )

        # Teacher B requests the SAME chapter — must get the system bank
        # version (Democracy.json), not teacher A's private edit.
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_B
        with TestClient(app) as c:
            resp = c.post("/api/teacher/lesson-plan/generate", json=CHAPTER_ARGS,
                           headers={"Authorization": "Bearer fake"})
            data = resp.json()
            assert data["success"] is True
            assert data["is_teacher_edited"] is False
            assert "Private to Teacher A" not in data["lesson_plan"]
            assert "Lesson Overview" in data["lesson_plan"]  # real bank content

        app.dependency_overrides.clear()

    def test_teacher_bs_own_save_does_not_overwrite_teacher_as(self, monkeypatch, fake_store):
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
        with TestClient(app) as c:
            c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## Teacher A version"},
                headers={"Authorization": "Bearer fake"},
            )

        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_B
        with TestClient(app) as c:
            c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## Teacher B version"},
                headers={"Authorization": "Bearer fake"},
            )

        # Teacher A must still see their own version, untouched by B's save.
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        with TestClient(app) as c:
            resp = c.post("/api/teacher/lesson-plan/generate", json=CHAPTER_ARGS,
                           headers={"Authorization": "Bearer fake"})
            data = resp.json()
            assert "Teacher A version" in data["lesson_plan"]
            assert "Teacher B version" not in data["lesson_plan"]

        app.dependency_overrides.clear()


class TestRevert:
    def test_revert_deletes_edit_and_falls_back_to_system_version(self, monkeypatch, fake_store):
        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
        with TestClient(app) as c:
            c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## My Edit"},
                headers={"Authorization": "Bearer fake"},
            )
            gen_before = c.post("/api/teacher/lesson-plan/generate", json=CHAPTER_ARGS,
                                 headers={"Authorization": "Bearer fake"})
            assert gen_before.json()["is_teacher_edited"] is True

            revert_resp = c.post("/api/teacher/lesson-plan/revert", json=CHAPTER_ARGS,
                                  headers={"Authorization": "Bearer fake"})
            assert revert_resp.status_code == 200
            revert_data = revert_resp.json()
            assert revert_data["success"] is True
            assert revert_data["is_teacher_edited"] is False
            assert "Lesson Overview" in revert_data["lesson_plan"]

            gen_after = c.post("/api/teacher/lesson-plan/generate", json=CHAPTER_ARGS,
                                headers={"Authorization": "Bearer fake"})
            assert gen_after.json()["is_teacher_edited"] is False
        app.dependency_overrides.clear()


class TestSystemBankNeverMutated:
    """Saving/editing must never touch the on-disk lesson_plan_bank file —
    verified by reading the real file's bytes before and after a save."""

    def test_bank_file_bytes_unchanged_after_teacher_save(self, monkeypatch, fake_store):
        from pathlib import Path
        bank_file = (
            Path(__file__).resolve().parents[1]
            / "app" / "data" / "lesson_plan_bank" / "grade_9" / "social_science" / "democracy.json"
        )
        before = bank_file.read_bytes()

        app.dependency_overrides[get_current_user] = lambda: FAKE_TEACHER_A
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
        with TestClient(app) as c:
            c.post(
                "/api/teacher/lesson-plan/save",
                json={**CHAPTER_ARGS, "lesson_plan_markdown": "## Attempted mutation"},
                headers={"Authorization": "Bearer fake"},
            )
        app.dependency_overrides.clear()

        after = bank_file.read_bytes()
        assert before == after
