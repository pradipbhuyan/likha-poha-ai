from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.auth_service import require_admin
from app.services.performance_scenarios import scenario_options
from app.services.performance_test_service import (
    create_performance_run,
    get_performance_run,
    list_performance_runs,
    run_performance_test_job,
)


router = APIRouter()


class CreatePerformanceRunRequest(BaseModel):
    """Admin-selected settings for one bounded performance test run."""

    test_type: str
    concurrency: int = Field(default=1, ge=1, le=10)
    duration_seconds: int = Field(default=30, ge=5, le=120)


@router.get("/scenarios")
def get_performance_scenarios(_admin=Depends(require_admin)):
    """Return safe admin-selectable performance test scenarios."""
    return {"scenarios": scenario_options()}


@router.post("/runs")
def start_performance_run(
    payload: CreatePerformanceRunRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """Queue a performance run and execute it in a backend background task."""
    try:
        run = create_performance_run(
            test_type=payload.test_type,
            concurrency=payload.concurrency,
            duration_seconds=payload.duration_seconds,
            started_by=admin["profile"].get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to create performance run: {exc}",
        ) from exc

    background_tasks.add_task(run_performance_test_job, run["id"])
    return {"run": run}


@router.get("/runs")
def get_performance_runs(
    limit: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_admin),
):
    """Return recent persisted performance runs for admin trend review."""
    return {"runs": list_performance_runs(limit)}


@router.get("/runs/{run_id}")
def get_performance_run_by_id(run_id: str, _admin=Depends(require_admin)):
    """Return one persisted performance run including detailed timings."""
    run = get_performance_run(run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail="Performance test run not found",
        )
    return {"run": run}
