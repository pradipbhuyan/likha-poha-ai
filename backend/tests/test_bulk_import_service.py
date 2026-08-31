"""
test_bulk_import_service.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/services/bulk_import_service.py — the core validate/create
logic shared by the admin bulk-import API (admin_bulk.py) and the
standalone Excel-import script.
"""
from unittest.mock import MagicMock, patch

import app.services.bulk_import_service as svc


def _chain_mock(execute_return, ilike_execute_return=None):
    m = MagicMock()
    for method in ("select", "eq", "limit", "insert", "upsert"):
        getattr(m, method).return_value = m
    m.execute.return_value = execute_return

    # .ilike(...) is the username-uniqueness check (unique_username) — give
    # it its own independent sub-chain, defaulting to "no collision", so a
    # test configuring the .eq(...) path (e.g. teacher-by-email lookup) can't
    # accidentally make every username look "taken" too.
    ilike_chain = MagicMock()
    ilike_chain.limit.return_value = ilike_chain
    ilike_chain.execute.return_value = ilike_execute_return or MagicMock(data=[])
    m.ilike.return_value = ilike_chain

    return m


class _TableRouter:
    """admin_client.table(name) -> a memoized chain mock per table name, so a
    test can inspect exactly what was passed to insert()/upsert() on it."""

    def __init__(self, responses: dict, ilike_responses: dict | None = None):
        self._responses = responses
        self._ilike_responses = ilike_responses or {}
        self.chains = {}

    def __call__(self, name):
        if name not in self.chains:
            self.chains[name] = _chain_mock(
                self._responses.get(name, MagicMock(data=[])),
                self._ilike_responses.get(name),
            )
        return self.chains[name]


class TestValidateStudentRows:
    def test_valid_row_has_no_errors(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com"}]
        preview, errors = svc.validate_student_rows(rows)
        assert errors == []
        assert preview[0]["errors"] == []

    def test_missing_name_is_an_error(self):
        rows = [{"name": "", "grade": "Grade 9"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert len(errors) == 1
        assert "name is required" in errors[0]["issues"]

    def test_invalid_email_is_an_error(self):
        rows = [{"name": "A", "grade": "Grade 9", "email": "not-an-email"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert any("invalid email" in issue for issue in errors[0]["issues"])

    def test_grade_must_start_with_grade_prefix(self):
        rows = [{"name": "A", "grade": "9"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert any("grade must start with" in issue for issue in errors[0]["issues"])

    def test_missing_email_is_not_an_error(self):
        # Students may not have an email yet — a placeholder is generated at import time.
        rows = [{"name": "A", "grade": "Grade 9"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert errors == []

    def test_grade_11_without_stream_is_an_error(self):
        rows = [{"name": "A", "grade": "Grade 11"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert any("stream is required" in issue for issue in errors[0]["issues"])

    def test_grade_12_with_invalid_stream_is_an_error(self):
        rows = [{"name": "A", "grade": "Grade 12", "stream": "Science"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert any("stream is required" in issue for issue in errors[0]["issues"])

    def test_grade_11_with_valid_stream_has_no_errors(self):
        rows = [{"name": "A", "grade": "Grade 11", "stream": "PCM"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert errors == []

    def test_grade_below_11_does_not_require_stream(self):
        rows = [{"name": "A", "grade": "Grade 10"}]
        _preview, errors = svc.validate_student_rows(rows)
        assert errors == []


class TestValidateTeacherRows:
    def test_valid_row_has_no_errors(self):
        rows = [{"name": "Anita Desai", "email": "anita@x.com"}]
        _preview, errors = svc.validate_teacher_rows(rows)
        assert errors == []

    def test_missing_email_is_an_error(self):
        # Unlike students, a teacher's email is required — they must log in themselves.
        rows = [{"name": "Anita Desai", "email": ""}]
        _preview, errors = svc.validate_teacher_rows(rows)
        assert "email is required for a teacher account" in errors[0]["issues"]

    def test_missing_name_is_an_error(self):
        rows = [{"name": "", "email": "a@x.com"}]
        _preview, errors = svc.validate_teacher_rows(rows)
        assert "name is required" in errors[0]["issues"]


class TestImportStudents:
    def test_creates_account_linked_to_school(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            outcome = svc.import_students(rows, school_id="school-1")

        assert outcome["created"] == 1
        assert outcome["failed"] == 0
        assert outcome["results"][0]["user_id"] == "new-uid"
        upsert_payload = router.chains["profiles"].upsert.call_args.args[0]
        assert upsert_payload["school_id"] == "school-1"

    def test_grade_11_sets_stream_and_derived_subjects(self):
        rows = [{"name": "A", "grade": "Grade 11", "email": "a@x.com", "stream": "PCM"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            svc.import_students(rows, school_id=None)

        upsert_payload = router.chains["profiles"].upsert.call_args.args[0]
        assert upsert_payload["stream"] == "PCM"
        assert upsert_payload["cbse_subjects"] == svc.STREAM_SUBJECTS["PCM"]

    def test_grade_below_11_writes_no_stream_or_subjects(self):
        rows = [{"name": "A", "grade": "Grade 9", "email": "a@x.com"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            svc.import_students(rows, school_id=None)

        upsert_payload = router.chains["profiles"].upsert.call_args.args[0]
        assert "stream" not in upsert_payload
        assert "cbse_subjects" not in upsert_payload

    def test_no_school_id_means_no_school_id_key_written(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            svc.import_students(rows, school_id=None)

        upsert_payload = router.chains["profiles"].upsert.call_args.args[0]
        assert "school_id" not in upsert_payload

    def test_teacher_email_links_when_teacher_found(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com", "teacher_email": "anita@x.com"}]
        router = _TableRouter({"profiles": MagicMock(data=[{"id": "teacher-uid"}])})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            outcome = svc.import_students(rows, school_id=None)

        assert outcome["results"][0]["teacher_link"] == "linked"
        assignment_payload = router.chains["teacher_student_assignments"].insert.call_args.args[0]
        assert assignment_payload["teacher_id"] == "teacher-uid"
        assert assignment_payload["student_id"] == "new-uid"

    def test_teacher_email_not_found_does_not_block_import(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com", "teacher_email": "ghost@x.com"}]
        router = _TableRouter({"profiles": MagicMock(data=[])})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            outcome = svc.import_students(rows, school_id=None)

        assert outcome["created"] == 1
        assert "not found" in outcome["results"][0]["teacher_link"]
        assert "teacher_student_assignments" not in router.chains

    def test_auth_creation_failure_is_recorded(self):
        rows = [{"name": "Aarav Sharma", "grade": "Grade 9", "email": "aarav@x.com"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.side_effect = Exception("email already registered")
            mock_client.table.side_effect = router
            outcome = svc.import_students(rows, school_id=None)

        assert outcome["created"] == 0
        assert outcome["failed"] == 1
        assert "already registered" in outcome["results"][0]["error"]


class TestImportTeachers:
    def test_creates_account_linked_to_school(self):
        rows = [{"name": "Anita Desai", "email": "anita@x.com"}]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            mock_client.table.side_effect = router
            outcome = svc.import_teachers(rows, school_id="school-1")

        assert outcome["created"] == 1
        upsert_payload = router.chains["profiles"].upsert.call_args.args[0]
        assert upsert_payload["role"] == "teacher"
        assert upsert_payload["school_id"] == "school-1"

    def test_failure_is_recorded_without_blocking_other_rows(self):
        rows = [
            {"name": "Anita Desai", "email": "anita@x.com"},
            {"name": "Rajesh Kumar", "email": "rajesh@x.com"},
        ]
        router = _TableRouter({})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.side_effect = [
                Exception("duplicate"),
                MagicMock(user=MagicMock(id="uid-2")),
            ]
            mock_client.table.side_effect = router
            outcome = svc.import_teachers(rows, school_id=None)

        assert outcome["failed"] == 1
        assert outcome["created"] == 1


class TestUniqueUsername:
    def test_returns_desired_name_when_free(self):
        with patch.object(svc, "admin_client") as mock_client:
            chain = MagicMock()
            chain.select.return_value = chain
            chain.ilike.return_value = chain
            chain.limit.return_value = chain
            chain.execute.return_value = MagicMock(data=[])
            mock_client.table.return_value = chain

            assert svc.unique_username("Priya Sharma") == "Priya Sharma"

    def test_appends_suffix_on_collision(self):
        with patch.object(svc, "admin_client") as mock_client:
            chain = MagicMock()
            chain.select.return_value = chain
            chain.ilike.return_value = chain
            chain.limit.return_value = chain
            chain.execute.side_effect = [MagicMock(data=[{"id": "x"}]), MagicMock(data=[])]
            mock_client.table.return_value = chain

            assert svc.unique_username("Priya Sharma") == "Priya Sharma (2)"

    def test_keeps_incrementing_through_multiple_collisions(self):
        with patch.object(svc, "admin_client") as mock_client:
            chain = MagicMock()
            chain.select.return_value = chain
            chain.ilike.return_value = chain
            chain.limit.return_value = chain
            chain.execute.side_effect = [
                MagicMock(data=[{"id": "x"}]),  # "Priya Sharma" taken
                MagicMock(data=[{"id": "y"}]),  # "Priya Sharma (2)" taken
                MagicMock(data=[]),             # "Priya Sharma (3)" free
            ]
            mock_client.table.return_value = chain

            assert svc.unique_username("Priya Sharma") == "Priya Sharma (3)"


class TestImportDuplicateNames:
    def test_student_with_taken_name_gets_a_disambiguating_suffix(self):
        rows = [{"name": "Priya Sharma", "grade": "Grade 9", "email": "priya@x.com"}]
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            chain = MagicMock()
            chain.select.return_value = chain
            chain.ilike.return_value = chain
            chain.limit.return_value = chain
            chain.upsert.return_value = chain
            chain.execute.side_effect = [
                MagicMock(data=[{"id": "existing"}]),  # "Priya Sharma" already taken
                MagicMock(data=[]),                     # "Priya Sharma (2)" is free
                MagicMock(data=[{"id": "new-uid"}]),    # the upsert() call itself
            ]
            mock_client.table.return_value = chain

            outcome = svc.import_students(rows, school_id=None)

        assert outcome["results"][0]["username"] == "Priya Sharma (2)"
        upsert_payload = chain.upsert.call_args.args[0]
        assert upsert_payload["username"] == "Priya Sharma (2)"

    def test_teacher_with_taken_name_gets_a_disambiguating_suffix(self):
        rows = [{"name": "Anita Desai", "email": "anita@x.com"}]
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="new-uid"))
            chain = MagicMock()
            chain.select.return_value = chain
            chain.ilike.return_value = chain
            chain.limit.return_value = chain
            chain.upsert.return_value = chain
            chain.execute.side_effect = [
                MagicMock(data=[{"id": "existing"}]),
                MagicMock(data=[]),
                MagicMock(data=[{"id": "new-uid"}]),
            ]
            mock_client.table.return_value = chain

            outcome = svc.import_teachers(rows, school_id=None)

        assert outcome["results"][0]["username"] == "Anita Desai (2)"


class TestSchoolExists:
    def test_true_when_found(self):
        router = _TableRouter({"schools": MagicMock(data=[{"id": "s1"}])})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.side_effect = router
            assert svc.school_exists("s1") is True

    def test_false_when_not_found(self):
        router = _TableRouter({"schools": MagicMock(data=[])})
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.side_effect = router
            assert svc.school_exists("missing") is False
