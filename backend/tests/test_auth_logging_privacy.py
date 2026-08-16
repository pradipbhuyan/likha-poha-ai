"""
test_auth_logging_privacy.py
═════════════════════════════
Regression tests for the go-live audit's PII-in-logs finding.

get_current_user is the dependency behind every protected route. It used to
run print("AUTH USER ID:", ...) and print("AUTH USER EMAIL:", ...) on each
successful validation, and require_admin printed the entire profile row —
so children's ids and email addresses accumulated in Render's log retention
on every single request, outside the platform's consent and deletion story.

The success path now logs nothing at all, and the failure paths route through
_safe_auth_error(), which redacts bearer tokens and email addresses.

NOTE ON CAPTURE: logger_service sets propagate = False on the "likhapoha"
logger, so pytest's caplog fixture never sees these records — assertions built
on caplog would pass vacuously. The capture_auth_logs fixture below attaches a
handler to that logger directly, which is the only way to actually observe
what this module emits.

Run with:
    cd backend && python -m pytest tests/test_auth_logging_privacy.py -v
"""

import inspect
import logging

import pytest

from app.services import auth_service
from app.services.auth_service import _safe_auth_error


SAMPLE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    ".dQw4w9WgXcQ-signature_part"
)


class _Capture(logging.Handler):
    """Collects LogRecords emitted by the likhapoha logger tree."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)

    @property
    def text(self) -> str:
        return " ".join(r.getMessage() for r in self.records)

    def field(self, name):
        return [getattr(r, name, None) for r in self.records]


@pytest.fixture
def capture_auth_logs():
    """Attach a capturing handler to the non-propagating likhapoha logger."""
    logger = logging.getLogger("likhapoha")
    handler = _Capture()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def _fake_client(*, user=None, raises=None):
    """Build a stand-in for the Supabase admin client used by get_current_user."""
    class _Auth:
        @staticmethod
        def get_user(_token):
            if raises is not None:
                raise raises
            return type("_Response", (), {"user": user})()

    return type("_Client", (), {"auth": _Auth()})()


class _Credentials:
    def __init__(self, token="any-token"):
        self.credentials = token


def _user(uid, email):
    return type("_User", (), {"id": uid, "email": email})()


# ─────────────────────────────────────────────────────────────────────────────
# The capture fixture itself must work — otherwise every silence assertion
# below would pass for the wrong reason.
# ─────────────────────────────────────────────────────────────────────────────

def test_capture_fixture_actually_captures(capture_auth_logs):
    auth_service._log.warning("auth.selftest", role="probe")
    assert capture_auth_logs.records, (
        "Fixture is not capturing — silence assertions in this file would be vacuous"
    )
    assert "probe" in capture_auth_logs.field("role")


# ─────────────────────────────────────────────────────────────────────────────
# No print() anywhere in the module
# ─────────────────────────────────────────────────────────────────────────────

class TestNoPrintStatements:
    """print() writes straight to stdout, bypassing the structured logger."""

    def test_module_has_no_print_calls(self):
        src = inspect.getsource(auth_service)
        offenders = [
            line.strip()
            for line in src.splitlines()
            if line.strip().startswith("print(")
        ]
        assert not offenders, (
            f"auth_service.py must not use print() — found: {offenders}. "
            f"Use the structured logger (_log) so output is levelled and filterable."
        )

    @pytest.mark.parametrize("fn_name", ["get_current_user", "require_admin"])
    def test_guard_does_not_print(self, fn_name):
        src = inspect.getsource(getattr(auth_service, fn_name))
        assert "print(" not in src, f"{fn_name} must not print()"


# ─────────────────────────────────────────────────────────────────────────────
# Success path is silent
# ─────────────────────────────────────────────────────────────────────────────

class TestSuccessPathIsSilent:
    """A valid token must produce no log output — this runs on every request."""

    def test_valid_token_logs_nothing(self, monkeypatch, capture_auth_logs):
        user = _user("11111111-1111-1111-1111-111111111111", "child@example.com")
        monkeypatch.setattr(auth_service, "admin_client", _fake_client(user=user))

        returned = auth_service.get_current_user(_Credentials())

        assert returned.id == user.id
        assert capture_auth_logs.records == [], (
            f"Success path must log nothing; got {capture_auth_logs.text!r}"
        )

    def test_no_identity_appears_in_log_output(self, monkeypatch, capture_auth_logs):
        user = _user("22222222-2222-2222-2222-222222222222", "student.name@school.example.in")
        monkeypatch.setattr(auth_service, "admin_client", _fake_client(user=user))

        auth_service.get_current_user(_Credentials())

        assert user.email not in capture_auth_logs.text
        assert user.id not in capture_auth_logs.text


# ─────────────────────────────────────────────────────────────────────────────
# Failure paths redact credentials and personal data
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorRedaction:

    def test_jwt_is_redacted(self):
        out = _safe_auth_error(Exception(f"invalid JWT: {SAMPLE_JWT}"))
        assert SAMPLE_JWT not in out
        assert "<redacted-token>" in out

    def test_email_is_redacted(self):
        out = _safe_auth_error(Exception("no user found for child@example.com"))
        assert "child@example.com" not in out
        assert "<redacted-email>" in out

    def test_both_redacted_together(self):
        out = _safe_auth_error(
            Exception(f"token {SAMPLE_JWT} rejected for kid@school.example.in")
        )
        assert SAMPLE_JWT not in out
        assert "kid@school.example.in" not in out

    def test_ordinary_message_survives_intact(self):
        msg = "bad_jwt: unable to parse or verify signature"
        assert _safe_auth_error(Exception(msg)) == msg

    def test_message_is_length_capped(self):
        assert len(_safe_auth_error(Exception("x" * 5000))) == 200

    def test_handles_none(self):
        """retries_exhausted passes last_exc, which can be None."""
        assert _safe_auth_error(None) == "None"

    def test_rejected_token_never_reaches_the_log(self, monkeypatch, capture_auth_logs):
        monkeypatch.setattr(
            auth_service, "admin_client",
            _fake_client(raises=Exception(f"invalid claim: {SAMPLE_JWT}")),
        )

        with pytest.raises(Exception) as exc_info:
            auth_service.get_current_user(_Credentials(token=SAMPLE_JWT))

        assert getattr(exc_info.value, "status_code", None) == 401
        assert capture_auth_logs.records, "A rejected token should be logged"
        assert SAMPLE_JWT not in capture_auth_logs.text
        assert "<redacted-token>" in " ".join(
            str(f) for f in capture_auth_logs.field("error")
        )


# ─────────────────────────────────────────────────────────────────────────────
# require_admin logs the role only, never the profile row
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminDenialLogging:

    def test_denied_admin_logs_role_not_profile(self, monkeypatch, capture_auth_logs):
        profile = {
            "id": "33333333-3333-3333-3333-333333333333",
            "email": "parent@example.com",
            "username": "a_parent",
            "role": "parent",
        }
        monkeypatch.setattr(auth_service, "get_user_profile", lambda _uid: profile)

        with pytest.raises(Exception) as exc_info:
            auth_service.require_admin(user=_user(profile["id"], profile["email"]))

        assert getattr(exc_info.value, "status_code", None) == 403

        assert profile["email"] not in capture_auth_logs.text
        assert profile["username"] not in capture_auth_logs.text
        assert profile["email"] not in str(capture_auth_logs.field("role"))

        # The role is the one field worth keeping — it says who was turned away.
        assert "parent" in capture_auth_logs.field("role")

    def test_granted_admin_logs_nothing(self, monkeypatch, capture_auth_logs):
        profile = {
            "id": "44444444-4444-4444-4444-444444444444",
            "email": "admin@example.com",
            "role": "admin",
        }
        monkeypatch.setattr(auth_service, "get_user_profile", lambda _uid: profile)

        result = auth_service.require_admin(user=_user(profile["id"], profile["email"]))

        assert result["profile"]["role"] == "admin"
        assert capture_auth_logs.records == [], (
            "A successful admin check must log nothing — it runs on every admin request"
        )
