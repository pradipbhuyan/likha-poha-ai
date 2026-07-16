"""
test_lesson_prewarm.py — Backend tests for the Lesson Prewarm admin workflow
(POST /api/lesson/prewarm/*, /api/lesson/prewarm/lkb-chips*).

Bug context (Defect e12251ed-e6c6-4262-9862-94982582ecdb):
Grade 11 English / "5. The Frog" / "What We Learn" served a hallucinated
Biology answer about real frogs (respiration, digestion, eggs, metamorphosis)
ending with the literal pasted line "Not relevant to the lesson." — a ChatGPT
disclaimer/aside that an admin pasted verbatim into POST /prewarm/store with
zero validation. Root cause: /api/lesson/prewarm/* endpoints (an explicitly
admin-only "ChatGPT manual lesson import" workflow) only required
Depends(get_current_user), so any authenticated user (not just admins) could
write directly into the shared lesson_cache table served to every student.

Covers:
- All /prewarm/* endpoints reject non-admin users with 403
- POST /prewarm/store rejects ChatGPT disclaimer/hallucination phrases,
  using the exact reported bug content as the regression input
- POST /prewarm/store still accepts clean, valid lesson content from an admin
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user, require_admin

client = TestClient(app)

ADMIN_ID = "33333333-3333-3333-3333-333333333001"
STUDENT_ID = "33333333-3333-3333-3333-333333333002"

# The exact reported bug content: hallucinated frog biology for an English
# poem chapter, ending with the leaked ChatGPT disclaimer line.
BUG_REPORT_CONTENT = """How do frogs breathe and what structures are involved?
What does the frog's digestive system look like?
Where do frogs lay their eggs and why?
How does a tadpole transform into a frog?
What key features help frogs adapt to both water and land environments?

Not relevant to the lesson."""

VALID_LESSON_CONTENT = """In "The Frog" by Norman Gale, the poet satirises human
manners by contrasting them with a frog's simple, unpretentious way of life.
The poem's tone is playful and ironic, poking fun at social snobbery."""


def _make_admin():
    return {"id": ADMIN_ID, "email": "admin@test.com", "profile": {"id": ADMIN_ID, "role": "admin"}}


def _make_student():
    return SimpleNamespace(id=STUDENT_ID, email="student@test.com")


PREWARM_REQUESTS = [
    ("POST", "/api/lesson/prewarm/prompt", {
        "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn",
    }),
    ("POST", "/api/lesson/prewarm/store", {
        "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn",
        "lesson_content": VALID_LESSON_CONTENT,
    }),
    ("POST", "/api/lesson/prewarm/generate-questions", {
        "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn",
    }),
]


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user, None)


class TestPrewarmAdminGate:
    """Every /prewarm/* endpoint must reject non-admin users with 403."""

    def _as_non_admin(self, monkeypatch):
        import app.services.auth_service as auth_svc
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides[get_current_user] = lambda: _make_student()
        monkeypatch.setattr(
            auth_svc, "get_user_profile",
            lambda user_id: {"id": user_id, "role": "student"},
        )

    @pytest.mark.parametrize("method,path,body", PREWARM_REQUESTS)
    def test_non_admin_rejected(self, monkeypatch, method, path, body):
        self._as_non_admin(monkeypatch)
        resp = client.request(method, path, json=body, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 403

    def test_debug_cache_non_admin_rejected(self, monkeypatch):
        self._as_non_admin(monkeypatch)
        resp = client.get(
            "/api/lesson/prewarm/debug-cache",
            params={"grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403

    def test_lkb_chips_list_non_admin_rejected(self, monkeypatch):
        self._as_non_admin(monkeypatch)
        resp = client.get(
            "/api/lesson/prewarm/lkb-chips",
            params={"grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403

    def test_lkb_chip_delete_non_admin_rejected(self, monkeypatch):
        self._as_non_admin(monkeypatch)
        resp = client.request(
            "DELETE", "/api/lesson/prewarm/lkb-chips/some-chip-id",
            params={"grade": "Grade 11"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403

    def test_lkb_chips_delete_all_non_admin_rejected(self, monkeypatch):
        self._as_non_admin(monkeypatch)
        resp = client.request(
            "DELETE", "/api/lesson/prewarm/lkb-chips",
            params={"grade": "Grade 11", "subject": "English", "chapter": "5. The Frog", "step_title": "What We Learn"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 403


class TestPrewarmStoreContentValidation:
    """POST /prewarm/store must reject ChatGPT disclaimer/hallucination pastes."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def test_rejects_exact_bug_report_content(self):
        """Regression test for defect e12251ed-e6c6-4262-9862-94982582ecdb."""
        resp = client.post(
            "/api/lesson/prewarm/store",
            json={
                "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog",
                "step_title": "What We Learn", "lesson_content": BUG_REPORT_CONTENT,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400
        assert "not relevant to the lesson" in resp.json()["detail"].lower()

    @pytest.mark.parametrize("phrase", [
        "As an AI language model, I cannot help with that.",
        "I don't have access to the actual textbook passage.",
        "This is outside the scope of this lesson.",
    ])
    def test_rejects_other_disclaimer_phrases(self, phrase):
        resp = client.post(
            "/api/lesson/prewarm/store",
            json={
                "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog",
                "step_title": "What We Learn", "lesson_content": phrase,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 400

    def test_accepts_valid_lesson_content(self, monkeypatch):
        import app.services.lesson_cache_service as cache_svc
        import app.services.rag_service as rag_svc

        monkeypatch.setattr(cache_svc, "get_cached_lesson", lambda *a, **kw: None)
        monkeypatch.setattr(cache_svc, "store_lesson_cache", lambda *a, **kw: None)
        monkeypatch.setattr(rag_svc, "search_textbook_content", lambda *a, **kw: [])

        resp = client.post(
            "/api/lesson/prewarm/store",
            json={
                "grade": "Grade 11", "subject": "English", "chapter": "5. The Frog",
                "step_title": "What We Learn", "lesson_content": VALID_LESSON_CONTENT,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
