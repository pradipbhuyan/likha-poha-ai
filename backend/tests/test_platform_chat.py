"""
test_platform_chat.py
═════════════════════════
Regression tests for platform chat access control.

Covers:
  - Chat is free for every role and subscription plan
  - The global admin kill-switch still gates access
  - Per-user allowlist is no longer required for access

Run with:
    cd backend && python -m pytest tests/test_platform_chat.py -v
"""
from __future__ import annotations

from app.routes.platform_chat import _user_can_chat


class TestUserCanChat:
    def test_free_student_can_chat_when_globally_enabled(self):
        profile = {"role": "student", "subscription_plan": "free"}
        assert _user_can_chat("s1", profile, {"global_enabled": True}) is True

    def test_free_parent_can_chat_when_globally_enabled(self):
        profile = {"role": "parent", "subscription_plan": "free"}
        assert _user_can_chat("p1", profile, {"global_enabled": True}) is True

    def test_paid_student_can_chat(self):
        profile = {"role": "student", "subscription_plan": "premium"}
        assert _user_can_chat("s1", profile, {"global_enabled": True}) is True

    def test_teacher_can_chat(self):
        profile = {"role": "teacher", "subscription_plan": "free"}
        assert _user_can_chat("t1", profile, {"global_enabled": True}) is True

    def test_no_access_without_explicit_grant_still_allowed(self):
        """Chat is free for all now — no admin allowlist entry required."""
        profile = {"role": "student", "subscription_plan": "free"}
        assert _user_can_chat("unlisted-user", profile, {"global_enabled": True}) is True

    def test_global_kill_switch_blocks_everyone(self):
        for role in ("student", "parent", "teacher", "admin"):
            profile = {"role": role, "subscription_plan": "free"}
            assert _user_can_chat("u1", profile, {"global_enabled": False}) is False

    def test_defaults_to_enabled_when_setting_missing(self):
        profile = {"role": "student", "subscription_plan": "free"}
        assert _user_can_chat("s1", profile, {}) is True
