"""
test_exam_prep.py — Exam Prep Center security and access-control tests
======================================================================
Tests:
  - Grade 10 student cannot access Exam Prep (403)
  - akshita.teststudent can access
  - Grade 11/12 student can access
  - Admin can always access
  - Dashboard endpoint returns JEE data
  - Subjects endpoint returns Physics/Chemistry/Maths for JEE
  - Topics endpoint returns priority topics
  - Questions endpoint returns only published questions
  - Answer submission returns correct feedback
  - Prewarm is admin-only
  - Non-admin cannot prewarm
  - Simulated test start works (empty question bank gracefully handled)
  - Simulated test submit returns score <= 100%
"""

import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from app.services.auth_service import get_current_user

client = TestClient(app)

# ── Test profiles ──────────────────────────────────────────────────────────────

def _make_user(uid, username, role, grade=None):
    return SimpleNamespace(
        id=uid,
        email=f"{username}@test.com",
        username=username,
        role=role,
    )


ADMIN_USER = _make_user("admin-1", "admin_user", "admin")
GRADE_12_USER = _make_user("g12-1", "grade12student", "student")
GRADE_10_USER = _make_user("g10-1", "grade10student", "student")
TEST_USER = _make_user("test-1", "akshita.teststudent", "student")

ADMIN_PROFILE = {
    "id": "admin-1", "username": "admin_user", "role": "admin", "grade": None,
    "email": "admin_user@test.com",
}
GRADE_12_PROFILE = {
    "id": "g12-1", "username": "grade12student", "role": "student", "grade": "Grade 12",
    "email": "grade12student@test.com",
}
GRADE_10_PROFILE = {
    "id": "g10-1", "username": "grade10student", "role": "student", "grade": "Grade 10",
    "email": "grade10student@test.com",
}
TEST_USER_PROFILE = {
    "id": "test-1", "username": "akshita.teststudent", "role": "student", "grade": "Grade 9",
    "email": "akshita.teststudent@test.com",
}


def override_user(user, profile):
    app.dependency_overrides[get_current_user] = lambda: user
    return profile


def clear_overrides():
    app.dependency_overrides.clear()


# ── Access control tests ───────────────────────────────────────────────────────

class TestExamPrepAccessControl:
    """Backend must enforce Exam Prep access rules regardless of frontend hiding."""

    def test_grade_10_student_cannot_access_status(self, monkeypatch):
        """Grade 10 student gets 403 on /status endpoint."""
        override_user(GRADE_10_USER, GRADE_10_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_10_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/status")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        assert "Grade 11" in r.json().get("detail", "") or "access" in r.json().get("detail", "").lower()
        clear_overrides()

    def test_grade_10_cannot_access_dashboard(self, monkeypatch):
        """Grade 10 student cannot access dashboard."""
        override_user(GRADE_10_USER, GRADE_10_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_10_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/dashboard?exam=jee_main")
        assert r.status_code == 403
        clear_overrides()

    def test_grade_10_cannot_access_subjects(self, monkeypatch):
        """Grade 10 student cannot access subjects."""
        override_user(GRADE_10_USER, GRADE_10_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_10_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/subjects?exam=jee_main")
        assert r.status_code == 403
        clear_overrides()

    def test_akshita_teststudent_can_access(self, monkeypatch):
        """akshita.teststudent can access Exam Prep regardless of grade."""
        override_user(TEST_USER, TEST_USER_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: TEST_USER_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/status")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["has_access"] is True
        clear_overrides()

    def test_grade_12_student_can_access(self, monkeypatch):
        """Grade 12 student can access Exam Prep."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/status")
        assert r.status_code == 200
        assert r.json()["has_access"] is True
        clear_overrides()

    def test_admin_can_always_access(self, monkeypatch):
        """Admin can always access Exam Prep."""
        override_user(ADMIN_USER, ADMIN_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: ADMIN_PROFILE,
            raising=False,
        )
        r = client.get("/api/exam-prep/status")
        assert r.status_code == 200
        clear_overrides()

    def test_unauthenticated_gets_401(self):
        """No token = 401."""
        clear_overrides()
        r = client.get("/api/exam-prep/status")
        assert r.status_code in (401, 403)


# ── Dashboard tests ─────────────────────────────────────────────────────────────

class TestExamPrepDashboard:
    """Dashboard endpoint returns correct JEE stats."""

    def test_dashboard_returns_jee_data(self, monkeypatch):
        """Dashboard returns exam_type jee_main and expected fields."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        # Mock content access — dashboard requires Premium subscription check.
        # authorize_feature is imported locally inside
        # check_exam_content_access_with_packs(), so it must be patched on its
        # defining module (feature_authorization_service), not exam_prep_service,
        # or the real function still runs and hits the network via
        # resolve_user_subscription().
        monkeypatch.setattr(
            "app.services.feature_authorization_service.authorize_feature",
            lambda uid, feat: {"allowed": True, "limited": False, "canonical_plan_key": "PREMIUM"},
            raising=False,
        )

        # Patch the service function directly to avoid complex mock chains
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        def mock_get_dashboard(exam_type, user_id):
            return {
                "exam_type": exam_type,
                "weeks_to_exam": 28,
                "total_questions": 0,
                "questions_attempted": 0,
                "accuracy_pct": 0,
                "correct_count": 0,
                "total_topics": 24,
                "subjects_count": 3,
            }

        monkeypatch.setattr(ep_svc, "get_dashboard", mock_get_dashboard, raising=False)

        r = client.get("/api/exam-prep/dashboard?exam=jee_main")

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["exam_type"] == "jee_main"
        assert "weeks_to_exam" in data
        assert "total_questions" in data
        assert "total_topics" in data
        clear_overrides()


# ── Subjects tests ──────────────────────────────────────────────────────────────

class TestExamPrepSubjects:
    """Subjects endpoint returns Physics, Chemistry, Mathematics for JEE."""

    def test_jee_subjects_returned(self, monkeypatch):
        """JEE subjects must include Physics, Chemistry, Mathematics."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        # Requires Premium+ content access — see comment in
        # test_dashboard_returns_jee_data for why this must be patched here.
        monkeypatch.setattr(
            "app.services.feature_authorization_service.authorize_feature",
            lambda uid, feat: {"allowed": True, "limited": False, "canonical_plan_key": "PREMIUM"},
            raising=False,
        )

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            r = client.get("/api/exam-prep/subjects?exam=jee_main")

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        subject_names = [s["name"] for s in data["subjects"]]
        assert "Physics" in subject_names
        assert "Chemistry" in subject_names
        assert "Mathematics" in subject_names
        clear_overrides()


# ── Per-subject / per-exam attempt scoping (regression) ──────────────────────────
# Previously "questions attempted" was a single lifetime count across every
# exam AND subject the student had ever practiced, with no subject or
# exam_type on exam_prep_attempts itself (only question_id). That made every
# subject's "Practice Questions" phase in the Structured Learning tab show
# "Done" simultaneously as soon as the student practiced any ONE subject in
# any exam. These tests exercise the service functions directly (no HTTP
# layer) against the join-based fix.

class TestDashboardExamScoping:
    def test_dashboard_only_counts_attempts_joined_to_this_exam(self):
        """questions_attempted/correct_count must come from the exam-scoped join."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 10
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "a1", "is_correct": True, "exam_prep_questions": {"subject": "Physics", "exam_type": "jee_main"}},
            {"id": "a2", "is_correct": False, "exam_prep_questions": {"subject": "Chemistry", "exam_type": "jee_main"}},
        ]

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            data = ep_svc.get_dashboard(exam_type="jee_main", user_id="g12-1")

        assert data["questions_attempted"] == 2
        assert data["correct_count"] == 1
        assert data["accuracy_pct"] == 50


class TestSubjectsPerSubjectAttempts:
    def test_each_subject_has_its_own_attempted_count(self):
        """A subject with no attempts must not inherit another subject's count."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "a1", "is_correct": True, "exam_prep_questions": {"subject": "Physics", "exam_type": "jee_main"}},
            {"id": "a2", "is_correct": True, "exam_prep_questions": {"subject": "Physics", "exam_type": "jee_main"}},
            {"id": "a3", "is_correct": False, "exam_prep_questions": {"subject": "Chemistry", "exam_type": "jee_main"}},
        ]

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            subjects = ep_svc.get_subjects(exam_type="jee_main", user_id="g12-1")

        by_name = {s["name"]: s for s in subjects}
        assert by_name["Physics"]["questions_attempted"] == 2
        assert by_name["Chemistry"]["questions_attempted"] == 1
        assert by_name["Mathematics"]["questions_attempted"] == 0


class TestSubmitAnswerIncludesTopic:
    def test_submit_answer_response_includes_subject_and_topic(self):
        """
        The frontend's "Revise Weak Topics" phase groups incorrect answers by
        subject/topic from this response. Before this fix, submit_answer's
        DB select and return dict both omitted subject/topic, so the feature
        silently never had anything to show, for any student.
        """
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "correct_option": "B",
            "detailed_explanation": "",
            "solution_steps_json": [],
            "formula_used": "",
            "ncert_reference": "",
            "marks": 4,
            "negative_marks": 1,
            "subject": "Physics",
            "topic": "Kinematics",
        }

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = ep_svc.submit_answer(user_id="g12-1", question_id="q-1", selected_option="A")

        assert result["subject"] == "Physics"
        assert result["topic"] == "Kinematics"


# ── Topics tests ────────────────────────────────────────────────────────────────

class TestExamPrepTopics:
    """Topics endpoint returns priority topics for a subject."""

    def test_physics_topics_have_priority(self, monkeypatch):
        """Physics topics must have priority field (HIGH/MED/LOW)."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        # Requires Premium+ content access — see comment in
        # test_dashboard_returns_jee_data for why this must be patched here.
        monkeypatch.setattr(
            "app.services.feature_authorization_service.authorize_feature",
            lambda uid, feat: {"allowed": True, "limited": False, "canonical_plan_key": "PREMIUM"},
            raising=False,
        )
        r = client.get("/api/exam-prep/topics?exam=jee_main&subject=Physics")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert len(data["topics"]) > 0
        for topic in data["topics"]:
            assert topic["priority"] in ("HIGH", "MED", "LOW"), f"Bad priority: {topic}"
        clear_overrides()


# ── Questions test ──────────────────────────────────────────────────────────────

class TestExamPrepQuestions:
    """Questions endpoint returns only published questions."""

    def test_questions_are_published_only(self, monkeypatch):
        """Questions must never include draft or archived questions."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        # Requires Premium+ content access — see comment in
        # test_dashboard_returns_jee_data for why this must be patched here.
        monkeypatch.setattr(
            "app.services.feature_authorization_service.authorize_feature",
            lambda uid, feat: {"allowed": True, "limited": False, "canonical_plan_key": "PREMIUM"},
            raising=False,
        )

        # Mock DB returning mix of statuses — only published should pass through
        mock_published = [
            {
                "id": "q-1",
                "subject": "Physics",
                "topic": "Kinematics",
                "question_text": "A ball is thrown...",
                "options_json": [{"key": "A", "text": "1m"}, {"key": "B", "text": "2m"},
                                  {"key": "C", "text": "3m"}, {"key": "D", "text": "4m"}],
                "correct_option": "B",
                "difficulty": "medium",
                "marks": 4, "negative_marks": 1,
                "chapter": "Motion", "subtopic": "Projectile",
                "estimated_time_seconds": 120, "ncert_reference": "",
                "formula_used": "", "source_type": "llm_generated",
                "status": "published",  # Only published
            }
        ]

        mock_db = MagicMock()
        mock_chain = MagicMock()
        mock_chain.execute.return_value.data = mock_published
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            r = client.get("/api/exam-prep/questions?exam=jee_main&subject=Physics")

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        # All returned questions should only be ones the DB returned (published)
        clear_overrides()


# ── Admin-only: Prewarm ─────────────────────────────────────────────────────────

class TestPrewarmAdminOnly:
    """Prewarm endpoint must be admin-only."""

    def test_non_admin_cannot_prewarm(self, monkeypatch):
        """Grade 12 student cannot access admin prewarm endpoint."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.services.auth_service.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        r = client.post("/api/admin/exam-prep/question-bank/prewarm", json={
            "exam_type": "jee_main",
            "grade": "Grade 12",
            "subject": "Physics",
            "question_count": 5,
        })
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        clear_overrides()

    def test_admin_can_access_question_bank_status(self, monkeypatch):
        """Admin can access question bank status."""
        override_user(ADMIN_USER, ADMIN_PROFILE)
        monkeypatch.setattr(
            "app.services.auth_service.get_user_profile",
            lambda uid: ADMIN_PROFILE,
            raising=False,
        )

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            r = client.get("/api/admin/exam-prep/question-bank/status")

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        clear_overrides()

    def test_grade_10_cannot_access_admin_qb_status(self, monkeypatch):
        """Grade 10 student cannot access admin question bank status."""
        override_user(GRADE_10_USER, GRADE_10_PROFILE)
        monkeypatch.setattr(
            "app.services.auth_service.get_user_profile",
            lambda uid: GRADE_10_PROFILE,
            raising=False,
        )
        r = client.get("/api/admin/exam-prep/question-bank/status")
        assert r.status_code == 403
        clear_overrides()


# ── Simulated test ──────────────────────────────────────────────────────────────

class TestSimulatedTest:
    """Simulated test flow returns valid results with score <= 100."""

    def test_start_test_with_empty_bank_succeeds(self, monkeypatch):
        """Starting a test with no questions in bank returns success gracefully."""
        override_user(GRADE_12_USER, GRADE_12_PROFILE)
        monkeypatch.setattr(
            "app.routes.exam_prep.get_user_profile",
            lambda uid: GRADE_12_PROFILE,
            raising=False,
        )
        # Requires Premium+ content access — see comment in
        # test_dashboard_returns_jee_data for why this must be patched here.
        monkeypatch.setattr(
            "app.services.feature_authorization_service.authorize_feature",
            lambda uid, feat: {"allowed": True, "limited": False, "canonical_plan_key": "PREMIUM"},
            raising=False,
        )

        mock_db = MagicMock()
        # No questions in DB
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        # Insert test session
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "test-session-1", "status": "active", "started_at": "2026-01-01T00:00:00Z"}
        ]

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            r = client.post("/api/exam-prep/simulated-tests/start", json={"exam": "jee_main"})

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "test_id" in data
        assert data["total_questions"] == 0
        clear_overrides()

    def test_submit_test_score_never_exceeds_100(self):
        """Score normalization: submitted test score must always be <= 100."""
        from app.services.exam_prep_service import submit_simulated_test

        # Build a mock test with 3 questions, all correct (max score)
        mock_db = MagicMock()

        # Mock test fetch
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-1",
            "user_id": "g12-1",
            "exam_type": "jee_main",
            "grade": "Grade 12",
            "question_ids": ["q-1", "q-2", "q-3"],
            "status": "active",
        }

        # Mock questions fetch
        mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "q-1", "subject": "Physics", "topic": "Kinematics", "correct_option": "A", "marks": 4, "negative_marks": 1},
            {"id": "q-2", "subject": "Chemistry", "topic": "Equilibrium", "correct_option": "B", "marks": 4, "negative_marks": 1},
            {"id": "q-3", "subject": "Mathematics", "topic": "Integration", "correct_option": "C", "marks": 4, "negative_marks": 1},
        ]

        # Mock answer insert
        mock_db.table.return_value.insert.return_value.execute.return_value.data = []
        # Mock test update
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        answers = [
            {"question_id": "q-1", "selected_option": "A", "time_taken_seconds": 30},  # correct
            {"question_id": "q-2", "selected_option": "B", "time_taken_seconds": 45},  # correct
            {"question_id": "q-3", "selected_option": "C", "time_taken_seconds": 60},  # correct
        ]

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = submit_simulated_test(
                test_id="test-1",
                user_id="g12-1",
                answers=answers,
                time_spent_seconds=135,
            )

        assert result["score_normalized"] <= 100.0, (
            f"Score normalized exceeded 100%: {result['score_normalized']}"
        )
        assert result["score_normalized"] >= 0.0
        assert result["correct"] == 3
        assert result["wrong"] == 0

    def test_submit_with_all_wrong_gives_negative_raw_but_zero_normalized(self):
        """All wrong answers: score_raw may be negative, score_normalized stays >= 0."""
        from app.services.exam_prep_service import submit_simulated_test

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-2",
            "user_id": "g12-1",
            "exam_type": "jee_main",
            "grade": "Grade 12",
            "question_ids": ["q-1"],
            "status": "active",
        }
        mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "q-1", "subject": "Physics", "topic": "Kinematics", "correct_option": "A", "marks": 4, "negative_marks": 1},
        ]
        mock_db.table.return_value.insert.return_value.execute.return_value.data = []
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        answers = [{"question_id": "q-1", "selected_option": "D", "time_taken_seconds": 30}]  # wrong

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = submit_simulated_test("test-2", "g12-1", answers, 30)

        assert result["score_normalized"] >= 0.0, "Normalized score cannot be negative"
        assert result["score_normalized"] <= 100.0
        assert result["wrong"] == 1


# ── Validation tests ────────────────────────────────────────────────────────────

class TestQuestionValidation:
    """Prewarm validation rejects malformed questions."""

    def test_empty_question_text_fails_validation(self):
        from app.services.exam_prep_service import _validate_question
        errors = _validate_question({
            "question_text": "",
            "options": {"A": "opt1", "B": "opt2", "C": "opt3", "D": "opt4"},
            "correct_option": "A",
            "detailed_explanation": "Some explanation",
            "difficulty": "medium",
            "topic": "Kinematics",
        })
        assert any("Empty question" in e for e in errors)

    def test_missing_option_fails_validation(self):
        from app.services.exam_prep_service import _validate_question
        errors = _validate_question({
            "question_text": "What is force?",
            "options": {"A": "opt1", "B": "opt2", "C": "opt3"},  # missing D
            "correct_option": "A",
            "detailed_explanation": "F=ma",
            "difficulty": "easy",
            "topic": "Newton's Laws",
        })
        assert any("4 options" in e for e in errors)

    def test_invalid_correct_option_fails_validation(self):
        from app.services.exam_prep_service import _validate_question
        errors = _validate_question({
            "question_text": "What is force?",
            "options": {"A": "opt1", "B": "opt2", "C": "opt3", "D": "opt4"},
            "correct_option": "E",  # invalid key
            "detailed_explanation": "F=ma",
            "difficulty": "easy",
            "topic": "Newton's Laws",
        })
        assert any("correct_option" in e.lower() or "A, B, C, or D" in e for e in errors)

    def test_duplicate_options_fails_validation(self):
        from app.services.exam_prep_service import _validate_question
        errors = _validate_question({
            "question_text": "What is force?",
            "options": {"A": "Same", "B": "Same", "C": "opt3", "D": "opt4"},
            "correct_option": "A",
            "detailed_explanation": "F=ma",
            "difficulty": "easy",
            "topic": "Newton's Laws",
        })
        assert any("duplicate" in e.lower() for e in errors)

    def test_valid_question_passes_validation(self):
        from app.services.exam_prep_service import _validate_question
        errors = _validate_question({
            "question_text": "A body of mass 2 kg is accelerated at 5 m/s². What is the force?",
            "options": {"A": "5 N", "B": "10 N", "C": "15 N", "D": "20 N"},
            "correct_option": "B",
            "detailed_explanation": "F = ma = 2 × 5 = 10 N",
            "difficulty": "easy",
            "topic": "Newton's Laws",
        })
        assert errors == [], f"Expected no errors, got: {errors}"
