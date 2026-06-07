from app.services.performance_scenarios import (
    TimingResult,
    classify_performance,
    scenario_options,
    summarize_results,
    validate_doubt_response,
    validate_lesson_response,
    validate_mock_test_response,
)


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
