"""
Supabase Retry Helper
======================
Render's free tier occasionally terminates the HTTP/2 connection pool
mid-request, causing transient httpx.ReadError / ConnectionTerminated
errors from the Supabase client that are NOT real database or auth
failures — just a dropped socket that succeeds on retry.

`auth_service.get_current_user()` already retries on this exact error
pattern. This module extracts that same retry policy into a small,
reusable helper so any other Supabase call site (profile lookups, exam
schedule queries, etc.) can get the same resilience without duplicating
the retry loop.

Usage:
    from app.services.supabase_retry import call_with_retry

    response = call_with_retry(
        lambda: supabase.table("student_profiles").select("*").eq("username", username).execute()
    )
"""

import logging
import time

_log = logging.getLogger("likhapoha.supabase_retry")

_TRANSIENT_MARKERS = (
    "connectionterminated", "connection terminated",
    "read error", "errno 11", "resource temporarily unavailable",
    "reset by peer", "broken pipe", "connection reset",
)


def is_transient_supabase_error(exc: Exception) -> bool:
    """Return True if this exception looks like a dropped-connection
    error rather than a real query/auth failure."""
    err_str = str(exc).lower()
    return any(marker in err_str for marker in _TRANSIENT_MARKERS)


def call_with_retry(fn, attempts: int = 3, base_delay: float = 0.3, logger=None):
    """
    Call fn() and retry up to `attempts` times if it raises a transient
    connection error. Non-transient exceptions are raised immediately —
    only dropped-connection style errors are retried.

    Returns fn()'s return value on success. Re-raises the last exception
    if all attempts are exhausted.
    """
    log = logger or _log
    last_exc = None

    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentionally broad, see docstring
            if is_transient_supabase_error(exc) and attempt < attempts - 1:
                last_exc = exc
                log.warning(
                    "Transient Supabase error (retry %s/%s): %s",
                    attempt + 1, attempts - 1, exc,
                )
                time.sleep(base_delay * (attempt + 1))
                continue
            raise

    # Should not reach here (loop either returns or raises), but keep a
    # safe fallback in case attempts <= 0 was passed.
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("call_with_retry: no attempts were made")
