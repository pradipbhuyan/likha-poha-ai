"""
metrics_service.py
─────────────────────────────────────────────────────────────────────────────
Lightweight in-process metrics service.

Maintains simple event counters with structured logging.  Can be replaced
with Prometheus, OpenTelemetry, or any other provider later — callers just
use increment() and log_metric().

Design goals:
  - Zero external dependencies
  - Thread-safe counter storage
  - Structured JSON log output so log-aggregation tools (e.g. Datadog,
    Loki, CloudWatch) can pick up counters without a separate agent
  - Never breaks business flow (all calls are wrapped in try/except)
  - Admin endpoint can expose current counters for quick diagnostics

Counter names (non-exhaustive):
  signup.success
  signup.failure
  login.success
  login.failure
  payment.order_created
  payment.verified
  payment.verify_idempotent
  payment.verify_failed
  payment.admin_test_created
  payment.admin_test_verified
  webhook.received
  webhook.duplicate_skipped
  webhook.activation_failed
  subscription.activated
  subscription.expired
  subscription.fallback_applied
  rate_limit.exceeded
  teacher.student_created
  parent_child.linked
  parent_child.unlinked
  expiry_job.ran
  expiry_job.users_revoked
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_counters: dict[str, int] = defaultdict(int)
_lock = Lock()


def increment(counter: str, value: int = 1, **tags: Any) -> None:
    """
    Increment a named counter and emit a structured log line.

    ``tags`` are included in the log line as extra context (e.g. plan_key="nano").
    Never raises — metrics failure must not break the calling flow.
    """
    try:
        with _lock:
            _counters[counter] += value
        # Structured log so aggregators can parse it
        log_payload = {"metric": counter, "value": value, "ts": time.time(), **tags}
        logger.info("metric %s", log_payload)
    except Exception as exc:
        logger.debug("metrics.increment_failed counter=%s error=%s", counter, exc)


def log_metric(event: str, **kwargs: Any) -> None:
    """
    Emit a structured log event without incrementing a counter.
    Useful for one-off events where counting is less important than detail.
    """
    try:
        payload = {"event": event, "ts": time.time(), **kwargs}
        logger.info("metric_event %s", payload)
    except Exception:
        pass


def get_counters() -> dict[str, int]:
    """Return a snapshot of all current counters (admin endpoint use only)."""
    with _lock:
        return dict(_counters)


def reset_counters() -> None:
    """Reset all counters to zero (for testing only)."""
    with _lock:
        _counters.clear()
