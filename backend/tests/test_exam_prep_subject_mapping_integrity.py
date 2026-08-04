"""
test_exam_prep_subject_mapping_integrity.py
============================================
Regression coverage for the subject/EXAM_SUBJECTS_MAP mapping-integrity check.

Root cause this guards against: 60 CUET questions were written with
subject="Physics"/"Mathematics"/"Biology" while the declared, student-facing
keys are "Physics (Domain)"/"Mathematics (Domain)"/"Biology (Domain)" —
the mismatch made otherwise-valid, already-validated questions permanently
unreachable via get_subjects()/get_topics(), with no error anywhere.

Both ingestion paths (create_prewarm_job for the AI prewarm pipeline,
admin_import_bulk for the ChatGPT/Custom GPT paste-import pipeline) must now
reject a subject value that isn't a real key in EXAM_SUBJECTS_MAP[exam_type].
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import app.services.exam_prep_service as svc
from app.routes.exam_prep import BulkImportRequest, admin_import_bulk


class TestCreatePrewarmJobSubjectValidation:
    def test_rejects_unknown_subject(self, monkeypatch):
        monkeypatch.setattr(svc, "_get_db", lambda: MagicMock())
        with pytest.raises(HTTPException) as exc:
            svc.create_prewarm_job(
                triggered_by="admin", exam_type="cuet_ug", grade="Grade 12",
                subject="Physics", chapter=None, topic=None,
                difficulty_mix=None, question_count=10, publish_mode="draft",
            )
        assert exc.value.status_code == 400
        assert "Unknown subject" in exc.value.detail
        assert "Physics (Domain)" in exc.value.detail

    def test_accepts_declared_subject(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "job-1", "subject": "Physics (Domain)"}
        ]
        monkeypatch.setattr(svc, "_get_db", lambda: mock_db)
        job = svc.create_prewarm_job(
            triggered_by="admin", exam_type="cuet_ug", grade="Grade 12",
            subject="Physics (Domain)", chapter=None, topic=None,
            difficulty_mix=None, question_count=10, publish_mode="draft",
        )
        assert job["subject"] == "Physics (Domain)"

    def test_unknown_exam_type_skips_check_and_falls_through(self, monkeypatch):
        """
        exam_type isn't validated here (that's the route layer's job) — an
        exam_type with no EXAM_SUBJECTS_MAP entry must not crash this check.
        """
        mock_db = MagicMock()
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "job-2", "subject": "Anything"}
        ]
        monkeypatch.setattr(svc, "_get_db", lambda: mock_db)
        job = svc.create_prewarm_job(
            triggered_by="admin", exam_type="not_a_real_exam", grade="Grade 12",
            subject="Anything", chapter=None, topic=None,
            difficulty_mix=None, question_count=10, publish_mode="draft",
        )
        assert job["subject"] == "Anything"


class TestAdminImportBulkSubjectValidation:
    def _question(self, **overrides):
        base = {
            "exam_type": "cuet_ug", "grade": "Grade 12", "subject": "Physics (Domain)",
            "chapter": "Kinematics", "topic": "Motion",
            "question_text": "Sample question?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_option": "A", "detailed_explanation": "Because.",
            "difficulty": "easy",
        }
        base.update(overrides)
        return base

    def test_rejects_unknown_subject(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value.data = []
        monkeypatch.setattr(svc, "_get_db", lambda: mock_db)

        result = admin_import_bulk(
            BulkImportRequest(questions=[self._question(subject="Physics")]),
            _admin={"profile": {"id": "admin-1"}},
        )

        assert result["skipped_invalid"] == 1
        assert result["imported"] == 0
        issues = result["report"][0]["issues"]
        assert any("Unknown subject" in i for i in issues)

    def test_accepts_declared_subject(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "q-1"}]
        monkeypatch.setattr(svc, "_get_db", lambda: mock_db)

        result = admin_import_bulk(
            BulkImportRequest(questions=[self._question(subject="Physics (Domain)")]),
            _admin={"profile": {"id": "admin-1"}},
        )

        assert result["imported"] == 1
        assert result["skipped_invalid"] == 0
