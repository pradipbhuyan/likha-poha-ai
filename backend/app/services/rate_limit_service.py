"""
rate_limit_service.py
─────────────────────────────────────────────────────────────────────────────
Sliding-window rate limiter for FastAPI endpoints.

Usage
-----
    from app.services.rate_limit_service import RateLimiter, rate_limit_dependency

    # Create a limiter: 10 requests per 60 seconds per key
    _login_limiter = RateLimiter(max_calls=10, window_seconds=60, name="login")

    @router.post("/login")
    def login(request: Request, _=Depends(rate_limit_dependency(_login_limiter))):
        ...

Keys
----
The default key is the client IP address.  For authenticated endpoints you can
combine IP + user-id for tighter per-user limits.

Disabling in tests
------------------
Set RATE_LIMIT_ENABLED=false in the environment or pass enabled=False to
RateLimiter() to skip all limiting (e.g. in test mode).  The dependency
returns transparently when disabled.

Shared state across processes
------------------------------
When REDIS_URL is configured (see app/services/redis_client.py), the sliding
window is stored in Redis — a sorted set per (limiter name, key), trimmed and
checked atomically via a Lua script — so every worker process/instance shares
the same count instead of each seeing only its own slice of traffic.

When REDIS_URL is unset, OR a Redis operation fails at runtime (timeout,
connection drop, etc.), this falls back to the original in-memory
implementation — correct on a single process, NOT shared across multiple
processes/instances. A Redis outage degrades rate-limiting accuracy, it never
breaks the request.

``name`` identifies a limiter's Redis key namespace and MUST be stable across
processes (i.e. not derived from object identity or randomness) for shared
state to actually line up. If omitted, it defaults to a
"{max_calls}x{window_seconds}s" derived name — deterministic as long as the
call site's own arguments don't change, but two distinct limiters that
happen to share both numbers would collide, so pass an explicit ``name``
whenever that's a real risk (the preconfigured limiters below all do).
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request

from app.config import settings as _settings
from app.services.redis_client import redis_client

_log = logging.getLogger("likhapoha.rate_limit")


def _rate_limit_enabled() -> bool:
    """Return True unless the env variable RATE_LIMIT_ENABLED is set to 'false'."""
    val = getattr(_settings, "RATE_LIMIT_ENABLED", "true")
    return str(val).strip().lower() not in ("false", "0", "no", "off")


# Lua script: atomic sliding-window check-and-add.
#   KEYS[1] = redis key (ratelimit:{name}:{caller_key})
#   ARGV[1] = now (unix time, seconds, float)
#   ARGV[2] = window_seconds
#   ARGV[3] = max_calls
#   ARGV[4] = unique member for this attempt (avoids collisions when two
#             calls land in the same millisecond)
# Returns 1 if allowed (and records the attempt), 0 if over the limit.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_calls = tonumber(ARGV[3])
local member = ARGV[4]

local cutoff = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= max_calls then
    redis.call('EXPIRE', key, window + 1)
    return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window + 1)
return 1
"""

_sliding_window_script = None  # lazily registered on first Redis use


def _get_sliding_window_script():
    global _sliding_window_script
    if _sliding_window_script is None and redis_client is not None:
        _sliding_window_script = redis_client.register_script(_SLIDING_WINDOW_LUA)
    return _sliding_window_script


class RateLimiter:
    """
    Sliding-window rate limiter. Redis-backed when REDIS_URL is configured,
    in-memory (single-process only) otherwise or if Redis is unreachable.

    Parameters
    ----------
    max_calls       Maximum number of requests allowed per window.
    window_seconds  Length of the sliding window in seconds.
    enabled         Override the global RATE_LIMIT_ENABLED setting.
                    Pass False to disable (useful in tests).
    name            Stable identifier for this limiter's Redis key namespace.
                    Defaults to a name derived from max_calls/window_seconds
                    if not given — see module docstring.
    """

    def __init__(
        self,
        max_calls: int,
        window_seconds: int,
        enabled: bool | None = None,
        name: str | None = None,
    ) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._enabled = enabled   # None = read from env at call time
        self._name = name or f"{max_calls}x{window_seconds}s"
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """
        Return True if the request is within the rate limit, False otherwise.

        Side effect: records the current timestamp for ``key`` (only when
        the request is allowed — a blocked attempt is not itself recorded).
        """
        if not self._is_active():
            return True

        if redis_client is not None:
            try:
                return self._is_allowed_redis(key)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "rate_limit.redis_failed name=%s error=%s — falling back to in-memory",
                    self._name, exc,
                )

        return self._is_allowed_memory(key)

    def _is_allowed_redis(self, key: str) -> bool:
        script = _get_sliding_window_script()
        now = time.time()
        redis_key = f"ratelimit:{self._name}:{key}"
        member = f"{now:.6f}:{uuid.uuid4().hex}"
        result = script(
            keys=[redis_key],
            args=[now, self.window_seconds, self.max_calls, member],
        )
        return bool(int(result))

    def _is_allowed_memory(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            calls = [t for t in self._store[key] if t > cutoff]
            if len(calls) >= self.max_calls:
                self._store[key] = calls   # prune old entries
                return False
            calls.append(now)
            self._store[key] = calls
            return True

    def _is_active(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        return _rate_limit_enabled()

    def retry_after_seconds(self, key: str) -> int:
        """
        Return the approximate number of seconds until the oldest window entry
        expires and the next request would be allowed.
        """
        if redis_client is not None:
            try:
                return self._retry_after_redis(key)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "rate_limit.redis_failed name=%s error=%s — falling back to in-memory",
                    self._name, exc,
                )

        return self._retry_after_memory(key)

    def _retry_after_redis(self, key: str) -> int:
        redis_key = f"ratelimit:{self._name}:{key}"
        now = time.time()
        cutoff = now - self.window_seconds
        redis_client.zremrangebyscore(redis_key, "-inf", cutoff)
        oldest = redis_client.zrange(redis_key, 0, 0, withscores=True)
        if not oldest:
            return 0
        oldest_score = oldest[0][1]
        return max(1, int(self.window_seconds - (now - oldest_score)) + 1)

    def _retry_after_memory(self, key: str) -> int:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            calls = sorted(t for t in self._store.get(key, []) if t > cutoff)
            if not calls:
                return 0
            oldest = calls[0]
            return max(1, int(self.window_seconds - (now - oldest)) + 1)


def client_ip(request: Request) -> str:
    """
    Extract the real client IP, honouring common reverse-proxy headers.

    Falls back to the direct connection IP when no forwarded header is present.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit_dependency(limiter: RateLimiter) -> Callable:
    """
    Return a FastAPI dependency that raises HTTP 429 when the rate limit is exceeded.

    Example
    -------
        _payment_limiter = RateLimiter(max_calls=5, window_seconds=60, name="payment")

        @router.post("/create-order")
        def create_order(request: Request, _=Depends(rate_limit_dependency(_payment_limiter))):
            ...
    """
    def _check(request: Request) -> None:
        key = client_ip(request)
        if not limiter.is_allowed(key):
            retry_after = limiter.retry_after_seconds(key)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. "
                    f"Try again in {retry_after} second(s)."
                ),
                headers={"Retry-After": str(retry_after)},
            )
    return _check


# ── Preconfigured limiters for sensitive endpoints ────────────────────────────
# Adjust thresholds via environment-specific settings; these are conservative
# defaults safe for production without being overly restrictive.

# Auth — login / signup / password reset  (per IP)
LOGIN_LIMITER = RateLimiter(max_calls=10, window_seconds=60, name="login")            # 10/min
SIGNUP_LIMITER = RateLimiter(max_calls=5, window_seconds=60, name="signup")           # 5/min
PASSWORD_RESET_LIMITER = RateLimiter(max_calls=3, window_seconds=300, name="password_reset")  # 3/5min

# Payment — order creation / verification  (per IP)
PAYMENT_CREATE_LIMITER = RateLimiter(max_calls=10, window_seconds=60, name="payment_create")  # 10/min
PAYMENT_VERIFY_LIMITER = RateLimiter(max_calls=10, window_seconds=60, name="payment_verify")  # 10/min

# Admin test payments  (stricter — admin-only traffic should be low volume)
ADMIN_TEST_PAYMENT_LIMITER = RateLimiter(max_calls=5, window_seconds=60, name="admin_test_payment")  # 5/min
