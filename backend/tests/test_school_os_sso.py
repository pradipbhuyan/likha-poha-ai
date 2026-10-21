from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import school_os_sso


def test_exchange_uses_fixed_path_purpose_and_exact_compact_body(monkeypatch):
    captured = {}

    monkeypatch.setenv("SCHOOL_OS_API_BASE_URL", "https://school-api.example.test")

    def fake_sign_service_assertion(**kwargs):
        captured["signed"] = kwargs
        return "signed-assertion"

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"provider":"likhapoha","subject":"50000000-0000-4000-8000-000000000001"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["headers"] = request.headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        school_os_sso, "sign_service_assertion", fake_sign_service_assertion
    )
    monkeypatch.setattr(school_os_sso, "urlopen", fake_urlopen)

    subject = school_os_sso._exchange_school_os_code("A" * 43)

    assert subject == "50000000-0000-4000-8000-000000000001"
    assert (
        captured["url"]
        == "https://school-api.example.test/api/v1/internal/lp-sso/exchange"
    )
    assert captured["body"] == b'{"code":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}'
    assert captured["signed"] == {
        "purpose": "lp-sso-exchange",
        "method": "POST",
        "path": "/api/v1/internal/lp-sso/exchange",
        "body": captured["body"],
    }
    assert captured["timeout"] == 4


def test_exchange_rejects_malformed_school_os_response(monkeypatch):
    monkeypatch.setenv("SCHOOL_OS_API_BASE_URL", "https://school-api.example.test")
    monkeypatch.setattr(
        school_os_sso, "sign_service_assertion", lambda **_kwargs: "assertion"
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return (
                b'{"provider":"wrong","subject":"50000000-0000-4000-8000-000000000001"}'
            )

    monkeypatch.setattr(
        school_os_sso, "urlopen", lambda *_args, **_kwargs: FakeResponse()
    )

    with pytest.raises(HTTPException) as error:
        school_os_sso._exchange_school_os_code("A" * 43)

    assert error.value.status_code == 503


def test_session_mint_uses_verified_subject_then_fresh_anon_client(monkeypatch):
    calls = {}
    subject = "50000000-0000-4000-8000-000000000001"
    user = SimpleNamespace(id=subject, email="canonical@example.test")
    generated = SimpleNamespace(properties=SimpleNamespace(email_otp="recovery-otp"))
    verified_session = SimpleNamespace(access_token="access", refresh_token="refresh")
    verified = SimpleNamespace(
        user=SimpleNamespace(id=subject), session=verified_session
    )

    class FakeAdmin:
        def get_user_by_id(self, requested_subject):
            calls["subject"] = requested_subject
            return SimpleNamespace(user=user)

        def generate_link(self, payload):
            calls["generate"] = payload
            return generated

    class FakeVerifierAuth:
        def verify_otp(self, payload):
            calls["verify"] = payload
            return verified

    class FakeVerifierClient:
        auth = FakeVerifierAuth()

    monkeypatch.setattr(
        school_os_sso,
        "admin_client",
        SimpleNamespace(auth=SimpleNamespace(admin=FakeAdmin())),
    )
    monkeypatch.setattr(school_os_sso, "SUPABASE_URL", "https://lp.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    def fake_create_client(url, key, options):
        calls["client"] = (
            url,
            key,
            options.persist_session,
            options.auto_refresh_token,
        )
        return FakeVerifierClient()

    monkeypatch.setattr(school_os_sso, "create_client", fake_create_client)

    assert school_os_sso._mint_session_for_verified_subject(subject) == (
        "access",
        "refresh",
    )
    assert calls["subject"] == subject
    assert calls["generate"] == {"type": "recovery", "email": "canonical@example.test"}
    assert calls["client"] == ("https://lp.example.test", "anon-key", False, False)
    assert calls["verify"] == {
        "email": "canonical@example.test",
        "token": "recovery-otp",
        "type": "recovery",
    }


def test_session_mint_rejects_mismatched_verified_user(monkeypatch):
    subject = "50000000-0000-4000-8000-000000000001"
    user = SimpleNamespace(id=subject, email="canonical@example.test")
    generated = SimpleNamespace(properties=SimpleNamespace(email_otp="recovery-otp"))
    verified = SimpleNamespace(
        user=SimpleNamespace(id="50000000-0000-4000-8000-000000000002"),
        session=SimpleNamespace(access_token="access", refresh_token="refresh"),
    )

    class FakeAdmin:
        def get_user_by_id(self, _subject):
            return SimpleNamespace(user=user)

        def generate_link(self, _payload):
            return generated

    monkeypatch.setattr(
        school_os_sso,
        "admin_client",
        SimpleNamespace(auth=SimpleNamespace(admin=FakeAdmin())),
    )
    monkeypatch.setattr(school_os_sso, "SUPABASE_URL", "https://lp.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setattr(
        school_os_sso,
        "create_client",
        lambda *_args, **_kwargs: SimpleNamespace(
            auth=SimpleNamespace(verify_otp=lambda _payload: verified)
        ),
    )

    with pytest.raises(HTTPException) as error:
        school_os_sso._mint_session_for_verified_subject(subject)

    assert error.value.status_code == 409
