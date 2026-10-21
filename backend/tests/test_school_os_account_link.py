"""Focused M11 Phase 2B account-link ownership-proof tests."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import school_os_account_link as account_link
from app.services.auth_service import get_current_user


def opaque_value() -> str:
    return base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).rstrip(b"=").decode("ascii")


def key_pair() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeInsert:
    def __init__(self, database):
        self.database = database

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        if any(item["state_verifier"] == self.row["state_verifier"] for item in self.database.rows):
            raise RuntimeError("duplicate key value violates unique constraint 23505")
        stored = {"id": str(uuid.uuid4()), **self.row, "created_at": datetime.now(UTC).isoformat()}
        self.database.rows.append(stored)
        return FakeResponse([stored])


class FakeRpc:
    def __init__(self, database, arguments):
        self.database = database
        self.arguments = arguments

    def execute(self):
        self.database.rpc_calls.append(self.arguments)
        now = datetime.now(UTC)
        for row in self.database.rows:
            if (
                row["completion_verifier"] == self.arguments["p_completion_verifier"]
                and row["state_verifier"] == self.arguments["p_state_verifier"]
                and row["status"] == "ISSUED"
                and datetime.fromisoformat(row["expires_at"]) > now
            ):
                row["status"] = "CONSUMED"
                row["consumed_at"] = now.isoformat()
                return FakeResponse([{"lp_user_id": row["lp_user_id"]}])
        return FakeResponse([])


class FakeAdminClient:
    def __init__(self):
        self.rows: list[dict] = []
        self.rpc_calls: list[dict] = []

    def table(self, table_name):
        assert table_name == "school_os_account_link_completion_artifacts"
        return FakeInsert(self)

    def rpc(self, function_name, arguments):
        assert function_name == "consume_school_os_account_link_completion_artifact"
        return FakeRpc(self, arguments)


@pytest.fixture
def fake_db(monkeypatch):
    database = FakeAdminClient()
    monkeypatch.setattr(account_link, "admin_client", database)
    monkeypatch.setattr(account_link, "write_audit_event", lambda **_: None)
    return database


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(account_link.proof_router, prefix="/api/account-link")
    app.include_router(account_link.internal_router, prefix="/api/internal")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="0f0d79d9-c65f-44a2-8a78-6f316ddb1bad")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def school_signer(monkeypatch):
    private_pem, public_pem = key_pair()
    monkeypatch.setenv("SCHOOL_OS_SERVICE_AUTH_ISSUER", "school-os-service")
    monkeypatch.setenv("LP_SERVICE_AUTH_AUDIENCE", "likha-poha-service")
    monkeypatch.setenv(
        "SCHOOL_OS_SERVICE_AUTH_PEER_PUBLIC_KEYS_JSON",
        json.dumps(
            {
                "school-current": base64.b64encode(public_pem).decode("ascii"),
            }
        ),
    )

    def sign(*, body: bytes, **overrides) -> str:
        now = int(time.time())
        payload = {
            "iss": "school-os-service",
            "aud": "likha-poha-service",
            "iat": now,
            "exp": now + 30,
            "jti": str(uuid.uuid4()),
            "ver": 1,
            "purpose": account_link.ACCOUNT_LINK_EXCHANGE_PURPOSE,
            "method": "POST",
            "path": account_link.EXCHANGE_PATH,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            **overrides,
        }
        return jwt.encode(
            payload,
            private_pem,
            algorithm="RS256",
            headers={"typ": "lp-service+jwt", "kid": "school-current"},
        )

    return sign


def issue(client: TestClient, state: str | None = None):
    return client.post(
        account_link.PROOF_PATH,
        json={"state": opaque_value() if state is None else state},
    )


def exchange(client: TestClient, signer, code: str, state: str, *, raw_body: bytes | None = None, **overrides):
    body = raw_body or json.dumps({"code": code, "state": state}, separators=(",", ":")).encode()
    assertion = signer(body=body, **overrides)
    return client.post(
        account_link.EXCHANGE_PATH,
        content=body,
        headers={account_link.SERVICE_ASSERTION_HEADER: assertion, "content-type": "application/json"},
    )


def test_authenticated_proof_uses_only_verified_principal_and_returns_only_code(client, fake_db):
    state = opaque_value()
    response = issue(client, state)

    assert response.status_code == 200
    assert set(response.json()) == {"code"}
    code = response.json()["code"]
    assert account_link._is_strict_opaque_value(code)

    assert len(fake_db.rows) == 1
    row = fake_db.rows[0]
    assert row["lp_user_id"] == "0f0d79d9-c65f-44a2-8a78-6f316ddb1bad"
    assert row["state_verifier"] == hashlib.sha256(state.encode("ascii")).hexdigest()
    assert row["completion_verifier"] == hashlib.sha256(code.encode("ascii")).hexdigest()
    assert state not in row.values()
    assert code not in row.values()
    assert "email" not in row and "phone" not in row
    assert datetime.fromisoformat(row["expires_at"]) - datetime.fromisoformat(row["created_at"]) <= timedelta(seconds=60)


def test_proof_rejects_unauthenticated_and_extra_identity_authority(app, fake_db):
    app.dependency_overrides.clear()
    client = TestClient(app)
    assert issue(client).status_code in {401, 403}

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="verified-user")
    state = opaque_value()
    rejected = client.post(
        account_link.PROOF_PATH,
        json={"state": state, "lp_user_id": "browser-selected-user", "email": "no@example.com", "phone": "123"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "INVALID_STATE"
    assert fake_db.rows == []


@pytest.mark.parametrize(
    "state",
    [
        "",
        "a" * 42,
        "a" * 44,
        opaque_value() + "=",
        "!" * 43,
    ],
)
def test_proof_rejects_malformed_state(client, fake_db, state):
    response = issue(client, state)
    assert response.status_code == 400
    assert response.json()["detail"] == "INVALID_STATE"
    assert fake_db.rows == []


def test_duplicate_state_is_not_replaced(client, fake_db):
    state = opaque_value()
    first = issue(client, state)
    second = issue(client, state)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "PROOF_ALREADY_ISSUED"
    assert len(fake_db.rows) == 1


def test_exchange_requires_service_auth_and_fails_closed_when_missing(client, fake_db):
    response = client.post(
        account_link.EXCHANGE_PATH,
        json={"code": opaque_value(), "state": opaque_value()},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "SERVICE_AUTH_REQUIRED"
    assert fake_db.rpc_calls == []


def test_exchange_rejects_malformed_and_invalid_signature_assertions(client, fake_db, school_signer):
    body = json.dumps({"code": opaque_value(), "state": opaque_value()}).encode()
    malformed = client.post(
        account_link.EXCHANGE_PATH,
        content=body,
        headers={account_link.SERVICE_ASSERTION_HEADER: "not-a-jwt", "content-type": "application/json"},
    )
    signed = school_signer(body=body)
    signed_prefix, signature = signed.rsplit(".", 1)
    invalid_signature_assertion = f"{signed_prefix}.{'a' if signature[0] != 'a' else 'b'}{signature[1:]}"
    invalid_signature = client.post(
        account_link.EXCHANGE_PATH,
        content=body,
        headers={
            account_link.SERVICE_ASSERTION_HEADER: invalid_signature_assertion,
            "content-type": "application/json",
        },
    )

    assert malformed.status_code == 401
    assert malformed.json()["detail"] == "SERVICE_AUTH_REQUIRED"
    assert invalid_signature.status_code == 401
    assert invalid_signature.json()["detail"] == "SERVICE_AUTH_REQUIRED"
    assert fake_db.rpc_calls == []


def test_exchange_fails_closed_when_service_auth_is_not_configured(client, fake_db, monkeypatch):
    monkeypatch.delenv("SCHOOL_OS_SERVICE_AUTH_ISSUER", raising=False)
    body = json.dumps({"code": opaque_value(), "state": opaque_value()}).encode()
    response = client.post(
        account_link.EXCHANGE_PATH,
        content=body,
        headers={account_link.SERVICE_ASSERTION_HEADER: "not-a-jwt", "content-type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "SERVICE_UNAVAILABLE"
    assert fake_db.rpc_calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "wrong"},
        {"aud": "wrong"},
        {"purpose": "lp-sso-exchange"},
        {"method": "GET"},
        {"path": "/api/internal/other"},
        {"body_sha256": "0" * 64},
    ],
)
def test_exchange_rejects_invalid_service_assertion_before_consumption(
    client, fake_db, school_signer, overrides
):
    issued = issue(client)
    state = fake_db.rows[0]["state_verifier"]
    code = issued.json()["code"]
    raw_body = json.dumps({"code": code, "state": opaque_value()}, separators=(",", ":")).encode()
    response = exchange(client, school_signer, code, opaque_value(), raw_body=raw_body, **overrides)

    assert response.status_code == 401
    assert response.json()["detail"] == "SERVICE_AUTH_REQUIRED"
    assert fake_db.rpc_calls == []


def test_exchange_consumes_once_and_returns_only_opaque_subject(client, fake_db, school_signer):
    state = opaque_value()
    issued = issue(client, state)
    code = issued.json()["code"]

    first = exchange(client, school_signer, code, state)
    second = exchange(client, school_signer, code, state)

    assert first.status_code == 200
    assert first.json() == {
        "provider": "likhapoha",
        "subject": "0f0d79d9-c65f-44a2-8a78-6f316ddb1bad",
    }
    assert second.status_code == 400
    assert second.json()["detail"] == "ACCOUNT_LINK_PROOF_INVALID"
    assert fake_db.rows[0]["status"] == "CONSUMED"
    assert "email" not in first.json()
    assert "phone" not in first.json()
    assert "token" not in first.json()
    assert "profile" not in first.json()


def test_exchange_rejects_wrong_or_mismatched_artifacts(client, fake_db, school_signer):
    first_state = opaque_value()
    second_state = opaque_value()
    first_code = issue(client, first_state).json()["code"]
    second_code = issue(client, second_state).json()["code"]

    for code, state in (
        (opaque_value(), first_state),
        (first_code, opaque_value()),
        (first_code, second_state),
        (second_code, first_state),
    ):
        response = exchange(client, school_signer, code, state)
        assert response.status_code == 400
        assert response.json()["detail"] == "ACCOUNT_LINK_PROOF_INVALID"

    assert all(row["status"] == "ISSUED" for row in fake_db.rows)


def test_exchange_rejects_expired_artifact(client, fake_db, school_signer):
    state = opaque_value()
    code = issue(client, state).json()["code"]
    fake_db.rows[0]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()

    response = exchange(client, school_signer, code, state)

    assert response.status_code == 400
    assert response.json()["detail"] == "ACCOUNT_LINK_PROOF_INVALID"
    assert fake_db.rows[0]["status"] == "ISSUED"


def test_exact_raw_body_binding_rejects_different_json_serialization(client, fake_db, school_signer):
    state = opaque_value()
    code = issue(client, state).json()["code"]
    assertion_body = f'{{"code":"{code}","state":"{state}"}}'.encode()
    different_bytes = f'{{ "state": "{state}", "code": "{code}" }}'.encode()

    assertion = school_signer(body=assertion_body)
    response = client.post(
        account_link.EXCHANGE_PATH,
        content=different_bytes,
        headers={account_link.SERVICE_ASSERTION_HEADER: assertion, "content-type": "application/json"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "SERVICE_AUTH_REQUIRED"
    assert fake_db.rows[0]["status"] == "ISSUED"
    assert fake_db.rpc_calls == []


def test_exchange_rejects_malformed_code_or_state_after_valid_service_auth(client, fake_db, school_signer):
    raw_body = b'{"code":"invalid","state":"invalid"}'
    response = exchange(
        client,
        school_signer,
        "ignored",
        "ignored",
        raw_body=raw_body,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "ACCOUNT_LINK_PROOF_INVALID"
    assert fake_db.rpc_calls == []
