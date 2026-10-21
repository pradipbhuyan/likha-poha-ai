"""M11 Phase 2D2 School OS SSO backend completion boundary.

This module exposes no browser SSO page or launch UI. It accepts only an opaque
one-time School OS artifact, exchanges it once with the fixed School OS internal
endpoint using Phase 2A service authentication, then creates a normal LP
Supabase session for the verified existing LP subject.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from supabase import ClientOptions, create_client

from app.security.service_auth import (
    SERVICE_ASSERTION_HEADER,
    ServiceAuthError,
    sign_service_assertion,
)
from app.services.auth_service import SUPABASE_URL, admin_client

router = APIRouter()

SCHOOL_OS_SSO_EXCHANGE_PATH = "/api/v1/internal/lp-sso/exchange"
SCHOOL_OS_SSO_EXCHANGE_PURPOSE = "lp-sso-exchange"
OPAQUE_VALUE_BYTES = 32
OPAQUE_VALUE_LENGTH = 43
EXCHANGE_TIMEOUT_SECONDS = 4


def _http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _is_opaque_code(value: str) -> bool:
    if not isinstance(value, str) or len(value) != OPAQUE_VALUE_LENGTH:
        return False
    if any(
        character
        not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in value
    ):
        return False
    try:
        decoded = base64.urlsafe_b64decode((value + "=").encode("ascii"))
    except (UnicodeEncodeError, ValueError):
        return False
    return len(decoded) == OPAQUE_VALUE_BYTES and (
        base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value
    )


class SchoolOsSsoCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not _is_opaque_code(value):
            raise ValueError("invalid opaque launch code")
        return value


def _school_os_base_url() -> str:
    configured = os.getenv("SCHOOL_OS_API_BASE_URL")
    if not configured:
        raise _http_error(503, "SSO integration unavailable")

    from urllib.parse import urlparse

    parsed = urlparse(configured)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or (
            parsed.scheme == "http"
            and parsed.hostname not in {"localhost", "127.0.0.1"}
        )
    ):
        raise _http_error(503, "SSO integration unavailable")

    return configured.rstrip("/") + "/"


def _exchange_school_os_code(code: str) -> str:
    """Exchange one opaque code exactly once. Never retry a one-time artifact."""
    body = json.dumps(
        {"code": code},
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    try:
        assertion = sign_service_assertion(
            purpose=SCHOOL_OS_SSO_EXCHANGE_PURPOSE,
            method="POST",
            path=SCHOOL_OS_SSO_EXCHANGE_PATH,
            body=body,
        )
    except ServiceAuthError as error:
        raise _http_error(503, "SSO integration unavailable") from error

    request = UrlRequest(
        _school_os_base_url() + SCHOOL_OS_SSO_EXCHANGE_PATH.lstrip("/"),
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            SERVICE_ASSERTION_HEADER: assertion,
        },
    )

    try:
        with urlopen(request, timeout=EXCHANGE_TIMEOUT_SECONDS) as response:
            raw_response = response.read()
    except HTTPError as error:
        if 400 <= error.code < 500:
            raise _http_error(409, "SSO launch cannot be completed") from error
        raise _http_error(503, "SSO integration unavailable") from error
    except (URLError, TimeoutError, OSError) as error:
        raise _http_error(503, "SSO integration unavailable") from error

    try:
        parsed: Any = json.loads(raw_response)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _http_error(503, "SSO integration unavailable") from error

    if (
        not isinstance(parsed, dict)
        or set(parsed) != {"provider", "subject"}
        or parsed.get("provider") != "likhapoha"
        or not isinstance(parsed.get("subject"), str)
    ):
        raise _http_error(503, "SSO integration unavailable")

    subject = parsed["subject"]
    try:
        UUID(subject)
    except (ValueError, AttributeError) as error:
        raise _http_error(503, "SSO integration unavailable") from error
    return subject


def _mint_session_for_verified_subject(subject: str) -> tuple[str, str]:
    """Mint a standard GoTrue session for an already verified LP auth user."""
    try:
        user_response = admin_client.auth.admin.get_user_by_id(subject)
        user = user_response.user
    except Exception as error:
        raise _http_error(409, "SSO launch cannot be completed") from error

    if (
        not user
        or user.id != subject
        or not isinstance(user.email, str)
        or not user.email
    ):
        raise _http_error(409, "SSO launch cannot be completed")

    try:
        generated = admin_client.auth.admin.generate_link(
            {"type": "recovery", "email": user.email}
        )
        recovery_otp = generated.properties.email_otp
    except Exception as error:
        raise _http_error(503, "SSO integration unavailable") from error

    if not isinstance(recovery_otp, str) or not recovery_otp:
        raise _http_error(503, "SSO integration unavailable")

    anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not SUPABASE_URL or not anon_key:
        raise _http_error(503, "SSO integration unavailable")

    verifier_client = create_client(
        SUPABASE_URL,
        anon_key,
        options=ClientOptions(
            persist_session=False,
            auto_refresh_token=False,
        ),
    )

    try:
        verified = verifier_client.auth.verify_otp(
            {"email": user.email, "token": recovery_otp, "type": "recovery"}
        )
    except Exception as error:
        raise _http_error(409, "SSO launch cannot be completed") from error

    session = verified.session
    verified_user = verified.user
    if (
        not session
        or not verified_user
        or verified_user.id != subject
        or not isinstance(session.access_token, str)
        or not session.access_token
        or not isinstance(session.refresh_token, str)
        or not session.refresh_token
    ):
        raise _http_error(409, "SSO launch cannot be completed")

    return session.access_token, session.refresh_token


@router.post("/school-os/complete")
async def complete_school_os_sso(request: Request) -> JSONResponse:
    try:
        payload = SchoolOsSsoCompletionRequest.model_validate(await request.json())
    except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise _http_error(400, "Invalid SSO launch") from error

    subject = _exchange_school_os_code(payload.code)
    access_token, refresh_token = _mint_session_for_verified_subject(subject)

    return JSONResponse(
        {"access_token": access_token, "refresh_token": refresh_token},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
