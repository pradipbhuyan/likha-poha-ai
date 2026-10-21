import base64
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.security.service_auth import (
    SERVICE_ASSERTION_TYPE,
    ServiceAuthError,
    sign_service_assertion,
    verify_service_assertion,
)

BODY = b'{"code":"example"}'
BODY_SHA256 = "343e8dff8e2d886e132a7d06b7e09270075b0d1a4277fc3003568b56f5956e3e"
PURPOSE = "lp-account-link-exchange"
METHOD = "POST"
PATH = "/internal/example"


def make_key_pair() -> tuple[bytes, bytes]:
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


def configure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    lp_private_key: bytes,
    school_public_keys: dict[str, bytes],
) -> None:
    monkeypatch.setenv("LP_SERVICE_AUTH_ISSUER", "likha-poha-service")
    monkeypatch.setenv("SCHOOL_OS_SERVICE_AUTH_AUDIENCE", "school-os-service")
    monkeypatch.setenv("LP_SERVICE_AUTH_SIGNING_KID", "lp-current")
    monkeypatch.setenv(
        "LP_SERVICE_AUTH_PRIVATE_KEY_B64",
        base64.b64encode(lp_private_key).decode("ascii"),
    )
    monkeypatch.setenv("SCHOOL_OS_SERVICE_AUTH_ISSUER", "school-os-service")
    monkeypatch.setenv("LP_SERVICE_AUTH_AUDIENCE", "likha-poha-service")
    monkeypatch.setenv(
        "SCHOOL_OS_SERVICE_AUTH_PEER_PUBLIC_KEYS_JSON",
        json.dumps(
            {
                kid: base64.b64encode(public_key).decode("ascii")
                for kid, public_key in school_public_keys.items()
            }
        ),
    )


def issue_school_assertion(
    private_key: bytes,
    *,
    kid: str = "school-current",
    payload_overrides: dict[str, object] | None = None,
    header_overrides: dict[str, object] | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "iss": "school-os-service",
        "aud": "likha-poha-service",
        "iat": now,
        "exp": now + 30,
        "jti": "b5f37983-962e-4c29-b39d-b1145c17b101",
        "ver": 1,
        "purpose": PURPOSE,
        "method": METHOD,
        "path": PATH,
        "body_sha256": BODY_SHA256,
        **(payload_overrides or {}),
    }
    header = {
        "alg": "RS256",
        "typ": SERVICE_ASSERTION_TYPE,
        "kid": kid,
        **(header_overrides or {}),
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers=header)


def assert_code(error: pytest.ExceptionInfo[ServiceAuthError], code: str) -> None:
    assert error.value.code == code


def test_signs_rs256_assertion_with_required_protocol_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lp_private, _ = make_key_pair()
    school_private, school_public = make_key_pair()
    configure(
        monkeypatch,
        lp_private_key=lp_private,
        school_public_keys={"school-current": school_public},
    )

    first = sign_service_assertion(
        purpose=PURPOSE, method=METHOD, path=PATH, body=BODY
    )
    second = sign_service_assertion(
        purpose=PURPOSE, method=METHOD, path=PATH, body=BODY
    )
    header = jwt.get_unverified_header(first)
    payload = jwt.decode(first, options={"verify_signature": False})

    assert header == {"alg": "RS256", "typ": SERVICE_ASSERTION_TYPE, "kid": "lp-current"}
    assert payload["iss"] == "likha-poha-service"
    assert payload["aud"] == "school-os-service"
    assert payload["ver"] == 1
    assert payload["purpose"] == PURPOSE
    assert payload["method"] == METHOD
    assert payload["path"] == PATH
    assert payload["body_sha256"] == BODY_SHA256
    assert payload["exp"] > payload["iat"]
    assert payload["exp"] - payload["iat"] <= 60
    assert payload["jti"] != jwt.decode(second, options={"verify_signature": False})["jti"]


def test_verifies_current_and_previous_school_os_rotation_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lp_private, _ = make_key_pair()
    current_private, current_public = make_key_pair()
    previous_private, previous_public = make_key_pair()
    configure(
        monkeypatch,
        lp_private_key=lp_private,
        school_public_keys={
            "school-current": current_public,
            "school-previous": previous_public,
        },
    )

    verified = verify_service_assertion(
        assertion=issue_school_assertion(current_private),
        expected_purpose=PURPOSE,
        expected_method=METHOD,
        expected_path=PATH,
        body=BODY,
    )
    previous = verify_service_assertion(
        assertion=issue_school_assertion(previous_private, kid="school-previous"),
        expected_purpose=PURPOSE,
        expected_method=METHOD,
        expected_path=PATH,
        body=BODY,
    )

    assert verified.key_id == "school-current"
    assert previous.key_id == "school-previous"


@pytest.mark.parametrize(
    ("assertion", "code"),
    [
        (None, "SERVICE_AUTH_MISSING"),
        ("not-a-jwt", "SERVICE_AUTH_MALFORMED"),
    ],
)
def test_rejects_missing_and_malformed_assertions(
    monkeypatch: pytest.MonkeyPatch, assertion: str | None, code: str
) -> None:
    lp_private, _ = make_key_pair()
    _, school_public = make_key_pair()
    configure(
        monkeypatch,
        lp_private_key=lp_private,
        school_public_keys={"school-current": school_public},
    )

    with pytest.raises(ServiceAuthError) as error:
        verify_service_assertion(
            assertion=assertion,
            expected_purpose=PURPOSE,
            expected_method=METHOD,
            expected_path=PATH,
            body=BODY,
        )
    assert_code(error, code)


def test_rejects_header_key_signature_claim_time_and_request_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lp_private, _ = make_key_pair()
    school_private, school_public = make_key_pair()
    attacker_private, _ = make_key_pair()
    configure(
        monkeypatch,
        lp_private_key=lp_private,
        school_public_keys={"school-current": school_public},
    )

    def verify(assertion: str, **overrides: object) -> None:
        verify_service_assertion(
            assertion=assertion,
            expected_purpose=overrides.get("purpose", PURPOSE),
            expected_method=overrides.get("method", METHOD),
            expected_path=overrides.get("path", PATH),
            body=overrides.get("body", BODY),
        )

    cases = [
        (
            issue_school_assertion(attacker_private, kid="unknown"),
            "SERVICE_AUTH_UNKNOWN_KID",
        ),
        (
            issue_school_assertion(
                attacker_private,
                header_overrides={"jku": "https://attacker.example/jwks.json"},
            ),
            "SERVICE_AUTH_MALFORMED",
        ),
        (
            issue_school_assertion(
                attacker_private, header_overrides={"typ": "JWT"}
            ),
            "SERVICE_AUTH_TYPE_REJECTED",
        ),
        (
            issue_school_assertion(attacker_private),
            "SERVICE_AUTH_SIGNATURE_INVALID",
        ),
        (
            issue_school_assertion(school_private, payload_overrides={"iss": "wrong"}),
            "SERVICE_AUTH_ISSUER_MISMATCH",
        ),
        (
            issue_school_assertion(school_private, payload_overrides={"aud": "wrong"}),
            "SERVICE_AUTH_AUDIENCE_MISMATCH",
        ),
        (
            issue_school_assertion(school_private, payload_overrides={"ver": 2}),
            "SERVICE_AUTH_UNSUPPORTED_VERSION",
        ),
        (
            issue_school_assertion(
                school_private, payload_overrides={"purpose": "lp-sso-exchange"}
            ),
            "SERVICE_AUTH_PURPOSE_MISMATCH",
        ),
    ]
    for assertion, expected_code in cases:
        with pytest.raises(ServiceAuthError) as error:
            verify(assertion)
        assert_code(error, expected_code)

    valid = issue_school_assertion(school_private)
    with pytest.raises(ServiceAuthError) as error:
        verify(valid, body=b'{"code":"changed"}')
    assert_code(error, "SERVICE_AUTH_BODY_MISMATCH")
    with pytest.raises(ServiceAuthError) as error:
        verify(valid, method="GET")
    assert_code(error, "SERVICE_AUTH_METHOD_MISMATCH")
    with pytest.raises(ServiceAuthError) as error:
        verify(valid, path="/internal/other")
    assert_code(error, "SERVICE_AUTH_PATH_MISMATCH")

    now = int(time.time())
    with pytest.raises(ServiceAuthError) as error:
        verify(
            issue_school_assertion(
                school_private, payload_overrides={"iat": now, "exp": now + 61}
            )
        )
    assert_code(error, "SERVICE_AUTH_TIME_INVALID")


def test_rejects_hs256_and_absent_or_malformed_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ServiceAuthError) as error:
        sign_service_assertion(purpose=PURPOSE, method=METHOD, path=PATH, body=BODY)
    assert_code(error, "SERVICE_AUTH_NOT_CONFIGURED")

    lp_private, _ = make_key_pair()
    _, school_public = make_key_pair()
    configure(
        monkeypatch,
        lp_private_key=lp_private,
        school_public_keys={"school-current": school_public},
    )
    now = datetime.now(UTC)
    hs_assertion = jwt.encode(
        {
            "iss": "school-os-service",
            "aud": "likha-poha-service",
            "iat": now,
            "exp": now + timedelta(seconds=30),
            "jti": "b5f37983-962e-4c29-b39d-b1145c17b102",
            "ver": 1,
            "purpose": PURPOSE,
            "method": METHOD,
            "path": PATH,
            "body_sha256": BODY_SHA256,
        },
        "test-only-hmac-key-with-at-least-thirty-two-bytes",
        algorithm="HS256",
        headers={"typ": SERVICE_ASSERTION_TYPE, "kid": "school-current"},
    )
    with pytest.raises(ServiceAuthError) as error:
        verify_service_assertion(
            assertion=hs_assertion,
            expected_purpose=PURPOSE,
            expected_method=METHOD,
            expected_path=PATH,
            body=BODY,
        )
    assert_code(error, "SERVICE_AUTH_ALGORITHM_REJECTED")

    monkeypatch.setenv("LP_SERVICE_AUTH_PRIVATE_KEY_B64", "not-base64!")
    with pytest.raises(ServiceAuthError) as error:
        sign_service_assertion(purpose=PURPOSE, method=METHOD, path=PATH, body=BODY)
    assert_code(error, "SERVICE_AUTH_MALFORMED")

    monkeypatch.setenv("SCHOOL_OS_SERVICE_AUTH_PEER_PUBLIC_KEYS_JSON", "[]")
    with pytest.raises(ServiceAuthError) as error:
        verify_service_assertion(
            assertion=issue_school_assertion(make_key_pair()[0]),
            expected_purpose=PURPOSE,
            expected_method=METHOD,
            expected_path=PATH,
            body=BODY,
        )
    assert_code(error, "SERVICE_AUTH_MALFORMED")


def test_shared_non_secret_body_hash_protocol_vector() -> None:
    assert hashlib.sha256(BODY).hexdigest() == BODY_SHA256
