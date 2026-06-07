from __future__ import annotations

import json
import os
import statistics
from dataclasses import asdict, dataclass, field
from itertools import cycle
from pathlib import Path
from typing import Any, Callable

from supabase import create_client


DEFAULT_GRADE = "Grade 9"
DEFAULT_BOARD = "CBSE"
DEFAULT_MODE = "CBSE"
DEFAULT_SUBJECT = "Science"
DEFAULT_CHAPTER = "Atoms and Molecules"
DEFAULT_USERNAME = "loadtest_student"

LESSON_MIN_CHARS = 500
DOUBT_MIN_CHARS = 500
MOCK_TEST_MIN_QUESTIONS = 3

TEST_USERS_FILE = Path(
    os.getenv(
        "PERFORMANCE_TEST_USERS_FILE",
        os.getenv("TEST_USERS_FILE", "tests/performance/test_users.json"),
    )
)

PERFORMANCE_TOKEN_SETUP_MESSAGE = (
    "Configure PERFORMANCE_TEST_EMAIL/PERFORMANCE_TEST_PASSWORD, "
    "PERFORMANCE_TEST_BEARER_TOKEN, or tests/performance/test_users.json."
)


def _resolve_test_users_file(path: Path | None = None) -> Path:
    """Resolve the test-user file from backend cwd, repo cwd, or an absolute path."""
    file_path = path or TEST_USERS_FILE
    if file_path.is_absolute() or file_path.exists():
        return file_path

    backend_root = Path(__file__).resolve().parents[2]
    backend_candidate = backend_root / file_path
    if backend_candidate.exists():
        return backend_candidate

    repo_candidate = backend_root.parent / file_path
    if repo_candidate.exists():
        return repo_candidate

    return file_path


def _first_env(*names: str) -> str:
    """Return the first non-empty environment value from the provided aliases."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _test_profile_defaults(username: str | None = None) -> dict[str, Any]:
    """Build default test-profile metadata without any secret fields."""
    return {
        "username": username
        or _first_env("PERFORMANCE_TEST_USERNAME", "TEST_USER_USERNAME")
        or DEFAULT_USERNAME,
        "grade": _first_env("PERFORMANCE_TEST_GRADE", "TEST_USER_GRADE")
        or DEFAULT_GRADE,
        "board": _first_env("PERFORMANCE_TEST_BOARD", "TEST_USER_BOARD")
        or DEFAULT_BOARD,
        "mode": _first_env("PERFORMANCE_TEST_MODE", "TEST_USER_MODE") or DEFAULT_MODE,
        "subject": _first_env("PERFORMANCE_TEST_SUBJECT", "TEST_USER_SUBJECT")
        or DEFAULT_SUBJECT,
        "chapter": _first_env("PERFORMANCE_TEST_CHAPTER", "TEST_USER_CHAPTER")
        or DEFAULT_CHAPTER,
    }


def _session_access_token(auth_response: Any) -> str:
    """Extract a Supabase access token from object or dict auth responses."""
    session = getattr(auth_response, "session", None)
    token = getattr(session, "access_token", None)
    if token:
        return token

    if isinstance(auth_response, dict):
        session = auth_response.get("session") or {}
        if isinstance(session, dict):
            return session.get("access_token", "")

    return ""


def _login_test_user_from_env() -> dict[str, Any] | None:
    """
    Sign in the configured test student and return a fresh token profile.

    This keeps long-lived access tokens out of the frontend and avoids stale
    bearer tokens during repeated admin performance runs.
    """
    email = _first_env(
        "PERFORMANCE_TEST_EMAIL",
        "PERFORMANCE_TEST_USER_EMAIL",
        "TEST_USER_EMAIL",
    )
    password = _first_env(
        "PERFORMANCE_TEST_PASSWORD",
        "PERFORMANCE_TEST_USER_PASSWORD",
        "TEST_USER_PASSWORD",
    )
    if not email and not password:
        return None
    if not email or not password:
        raise RuntimeError(
            "Both PERFORMANCE_TEST_EMAIL and PERFORMANCE_TEST_PASSWORD are required.",
        )

    supabase_url = _first_env("SUPABASE_URL")
    supabase_key = _first_env(
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "VITE_SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    )
    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Supabase URL/key missing for performance-test student login.",
        )

    client = create_client(supabase_url, supabase_key)
    auth_response = client.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )
    token = _session_access_token(auth_response)
    if not token:
        raise RuntimeError("Performance-test student login did not return a token.")

    username = _first_env("PERFORMANCE_TEST_USERNAME", "TEST_USER_USERNAME")
    if not username:
        username = email.split("@", 1)[0]

    return {
        **_test_profile_defaults(username),
        "email": email,
        "access_token": token,
    }


def _token_test_user_from_env() -> dict[str, Any] | None:
    """Return a static-token performance user when one is explicitly configured."""
    env_token = _first_env("PERFORMANCE_TEST_BEARER_TOKEN", "TEST_USER_ACCESS_TOKEN")
    if not env_token:
        return None

    return {
        **_test_profile_defaults(),
        "access_token": env_token,
    }


@dataclass(frozen=True)
class ValidationResult:
    """Validation outcome for one performance response payload."""

    ok: bool
    error: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioRequest:
    """One HTTP request definition shared by Locust and admin test runs."""

    name: str
    method: str
    path: str
    params: dict[str, Any] | None = None
    json: dict[str, Any] | None = None
    requires_auth: bool = False
    uses_ai: bool = False
    validator_name: str = "success"


@dataclass(frozen=True)
class ScenarioDefinition:
    """Performance scenario metadata and factory for request definitions."""

    key: str
    label: str
    description: str
    request_builder: Callable[[dict], list[ScenarioRequest]]
    target_p95_ms: int
    safe_max_concurrency: int
    uses_ai: bool = False


@dataclass
class TimingResult:
    """Serializable timing result for one HTTP request execution."""

    name: str
    method: str
    path: str
    ok: bool
    elapsed_ms: float
    status_code: int | None = None
    response_length: int = 0
    error: str = ""
    validation: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe timing result."""
        return asdict(self)


def load_test_users(path: Path | None = None) -> list[dict]:
    """Load backend-only test user profiles and bearer tokens for protected APIs."""
    file_path = _resolve_test_users_file(path)
    if not file_path.exists():
        env_login_user = _login_test_user_from_env()
        if env_login_user:
            return [env_login_user]

        env_token_user = _token_test_user_from_env()
        return [env_token_user] if env_token_user else []

    data = json.loads(file_path.read_text(encoding="utf-8"))
    users = data.get("users", data if isinstance(data, list) else [])
    return [user for user in users if user.get("username")]


def auth_headers(profile: dict) -> dict:
    """Build auth headers from a backend-only test profile token."""
    token = profile.get("access_token") or profile.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def profile_payload(profile: dict | None = None) -> dict:
    """Build the common lesson/doubt/mock payload scope for a test profile."""
    profile = profile or {}
    return {
        "username": profile.get("username", DEFAULT_USERNAME),
        "grade": profile.get("grade", DEFAULT_GRADE),
        "board": profile.get("board", DEFAULT_BOARD),
        "mode": profile.get("mode", DEFAULT_MODE),
        "subject": profile.get("subject", DEFAULT_SUBJECT),
        "chapter": profile.get("chapter", DEFAULT_CHAPTER),
    }


def progress_payload(profile: dict | None = None) -> dict:
    """Build a harmless progress save payload used by browsing baselines."""
    base = profile_payload(profile)
    return {
        **base,
        "current_step_index": 1,
        "highest_unlocked_step": 1,
        "completed": False,
        "last_lesson": "Performance test progress marker.",
        "step_lessons": {},
    }


def lesson_payload(profile: dict | None = None) -> dict:
    """Build the AI lesson payload reused by Locust and admin tests."""
    return {
        **profile_payload(profile),
        "step_title": "Concept overview",
        "teacher_persona": "Explain simply for a school student.",
    }


def doubt_payload(profile: dict | None = None) -> dict:
    """Build the AI doubt payload reused by Locust and admin tests."""
    return {
        **profile_payload(profile),
        "question": "Explain the difference between atoms and molecules with one example.",
        "display_question": "Atoms vs molecules",
        "save_to_history": False,
    }


def mock_test_payload(profile: dict | None = None) -> dict:
    """Build a small mock-test payload reused by Locust and admin tests."""
    return {
        **profile_payload(profile),
        "mock_type": "Chapter Practice",
        "difficulty": "Easy",
        "question_count": 5,
        "exam_type": "CBSE",
    }


def validate_success_payload(payload: Any) -> ValidationResult:
    """Validate a generic API response payload."""
    if isinstance(payload, dict) and payload.get("success") is False:
        return ValidationResult(False, payload.get("message") or "success=false")
    return ValidationResult(True)


def validate_lesson_response(payload: Any) -> ValidationResult:
    """Validate that lesson generation returned meaningful lesson text."""
    text = payload.get("lesson") if isinstance(payload, dict) else None
    length = len(text.strip()) if isinstance(text, str) else 0
    if length < LESSON_MIN_CHARS:
        return ValidationResult(
            False,
            f"lesson response below {LESSON_MIN_CHARS} chars",
            {"chars": length},
        )
    return ValidationResult(True, metrics={"chars": length})


def validate_doubt_response(payload: Any) -> ValidationResult:
    """Validate that doubt answering returned meaningful answer text."""
    text = payload.get("answer") if isinstance(payload, dict) else None
    length = len(text.strip()) if isinstance(text, str) else 0
    if length < DOUBT_MIN_CHARS:
        return ValidationResult(
            False,
            f"doubt response below {DOUBT_MIN_CHARS} chars",
            {"chars": length},
        )
    return ValidationResult(True, metrics={"chars": length})


def validate_mock_test_response(payload: Any) -> ValidationResult:
    """Validate that mock-test generation returned enough questions."""
    questions = payload.get("questions") if isinstance(payload, dict) else None
    count = len(questions) if isinstance(questions, list) else 0
    if count < MOCK_TEST_MIN_QUESTIONS:
        return ValidationResult(
            False,
            f"mock test below {MOCK_TEST_MIN_QUESTIONS} questions",
            {"questions": count},
        )
    return ValidationResult(True, metrics={"questions": count})


VALIDATORS = {
    "success": validate_success_payload,
    "lesson": validate_lesson_response,
    "doubt": validate_doubt_response,
    "mock_test": validate_mock_test_response,
}


def public_read_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the public read endpoint set used by browsing tests."""
    base = profile_payload(profile)
    return [
        ScenarioRequest("health", "GET", "/api/health"),
        ScenarioRequest("syllabus", "GET", "/api/syllabus"),
        ScenarioRequest(
            "resources",
            "GET",
            "/api/resources",
            params={
                "grade": base["grade"],
                "subject": base["subject"],
                "chapter": base["chapter"],
            },
        ),
        ScenarioRequest("leaderboard", "GET", "/api/analytics/leaderboard"),
    ]


def student_progress_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return protected progress endpoints used by student browsing tests."""
    username = profile_payload(profile)["username"]
    return [
        ScenarioRequest(
            "progress:user",
            "GET",
            f"/api/progress/user/{username}",
            requires_auth=True,
        ),
        ScenarioRequest(
            "analytics:history",
            "GET",
            f"/api/analytics/test-history/{username}",
            requires_auth=True,
        ),
        ScenarioRequest(
            "progress:save",
            "POST",
            "/api/progress/save",
            json=progress_payload(profile),
            requires_auth=True,
        ),
    ]


def lesson_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the single lesson-generation request definition."""
    return [
        ScenarioRequest(
            "ai:lesson",
            "POST",
            "/api/lesson/generate",
            json=lesson_payload(profile),
            requires_auth=True,
            uses_ai=True,
            validator_name="lesson",
        )
    ]


def doubt_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the single doubt-answer request definition."""
    return [
        ScenarioRequest(
            "ai:doubt",
            "POST",
            "/api/doubt/answer",
            json=doubt_payload(profile),
            requires_auth=True,
            uses_ai=True,
            validator_name="doubt",
        )
    ]


def mock_test_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the single mock-test generation request definition."""
    return [
        ScenarioRequest(
            "ai:mock-test",
            "POST",
            "/api/mock-test/generate",
            json=mock_test_payload(profile),
            requires_auth=True,
            uses_ai=True,
            validator_name="mock_test",
        )
    ]


def browsing_baseline_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the same browsing endpoint set covered by StudentBrowsingUser."""
    return public_read_requests(profile) + student_progress_requests(profile)


def mixed_student_journey_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the same mixed journey shape covered by StudentMixedUser."""
    return (
        public_read_requests(profile)
        + student_progress_requests(profile)
        + lesson_requests(profile)
        + doubt_requests(profile)
    )


def ai_burst_requests(profile: dict | None = None) -> list[ScenarioRequest]:
    """Return the AI endpoint set covered by StudentAIHeavyUser."""
    return lesson_requests(profile) + doubt_requests(profile) + mock_test_requests(profile)


SCENARIOS = {
    "browsing_baseline": ScenarioDefinition(
        key="browsing_baseline",
        label="Browsing Baseline",
        description="Read-heavy student browsing, progress, and save endpoints.",
        request_builder=browsing_baseline_requests,
        target_p95_ms=1000,
        safe_max_concurrency=10,
    ),
    "mixed_student_journey": ScenarioDefinition(
        key="mixed_student_journey",
        label="Mixed Student Journey",
        description="Browsing plus lesson and doubt generation.",
        request_builder=mixed_student_journey_requests,
        target_p95_ms=45000,
        safe_max_concurrency=3,
        uses_ai=True,
    ),
    "single_lesson": ScenarioDefinition(
        key="single_lesson",
        label="Single Lesson",
        description="One AI lesson generation request.",
        request_builder=lesson_requests,
        target_p95_ms=35000,
        safe_max_concurrency=3,
        uses_ai=True,
    ),
    "single_doubt": ScenarioDefinition(
        key="single_doubt",
        label="Single Doubt",
        description="One AI doubt-answer request.",
        request_builder=doubt_requests,
        target_p95_ms=45000,
        safe_max_concurrency=3,
        uses_ai=True,
    ),
    "single_mock_test": ScenarioDefinition(
        key="single_mock_test",
        label="Single Mock Test",
        description="One small mock-test generation request.",
        request_builder=mock_test_requests,
        target_p95_ms=15000,
        safe_max_concurrency=2,
        uses_ai=True,
    ),
    "ai_burst_5": ScenarioDefinition(
        key="ai_burst_5",
        label="AI Burst 5",
        description="Small AI burst using lesson, doubt, and mock-test requests.",
        request_builder=ai_burst_requests,
        target_p95_ms=45000,
        safe_max_concurrency=5,
        uses_ai=True,
    ),
}


def get_scenario(key: str) -> ScenarioDefinition:
    """Return a scenario definition or raise a helpful error for unknown keys."""
    if key not in SCENARIOS:
        raise ValueError(f"Unknown performance test type: {key}")
    return SCENARIOS[key]


def scenario_options() -> list[dict[str, Any]]:
    """Return JSON-safe scenario metadata for admin UI selectors."""
    return [
        {
            "key": scenario.key,
            "label": scenario.label,
            "description": scenario.description,
            "target_p95_ms": scenario.target_p95_ms,
            "safe_max_concurrency": scenario.safe_max_concurrency,
            "uses_ai": scenario.uses_ai,
        }
        for scenario in SCENARIOS.values()
    ]


def _percentile(values: list[float], percentile: int) -> float:
    """Return a simple nearest-rank percentile from a list of values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * len(ordered)) - 1))
    return float(ordered[index])


def summarize_results(
    results: list[dict[str, Any]] | list[TimingResult],
    target_p95_ms: int,
) -> dict[str, Any]:
    """Compute timing and reliability summary for a run."""
    rows = [
        result.to_dict() if isinstance(result, TimingResult) else result
        for result in results
    ]
    skipped = [row for row in rows if row.get("skipped")]
    measured_rows = [row for row in rows if not row.get("skipped")]
    elapsed = [float(row.get("elapsed_ms") or 0) for row in measured_rows]
    failures = [row for row in measured_rows if not row.get("ok")]
    success_count = len(measured_rows) - len(failures)
    error_rate = (len(failures) / len(measured_rows) * 100) if measured_rows else 0.0
    p50 = statistics.median(elapsed) if elapsed else 0.0
    p95 = _percentile(elapsed, 95)
    max_ms = max(elapsed) if elapsed else 0.0

    return {
        "target_p95_ms": target_p95_ms,
        "request_count": len(rows),
        "measured_count": len(measured_rows),
        "skipped_count": len(skipped),
        "skipped_requests": skipped,
        "success_count": success_count,
        "failure_count": len(failures),
        "error_rate": round(error_rate, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(max_ms, 2),
        "ai_failures": [
            row for row in failures
            if str(row.get("name", "")).startswith("ai:")
        ],
        "auth_failures": [
            row for row in failures
            if row.get("status_code") in {401, 403}
        ],
        "server_failures": [
            row for row in failures
            if int(row.get("status_code") or 0) >= 500
        ],
    }


def classify_performance(
    summary: dict[str, Any],
    *,
    uses_ai: bool = False,
) -> str:
    """Classify a run as Good, Warning, Degrading, or Critical."""
    p95 = float(summary.get("p95_ms") or 0)
    target = float(summary.get("target_p95_ms") or 1)
    error_rate = float(summary.get("error_rate") or 0)
    max_ms = float(summary.get("max_ms") or 0)

    if (
        summary.get("auth_failures")
        or summary.get("server_failures")
        or (uses_ai and summary.get("ai_failures"))
        or max_ms > target * 2
    ):
        return "Critical"

    if p95 <= target and error_rate < 1:
        return "Good"

    if p95 <= target * 1.25 or 1 <= error_rate <= 3:
        return "Warning"

    return "Degrading"


def next_profile_factory(users: list[dict]):
    """Return a rotating profile supplier shared by local runners."""
    user_cycle = cycle(users) if users else None

    def _next_profile() -> dict:
        if user_cycle:
            return next(user_cycle)
        return profile_payload({})

    return _next_profile
