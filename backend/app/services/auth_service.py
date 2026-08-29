import hashlib
import os
import re as _re
import threading
import time as _time_module

from dotenv import load_dotenv

from app.services.logger_service import get_logger
from app.services.ssl_service import enable_system_truststore

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import ClientOptions, create_client

enable_system_truststore()

load_dotenv()

_log = get_logger("services.auth")

# Provider error strings are not guaranteed to keep credentials or personal
# data out of their message, so scrub both before anything reaches the logs.
# A JWT is three base64url segments separated by dots; a bearer token in a log
# line is a session-hijack vector. Emails are scrubbed because the users here
# are children and their addresses must not accumulate in log retention.
_JWT_PATTERN = _re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_EMAIL_PATTERN = _re.compile(r"\b[^\s@<>]+@[^\s@<>]+\.[A-Za-z]{2,}\b")


def _safe_auth_error(exc: object, limit: int = 200) -> str:
    """
    Render an auth exception for logging with tokens and emails redacted and the
    message length capped.

    Used on every auth failure path. The success path logs nothing at all.
    """
    text = _JWT_PATTERN.sub("<redacted-token>", str(exc))
    return _EMAIL_PATTERN.sub("<redacted-email>", text)[:limit]

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

admin_client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    options=ClientOptions(
        # Default is 120s. admin_client is one long-lived client shared by
        # every request for this process's whole lifetime; if a pooled
        # keep-alive connection goes stale (network blip, a proxy/NAT
        # silently dropping an idle connection — the exact class of issue
        # the retry loop below this already works around for auth calls),
        # every PostgREST call reusing that connection hung for a full 2
        # minutes with zero feedback before failing. 15s turns that into a
        # fast, visible failure the frontend can show and retry instead of
        # an indefinite-looking freeze.
        postgrest_client_timeout=15,
    ),
)


# ── Token validation cache ───────────────────────────────────────────────────
# Every authenticated request made two network round trips before reaching any
# handler: admin_client.auth.get_user(token) against Supabase Auth, then a
# profiles query in whichever require_* guard the route uses. The auth call is
# the expensive one — a full HTTP request to a separate service, on the
# critical path of every request, and a hard dependency: if Supabase Auth is
# slow, everything is slow. The retry loop below, added for Render dropping
# connections mid-request, is evidence of that pressure.
#
# This caches the token -> user result for a short window, so a burst of
# requests from one signed-in user costs one auth call rather than one each.
#
# DELIBERATELY NOT CACHING THE PROFILE ROW. That is where role, plan and
# entitlements live, and staleness there is user-visible in the worst place:
# someone finishes a payment, the webhook activates their plan, and they keep
# seeing the free tier until the entry expires. Halving the round trips is
# worth having; risking that is not.
#
# What staleness this does introduce is bounded and mild: a revoked or
# signed-out session keeps validating until its entry expires. Failures are
# never cached, so an invalid token is rechecked every time.
_AUTH_CACHE_TTL_SECONDS = float(os.getenv("AUTH_CACHE_TTL_SECONDS", "30"))
_AUTH_CACHE_MAX_ENTRIES = 2000

_auth_cache: dict[str, tuple[float, object]] = {}
_auth_cache_lock = threading.Lock()


def _token_key(token: str) -> str:
    """Hash the token so raw bearer tokens are not held as dict keys."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _auth_cache_get(token: str):
    """Return the cached user for a token, or None when absent or expired."""
    if _AUTH_CACHE_TTL_SECONDS <= 0:
        return None
    key = _token_key(token)
    now = _time_module.monotonic()
    with _auth_cache_lock:
        entry = _auth_cache.get(key)
        if not entry:
            return None
        expires_at, user = entry
        if expires_at <= now:
            _auth_cache.pop(key, None)
            return None
        return user


def _auth_cache_put(token: str, user) -> None:
    """Cache a successful validation. Never called for failures."""
    if _AUTH_CACHE_TTL_SECONDS <= 0:
        return
    now = _time_module.monotonic()
    with _auth_cache_lock:
        if len(_auth_cache) >= _AUTH_CACHE_MAX_ENTRIES:
            # Drop everything already expired; if that frees nothing, clear the
            # lot. Both are cheap and correctness-preserving — the worst case
            # is that the next requests revalidate.
            for k, (exp, _) in list(_auth_cache.items()):
                if exp <= now:
                    _auth_cache.pop(k, None)
            if len(_auth_cache) >= _AUTH_CACHE_MAX_ENTRIES:
                _auth_cache.clear()
        _auth_cache[_token_key(token)] = (now + _AUTH_CACHE_TTL_SECONDS, user)


def clear_auth_cache() -> None:
    """Drop every cached validation. For tests, and for sign-out-everywhere."""
    with _auth_cache_lock:
        _auth_cache.clear()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Validate the bearer token from the request and return the Supabase auth user.

    All protected routes depend on this function, so failures are deliberately
    normalized to HTTP 401 instead of leaking provider-specific auth errors.

    Retries up to 2 times on transient HTTP/2 connection drops (Render free tier
    occasionally terminates the connection pool mid-request, causing ConnectionTerminated
    or ReadError errors that are not auth failures).

    Deliberately logs nothing on the success path. This runs on every
    authenticated request, and it previously printed the user's id and email to
    stdout each time — accumulating children's personal data in log retention,
    outside the platform's consent and deletion story. Failures log the provider
    error only; the token and the user's identity are never logged. Per-request
    identity belongs in tracing, not here.

    Successful validations are cached briefly against the token — see the cache
    block above for what that does and does not cover. Failures are never
    cached, so an invalid token costs a real check every time.
    """
    import time as _time  # noqa: PLC0415

    token = credentials.credentials
    last_exc = None

    cached_user = _auth_cache_get(token)
    if cached_user is not None:
        return cached_user

    for attempt in range(3):
        try:
            response = admin_client.auth.get_user(token)

            if not response.user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token",
                )

            _auth_cache_put(token, response.user)
            return response.user

        except HTTPException:
            raise  # Auth failures are not retried

        except Exception as e:
            err_str = str(e).lower()
            # Retry only on transient network errors, not real auth failures
            is_transient = any(k in err_str for k in (
                "connectionterminated", "connection terminated",
                "read error", "errno 11", "resource temporarily unavailable",
                "reset by peer", "broken pipe", "connection reset",
            ))
            if is_transient and attempt < 2:
                last_exc = e
                _log.warning("auth.transient_error", attempt=attempt + 1, error=_safe_auth_error(e))
                _time.sleep(0.3 * (attempt + 1))
                continue
            _log.warning("auth.token_rejected", error=_safe_auth_error(e))
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

    # All retries exhausted — still a transient error, return 401
    _log.error("auth.retries_exhausted", error=_safe_auth_error(last_exc))
    raise HTTPException(
        status_code=401,
        detail="Invalid or expired token",
    )

_PROFILE_COLUMNS = (
    "id, email, username, role, parent_id, family_id, grade, stream, "
    "cbse_subjects, account_status, subscription_plan"
)

# is_test_account is selected separately so this module keeps working whether
# or not the column exists yet. Deploys are automatic on push, so code can
# reach production before the migration is applied; selecting an unknown
# column would fail every profile lookup and take down all authentication.
# The first failure flips this off and the short column list is used from then
# on — self-healing in the other direction too, since a process started before
# the migration picks the column up on its next restart.
_OPTIONAL_PROFILE_COLUMNS = ["is_test_account"]
_optional_columns_available = True


def get_user_profile(user_id: str):
    """
    Load the application profile row that belongs to an authenticated user id.

    Supabase auth confirms identity, while the profile row provides app-level
    role and family metadata used by route guards.
    """
    global _optional_columns_available

    def _query(columns: str):
        return (
            admin_client
            .table("profiles")
            .select(columns)
            .eq("id", user_id)
            .single()
            .execute()
        )

    if _optional_columns_available:
        try:
            return _query(
                _PROFILE_COLUMNS + ", " + ", ".join(_OPTIONAL_PROFILE_COLUMNS)
            ).data
        except Exception as e:
            message = str(e).lower()
            # Only treat an unknown-column error as "not migrated yet"; any
            # other failure must surface rather than being silently retried.
            if not any(col in message for col in _OPTIONAL_PROFILE_COLUMNS):
                raise
            _optional_columns_available = False
            _log.warning(
                "auth.profile_optional_columns_missing",
                columns=",".join(_OPTIONAL_PROFILE_COLUMNS),
                hint="run docs/sql/2026-08-16_add_is_test_account.sql",
            )

    return _query(_PROFILE_COLUMNS).data


def get_profile_by_username(username: str):
    """Resolve a display username to its immutable profile row."""
    normalized = str(username or "").strip().casefold()
    response = (
        admin_client.table("profiles")
        .select("*")
        .ilike("username", str(username or "").strip())
        .execute()
    )
    return next(
        (
            row for row in response.data or []
            if str(row.get("username") or "").strip().casefold() == normalized
        ),
        None,
    )


def require_parent(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only users whose profile role is parent.

    Returns both the raw auth user and profile so parent routes can safely scope
    child/family lookups to the signed-in parent.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "parent":
        raise HTTPException(
            status_code=403,
            detail="Parent access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_student(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows student and child profile users.

    Children created by admins (role='child') are functionally students —
    they use the same lesson, quiz, and practice question features.
    Both 'student' and 'child' roles are accepted here.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") not in ("student", "child"):
        raise HTTPException(
            status_code=403,
            detail="Student access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_admin(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only admin profile users.

    Admin-only routes can mutate access, families, plans, and user records, so
    they must use this guard before touching service-role Supabase APIs.

    A denied attempt is logged, since a non-admin reaching an admin route is
    worth seeing. Only the role is recorded — this previously printed the whole
    profile row, email included, on every admin request.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "admin":
        _log.warning("auth.admin_denied", role=(profile or {}).get("role"))
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_teacher(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only teacher profile users.

    Teachers can self-signup via POST /api/auth/teacher-signup, which sets
    account_status="pending_verification" until an admin approves the account
    (see POST /api/admin/support/users/{id}/verify-teacher). This guard blocks
    every teacher-dashboard route until that approval lands, same as the
    account_status gate already used for lesson/doubt/mock-test access.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Teacher access required",
        )

    if profile.get("account_status") not in (None, "active", "trial"):
        raise HTTPException(
            status_code=403,
            detail="Teacher account pending verification",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_teacher_or_admin(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows teacher OR admin profile users.

    Applies the same pending_verification gate as require_teacher() to
    teachers, but also lets admins through unconditionally (admins are never
    gated). Used by the teacher content-generation routes in
    app/routes/teacher.py, which previously used an ad-hoc role check that let
    a pending_verification teacher call them directly and bypass admin
    approval entirely.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") not in ("teacher", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Teacher access required",
        )

    if profile.get("role") == "teacher" and profile.get("account_status") not in (None, "active", "trial"):
        raise HTTPException(
            status_code=403,
            detail="Teacher account pending verification",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_self_by_username(username: str, user=Depends(get_current_user)):
    """
    FastAPI dependency for routes that take a student username in the path.

    Allows the signed-in user to read their own record, and admins/teachers to
    read anyone's. Use this instead of trusting the path segment: these routes
    historically had no auth at all, which let any caller read another
    student's progress, profile, or recommendations by guessing a username.

    analytics.py carries its own near-identical require_self_or_admin_or_teacher
    with the same semantics but a history-specific 403 message; it is left in
    place so its existing tests keep asserting against that wording.
    """
    profile = get_user_profile(user.id)
    role = profile.get("role") if profile else None
    target_profile = get_profile_by_username(username)
    allowed = bool(profile and target_profile and profile.get("id") == target_profile.get("id"))

    if profile and target_profile and role == "admin":
        allowed = True
    elif profile and target_profile and role == "teacher":
        assignment = (
            admin_client.table("teacher_student_assignments")
            .select("student_id")
            .eq("teacher_id", profile.get("id"))
            .eq("student_id", target_profile.get("id"))
            .limit(1)
            .execute()
        )
        allowed = bool(assignment.data)

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this student's record",
        )

    return {"auth_user": user, "profile": profile, "target_profile": target_profile}


def resolve_session_username(user) -> str:
    """
    Return the username of the signed-in user, for routes that used to accept a
    client-supplied username in the request body.

    Writes keyed on a client-supplied username let any caller author records
    into another student's account — the same flaw already closed in
    weak_area_alerts.py. Route handlers call this and ignore the body value.
    """
    profile = get_user_profile(user.id)

    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found")

    username = profile.get("username")

    if not username:
        raise HTTPException(status_code=403, detail="Profile has no username")

    return username


def require_sales(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only sales profile users.

    Sales accounts are admin-created and can only see their own onboarding and
    incentive data.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "sales":
        raise HTTPException(
            status_code=403,
            detail="Sales access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_principal(user=Depends(get_current_user)):
    """
    FastAPI dependency that allows only principal profile users.

    Principals self-signup via POST /api/auth/principal-signup, which creates
    a `schools` row with status="pending_verification" until an admin
    confirms the school is real (see POST /api/admin/schools/{id}/verify).
    This guard blocks every /api/principal/* route until that approval lands
    — same gate require_teacher() already applies to teacher-dashboard
    routes, and for the same reason: don't let an unverified account start
    accumulating school-level incentive credit.

    Every principal route is read-only or link/unlink only against
    individual student/teacher rows — it never creates a login, changes a
    role, or touches subscription/plan state for anyone but the school
    object itself.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") != "principal":
        raise HTTPException(
            status_code=403,
            detail="Principal access required",
        )

    if profile.get("account_status") not in (None, "active", "trial"):
        raise HTTPException(
            status_code=403,
            detail="School account pending verification",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }


def require_admin_or_sales(user=Depends(get_current_user)):
    """
    FastAPI dependency for routes shared by admins and sales users.

    Admins receive the full sales dashboard; salespeople receive data scoped to
    their own profile id.
    """
    profile = get_user_profile(user.id)

    if not profile or profile.get("role") not in {"admin", "sales"}:
        raise HTTPException(
            status_code=403,
            detail="Admin or sales access required",
        )

    return {
        "auth_user": user,
        "profile": profile,
    }
    
def create_auth_user(email: str, password: str, email_confirm: bool = True):
    """
    Create a Supabase auth user using the service-role admin API.

    email_confirm=True  (default) — account is immediately active, no email
                                    sent. Use this for admin-created children,
                                    teachers, and in-person parent onboarding.

    email_confirm=False            — account is created but NOT confirmed; the
                                    user cannot log in. Use this only when you
                                    will immediately follow up with
                                    invite_parent_by_email() to send the real
                                    confirmation email via Supabase.

    NOTE: Supabase admin create_user with email_confirm=False does NOT send
    any email automatically. To send a real invite/confirmation email, use
    invite_parent_by_email() instead.
    """
    try:
        response = admin_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        })

        return response.user

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to create auth user: {str(e)}",
        )


def invite_parent_by_email(email: str, username: str) -> object:
    """
    Create a parent account and send a real invitation email via Supabase.

    Supabase's invite_user_by_email:
    - Creates the auth user in an unconfirmed state
    - Sends an invitation email with a confirmation link
    - The parent clicks the link to verify their email and set their password
    - The account cannot be used until the parent confirms

    This is the correct way to enforce email confirmation for parent signups.
    Use this for all parent-initiated invites and for admin-created parent
    accounts that should require email verification.
    """
    try:
        response = admin_client.auth.admin.invite_user_by_email(
            email,
            options={"data": {"username": username, "role": "parent"}},
        )

        return response.user

    except Exception as e:
        err_msg = str(e).lower()

        if "rate limit" in err_msg or "email_rate_limit" in err_msg or "over_email" in err_msg:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many invitation emails have been sent recently. "
                    "Please wait a few minutes before creating another parent account, "
                    "or use the in-person onboarding option to set a password directly."
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=f"Unable to send parent invitation: {str(e)}",
        )
