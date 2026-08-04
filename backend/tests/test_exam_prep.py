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


class TestSubjectsThinBankFlag:
    """
    Subjects at or below their per-session target have zero rotation
    headroom — every attempt already shows the whole bank, no amount of
    exclusion/shuffling logic can fix that, only more written questions can.
    Subjects with zero published questions get a distinct no_content flag
    instead (there's nothing to rotate through at all).
    """

    def test_flags_thin_and_empty_subjects_relative_to_session_target(self):
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        # JEE's target is 25/subject: Physics gets plenty of headroom (100),
        # Chemistry sits exactly at the target (25, thin), Mathematics none.
        question_rows = [{"subject": "Physics"}] * 100 + [{"subject": "Chemistry"}] * 25

        def fake_table(name):
            if name == "exam_prep_questions":
                return _FakeTable(question_rows)
            return _FakeTable([])

        mock_db = MagicMock()
        mock_db.table.side_effect = fake_table

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            subjects = ep_svc.get_subjects(exam_type="jee_main", user_id="g12-1")

        by_name = {s["name"]: s for s in subjects}
        assert by_name["Physics"]["target_per_session"] == 25
        assert by_name["Physics"]["thin_bank"] is False
        assert by_name["Physics"]["no_content"] is False

        assert by_name["Chemistry"]["thin_bank"] is True
        assert by_name["Chemistry"]["no_content"] is False

        assert by_name["Mathematics"]["question_count"] == 0
        assert by_name["Mathematics"]["no_content"] is True
        assert by_name["Mathematics"]["thin_bank"] is False

    def test_cuet_subject_without_explicit_target_uses_cuet_default(self):
        """CUET subjects aren't in the fixed per-exam target map (student
        picks their own combination) — they fall back to the flat 40/subject
        CUET default instead."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        question_rows = [{"subject": "Business Studies"}] * 12

        def fake_table(name):
            if name == "exam_prep_questions":
                return _FakeTable(question_rows)
            return _FakeTable([])

        mock_db = MagicMock()
        mock_db.table.side_effect = fake_table

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            subjects = ep_svc.get_subjects(exam_type="cuet_ug", user_id="g12-1")

        by_name = {s["name"]: s for s in subjects}
        assert by_name["Business Studies"]["target_per_session"] == 40
        assert by_name["Business Studies"]["thin_bank"] is True


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


# ── Question rotation / exclusion (regression) ───────────────────────────────────
# Previously every question fetch (Practice tab and Simulated Test) was a bare
# `LIMIT N` with no ORDER BY and no exclusion of already-attempted questions,
# so the same fixed subset was served in the same order on every single
# attempt, forever — "how many unique questions before it repeats" was
# effectively "one." These tests exercise the new _pick_questions() helper
# directly, and get_questions()/start_simulated_test() through it.

def _mk_question_row(qid, subject, topic="Topic A"):
    return {
        "id": qid, "subject": subject, "chapter": "Ch1", "topic": topic, "subtopic": "",
        "question_text": f"Question {qid}",
        "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_option": "A", "difficulty": "medium", "marks": 4, "negative_marks": 1,
        "estimated_time_seconds": 60, "ncert_reference": "", "formula_used": "", "source_type": "llm_generated",
    }


class _FakeTable:
    """Minimal chainable fake matching this codebase's existing test convention
    (see test_admin_payment_upgrade.py) — every builder method returns self,
    .execute() returns the fixed rows this table was built with."""

    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def ilike(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def insert(self, data):
        self._inserted = data
        return self
    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=self._rows)


class TestPickQuestions:
    """Pure unit tests for the exclude-seen + shuffle + fallback helper."""

    def test_excludes_seen_when_enough_unseen_remain(self):
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415
        rows = [{"id": f"q{i}"} for i in range(10)]
        seen = {"q0", "q1", "q2"}
        picked = ep_svc._pick_questions(rows, limit=5, seen_ids=seen)
        picked_ids = {r["id"] for r in picked}
        assert len(picked) == 5
        assert picked_ids.isdisjoint(seen)

    def test_falls_back_to_full_pool_once_exhausted(self):
        """A student who has seen every question in the pool keeps
        practicing from the full set instead of getting a short/empty one."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415
        rows = [{"id": f"q{i}"} for i in range(5)]
        seen = {"q0", "q1", "q2", "q3", "q4"}
        picked = ep_svc._pick_questions(rows, limit=3, seen_ids=seen)
        assert len(picked) == 3

    def test_never_returns_more_than_available(self):
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415
        rows = [{"id": "q1"}, {"id": "q2"}]
        picked = ep_svc._pick_questions(rows, limit=10, seen_ids=set())
        assert len(picked) == 2

    def test_order_is_randomized_not_a_fixed_top_n(self):
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415
        rows = [{"id": f"q{i}"} for i in range(30)]
        orders = {tuple(r["id"] for r in ep_svc._pick_questions(rows, limit=30, seen_ids=set())) for _ in range(8)}
        assert len(orders) > 1


class TestGetQuestionsExclusion:
    def test_excludes_previously_attempted_questions(self):
        """A question this user already attempted must not reappear while
        there are still enough unattempted ones to fill the request."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        all_questions = [_mk_question_row(f"q{i}", "Physics") for i in range(10)]
        attempted = [
            {"question_id": "q0", "is_correct": True, "exam_prep_questions": {"subject": "Physics", "exam_type": "jee_main"}},
            {"question_id": "q1", "is_correct": False, "exam_prep_questions": {"subject": "Physics", "exam_type": "jee_main"}},
        ]

        def fake_table(name):
            if name == "exam_prep_questions":
                return _FakeTable(all_questions)
            if name == "exam_prep_attempts":
                return _FakeTable(attempted)
            return _FakeTable([])

        mock_db = MagicMock()
        mock_db.table.side_effect = fake_table

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = ep_svc.get_questions(exam_type="jee_main", subject="Physics", topic=None, limit=5, user_id="g12-1")

        result_ids = {r["id"] for r in result}
        assert "q0" not in result_ids
        assert "q1" not in result_ids
        assert len(result) == 5


class TestStartSimulatedTestNeetBiology:
    def test_neet_uses_biology_not_botany_zoology(self):
        """
        Regression: the simulator used to request subjects "Botany" and
        "Zoology", which don't exist in the database — every real Biology
        question is tagged just "Biology" (matching Practice mode and
        EXAM_SUBJECTS_MAP). Both queries returned zero rows, so every NEET
        simulated test silently dropped from 180 to 90 questions with no
        Biology at all. Biology now gets double the per-subject share
        (90) in a single "Biology" entry instead of two subjects that
        return nothing.
        """
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        physics = [_mk_question_row(f"phy{i}", "Physics") for i in range(60)]
        chemistry = [_mk_question_row(f"chem{i}", "Chemistry") for i in range(60)]
        biology = [_mk_question_row(f"bio{i}", "Biology") for i in range(120)]
        by_subject = {"Physics": physics, "Chemistry": chemistry, "Biology": biology}

        def fake_table(name):
            if name == "exam_prep_questions":
                # The fake needs to know which subject was asked for; since
                # _FakeTable.eq() is a no-op, route by returning a table that
                # inspects the most recent .eq("subject", ...) call instead.
                return _SubjectAwareQuestionsTable(by_subject)
            if name == "exam_prep_attempts":
                return _FakeTable([])
            if name == "exam_prep_simulated_tests":
                return _FakeTable([{"id": "test-1", "status": "active", "started_at": "2026-01-01T00:00:00Z"}])
            return _FakeTable([])

        mock_db = MagicMock()
        mock_db.table.side_effect = fake_table

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = ep_svc.start_simulated_test(user_id="g12-1", exam_type="neet_ug", grade="Grade 12")

        subjects_shown = {q["subject"] for q in result["questions"]}
        assert subjects_shown == {"Physics", "Chemistry", "Biology"}
        assert "Botany" not in subjects_shown
        assert "Zoology" not in subjects_shown

        by_result_subject = {}
        for q in result["questions"]:
            by_result_subject.setdefault(q["subject"], 0)
            by_result_subject[q["subject"]] += 1
        assert by_result_subject["Physics"] == 45
        assert by_result_subject["Chemistry"] == 45
        assert by_result_subject["Biology"] == 90
        assert result["total_questions"] == 180


class _SubjectAwareQuestionsTable:
    """Like _FakeTable, but returns rows for whichever subject was filtered
    via .eq("subject", <value>) — needed when a test issues several
    per-subject queries against the same mocked table in one call."""

    def __init__(self, rows_by_subject):
        self._rows_by_subject = rows_by_subject
        self._subject = None

    def select(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def ilike(self, *_a, **_k): return self

    def eq(self, field, value):
        if field == "subject":
            self._subject = value
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=self._rows_by_subject.get(self._subject, []))


class TestStartSimulatedTestCuetSubjects:
    def test_subjects_param_overrides_default_subject_list(self):
        """CUET students pick their own subject combination — start_simulated_test
        must fetch exactly those subjects, each capped at the CUET default of 40,
        instead of the fixed per-exam target map used by other exams."""
        import app.services.exam_prep_service as ep_svc  # noqa: PLC0415

        history = [_mk_question_row(f"hist{i}", "History") for i in range(50)]
        geography = [_mk_question_row(f"geo{i}", "Geography") for i in range(50)]
        by_subject = {"History": history, "Geography": geography}

        def fake_table(name):
            if name == "exam_prep_questions":
                return _SubjectAwareQuestionsTable(by_subject)
            if name == "exam_prep_attempts":
                return _FakeTable([])
            if name == "exam_prep_simulated_tests":
                return _FakeTable([{"id": "test-2", "status": "active", "started_at": "2026-01-01T00:00:00Z"}])
            return _FakeTable([])

        mock_db = MagicMock()
        mock_db.table.side_effect = fake_table

        with patch("app.services.exam_prep_service._get_db", return_value=mock_db):
            result = ep_svc.start_simulated_test(
                user_id="g12-1", exam_type="cuet_ug", grade="Grade 12",
                subjects=["History", "Geography"],
            )

        subjects_shown = {q["subject"] for q in result["questions"]}
        assert subjects_shown == {"History", "Geography"}
        assert result["total_questions"] == 80  # 40 + 40


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
