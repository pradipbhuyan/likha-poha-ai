from app.services.performance_scenarios import (
    TimingResult,
    classify_performance,
    load_test_users,
    scenario_options,
    summarize_results,
    validate_doubt_response,
    validate_lesson_response,
    validate_mock_test_response,
)


class _FakeSession:
    access_token = "fresh-supabase-token"


class _FakeAuthResponse:
    session = _FakeSession()


class _FakeAuth:
    def __init__(self):
        self.payload = None

    def sign_in_with_password(self, payload):
        self.payload = payload
        return _FakeAuthResponse()


class _FakeSupabaseClient:
    def __init__(self):
        self.auth = _FakeAuth()


def test_ai_validators_accept_meaningful_payloads():
    assert validate_lesson_response({"lesson": "A" * 501}).ok
    assert validate_doubt_response({"answer": "B" * 501}).ok
    assert validate_mock_test_response({"questions": [{}, {}, {}]}).ok


def test_ai_validators_reject_weak_payloads():
    assert not validate_lesson_response({"lesson": "short"}).ok
    assert not validate_doubt_response({"answer": "short"}).ok
    assert not validate_mock_test_response({"questions": [{}]}).ok


def test_summary_and_good_classification():
    rows = [
        TimingResult("health", "GET", "/api/health", True, 100).to_dict(),
        TimingResult("resources", "GET", "/api/resources", True, 200).to_dict(),
    ]

    summary = summarize_results(rows, 1000)

    assert summary["success_count"] == 2
    assert summary["failure_count"] == 0
    assert classify_performance(summary) == "Good"


def test_summary_skips_config_missing_probes():
    rows = [
        TimingResult("health", "GET", "/api/health", True, 100).to_dict(),
        TimingResult(
            "progress:user",
            "GET",
            "/api/progress/user/loadtest_student",
            True,
            0,
            error="Skipped: configure PERFORMANCE_TEST_BEARER_TOKEN.",
            skipped=True,
        ).to_dict(),
    ]

    summary = summarize_results(rows, 1000)

    assert summary["request_count"] == 2
    assert summary["measured_count"] == 1
    assert summary["skipped_count"] == 1
    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0
    assert summary["error_rate"] == 0
    assert classify_performance(summary) == "Good"


def test_critical_classification_for_ai_failure():
    summary = summarize_results(
        [
            TimingResult(
                "ai:lesson",
                "POST",
                "/api/lesson/generate",
                False,
                100,
                error="validation failed",
            ).to_dict()
        ],
        35000,
    )

    assert classify_performance(summary, uses_ai=True) == "Critical"


def test_scenario_options_include_admin_test_types():
    keys = {item["key"] for item in scenario_options()}

    assert {
        "browsing_baseline",
        "single_lesson",
        "single_doubt",
        "single_mock_test",
        "ai_burst_5",
    }.issubset(keys)


def test_load_test_users_signs_in_with_env_credentials(monkeypatch, tmp_path):
    fake_client = _FakeSupabaseClient()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "anon-key")
    monkeypatch.setenv("PERFORMANCE_TEST_EMAIL", "akshita.teststudent@example.com")
    monkeypatch.setenv("PERFORMANCE_TEST_PASSWORD", "secret")
    monkeypatch.setenv("PERFORMANCE_TEST_USERNAME", "akshita.teststudent")
    monkeypatch.setenv("PERFORMANCE_TEST_GRADE", "Grade 9")
    monkeypatch.setenv("PERFORMANCE_TEST_SUBJECT", "Maths")
    monkeypatch.delenv("PERFORMANCE_TEST_USER_EMAIL", raising=False)
    monkeypatch.delenv("PERFORMANCE_TEST_USER_PASSWORD", raising=False)
    monkeypatch.delenv("TEST_USER_EMAIL", raising=False)
    monkeypatch.delenv("TEST_USER_PASSWORD", raising=False)
    monkeypatch.delenv("PERFORMANCE_TEST_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TEST_USER_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        "app.services.performance_scenarios.create_client",
        lambda *_args, **_kwargs: fake_client,
    )

    users = load_test_users(tmp_path / "missing-test-users.json")

    assert users == [
        {
            "username": "akshita.teststudent",
            "grade": "Grade 9",
            "board": "CBSE",
            "mode": "CBSE",
            "subject": "Maths",
            "chapter": "Atoms and Molecules",
            "email": "akshita.teststudent@example.com",
            "access_token": "fresh-supabase-token",
        }
    ]
    assert fake_client.auth.payload == {
        "email": "akshita.teststudent@example.com",
        "password": "secret",
    }


def test_load_test_users_uses_static_token_when_no_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("PERFORMANCE_TEST_EMAIL", raising=False)
    monkeypatch.delenv("PERFORMANCE_TEST_PASSWORD", raising=False)
    monkeypatch.delenv("PERFORMANCE_TEST_USER_EMAIL", raising=False)
    monkeypatch.delenv("PERFORMANCE_TEST_USER_PASSWORD", raising=False)
    monkeypatch.delenv("TEST_USER_EMAIL", raising=False)
    monkeypatch.delenv("TEST_USER_PASSWORD", raising=False)
    monkeypatch.setenv("PERFORMANCE_TEST_BEARER_TOKEN", "static-token")
    monkeypatch.setenv("PERFORMANCE_TEST_USERNAME", "akshita.teststudent")

    users = load_test_users(tmp_path / "missing-test-users.json")

    assert users[0]["username"] == "akshita.teststudent"
    assert users[0]["access_token"] == "static-token"
