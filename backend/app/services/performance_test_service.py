from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.auth_service import admin_client
from app.services.performance_scenarios import (
    PERFORMANCE_TOKEN_SETUP_MESSAGE,
    VALIDATORS,
    ScenarioDefinition,
    ScenarioRequest,
    TimingResult,
    auth_headers,
    classify_performance,
    get_scenario,
    load_test_users,
    next_profile_factory,
    summarize_results,
)


RUNS_TABLE = "performance_test_runs"
DEFAULT_BASE_URL = (
    os.getenv("PERFORMANCE_TEST_BASE_URL")
    or os.getenv("BACKEND_BASE_URL")
    or "http://localhost:8000"
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("PERFORMANCE_TEST_TIMEOUT_SECONDS", "90"))
MAX_RESULTS_RETURNED = int(os.getenv("PERFORMANCE_TEST_RESULT_LIMIT", "200"))


def _now_iso() -> str:
    """Return an ISO timestamp suitable for Supabase timestamptz fields."""
    return datetime.now(timezone.utc).isoformat()


def _safe_json(value: Any) -> Any:
    """Convert nested values into JSON-safe primitives."""
    return json.loads(json.dumps(value, default=str))


def _insert_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a performance run row and return the stored record."""
    response = admin_client.table(RUNS_TABLE).insert(payload).execute()
    return response.data[0]


def _update_run(run_id: str, payload: dict[str, Any]) -> None:
    """Update a performance run row by id."""
    admin_client.table(RUNS_TABLE).update(payload).eq("id", run_id).execute()


def get_performance_run(run_id: str) -> dict[str, Any] | None:
    """Load one persisted performance run."""
    response = (
        admin_client
        .table(RUNS_TABLE)
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def list_performance_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent persisted performance runs for trend display."""
    safe_limit = max(1, min(int(limit or 20), 100))
    response = (
        admin_client
        .table(RUNS_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )
    return response.data or []


def create_performance_run(
    *,
    test_type: str,
    concurrency: int,
    duration_seconds: int,
    started_by: str | None,
) -> dict[str, Any]:
    """Create a queued performance run with bounded admin-controlled settings."""
    scenario = get_scenario(test_type)
    safe_concurrency = max(1, min(int(concurrency or 1), scenario.safe_max_concurrency))
    safe_duration = max(5, min(int(duration_seconds or 30), 120))

    return _insert_run(
        {
            "test_type": scenario.key,
            "status": "queued",
            "concurrency": safe_concurrency,
            "duration_seconds": safe_duration,
            "started_by": started_by,
            "classification": "Queued",
            "summary": {
                "scenario": scenario.label,
                "target_p95_ms": scenario.target_p95_ms,
                "uses_ai": scenario.uses_ai,
                "safe_max_concurrency": scenario.safe_max_concurrency,
            },
            "results": [],
        }
    )


def _requests_for_worker(
    scenario: ScenarioDefinition,
    profile: dict[str, Any],
    worker_index: int,
) -> list[ScenarioRequest]:
    """Choose the request list each simulated user should execute."""
    requests = scenario.request_builder(profile)
    if scenario.key != "ai_burst_5" or not requests:
        return requests

    pattern = [requests[0], requests[0], requests[1], requests[1], requests[2]]
    selected = pattern[worker_index % len(pattern)]
    return [replace(selected, name=f"{selected.name}-{worker_index + 1}")]


def _request_body(request_def: ScenarioRequest) -> bytes | None:
    """Serialize a JSON request body when the scenario needs one."""
    if request_def.json is None:
        return None
    return json.dumps(request_def.json).encode("utf-8")


def _execute_request(
    *,
    base_url: str,
    request_def: ScenarioRequest,
    profile: dict[str, Any],
) -> TimingResult:
    """Execute one shared scenario request and validate its response."""
    params = f"?{urlencode(request_def.params)}" if request_def.params else ""
    url = f"{base_url}{request_def.path}{params}"
    headers = {"Accept": "application/json"}
    body = _request_body(request_def)
    if body is not None:
        headers["Content-Type"] = "application/json"

    if request_def.requires_auth:
        auth = auth_headers(profile)
        if not auth:
            if not request_def.uses_ai:
                return TimingResult(
                    name=request_def.name,
                    method=request_def.method,
                    path=request_def.path,
                    ok=True,
                    elapsed_ms=0,
                    error=f"Skipped: {PERFORMANCE_TOKEN_SETUP_MESSAGE}",
                    skipped=True,
                    validation={"skip_reason": "missing_performance_test_token"},
                )
            return TimingResult(
                name=request_def.name,
                method=request_def.method,
                path=request_def.path,
                ok=False,
                elapsed_ms=0,
                status_code=401,
                error=f"Missing backend performance-test auth. {PERFORMANCE_TOKEN_SETUP_MESSAGE}",
            )
        headers.update(auth)

    start = time.perf_counter()
    try:
        http_request = Request(
            url,
            data=body,
            headers=headers,
            method=request_def.method.upper(),
        )
        with urlopen(http_request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw_body = response.read()
            elapsed_ms = (time.perf_counter() - start) * 1000
            status_code = response.status
            payload = None
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None

            validation = VALIDATORS[request_def.validator_name](payload)
            return TimingResult(
                name=request_def.name,
                method=request_def.method,
                path=request_def.path,
                ok=200 <= status_code < 400 and validation.ok,
                elapsed_ms=round(elapsed_ms, 2),
                status_code=status_code,
                response_length=len(raw_body),
                error="" if validation.ok else validation.error,
                validation=validation.metrics,
            )
    except HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            error_text = exc.read().decode("utf-8")[:500]
        except Exception:
            error_text = str(exc)
        return TimingResult(
            name=request_def.name,
            method=request_def.method,
            path=request_def.path,
            ok=False,
            elapsed_ms=round(elapsed_ms, 2),
            status_code=exc.code,
            error=error_text or str(exc),
        )
    except (TimeoutError, URLError, OSError) as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return TimingResult(
            name=request_def.name,
            method=request_def.method,
            path=request_def.path,
            ok=False,
            elapsed_ms=round(elapsed_ms, 2),
            error=str(exc),
        )


def _execute_worker(
    *,
    base_url: str,
    scenario: ScenarioDefinition,
    profile: dict[str, Any],
    worker_index: int,
) -> list[TimingResult]:
    """Run one simulated user's sequence of scenario requests."""
    return [
        _execute_request(base_url=base_url, request_def=request_def, profile=profile)
        for request_def in _requests_for_worker(scenario, profile, worker_index)
    ]


def run_performance_test_job(run_id: str) -> None:
    """Background job that executes and persists one performance test run."""
    run = get_performance_run(run_id)
    if not run:
        return

    try:
        scenario = get_scenario(run["test_type"])
        concurrency = max(1, min(int(run.get("concurrency") or 1), scenario.safe_max_concurrency))
        base_url = DEFAULT_BASE_URL
        users = load_test_users()
        next_profile = next_profile_factory(users)

        _update_run(
            run_id,
            {
                "status": "running",
                "classification": "Running",
                "started_at": _now_iso(),
                "summary": {
                    **(run.get("summary") or {}),
                    "base_url": base_url,
                    "has_test_tokens": bool(users),
                },
            },
        )

        started = time.perf_counter()
        results: list[TimingResult] = []
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(
                    _execute_worker,
                    base_url=base_url,
                    scenario=scenario,
                    profile=next_profile(),
                    worker_index=index,
                )
                for index in range(concurrency)
            ]
            for future in as_completed(futures):
                results.extend(future.result())

        wall_time_ms = (time.perf_counter() - started) * 1000
        result_rows = [result.to_dict() for result in results]
        measured_rows = [row for row in result_rows if not row.get("skipped")]
        summary = summarize_results(result_rows, scenario.target_p95_ms)
        summary.update(
            {
                "scenario": scenario.label,
                "test_type": scenario.key,
                "base_url": base_url,
                "concurrency": concurrency,
                "duration_seconds": run.get("duration_seconds"),
                "wall_time_ms": round(wall_time_ms, 2),
                "avg_request_ms": round(
                    sum(row["elapsed_ms"] for row in measured_rows) / len(measured_rows),
                    2,
                ) if measured_rows else 0,
                "uses_ai": scenario.uses_ai,
            }
        )
        classification = classify_performance(summary, uses_ai=scenario.uses_ai)

        _update_run(
            run_id,
            {
                "status": "completed",
                "classification": classification,
                "finished_at": _now_iso(),
                "summary": _safe_json(summary),
                "results": _safe_json(result_rows[:MAX_RESULTS_RETURNED]),
                "error_message": "",
            },
        )
    except Exception as exc:
        _update_run(
            run_id,
            {
                "status": "failed",
                "classification": "Critical",
                "finished_at": _now_iso(),
                "error_message": str(exc),
            },
        )
