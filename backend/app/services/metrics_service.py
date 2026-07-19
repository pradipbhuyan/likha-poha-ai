"""
metrics_service.py
─────────────────────────────────────────────────────────────────────────────
Lightweight metrics service — event counters with structured logging.

Maintains simple event counters with structured logging.  Can be replaced
with Prometheus, OpenTelemetry, or any other provider later — callers just
use increment() and log_metric().

Design goals:
  - Thread-safe counter storage
  - Structured JSON log output so log-aggregation tools (e.g. Datadog,
    Loki, CloudWatch) can pick up counters without a separate agent
  - Never breaks business flow (all calls are wrapped in try/except)
  - Admin endpoint can expose current counters for quick diagnostics

Shared state across processes
------------------------------
When REDIS_URL is configured (see app/services/redis_client.py), counters
are stored in Redis (INCRBY per counter key) so every worker process/instance
shares the same numbers instead of each only knowing about its own traffic.

When REDIS_URL is unset, OR a Redis operation fails at runtime, this falls
back to the original in-memory dict — correct on a single process, resets on
every deploy/restart, NOT shared across multiple processes/instances. A
Redis outage degrades metrics accuracy for that window, it never breaks the
calling flow — every public function here still never raises.

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

from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

_REDIS_PREFIX = "metrics:"

_counters: dict[str, int] = defaultdict(int)
_lock = Lock()


def _redis_scan_keys(pattern: str) -> list[str]:
    """SCAN (not KEYS) so this never blocks Redis on a large keyspace."""
    keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = redis_client.scan(cursor=cursor, match=pattern, count=200)
        keys.extend(batch)
        if cursor == 0:
            break
    return keys


def increment(counter: str, value: int = 1, **tags: Any) -> None:
    """
    Increment a named counter and emit a structured log line.

    ``tags`` are included in the log line as extra context (e.g. plan_key="nano").
    Never raises — metrics failure must not break the calling flow.
    """
    try:
        if redis_client is not None:
            try:
                redis_client.incrby(f"{_REDIS_PREFIX}{counter}", value)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "metrics.redis_failed op=increment counter=%s error=%s — falling back to in-memory",
                    counter, exc,
                )
                with _lock:
                    _counters[counter] += value
        else:
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
    if redis_client is not None:
        try:
            keys = _redis_scan_keys(f"{_REDIS_PREFIX}*")
            if not keys:
                return {}
            values = redis_client.mget(keys)
            result: dict[str, int] = {}
            for key, raw_value in zip(keys, values):
                name = key[len(_REDIS_PREFIX):]
                try:
                    result[name] = int(raw_value) if raw_value is not None else 0
                except (TypeError, ValueError):
                    result[name] = 0
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "metrics.redis_failed op=get_counters error=%s — falling back to in-memory",
                exc,
            )

    with _lock:
        return dict(_counters)


def reset_counters() -> None:
    """Reset all counters to zero (for testing only)."""
    if redis_client is not None:
        try:
            keys = _redis_scan_keys(f"{_REDIS_PREFIX}*")
            if keys:
                redis_client.delete(*keys)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "metrics.redis_failed op=reset_counters error=%s",
                exc,
            )

    with _lock:
        _counters.clear()
