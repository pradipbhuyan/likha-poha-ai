"""
Unhandled Exception → JSON Middleware
======================================
Starlette's ServerErrorMiddleware (which produces the fallback 500 response
for any exception that isn't an HTTPException or a registered handler) is
always the outermost layer of the middleware stack — it wraps every
app.add_middleware(...) call, including CORSMiddleware, regardless of
registration order. That means an unhandled exception (e.g. a database
error, a bug) currently escapes past CORSMiddleware entirely, so its 500
response carries no Access-Control-Allow-Origin header. The browser reports
that as a CORS failure ("blocked by CORS policy" / "Failed to fetch"),
which hides the real error and makes it look like a CORS misconfiguration.

Registering this middleware BEFORE CORSMiddleware in main.py (so it ends up
just inside CORS, between CORS and the router) catches the exception first
and turns it into a normal JSONResponse, which then flows back out through
CORSMiddleware like any other response and gets the CORS headers it needs.

Usage: registered in main.py via app.add_middleware(UnhandledExceptionMiddleware),
added before app.add_middleware(CORSMiddleware, ...).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services.logger_service import get_logger

_log = get_logger("middleware.error_handling")


class UnhandledExceptionMiddleware(BaseHTTPMiddleware):
    """Converts unhandled exceptions into a JSON 500 response before they
    can escape past CORSMiddleware."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        try:
            return await call_next(request)
        except Exception:
            _log.error(
                "request.unhandled_exception",
                method=request.method,
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                {"detail": "We're having trouble right now. Please try again in a moment."},
                status_code=500,
            )
