"""
Request Tracing Middleware
===========================
Attaches a trace ID to every incoming HTTP request and logs:
  - REQUEST  — method, path, client IP
  - RESPONSE — status code, duration_ms

The trace ID is:
  1. Taken from the incoming X-Trace-Id header if present (e.g. from a proxy)
  2. Otherwise generated fresh as a 16-char UUID hex

The trace ID is returned in the X-Trace-Id response header so the frontend
and support team can correlate client-side errors with server-side logs.

Usage: registered in main.py via app.add_middleware(TracingMiddleware)
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.logger_service import get_logger, new_trace_id, set_trace_id

_log = get_logger("middleware.tracing")

# Paths to skip for high-frequency noise reduction
_SKIP_PATHS = {"/api/health", "/", "/api/health/dependencies"}


class TracingMiddleware(BaseHTTPMiddleware):
    """Injects trace IDs and structured request/response logging."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # Honour incoming trace ID from load-balancer / frontend
        incoming_tid = request.headers.get("X-Trace-Id", "").strip()
        if incoming_tid:
            set_trace_id(incoming_tid)
            tid = incoming_tid
        else:
            tid = new_trace_id()

        path = request.url.path
        method = request.method
        client_ip = (request.headers.get("X-Forwarded-For") or
                     (request.client.host if request.client else "unknown"))

        skip = path in _SKIP_PATHS or path.startswith("/api/health")

        if not skip:
            _log.info(
                "request.start",
                method=method,
                path=path,
                client_ip=client_ip,
                trace_id=tid,
            )

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000)
            _log.error(
                "request.unhandled_exception",
                method=method,
                path=path,
                duration_ms=duration_ms,
                error=str(exc),
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000)

        if not skip:
            level = "warn" if response.status_code >= 500 else "info"
            getattr(_log, level)(
                "request.complete",
                method=method,
                path=path,
                status=response.status_code,
                duration_ms=duration_ms,
                trace_id=tid,
            )

        # Return trace ID in response headers for client-side correlation
        response.headers["X-Trace-Id"] = tid
        return response
