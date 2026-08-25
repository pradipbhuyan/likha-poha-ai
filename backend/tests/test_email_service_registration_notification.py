"""
test_email_service_registration_notification.py
─────────────────────────────────────────────────────────────────────────────
Covers the admin notification email sent whenever a new student or parent
registers, mirroring the existing teacher-signup notification pattern.

The team wanted visibility into every student/parent signup as it happens —
before this, only teacher signups (which need manual approval) triggered an
admin-inbox email. Student/parent signups are self-serve and instant, so
this notification is purely informational (never blocks or delays signup).

Run with:
    cd backend && python -m pytest tests/test_email_service_registration_notification.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock

import app.services.email_service as email_service


class TestSendNewRegistrationAdminNotification:

    def test_sends_to_admin_inbox_with_student_details(self, monkeypatch):
        captured = {}

        def fake_send_async(to, subject, html, text):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html
            captured["text"] = text

        monkeypatch.setattr(email_service, "_send_async", fake_send_async)

        email_service.send_new_registration_admin_notification(
            name="Ananya Sharma",
            email="ananya.sharma@example.com",
            role="student",
            grade="Grade 9",
        )

        assert captured["to"] == email_service._ADMIN_NOTIFICATION_EMAIL
        assert "student" in captured["subject"].lower()
        assert "Ananya" in captured["subject"]
        assert "Grade 9" in captured["subject"]

        # Body must include name, email, role, and grade — the exact fields
        # the team asked for.
        assert "Ananya Sharma" in captured["html"]
        assert "ananya.sharma@example.com" in captured["html"]
        assert "Student" in captured["html"]
        assert "Grade 9" in captured["html"]
        assert "Ananya Sharma" in captured["text"]
        assert "ananya.sharma@example.com" in captured["text"]
        assert "Grade 9" in captured["text"]

    def test_sends_to_admin_inbox_with_parent_details_no_grade(self, monkeypatch):
        captured = {}

        def fake_send_async(to, subject, html, text):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html
            captured["text"] = text

        monkeypatch.setattr(email_service, "_send_async", fake_send_async)

        email_service.send_new_registration_admin_notification(
            name="Rajesh Kumar",
            email="rajesh.kumar@example.com",
            role="parent",
        )

        assert captured["to"] == email_service._ADMIN_NOTIFICATION_EMAIL
        assert "parent" in captured["subject"].lower()
        assert "Rajesh" in captured["subject"]
        assert "Rajesh Kumar" in captured["html"]
        assert "rajesh.kumar@example.com" in captured["html"]
        assert "Parent" in captured["html"]
        # No grade table-row for a parent (the footer's "Grades 5-12" brand
        # text is unrelated and legitimately present in every email).
        assert ">Grade</td>" not in captured["html"]

    def test_teacher_role_is_ignored(self, monkeypatch):
        """
        Teacher signups already trigger send_teacher_signup_admin_notification()
        with its own approval-workflow messaging — this function must not
        double-send for role='teacher'.
        """
        called = MagicMock()
        monkeypatch.setattr(email_service, "_send_async", called)

        email_service.send_new_registration_admin_notification(
            name="A Teacher", email="teacher@example.com", role="teacher",
        )

        called.assert_not_called()

    def test_unknown_role_is_ignored(self, monkeypatch):
        called = MagicMock()
        monkeypatch.setattr(email_service, "_send_async", called)

        email_service.send_new_registration_admin_notification(
            name="Someone", email="someone@example.com", role="admin",
        )

        called.assert_not_called()

    def test_noop_when_admin_notification_email_not_configured(self, monkeypatch):
        called = MagicMock()
        monkeypatch.setattr(email_service, "_send_async", called)
        monkeypatch.setattr(email_service, "_ADMIN_NOTIFICATION_EMAIL", "")

        email_service.send_new_registration_admin_notification(
            name="Ananya Sharma", email="ananya@example.com", role="student", grade="Grade 9",
        )

        called.assert_not_called()


class TestWelcomeEmailTriggersRegistrationNotification:
    """
    send_welcome_email() is the single call site used by every student/parent
    signup path (Free Tier, paid, offer-code, Google OAuth) — wiring the
    notification in there, exactly like the existing teacher pattern, covers
    every registration path with one hook.
    """

    def test_student_welcome_email_triggers_notification(self, monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(email_service, "send_new_registration_admin_notification", notify_mock)
        monkeypatch.setattr(email_service, "_send_async", MagicMock())

        email_service.send_welcome_email(
            to="student@example.com",
            name="Ananya Sharma",
            role="student",
            grade="Grade 9",
        )

        notify_mock.assert_called_once_with(
            name="Ananya Sharma", email="student@example.com", role="student", grade="Grade 9",
        )

    def test_parent_welcome_email_triggers_notification(self, monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(email_service, "send_new_registration_admin_notification", notify_mock)
        monkeypatch.setattr(email_service, "_send_async", MagicMock())

        email_service.send_welcome_email(
            to="parent@example.com",
            name="Rajesh Kumar",
            role="parent",
        )

        notify_mock.assert_called_once_with(
            name="Rajesh Kumar", email="parent@example.com", role="parent", grade="",
        )

    def test_teacher_welcome_email_does_not_trigger_registration_notification(self, monkeypatch):
        """Teachers keep using send_teacher_signup_admin_notification() instead."""
        registration_notify_mock = MagicMock()
        teacher_notify_mock = MagicMock()
        monkeypatch.setattr(email_service, "send_new_registration_admin_notification", registration_notify_mock)
        monkeypatch.setattr(email_service, "send_teacher_signup_admin_notification", teacher_notify_mock)
        monkeypatch.setattr(email_service, "_send_async", MagicMock())

        email_service.send_welcome_email(
            to="teacher@example.com",
            name="A Teacher",
            role="teacher",
            school="Delhi Public School",
        )

        registration_notify_mock.assert_not_called()
        teacher_notify_mock.assert_called_once()

    def test_notification_failure_never_blocks_welcome_email(self, monkeypatch):
        """A crash in the admin notification must never prevent the user's own welcome email."""
        def boom(*args, **kwargs):
            raise RuntimeError("SMTP exploded")

        monkeypatch.setattr(email_service, "send_new_registration_admin_notification", boom)
        send_async_mock = MagicMock()
        monkeypatch.setattr(email_service, "_send_async", send_async_mock)

        # Must not raise.
        email_service.send_welcome_email(
            to="student@example.com", name="Ananya", role="student", grade="Grade 9",
        )

        # The user's own welcome email must still have been queued.
        send_async_mock.assert_called_once()
