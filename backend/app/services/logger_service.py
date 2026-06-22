"""
LikhaPoha AI — Structured Logging & Tracing Service
=====================================================
Provides structured JSON logging with:
  - Trace IDs (per-request UUID) for end-to-end tracing
  - Platform error codes (LP-xxx-xxx) for support lookup
  - Severity levels: DEBUG / INFO / WARN / ERROR / CRITICAL
  - Context fields: username, grade, subject, feature, duration_ms

Usage in route handlers:
    from app.services.logger_service import get_logger, PlatformError
    log = get_logger(__name__)
    log.info("lesson.generated", username="likha", grade="Grade 9", duration_ms=1200)
    log.error("llm.timeout", error_code=PlatformError.LLM_TIMEOUT, username="likha")

Trace IDs:
    Each incoming HTTP request gets a trace_id injected via middleware.
    Access it anywhere in the request lifecycle:
        from app.services.logger_service import get_trace_id
        trace_id = get_trace_id()
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ── Context variable for per-request trace ID ────────────────────────────────
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    """Generate and store a new trace ID for the current request context."""
    tid = str(uuid.uuid4())[:16]
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Return the trace ID for the current request (empty string if none)."""
    return _trace_id_var.get("")


def set_trace_id(tid: str) -> None:
    """Set an explicit trace ID (e.g. from an incoming X-Trace-Id header)."""
    _trace_id_var.set(tid)


# ── Platform error code registry ─────────────────────────────────────────────
class PlatformError:
    """
    Platform error codes for structured error tracking.

    Format: LP-{DOMAIN}-{CODE}
      LP = LikhaPoha
      DOMAIN = AUTH | LLM | DB | RAG | PAY | SUBS | CACHE | RATE | SYS
      CODE = 3-digit sequential number

    Use these codes in error logs so support can search by code.
    """
    # Authentication / Authorization
    AUTH_TOKEN_INVALID       = "LP-AUTH-001"
    AUTH_TOKEN_EXPIRED       = "LP-AUTH-002"
    AUTH_USER_NOT_FOUND      = "LP-AUTH-003"
    AUTH_ROLE_DENIED         = "LP-AUTH-004"
    AUTH_SIGNUP_FAILED       = "LP-AUTH-005"
    AUTH_EMAIL_NOT_CONFIRMED = "LP-AUTH-006"
    AUTH_RATE_LIMIT          = "LP-AUTH-007"

    # LLM / AI
    LLM_TIMEOUT              = "LP-LLM-001"
    LLM_RATE_LIMIT           = "LP-LLM-002"
    LLM_CONTEXT_TOO_LONG     = "LP-LLM-003"
    LLM_INVALID_RESPONSE     = "LP-LLM-004"
    LLM_QUOTA_EXCEEDED       = "LP-LLM-005"
    LLM_GUARDRAIL_BLOCKED    = "LP-LLM-006"

    # Database / Supabase
    DB_QUERY_FAILED          = "LP-DB-001"
    DB_INSERT_FAILED         = "LP-DB-002"
    DB_UPDATE_FAILED         = "LP-DB-003"
    DB_NOT_FOUND             = "LP-DB-004"
    DB_CONSTRAINT_VIOLATION  = "LP-DB-005"
    DB_CONNECTION_ERROR      = "LP-DB-006"

    # RAG / Embeddings
    RAG_UPLOAD_FAILED        = "LP-RAG-001"
    RAG_EMBED_FAILED         = "LP-RAG-002"
    RAG_SEARCH_FAILED        = "LP-RAG-003"
    RAG_FILE_PARSE_FAILED    = "LP-RAG-004"
    RAG_NO_CONTENT_FOUND     = "LP-RAG-005"

    # Payments
    PAY_ORDER_FAILED         = "LP-PAY-001"
    PAY_VERIFY_FAILED        = "LP-PAY-002"
    PAY_WEBHOOK_FAILED       = "LP-PAY-003"
    PAY_REFUND_FAILED        = "LP-PAY-004"

    # Subscription / Access
    SUBS_NO_ACCESS           = "LP-SUBS-001"
    SUBS_PLAN_NOT_FOUND      = "LP-SUBS-002"
    SUBS_LIMIT_EXCEEDED      = "LP-SUBS-003"
    SUBS_OFFER_INVALID       = "LP-SUBS-004"
    SUBS_OFFER_EXPIRED       = "LP-SUBS-005"

    # Cache
    CACHE_MISS               = "LP-CACHE-001"
    CACHE_WRITE_FAILED       = "LP-CACHE-002"
    CACHE_READ_FAILED        = "LP-CACHE-003"

    # Rate limiting / Quotas
    RATE_DAILY_EXCEEDED      = "LP-RATE-001"
    RATE_MONTHLY_EXCEEDED    = "LP-RATE-002"
    RATE_IP_BLOCKED          = "LP-RATE-003"

    # System / Infra
    SYS_INTERNAL_ERROR       = "LP-SYS-001"
    SYS_CONFIG_MISSING       = "LP-SYS-002"
    SYS_EXTERNAL_API_FAILED  = "LP-SYS-003"
    SYS_FILE_NOT_FOUND       = "LP-SYS-004"
    SYS_TIMEOUT              = "LP-SYS-005"


# ── JSON formatter ────────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for structured log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        tid = get_trace_id()
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if tid:
            payload["trace_id"] = tid

        # Include any extra fields set on the record
        skip = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in skip and not key.startswith("_"):
                payload[key] = val

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


# ── Logger factory ────────────────────────────────────────────────────────────
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_USE_JSON = os.getenv("LOG_FORMAT", "json").lower() == "json"


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if _USE_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
    return handler


_root = logging.getLogger("likhapoha")
if not _root.handlers:
    _root.addHandler(_build_handler())
_root.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
_root.propagate = False


def get_logger(name: str) -> "StructuredLogger":
    """Return a StructuredLogger wrapping the named Python logger."""
    return StructuredLogger(logging.getLogger(f"likhapoha.{name}"))


# ── Structured logger wrapper ─────────────────────────────────────────────────
class StructuredLogger:
    """
    Thin wrapper around Python's Logger that adds keyword-argument style
    structured fields to every log record.

    Example:
        log.info("lesson.generated", username="alice", duration_ms=830)
        log.error("db.query_failed", error_code=PlatformError.DB_QUERY_FAILED,
                  table="profiles", exc_info=True)
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def _emit(self, level: int, event: str, **kwargs: Any) -> None:
        error_code = kwargs.pop("error_code", None)
        exc_info = kwargs.pop("exc_info", False)
        msg = event
        if error_code:
            msg = f"[{error_code}] {event}"
            kwargs["error_code"] = error_code
        extra = kwargs
        self._log.log(level, msg, extra=extra, exc_info=exc_info, stacklevel=3)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warn(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.CRITICAL, event, **kwargs)

    def timed(self, event: str, start: float, **kwargs: Any) -> None:
        """Log an INFO event with duration_ms computed from start time."""
        kwargs["duration_ms"] = round((time.perf_counter() - start) * 1000)
        self._emit(logging.INFO, event, **kwargs)
