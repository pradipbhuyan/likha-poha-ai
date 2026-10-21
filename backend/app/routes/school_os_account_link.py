"""M11 Phase 2B School OS account-link ownership-proof backend capability.

This module intentionally exposes no redirect, callback, browser UI, account
link creation, SSO, or session transfer. Phase 2C may call the authenticated
proof endpoint only after an explicit LP user approval action.

The public proof endpoint establishes that the LP principal verified from the
normal bearer session asked for an artifact associated with an opaque School OS
state. The internal exchange endpoint accepts only a Phase 2A service assertion
and atomically exchanges one unexpired artifact for the opaque LP subject.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.security.service_auth import (
    SERVICE_ASSERTION_HEADER,
    ServiceAuthError,
    verify_service_assertion,
)
from app.services.audit_log_service import write_audit_event
from app.services.auth_service import admin_client, get_current_user

proof_router = APIRouter()
internal_router = APIRouter()

PROOF_PATH = "/api/account-link/school-os/proof"
EXCHANGE_PATH = "/api/internal/school-os/account-link/exchange"
ACCOUNT_LINK_EXCHANGE_PURPOSE = "lp-account-link-exchange"
COMPLETION_ARTIFACT_TTL_SECONDS = 60
OPAQUE_VALUE_BYTES = 32
OPAQUE_VALUE_LENGTH = 43
_SHA256_HEX_LENGTH = 64


def _http_error(status_code: int, code: str) -> HTTPException:
    """Return a stable, non-sensitive API error shape."""
    return HTTPException(status_code=status_code, detail=code)


def _is_strict_opaque_value(value: str) -> bool:
    """Accept only canonical unpadded base64url encoding of exactly 32 bytes."""
    if not isinstance(value, str) or len(value) != OPAQUE_VALUE_LENGTH:
        return False
    if any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in value):
        return False

    try:
        decoded = base64.urlsafe_b64decode((value + "=").encode("ascii"))
    except (UnicodeEncodeError, ValueError):
        return False

    return len(decoded) == OPAQUE_VALUE_BYTES and (
        base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value
    )


def _opaque_value_digest(value: str) -> str:
    """Return the database's strict lowercase hexadecimal SHA-256 representation."""
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _new_completion_code() -> str:
    """Generate a 256-bit opaque, unpadded base64url code."""
    return secrets.token_urlsafe(OPAQUE_VALUE_BYTES)


class ProofRequest(BaseModel):
    """The state is correlation material only; it is never identity authority."""

    model_config = ConfigDict(extra="forbid", strict=True)

    state: str

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        if not _is_strict_opaque_value(value):
            raise ValueError("invalid opaque state")
        return value


class ExchangeRequest(BaseModel):
    """Both values are opaque and must bind to one persisted artifact."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    state: str

    @field_validator("code", "state")
    @classmethod
    def validate_opaque_value(cls, value: str) -> str:
        if not _is_strict_opaque_value(value):
            raise ValueError("invalid opaque value")
        return value


def _parse_proof_request(raw_body: bytes) -> ProofRequest:
    try:
        return ProofRequest.model_validate(json.loads(raw_body))
    except (json.JSONDecodeError, TypeError, ValidationError) as error:
        raise _http_error(400, "INVALID_STATE") from error


def _parse_exchange_request(raw_body: bytes) -> ExchangeRequest:
    try:
        return ExchangeRequest.model_validate(json.loads(raw_body))
    except (json.JSONDecodeError, TypeError, ValidationError) as error:
        raise _http_error(400, "ACCOUNT_LINK_PROOF_INVALID") from error


def _is_unique_violation(error: Exception) -> bool:
    """Classify only database uniqueness errors without returning database detail."""
    message = str(error).lower()
    return "23505" in message or "duplicate key" in message or "unique constraint" in message


def _response_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else None
    return data if isinstance(data, dict) else None


def issue_proof_for_user(*, lp_user_id: str, state: str) -> dict[str, str]:
    """Persist one state-bound artifact and return its plaintext code once.

    `lp_user_id` is supplied exclusively by the verified `get_current_user`
    dependency. No browser-supplied account identifier is accepted.
    """
    completion_code = _new_completion_code()
    expires_at = datetime.now(UTC) + timedelta(seconds=COMPLETION_ARTIFACT_TTL_SECONDS)
    state_verifier = _opaque_value_digest(state)
    completion_verifier = _opaque_value_digest(completion_code)

    try:
        response = (
            admin_client.table("school_os_account_link_completion_artifacts")
            .insert(
                {
                    "lp_user_id": lp_user_id,
                    "state_verifier": state_verifier,
                    "completion_verifier": completion_verifier,
                    "status": "ISSUED",
                    "expires_at": expires_at.isoformat(),
                }
            )
            .execute()
        )
    except Exception as error:
        if _is_unique_violation(error):
            raise _http_error(409, "PROOF_ALREADY_ISSUED") from error
        raise _http_error(503, "PROOF_UNAVAILABLE") from error

    row = _response_row(response)
    write_audit_event(
        event_type="school_os_link.proof_issued",
        actor_user_id=lp_user_id,
        entity_type="school_os_account_link_completion_artifact",
        entity_id=(row or {}).get("id"),
    )
    return {"code": completion_code}


def consume_proof(*, code: str, state: str) -> str | None:
    """Atomically consume a matching issued and unexpired artifact via database RPC."""
    try:
        response = admin_client.rpc(
            "consume_school_os_account_link_completion_artifact",
            {
                "p_completion_verifier": _opaque_value_digest(code),
                "p_state_verifier": _opaque_value_digest(state),
            },
        ).execute()
    except Exception as error:
        raise _http_error(503, "SERVICE_UNAVAILABLE") from error

    row = _response_row(response)
    if not row or not isinstance(row.get("lp_user_id"), str):
        return None

    lp_user_id = row["lp_user_id"]
    write_audit_event(
        event_type="school_os_link.proof_consumed",
        target_user_id=lp_user_id,
        entity_type="school_os_account_link_completion_artifact",
    )
    return lp_user_id


@proof_router.post("/school-os/proof")
async def create_school_os_account_link_proof(
    request: Request,
    user=Depends(get_current_user),
) -> dict[str, str]:
    """Create one artifact after future Phase 2C explicit user consent only."""
    proof_request = _parse_proof_request(await request.body())
    return issue_proof_for_user(lp_user_id=user.id, state=proof_request.state)


@internal_router.post("/school-os/account-link/exchange")
async def exchange_school_os_account_link_proof(request: Request) -> dict[str, str]:
    """Exchange exactly one artifact for the opaque LP subject.

    Starlette caches `Request.body()`, so this reads the exact received bytes
    once for Phase 2A verification, then parses those same bytes afterwards.
    """
    raw_body = await request.body()
    try:
        verify_service_assertion(
            assertion=request.headers.get(SERVICE_ASSERTION_HEADER),
            expected_purpose=ACCOUNT_LINK_EXCHANGE_PURPOSE,
            expected_method="POST",
            expected_path=EXCHANGE_PATH,
            body=raw_body,
        )
    except ServiceAuthError as error:
        if error.code == "SERVICE_AUTH_NOT_CONFIGURED":
            raise _http_error(503, "SERVICE_UNAVAILABLE") from error
        raise _http_error(401, "SERVICE_AUTH_REQUIRED") from error

    exchange_request = _parse_exchange_request(raw_body)
    lp_user_id = consume_proof(code=exchange_request.code, state=exchange_request.state)
    if lp_user_id is None:
        raise _http_error(400, "ACCOUNT_LINK_PROOF_INVALID")

    return {"provider": "likhapoha", "subject": lp_user_id}
