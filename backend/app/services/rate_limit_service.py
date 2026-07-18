"""
rate_limit_service.py
─────────────────────────────────────────────────────────────────────────────
Lightweight in-memory sliding-window rate limiter for FastAPI endpoints.

Usage
-----
    from app.services.rate_limit_service import RateLimiter, rate_limit_dependency

    # Create a limiter: 10 requests per 60 seconds per key
    _login_limiter = RateLimiter(max_calls=10, window_seconds=60)

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

Thread safety
-------------
Uses a threading.Lock for the window list, so it is safe under Uvicorn's
default multi-threaded request handling.  It is NOT shared across multiple
worker processes — use Redis-backed limiting for multi-process deployments.
app/main.py logs a startup warning if WEB_CONCURRENCY > 1 is detected, but
that check has no visibility into horizontal replica scaling done outside
this process (e.g. a Render/Railway dashboard setting) — see
docs/product-specs/07_ARCHITECTURE_ASSESSMENT.md §3.1 for the full fix.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request

from app.config import settings as _settings


def _rate_limit_enabled() -> bool:
    """Return True unless the env variable RATE_LIMIT_ENABLED is set to 'false'."""
    val = getattr(_settings, "RATE_LIMIT_ENABLED", "true")
    return str(val).strip().lower() not in ("false", "0", "no", "off")


class RateLimiter:
    """
    Sliding-window in-memory rate limiter.

    Parameters
    ----------
    max_calls       Maximum number of requests allowed per window.
    window_seconds  Length of the sliding window in seconds.
    enabled         Override the global RATE_LIMIT_ENABLED setting.
                    Pass False to disable (useful in tests).
    """

    def __init__(
        self,
        max_calls: int,
        window_seconds: int,
        enabled: bool | None = None,
    ) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._enabled = enabled   # None = read from env at call time
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """
        Return True if the request is within the rate limit, False otherwise.

        Side effect: records the current timestamp for ``key``.
        """
        if not self._is_active():
            return True

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
        _payment_limiter = RateLimiter(max_calls=5, window_seconds=60)

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
LOGIN_LIMITER = RateLimiter(max_calls=10, window_seconds=60)     # 10/min
SIGNUP_LIMITER = RateLimiter(max_calls=5, window_seconds=60)     # 5/min
PASSWORD_RESET_LIMITER = RateLimiter(max_calls=3, window_seconds=300)  # 3/5min

# Payment — order creation / verification  (per IP)
PAYMENT_CREATE_LIMITER = RateLimiter(max_calls=10, window_seconds=60)   # 10/min
PAYMENT_VERIFY_LIMITER = RateLimiter(max_calls=10, window_seconds=60)   # 10/min

# Admin test payments  (stricter — admin-only traffic should be low volume)
ADMIN_TEST_PAYMENT_LIMITER = RateLimiter(max_calls=5, window_seconds=60)  # 5/min
