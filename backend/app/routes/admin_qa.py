"""
admin_qa.py  —  Admin Platform QA Center endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only endpoints for the Platform QA Center.

Endpoints:
  GET  /api/admin/qa/lesson-quality/latest      — latest completed report summary
  GET  /api/admin/qa/lesson-quality/history     — list of past runs
  POST /api/admin/qa/lesson-quality/run         — start an audit job
  GET  /api/admin/qa/lesson-quality/status/{id} — job status / progress
  GET  /api/admin/qa/lesson-quality/report      — download report (json|md|csv)

Safety:
  - All endpoints require admin role (require_admin dependency)
  - No secrets, API keys, or student PII in responses
  - Errors sanitised before returning to frontend
  - LLM disabled by default
  - Full audit warned and guarded
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client
from app.routes.parent_dashboard_v2 import _safe_query

router = APIRouter()
_log = logging.getLogger("likhapoha.admin_qa")

REPORT_DIR = Path("reports/lesson_quality")
TABLE = "lesson_quality_audit_runs"

# ── In-memory job registry (fallback if DB not yet applied) ───────────────────
_JOBS: dict[str, dict] = {}  # job_id → status dict


# ── Pydantic models ───────────────────────────────────────────────────────────

class AuditRunRequest(BaseModel):
    mode: str = "sample"       # sample | grade | subject | grade_subject | chapter | full
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    use_llm: bool = False
    use_e2e: bool = False
    fail_critical: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_latest_report() -> dict | None:
    """Load the latest lesson quality JSON report from disk."""
    p = REPORT_DIR / "lesson_quality_report.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        _log.error("Failed to read latest report: %s", e)
        return None


def _summarise_report(data: dict) -> dict:
    """Extract a safe, sanitised summary from raw report JSON."""
    lessons = data.get("lessons") or []
    if not lessons:
        return {
            "available": False,
            "audited_at": data.get("audited_at"),
            "lessons_audited": 0,
            "overall_score": None,
            "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0,
            "grade_scores": {}, "subject_scores": {}, "worst_lessons": [], "all_issues": [],
        }

    total_c = sum(r.get("findings_summary", {}).get("critical", 0) for r in lessons)
    total_h = sum(r.get("findings_summary", {}).get("high", 0) for r in lessons)
    total_m = sum(r.get("findings_summary", {}).get("medium", 0) for r in lessons)
    total_l = sum(r.get("findings_summary", {}).get("low", 0) for r in lessons)
    avg_score = round(sum(r["scores"]["overall_score"] for r in lessons) / len(lessons))

    # Grade scores
    from collections import defaultdict
    grade_map: dict = defaultdict(list)
    subj_map:  dict = defaultdict(list)
    for r in lessons:
        grade_map[r.get("grade","?")].append(r["scores"]["overall_score"])
        subj_map[r.get("subject","?")].append(r["scores"]["overall_score"])

    grade_scores = {g: round(sum(v)/len(v)) for g, v in grade_map.items()}
    subject_scores = {s: round(sum(v)/len(v)) for s, v in subj_map.items()}

    # Worst 10 lessons
    worst = sorted(lessons, key=lambda r: r["scores"]["overall_score"])[:10]
    worst_safe = [{
        "grade": r.get("grade"), "subject": r.get("subject"), "chapter": r.get("chapter"),
        "step_count": r.get("step_count"), "overall_score": r["scores"]["overall_score"],
        "critical": r["findings_summary"].get("critical", 0),
        "high": r["findings_summary"].get("high", 0),
    } for r in worst]

    # All issues (sanitised — no raw lesson content)
    all_issues = []
    for r in lessons:
        for f in (r.get("findings") or []):
            all_issues.append({
                "grade": r.get("grade"), "subject": r.get("subject"),
                "chapter": r.get("chapter"), "severity": f.get("severity"),
                "category": f.get("category"), "message": f.get("message"),
                "detail": (f.get("detail") or "")[:200],
            })

    return {
        "available": True,
        "audited_at": data.get("audited_at"),
        "lessons_audited": len(lessons),
        "overall_score": avg_score,
        "critical_count": total_c, "high_count": total_h,
        "medium_count": total_m, "low_count": total_l,
        "grade_scores": grade_scores,
        "subject_scores": subject_scores,
        "worst_lessons": worst_safe,
        "all_issues": all_issues[:500],  # cap to prevent huge response
    }


def _upsert_run(job_id: str, updates: dict, admin_id: str | None = None) -> None:
    """Update run record in DB (graceful fallback to in-memory if DB unavailable)."""
    _JOBS[job_id] = {**_JOBS.get(job_id, {}), **updates}
    try:
        existing, _ = _safe_query(
            lambda: admin_client.table(TABLE).select("id").eq("id", job_id).limit(1).execute()
        )
        if existing:
            admin_client.table(TABLE).update(updates).eq("id", job_id).execute()
        else:
            row = {"id": job_id, **updates}
            if admin_id:
                row["created_by_admin_id"] = admin_id
            admin_client.table(TABLE).insert(row).execute()
    except Exception as e:
        _log.warning("Could not persist run %s to DB: %s", job_id, e)


def _run_audit_background(job_id: str, req: AuditRunRequest, admin_id: str) -> None:
    """Run the audit in a background thread. Updates job status in DB + in-memory."""
    _upsert_run(job_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    try:
        # Import audit functions — reuse existing engine
        from scripts.audit_lesson_quality import (
            _fetch_lessons, _group_by_lesson, audit_lesson,
            _write_json, _write_markdown, _write_csv,
        )

        # Normalise grade
        grade = req.grade
        if grade and not grade.startswith("Grade "):
            grade = "Grade " + grade

        is_sample = req.mode == "sample"
        rows = _fetch_lessons(grade, req.subject, req.chapter, is_sample)
        lessons_grouped = _group_by_lesson(rows)
        results = []
        for key, lesson_rows in lessons_grouped.items():
            result = audit_lesson(key, lesson_rows, use_llm=req.use_llm)
            results.append(result)

        # Write reports
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        _write_json(results, REPORT_DIR)
        _write_markdown(results, REPORT_DIR)
        _write_csv(results, REPORT_DIR)

        total_c = sum(r["critical_count"] for r in results)
        avg_sc  = round(sum(r["scores"]["overall_score"] for r in results) / max(len(results), 1))

        _upsert_run(job_id, {
            "status":           "completed",
            "completed_at":     datetime.now(timezone.utc).isoformat(),
            "overall_score":    avg_sc,
            "critical_count":   total_c,
            "high_count":       sum(r["findings_summary"].get("high",0) for r in results),
            "medium_count":     sum(r["findings_summary"].get("medium",0) for r in results),
            "low_count":        sum(r["findings_summary"].get("low",0) for r in results),
            "lessons_audited":  len(results),
            "report_json_path": str(REPORT_DIR / "lesson_quality_report.json"),
            "report_md_path":   str(REPORT_DIR / "lesson_quality_report.md"),
            "report_csv_path":  str(REPORT_DIR / "lesson_quality_summary.csv"),
        })
        _log.info("Audit job %s completed: %d lessons, score=%d, critical=%d",
                  job_id, len(results), avg_sc, total_c)

    except Exception as e:
        sanitised = str(e)[:500].replace("\n", " ")
        _log.error("Audit job %s failed: %s", job_id, sanitised)
        _upsert_run(job_id, {
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": sanitised,
        })


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/lesson-quality/latest")
def get_latest_lesson_quality_report(admin=Depends(require_admin)):
    """Return summary of the latest lesson quality audit report."""
    data = _read_latest_report()
    if not data:
        return {
            "success": True,
            "available": False,
            "message": "No lesson quality audit has been run yet.",
        }
    summary = _summarise_report(data)
    return {"success": True, **summary}


@router.get("/lesson-quality/history")
def get_lesson_quality_history(
    limit: int = Query(20, le=100),
    admin=Depends(require_admin),
):
    """Return recent audit run history."""
    # Try DB first
    runs, err = _safe_query(
        lambda: admin_client.table(TABLE)
        .select("id, mode, grade, subject, status, overall_score, critical_count, "
                "lessons_audited, started_at, completed_at, created_at, use_llm, error_message")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if err and "schema cache" in str(err).lower():
        # DB table not applied — return in-memory only
        runs = sorted(_JOBS.values(), key=lambda j: j.get("created_at",""), reverse=True)[:limit]

    return {"success": True, "runs": runs or []}


@router.post("/lesson-quality/run")
def run_lesson_quality_audit(
    req: AuditRunRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """Start a lesson quality audit job. Returns job_id immediately."""
    # Validate mode
    valid_modes = {"sample", "grade", "subject", "grade_subject", "chapter", "full"}
    if req.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {sorted(valid_modes)}")

    # Guard: LLM disabled by default
    if req.use_llm:
        _log.info("Admin triggered audit WITH LLM review (job will incur LLM cost)")

    # Guard: E2E not yet configured
    if req.use_e2e:
        return {
            "success": False,
            "message": "Browser E2E journey tests are not configured yet. Run without use_e2e=true.",
        }

    admin_id = admin.get("id") or admin.get("profile", {}).get("id")
    job_id = str(uuid.uuid4())

    # Register job
    now = datetime.now(timezone.utc).isoformat()
    _JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "mode": req.mode,
        "grade": req.grade,
        "subject": req.subject,
        "chapter": req.chapter,
        "use_llm": req.use_llm,
        "use_e2e": req.use_e2e,
        "fail_critical": req.fail_critical,
        "created_at": now,
        "created_by_admin_id": admin_id,
    }
    _upsert_run(job_id, _JOBS[job_id], admin_id)

    # Run in background thread (non-blocking)
    t = threading.Thread(target=_run_audit_background, args=(job_id, req, admin_id), daemon=True)
    t.start()

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Audit job {job_id} started ({req.mode} mode).",
    }


@router.get("/lesson-quality/status/{job_id}")
def get_audit_job_status(job_id: str, admin=Depends(require_admin)):
    """Poll status of an audit job."""
    # Check in-memory first (fastest)
    if job_id in _JOBS:
        job = dict(_JOBS[job_id])
        job.pop("created_by_admin_id", None)  # sanitise
        return {"success": True, "job": job}

    # Fall back to DB
    row, _ = _safe_query(
        lambda: admin_client.table(TABLE)
        .select("id, status, mode, grade, subject, overall_score, critical_count, "
                "lessons_audited, started_at, completed_at, error_message")
        .eq("id", job_id).limit(1).execute()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = row[0] if isinstance(row, list) else row
    return {"success": True, "job": job}


@router.get("/lesson-quality/report")
def download_lesson_quality_report(
    format: str = Query("json", regex="^(json|md|csv)$"),
    admin=Depends(require_admin),
):
    """Download the latest lesson quality report in JSON, Markdown, or CSV."""
    files = {
        "json": REPORT_DIR / "lesson_quality_report.json",
        "md":   REPORT_DIR / "lesson_quality_report.md",
                "csv":  REPORT_DIR / "lesson_quality_summary.csv",
    }
    fp = files.get(format)
    if not fp or not fp.exists():
        raise HTTPException(status_code=404, detail="Report not found. Run an audit first.")
    content_types = {"json": "application/json", "md": "text/markdown", "csv": "text/csv"}
    return PlainTextResponse(
        content=fp.read_text(encoding="utf-8"),
        media_type=content_types[format],
        headers={"Content-Disposition": f"attachment; filename=lesson_quality_report.{format}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Feature Authorization Audit endpoints
# ─────────────────────────────────────────────────────────────────────────────

FEAT_AUTH_REPORT_DIR = Path("reports/feature_authorization")
_FA_JOBS: dict[str, dict] = {}   # in-memory job registry for feature auth jobs


def _run_feat_auth_background(job_id: str, sample: bool, admin_id: str) -> None:
    """Run feature authorization audit in background thread."""
    _FA_JOBS[job_id] = {**_FA_JOBS.get(job_id, {}), "status": "running",
                        "started_at": datetime.now(timezone.utc).isoformat()}
    try:
        from scripts.audit_feature_authorization import run_audit
        FEAT_AUTH_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        summary = run_audit(sample=sample, fail_critical=False, output_json=False)
        _FA_JOBS[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "overall": summary.get("overall"),
            "total": summary.get("total"),
            "passed": summary.get("passed"),
            "failed": summary.get("failed"),
            "critical": summary.get("critical"),
            "pass_rate": summary.get("pass_rate"),
        })
    except Exception as e:
        sanitised = str(e)[:500].replace("\n", " ")
        _log.error("Feature auth audit job %s failed: %s", job_id, sanitised)
        _FA_JOBS[job_id].update({"status": "failed", "error_message": sanitised,
                                  "completed_at": datetime.now(timezone.utc).isoformat()})


def _read_feat_auth_report() -> dict | None:
    p = FEAT_AUTH_REPORT_DIR / "feature_authorization_report.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


@router.get("/feature-authorization/latest")
def get_latest_feat_auth_report(admin=Depends(require_admin)):
    data = _read_feat_auth_report()
    if not data:
        return {"success": True, "available": False,
                "message": "No feature authorization audit has been run yet."}
    summary = data.get("summary", {})
    failed = [c for c in (data.get("failed_checks") or []) if not c.get("passed")][:200]
    return {
        "success": True, "available": True,
        "audited_at": data.get("audited_at"),
        "summary": summary,
        "failed_checks": failed,
    }


@router.get("/feature-authorization/history")
def get_feat_auth_history(limit: int = Query(20, le=100), admin=Depends(require_admin)):
    runs = sorted(_FA_JOBS.values(), key=lambda j: j.get("created_at",""), reverse=True)[:limit]
    return {"success": True, "runs": runs}


@router.post("/feature-authorization/run")
def run_feat_auth_audit(
    mode: str = "sample",
    background_tasks: BackgroundTasks = None,
    admin=Depends(require_admin),
):
    if mode not in ("sample", "full"):
        raise HTTPException(status_code=400, detail="mode must be sample or full")
    admin_id = admin.get("id") or admin.get("profile", {}).get("id")
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _FA_JOBS[job_id] = {"id": job_id, "status": "queued", "mode": mode,
                         "created_at": now, "created_by_admin_id": admin_id}
    t = threading.Thread(target=_run_feat_auth_background,
                         args=(job_id, mode=="sample", admin_id), daemon=True)
    t.start()
    return {"success": True, "job_id": job_id, "message": f"Feature auth audit started ({mode})."}


@router.get("/feature-authorization/status/{job_id}")
def get_feat_auth_status(job_id: str, admin=Depends(require_admin)):
    if job_id not in _FA_JOBS:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = dict(_FA_JOBS[job_id])
    job.pop("created_by_admin_id", None)
    return {"success": True, "job": job}


@router.get("/feature-authorization/report")
def download_feat_auth_report(
    format: str = Query("json", regex="^(json|md|csv)$"),
    admin=Depends(require_admin),
):
    files = {
        "json": FEAT_AUTH_REPORT_DIR / "feature_authorization_report.json",
        "md":   FEAT_AUTH_REPORT_DIR / "feature_authorization_report.md",
        "csv":  FEAT_AUTH_REPORT_DIR / "feature_authorization_summary.csv",
    }
    fp = files.get(format)
    if not fp or not fp.exists():
        raise HTTPException(status_code=404, detail="Report not found. Run an audit first.")
    ct = {"json": "application/json", "md": "text/markdown", "csv": "text/csv"}
    return PlainTextResponse(
        content=fp.read_text(encoding="utf-8"), media_type=ct[format],
        headers={"Content-Disposition": f"attachment; filename=feature_authorization_report.{format}"},
    )
