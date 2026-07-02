"""
learning_simulation.py — Admin Learning Simulation endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only endpoints for the Student Learning Simulation feature.
All routes require admin authentication.

Endpoints:
  GET  /api/admin/simulation/learning/status
  POST /api/admin/simulation/learning/run
  POST /api/admin/simulation/learning/reset
  GET  /api/admin/simulation/learning/runs
  GET  /api/admin/simulation/learning/runs/{run_id}
  GET  /api/admin/simulation/learning/anomalies
  POST /api/admin/simulation/learning/anomalies/{anomaly_id}/create-bug
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_admin
from app.services.student_learning_simulation_service import (
    get_simulation_status,
    setup_simulation_users,
    run_simulation,
    reset_simulation_data,
    get_run_detail,
    get_anomalies,
    _create_product_bug,
    SIM_USERS,
)

router = APIRouter()


class RunSimulationRequest(BaseModel):
    cycle_days:         int  = 7
    dry_run:            bool = False
    create_bugs:        bool = True
    strict_validation:  bool = True


# ── POST /setup ───────────────────────────────────────────────────────────────

@router.post("/api/admin/simulation/learning/setup")
def setup_users_endpoint(admin=Depends(require_admin)):
    """
    Idempotently create Vijay, Manish, Manisha simulation users.
    Safe to call multiple times — won't duplicate users.
    Run this BEFORE running a simulation to ensure users exist in Supabase.
    """
    try:
        result = setup_simulation_users(dry_run=False)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


# ── GET /status ───────────────────────────────────────────────────────────────

@router.get("/api/admin/simulation/learning/status")
def simulation_status(admin=Depends(require_admin)):
    """Return current simulation status, user setup, and recent runs."""
    try:
        status = get_simulation_status()
        # Add vijay/manish profile ids for dashboard links
        vijay  = admin_client.table("profiles").select("id,username,subscription_plan,access_cbse").eq(
            "email", SIM_USERS["vijay"]["email"]
        ).limit(1).execute()
        manish = admin_client.table("profiles").select("id,username").eq(
            "email", SIM_USERS["manish"]["email"]
        ).limit(1).execute()
        status["vijay_profile"]  = vijay.data[0]  if vijay.data  else None
        status["manish_profile"] = manish.data[0] if manish.data else None
        return {"success": True, **status}
    except Exception as e:
        return {"success": False, "error": str(e)[:200], "current_day": 0}


# ── POST /run ─────────────────────────────────────────────────────────────────

@router.post("/api/admin/simulation/learning/run")
def run_simulation_endpoint(
    body: RunSimulationRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Trigger a new learning simulation cycle.
    Runs synchronously and returns the full summary.
    For large cycles use background_tasks.
    """
    admin_id = admin["auth_user"].id

    try:
        summary = run_simulation(
            cycle_days       = body.cycle_days,
            dry_run          = body.dry_run,
            create_bugs      = body.create_bugs,
            strict_validation = body.strict_validation,
            admin_id         = admin_id,
        )
        return {"success": True, **summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)[:300]}")


# ── POST /reset ───────────────────────────────────────────────────────────────

@router.post("/api/admin/simulation/learning/reset")
def reset_simulation_endpoint(admin=Depends(require_admin)):
    """Reset all synthetic simulation data. Does NOT delete real users."""
    admin_id = admin["auth_user"].id
    try:
        result = reset_simulation_data(admin_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ── GET /runs ─────────────────────────────────────────────────────────────────

@router.get("/api/admin/simulation/learning/runs")
def list_runs(
    limit:  int = Query(20, le=100),
    offset: int = Query(0),
    admin=Depends(require_admin),
):
    """List all learning simulation runs, most recent first."""
    try:
        r = (admin_client.table("learning_simulation_runs")
             .select("*")
             .order("created_at", desc=True)
             .range(offset, offset + limit - 1)
             .execute())
        return {"success": True, "runs": r.data or [], "total": len(r.data or [])}
    except Exception as e:
        return {"success": False, "runs": [], "error": str(e)[:200]}


# ── GET /runs/{run_id} ────────────────────────────────────────────────────────

@router.get("/api/admin/simulation/learning/runs/{run_id}")
def get_run(run_id: str, admin=Depends(require_admin)):
    """Get full detail for a specific simulation run including events and anomalies."""
    try:
        detail = get_run_detail(run_id)
        if "error" in detail:
            raise HTTPException(status_code=404, detail=detail["error"])
        return {"success": True, **detail}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ── GET /anomalies ────────────────────────────────────────────────────────────

@router.get("/api/admin/simulation/learning/anomalies")
def list_anomalies(
    run_id: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """List anomalies, optionally filtered by run_id."""
    try:
        anomalies = get_anomalies(run_id=run_id)
        return {"success": True, "anomalies": anomalies, "total": len(anomalies)}
    except Exception as e:
        return {"success": False, "anomalies": [], "error": str(e)[:200]}


# ── POST /anomalies/{anomaly_id}/create-bug ───────────────────────────────────

@router.post("/api/admin/simulation/learning/anomalies/{anomaly_id}/create-bug")
def create_bug_for_anomaly(anomaly_id: str, admin=Depends(require_admin)):
    """Manually create a Product Bug report for a specific simulation anomaly."""
    admin_id = admin["auth_user"].id
    try:
        # Get anomaly
        r = (admin_client.table("learning_simulation_anomalies")
             .select("*").eq("id", anomaly_id).limit(1).execute())
        if not r.data:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        anomaly = r.data[0]

        if anomaly.get("product_issue_id"):
            return {"success": True, "message": "Bug already created",
                    "product_issue_id": anomaly["product_issue_id"]}

        import json as _json
        context = {}
        try:
            context = _json.loads(anomaly.get("context_json") or "{}")
        except Exception:
            pass

        bug_id = _create_product_bug(
            anomaly_id = anomaly_id,
            run_id     = anomaly.get("run_id", ""),
            severity   = anomaly.get("severity", "medium"),
            message    = anomaly.get("message", ""),
            context    = context,
            admin_id   = admin_id,
        )
        if bug_id:
            return {"success": True, "product_issue_id": bug_id}
        return {"success": False, "message": "Could not create bug — check product_issue_reports table"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
