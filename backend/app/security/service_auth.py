"""M11 Phase 2A bilateral service assertion protocol.

This module authenticates configured peer backends only. It intentionally does
not authenticate an LP user, a School OS user, an organization, a role, or an
entitlement, and it exposes no HTTP endpoint in this phase.

The protocol uses PyJWT with cryptography-backed RS256 keys. Each service owns
one private signing key; peer public keys are configured as a rotation-capable
``kid`` to base64-encoded PEM map. Assertions bind a future server request's
exact uppercase method, pathname, and exact body bytes. ``jti`` is not
persisted in Phase 2A: future one-time link/SSO artifacts must provide atomic
replay protection and this assertion must not be generalized to standalone
non-idempotent APIs without a replay-model review.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Final, Mapping

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

SERVICE_ASSERTION_ALGORITHM: Final = "RS256"
SERVICE_ASSERTION_TYPE: Final = "lp-service+jwt"
SERVICE_ASSERTION_HEADER: Final = "X-LP-Service-Assertion"
SERVICE_ASSERTION_VERSION: Final = 1
SERVICE_ASSERTION_TTL_SECONDS: Final = 30
SERVICE_ASSERTION_MAX_TTL_SECONDS: Final = 60
SERVICE_ASSERTION_CLOCK_SKEW_SECONDS: Final = 5
SERVICE_ASSERTION_PURPOSES: Final = frozenset(
    {"lp-account-link-exchange", "lp-sso-exchange"}
)

ServiceAssertionPurpose = str


@dataclass(frozen=True)
class ServiceAuthError(Exception):
    """Safe typed internal service-auth failure."""

    code: str

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True)
class VerifiedServiceAssertion:
    issuer: str
    audience: str
    key_id: str
    issued_at: int
    expires_at: int
    jti: str


def _required(value: str | None) -> str:
    if value is None or not value.strip():
        raise ServiceAuthError("SERVICE_AUTH_NOT_CONFIGURED")
    return value.strip()


def _decode_pem(encoded: str) -> bytes:
    try:
        pem = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as error:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED") from error
    if b"-----BEGIN " not in pem or b"-----END " not in pem:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return pem


def _load_private_key(encoded: str) -> RSAPrivateKey:
    try:
        key = serialization.load_pem_private_key(_decode_pem(encoded), password=None)
    except (TypeError, ValueError) as error:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED") from error
    if not isinstance(key, RSAPrivateKey):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return key


def _load_public_key(encoded: str) -> RSAPublicKey:
    try:
        key = serialization.load_pem_public_key(_decode_pem(encoded))
    except (TypeError, ValueError) as error:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED") from error
    if not isinstance(key, RSAPublicKey):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return key


def _load_public_key_ring(encoded: str) -> dict[str, RSAPublicKey]:
    try:
        parsed = json.loads(encoded)
    except json.JSONDecodeError as error:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED") from error
    if not isinstance(parsed, dict) or not parsed:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")

    keys: dict[str, RSAPublicKey] = {}
    for kid, key_material in parsed.items():
        if not isinstance(kid, str) or not kid.strip() or not isinstance(key_material, str):
            raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
        keys[kid] = _load_public_key(key_material)
    return keys


def _assert_request_input(
    purpose: ServiceAssertionPurpose, method: str, path: str, body: bytes
) -> None:
    if (
        purpose not in SERVICE_ASSERTION_PURPOSES
        or not method
        or method != method.upper()
        or not path.startswith("/")
        or "?" in path
        or "#" in path
        or not isinstance(body, bytes)
    ):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")


def _body_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _signing_configuration() -> tuple[str, str, str, RSAPrivateKey]:
    return (
        _required(os.getenv("LP_SERVICE_AUTH_ISSUER")),
        _required(os.getenv("SCHOOL_OS_SERVICE_AUTH_AUDIENCE")),
        _required(os.getenv("LP_SERVICE_AUTH_SIGNING_KID")),
        _load_private_key(_required(os.getenv("LP_SERVICE_AUTH_PRIVATE_KEY_B64"))),
    )


def _verification_configuration() -> tuple[str, str, dict[str, RSAPublicKey]]:
    return (
        _required(os.getenv("SCHOOL_OS_SERVICE_AUTH_ISSUER")),
        _required(os.getenv("LP_SERVICE_AUTH_AUDIENCE")),
        _load_public_key_ring(
            _required(os.getenv("SCHOOL_OS_SERVICE_AUTH_PEER_PUBLIC_KEYS_JSON"))
        ),
    )


def sign_service_assertion(
    *,
    purpose: ServiceAssertionPurpose,
    method: str,
    path: str,
    body: bytes,
) -> str:
    """Create one short-lived LP-to-School-OS assertion for exact request bytes."""

    _assert_request_input(purpose, method, path, body)
    issuer, audience, kid, private_key = _signing_configuration()
    issued_at = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "iat": issued_at,
        "exp": issued_at + SERVICE_ASSERTION_TTL_SECONDS,
        "jti": str(uuid.uuid4()),
        "ver": SERVICE_ASSERTION_VERSION,
        "purpose": purpose,
        "method": method,
        "path": path,
        "body_sha256": _body_sha256(body),
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm=SERVICE_ASSERTION_ALGORITHM,
        headers={
            "alg": SERVICE_ASSERTION_ALGORITHM,
            "typ": SERVICE_ASSERTION_TYPE,
            "kid": kid,
        },
    )


def _validated_header(assertion: str) -> Mapping[str, object]:
    try:
        header = jwt.get_unverified_header(assertion)
    except jwt.PyJWTError as error:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED") from error

    if header.get("alg") != SERVICE_ASSERTION_ALGORITHM:
        raise ServiceAuthError("SERVICE_AUTH_ALGORITHM_REJECTED")
    if header.get("typ") != SERVICE_ASSERTION_TYPE:
        raise ServiceAuthError("SERVICE_AUTH_TYPE_REJECTED")
    if not isinstance(header.get("kid"), str) or not header["kid"]:
        raise ServiceAuthError("SERVICE_AUTH_MISSING")
    if any(name in header for name in ("jku", "x5u", "jwk")):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return header


def _decode_verified(
    assertion: str,
    public_key: RSAPublicKey,
    issuer: str,
    audience: str,
) -> dict[str, object]:
    try:
        payload = jwt.decode(
            assertion,
            public_key,
            algorithms=[SERVICE_ASSERTION_ALGORITHM],
            issuer=issuer,
            audience=audience,
            leeway=SERVICE_ASSERTION_CLOCK_SKEW_SECONDS,
            options={
                "require": [
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "jti",
                    "ver",
                    "purpose",
                    "method",
                    "path",
                    "body_sha256",
                ]
            },
        )
    except jwt.ExpiredSignatureError as error:
        raise ServiceAuthError("SERVICE_AUTH_EXPIRED") from error
    except jwt.InvalidIssuerError as error:
        raise ServiceAuthError("SERVICE_AUTH_ISSUER_MISMATCH") from error
    except jwt.InvalidAudienceError as error:
        raise ServiceAuthError("SERVICE_AUTH_AUDIENCE_MISMATCH") from error
    except (jwt.InvalidIssuedAtError, jwt.ImmatureSignatureError) as error:
        raise ServiceAuthError("SERVICE_AUTH_TIME_INVALID") from error
    except jwt.PyJWTError as error:
        raise ServiceAuthError("SERVICE_AUTH_SIGNATURE_INVALID") from error

    if not isinstance(payload, dict):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return payload


def _claim_string(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return value


def _claim_int(payload: Mapping[str, object], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ServiceAuthError("SERVICE_AUTH_MALFORMED")
    return value


def verify_service_assertion(
    *,
    assertion: str | None,
    expected_purpose: ServiceAssertionPurpose,
    expected_method: str,
    expected_path: str,
    body: bytes,
) -> VerifiedServiceAssertion:
    """Verify a School-OS assertion and exact request binding against local config."""

    _assert_request_input(expected_purpose, expected_method, expected_path, body)
    if not assertion:
        raise ServiceAuthError("SERVICE_AUTH_MISSING")

    expected_issuer, expected_audience, key_ring = _verification_configuration()
    header = _validated_header(assertion)
    kid = header["kid"]
    assert isinstance(kid, str)
    public_key = key_ring.get(kid)
    if public_key is None:
        raise ServiceAuthError("SERVICE_AUTH_UNKNOWN_KID")

    payload = _decode_verified(assertion, public_key, expected_issuer, expected_audience)
    issuer = _claim_string(payload, "iss")
    audience = _claim_string(payload, "aud")
    issued_at = _claim_int(payload, "iat")
    expires_at = _claim_int(payload, "exp")
    jti = _claim_string(payload, "jti")
    version = _claim_int(payload, "ver")
    purpose = _claim_string(payload, "purpose")
    method = _claim_string(payload, "method")
    path = _claim_string(payload, "path")
    claimed_digest = _claim_string(payload, "body_sha256")

    if version != SERVICE_ASSERTION_VERSION:
        raise ServiceAuthError("SERVICE_AUTH_UNSUPPORTED_VERSION")
    if purpose not in SERVICE_ASSERTION_PURPOSES or purpose != expected_purpose:
        raise ServiceAuthError("SERVICE_AUTH_PURPOSE_MISMATCH")
    if method != method.upper() or method != expected_method:
        raise ServiceAuthError("SERVICE_AUTH_METHOD_MISMATCH")
    if (
        not path.startswith("/")
        or "?" in path
        or "#" in path
        or path != expected_path
    ):
        raise ServiceAuthError("SERVICE_AUTH_PATH_MISMATCH")
    if len(claimed_digest) != 64 or any(
        character not in "0123456789abcdef" for character in claimed_digest
    ):
        raise ServiceAuthError("SERVICE_AUTH_BODY_MISMATCH")

    now = int(time.time())
    if (
        issued_at > now + SERVICE_ASSERTION_CLOCK_SKEW_SECONDS
        or expires_at <= issued_at
        or expires_at - issued_at > SERVICE_ASSERTION_MAX_TTL_SECONDS
    ):
        raise ServiceAuthError("SERVICE_AUTH_TIME_INVALID")
    if not hmac.compare_digest(claimed_digest, _body_sha256(body)):
        raise ServiceAuthError("SERVICE_AUTH_BODY_MISMATCH")

    return VerifiedServiceAssertion(
        issuer=issuer,
        audience=audience,
        key_id=kid,
        issued_at=issued_at,
        expires_at=expires_at,
        jti=jti,
    )
