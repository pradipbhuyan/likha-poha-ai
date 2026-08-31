"""
test_admin_bulk.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/routes/admin_bulk.py's /import-students and /import-teachers —
the school-linked bulk-account-creation endpoints. Account-creation logic
itself is covered in test_bulk_import_service.py; these tests mock
bulk_import_service and focus on the route's two-phase contract, school_id
validation, and response shape.
"""
from unittest.mock import patch

import app.routes.admin_bulk as route


def fake_admin():
    return {"id": "admin-1", "profile": {"id": "admin-1", "role": "admin"}}


class TestImportStudents:
    def test_unknown_school_id_is_rejected_before_any_validation(self):
        req = route.BulkImportRequest(
            rows=[route.CsvStudentRow(name="A", grade="Grade 9")],
            school_id="ghost-school",
        )
        with patch.object(route.bulk_import_service, "school_exists", return_value=False):
            result = route.bulk_import_students(req, admin=fake_admin())

        assert result["success"] is False
        assert "ghost-school" in result["error"]

    def test_preview_mode_does_not_create_accounts(self):
        req = route.BulkImportRequest(rows=[route.CsvStudentRow(name="A", grade="Grade 9")], confirmed=False)
        with patch.object(route.bulk_import_service, "import_students") as mock_import:
            result = route.bulk_import_students(req, admin=fake_admin())

        assert result["preview"] is True
        mock_import.assert_not_called()

    def test_validation_errors_block_the_import(self):
        req = route.BulkImportRequest(rows=[route.CsvStudentRow(name="", grade="Grade 9")], confirmed=True)
        with patch.object(route.bulk_import_service, "import_students") as mock_import:
            result = route.bulk_import_students(req, admin=fake_admin())

        assert result["success"] is False
        mock_import.assert_not_called()

    def test_confirmed_import_passes_school_id_through(self):
        req = route.BulkImportRequest(
            rows=[route.CsvStudentRow(name="A", grade="Grade 9", email="a@x.com")],
            school_id="school-1",
            confirmed=True,
        )
        with patch.object(route.bulk_import_service, "school_exists", return_value=True), \
             patch.object(route.bulk_import_service, "import_students",
                          return_value={"created": 1, "failed": 0, "results": []}) as mock_import, \
             patch.object(route, "write_audit_event"):
            result = route.bulk_import_students(req, admin=fake_admin())

        assert result["success"] is True
        assert result["created"] == 1
        mock_import.assert_called_once()
        _, kwargs = mock_import.call_args
        assert kwargs["school_id"] == "school-1"


class TestImportTeachers:
    def test_empty_email_is_caught_by_validation_not_construction(self):
        # CsvTeacherRow's email is a plain str (empty string is a valid Pydantic
        # value) — "required" is a business rule enforced by
        # bulk_import_service.validate_teacher_rows, not the model itself.
        req = route.BulkImportTeachersRequest(rows=[route.CsvTeacherRow(name="Anita Desai", email="")])
        result = route.bulk_import_teachers(req, admin=fake_admin())
        assert result["preview"] is True
        assert result["error_count"] == 1

    def test_preview_mode_does_not_create_accounts(self):
        req = route.BulkImportTeachersRequest(
            rows=[route.CsvTeacherRow(name="Anita Desai", email="anita@x.com")], confirmed=False
        )
        with patch.object(route.bulk_import_service, "import_teachers") as mock_import:
            result = route.bulk_import_teachers(req, admin=fake_admin())

        assert result["preview"] is True
        mock_import.assert_not_called()

    def test_confirmed_import_passes_school_id_through(self):
        req = route.BulkImportTeachersRequest(
            rows=[route.CsvTeacherRow(name="Anita Desai", email="anita@x.com")],
            school_id="school-1",
            confirmed=True,
        )
        with patch.object(route.bulk_import_service, "school_exists", return_value=True), \
             patch.object(route.bulk_import_service, "import_teachers",
                          return_value={"created": 1, "failed": 0, "results": []}) as mock_import, \
             patch.object(route, "write_audit_event"):
            result = route.bulk_import_teachers(req, admin=fake_admin())

        assert result["success"] is True
        mock_import.assert_called_once()
        _, kwargs = mock_import.call_args
        assert kwargs["school_id"] == "school-1"

    def test_unknown_school_id_is_rejected(self):
        req = route.BulkImportTeachersRequest(
            rows=[route.CsvTeacherRow(name="Anita Desai", email="anita@x.com")],
            school_id="ghost-school",
        )
        with patch.object(route.bulk_import_service, "school_exists", return_value=False):
            result = route.bulk_import_teachers(req, admin=fake_admin())

        assert result["success"] is False
