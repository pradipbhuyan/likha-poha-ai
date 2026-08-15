"""
test_unauthenticated_endpoint_regression.py
════════════════════════════════════════════
Regression tests for the go-live audit's blockers 1-3 — three groups of
endpoints that shipped with no authentication dependency at all.

Blocker 1 — RAG corpus writes/deletes were open to anonymous callers, so the
            knowledge base grounding every lesson and doubt answer could be
            deleted or poisoned from the internet.
Blocker 2 — The Razorpay webhook skipped signature verification entirely when
            RAZORPAY_WEBHOOK_SECRET was unset, letting a forged
            payment.captured activate a paid plan.
Blocker 3 — Progress/profile/usage/recommendation routes identified the user
            from a client-supplied username string, so any caller could read
            or write another student's records.

These assert against the real FastAPI dependency graph rather than parameter
names, so renaming a guard parameter cannot silently re-open a route.

Run with:
    cd backend && python -m pytest tests/test_unauthenticated_endpoint_regression.py -v
"""

import hashlib
import hmac

import pytest
from fastapi.routing import APIRoute

from app.main import app
from app.services.auth_service import (
    get_current_user,
    require_admin,
    require_self_by_username,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _guards_for(path: str, method: str) -> set:
    """Return every dependency callable in a route's resolved dependency tree."""
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method.upper() in route.methods:
            found = set()

            def walk(dependant):
                if dependant.call is not None:
                    found.add(dependant.call)
                for sub in dependant.dependencies:
                    walk(sub)

            for sub in route.dependant.dependencies:
                walk(sub)
            return found

    raise AssertionError(f"Route not registered: {method.upper()} {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Blocker 1 — RAG corpus endpoints are admin-only
# ─────────────────────────────────────────────────────────────────────────────

RAG_ADMIN_ROUTES = [
    ("POST",   "/api/rag/upload-text"),
    ("POST",   "/api/rag/upload-image"),
    ("POST",   "/api/rag/upload-file"),
    ("POST",   "/api/rag/upload-files"),
    ("GET",    "/api/rag/documents"),
    ("DELETE", "/api/rag/documents/{document_id}"),
    ("POST",   "/api/rag/analyze-image"),
    ("POST",   "/api/rag/search"),
    ("POST",   "/api/rag/analyze-book-set"),
    ("POST",   "/api/rag/analyze-full-book"),
    ("POST",   "/api/rag/upload-full-book-sections"),
    ("POST",   "/api/rag/bulk-book-upload"),
    ("POST",   "/api/rag/book-set-upload"),
]


class TestBlocker1RagCorpusIsAdminOnly:
    """Every route that reads, writes or deletes the RAG corpus needs require_admin."""

    @pytest.mark.parametrize("method,path", RAG_ADMIN_ROUTES)
    def test_rag_route_requires_admin(self, method, path):
        assert require_admin in _guards_for(path, method), (
            f"{method} {path} must depend on require_admin — this endpoint "
            f"reads or mutates the corpus that grounds student-facing AI answers."
        )

    def test_no_rag_route_is_unguarded(self):
        """Catches a newly added RAG route that ships without a guard."""
        unguarded = []
        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue
            if not route.path.startswith("/api/rag/"):
                continue
            guards = _guards_for(route.path, next(iter(route.methods)))
            if require_admin not in guards:
                unguarded.append(f"{sorted(route.methods)} {route.path}")

        assert not unguarded, f"Unguarded RAG routes: {unguarded}"


# ─────────────────────────────────────────────────────────────────────────────
# Blocker 2 — webhook signature verification fails closed
# ─────────────────────────────────────────────────────────────────────────────

class _FakeRequest:
    """Minimal stand-in for starlette Request — body + headers only."""

    def __init__(self, body: bytes, headers: dict):
        self._body = body
        self.headers = headers

    async def body(self):
        return self._body

    async def json(self):
        import json
        return json.loads(self._body)


def _captured_body(order_id: str = "order_TEST123") -> bytes:
    import json
    return json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"order_id": order_id, "id": "pay_TEST123"}}},
    }).encode()


def _call_webhook(request) -> dict:
    """Drive the async webhook handler from a sync test (no async plugin needed)."""
    import asyncio

    import app.routes.payments as payments_route

    return asyncio.run(payments_route.razorpay_webhook(request))


class TestBlocker2WebhookFailsClosed:
    """An unsigned or unverifiable webhook must never reach plan activation."""

    def test_missing_secret_refuses_to_process(self, monkeypatch):
        """With no secret configured the webhook must refuse, not skip verification."""
        import app.routes.payments as payments_route

        monkeypatch.setattr(payments_route.settings, "RAZORPAY_WEBHOOK_SECRET", None)

        def _boom(*a, **k):
            raise AssertionError("activation must not be reached without a valid signature")

        monkeypatch.setattr(payments_route, "activate_plan_for_payment", _boom)

        result = _call_webhook(
            _FakeRequest(_captured_body(), {"X-Razorpay-Signature": "anything"})
        )

        assert result["status"] == "ignored"
        assert result["reason"] == "webhook_secret_not_configured"

    def test_missing_signature_header_is_ignored(self, monkeypatch):
        import app.routes.payments as payments_route

        monkeypatch.setattr(payments_route.settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")
        monkeypatch.setattr(
            payments_route, "activate_plan_for_payment",
            lambda *a, **k: pytest.fail("activation reached without a signature"),
        )

        result = _call_webhook(_FakeRequest(_captured_body(), {}))

        assert result == {"status": "ignored", "reason": "missing_signature"}

    def test_bad_signature_is_ignored(self, monkeypatch):
        import app.routes.payments as payments_route

        monkeypatch.setattr(payments_route.settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")
        monkeypatch.setattr(
            payments_route, "activate_plan_for_payment",
            lambda *a, **k: pytest.fail("activation reached with a bad signature"),
        )

        result = _call_webhook(
            _FakeRequest(_captured_body(), {"X-Razorpay-Signature": "deadbeef"})
        )

        assert result == {"status": "ignored", "reason": "invalid_signature"}

    def test_valid_signature_passes_verification(self, monkeypatch):
        """A correctly signed body must get past verification and into event handling."""
        import app.routes.payments as payments_route

        secret = "whsec_test"
        body = _captured_body("order_NOT_IN_DB")
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        monkeypatch.setattr(payments_route.settings, "RAZORPAY_WEBHOOK_SECRET", secret)
        monkeypatch.setattr(payments_route, "get_payment_by_order_id", lambda _oid: None)

        result = _call_webhook(
            _FakeRequest(body, {"X-Razorpay-Signature": signature})
        )

        # Got past the signature gate — stopped later, at the unknown order.
        assert result["status"] == "ok"
        assert result.get("note") == "order_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# Blocker 3 — student records are session-scoped, not username-scoped
# ─────────────────────────────────────────────────────────────────────────────

SESSION_SCOPED_WRITES = [
    ("POST", "/api/progress/chapter"),
    ("POST", "/api/progress/save"),
    ("POST", "/api/profile/activity"),
]

USERNAME_PATH_READS = [
    ("GET", "/api/progress/user/{username}"),
    ("GET", "/api/profile/{username}"),
    ("GET", "/api/recommendations/{username}"),
]


class TestBlocker3StudentRecordsAreScoped:

    @pytest.mark.parametrize("method,path", SESSION_SCOPED_WRITES)
    def test_write_requires_authentication(self, method, path):
        assert get_current_user in _guards_for(path, method), (
            f"{method} {path} must depend on get_current_user and derive the "
            f"username from the session — a client-supplied username let any "
            f"caller author records into another student's account."
        )

    @pytest.mark.parametrize("method,path", USERNAME_PATH_READS)
    def test_username_path_read_is_guarded(self, method, path):
        assert require_self_by_username in _guards_for(path, method), (
            f"{method} {path} must depend on require_self_by_username so a "
            f"student can only read their own record."
        )

    def test_usage_summary_requires_admin(self):
        assert require_admin in _guards_for("/api/usage/summary", "GET"), (
            "GET /api/usage/summary exposes platform-wide AI spend and a "
            "per-user cost breakdown — it must require admin."
        )

    def test_request_body_username_is_ignored(self, monkeypatch):
        """The save handler must overwrite any username sent by the client."""
        import app.routes.progress as progress_route

        captured = {}
        monkeypatch.setattr(
            progress_route, "save_chapter_progress",
            lambda payload: captured.update(payload) or payload,
        )
        monkeypatch.setattr(
            progress_route, "resolve_session_username", lambda _user: "real_student"
        )

        progress_route.save_progress(
            progress_route.SaveProgressRequest(
                username="victim_student",
                grade="Grade 9",
                mode="CBSE",
                subject="Science",
                chapter="Motion",
                current_step_index=1,
            ),
            user=object(),
        )

        assert captured["username"] == "real_student", (
            "save_progress must ignore the body username and use the session's"
        )
