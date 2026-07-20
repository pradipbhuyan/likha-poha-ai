"""
redis_client.py
─────────────────────────────────────────────────────────────────────────────
Shared Redis client for cross-process state (rate limiting, metrics).

Both rate_limit_service.py and metrics_service.py were originally in-memory
only, which is correct on a single Uvicorn process but silently wrong the
moment the backend runs more than one worker/instance — each process gets
its own independent counters. This module gives them a shared backing store.

Environment variables
----------------------
    REDIS_URL   e.g. rediss://default:<password>@<host>:<port>  (Upstash and
                most managed Redis providers give you this as one string)

                Optional. When unset, or when the connection fails, this
                module logs a warning and redis_client stays None — callers
                MUST fall back to their own in-memory implementation rather
                than raising. Never let a Redis outage break a real request.

Timeouts are set deliberately short (2s) so a slow/unreachable Redis never
turns into a hung request — callers should still wrap each Redis operation
in its own try/except and fall back to in-memory on any failure, not just
treat this module's startup check as sufficient.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger("likhapoha.redis")

_redis_url = (os.getenv("REDIS_URL") or "").strip() or None

redis_client = None

if not _redis_url:
    _logger.warning(
        "REDIS_URL is not set. rate_limit_service and metrics_service will "
        "use in-memory state, which is NOT shared across multiple worker "
        "processes or instances. Set REDIS_URL (e.g. from Upstash) for "
        "correct behavior once the backend scales past one process."
    )
else:
    try:
        import redis as _redis_pkg  # noqa: PLC0415

        redis_client = _redis_pkg.Redis.from_url(
            _redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        redis_client.ping()
        _logger.info("Redis client connected successfully.")
    except Exception as exc:  # noqa: BLE001
        _logger.error(
            "Redis connection failed (%s) — falling back to in-memory state. "
            "Check REDIS_URL.",
            exc,
        )
        redis_client = None


def is_redis_available() -> bool:
    """True when a working Redis connection is configured."""
    return redis_client is not None
