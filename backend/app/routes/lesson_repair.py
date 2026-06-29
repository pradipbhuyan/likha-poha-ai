"""
lesson_repair.py — Admin Lesson Repair endpoints
─────────────────────────────────────────────────────────────────────────────
Admin-only REST API for the Lesson Repair workflow.

All endpoints require admin role (require_admin).
No secrets, raw provider errors, API keys, or student PII in responses.

Endpoints:
  GET  /api/admin/qa/lesson-repair/latest
  GET  /api/admin/qa/lesson-repair/history
  POST /api/admin/qa/lesson-repair/run
  GET  /api/admin/qa/lesson-repair/status/{job_id}
  GET  /api/admin/qa/lesson-repair/tasks/{job_id}
  GET  /api/admin/qa/lesson-repair/task/{task_id}
  POST /api/admin/qa/lesson-repair/task/{task_id}/approve
  POST /api/admin/qa/lesson-repair/task/{task_id}/publish
  POST /api/admin/qa/lesson-repair/task/{task_id}/rerun
  POST /api/admin/qa/lesson-repair/job/{job_id}/cancel
  GET  /api/admin/qa/lesson-repair/report
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import csv
import io
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.services.auth_service import require_admin
from app.services.lesson_repair_service import (
    _db_get_job,
    _db_get_task,
    _db_get_tasks,
    _db_insert_job,
    _db_list_jobs,
    _db_update_job,
    _db_update_task,
    load_latest_audit_report,
    publish_repaired_task,
    run_llm_repair,
    run_repair_job,
    validate_repaired_draft,
)

router = APIRouter()
_log = logging.getLogger("likhapoha.lesson_repair_routes")

# ── In-memory registries (fallback when DB table not applied) ──────────────────
_REPAIR_JOBS: dict[str, dict] = {}
_REPAIR_TASKS: dict[str, dict] = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

# ── Per-lesson token estimates for cost projection ────────────────────────────
# Based on a typical repair prompt: ~1600 input tokens, ~2500 output tokens.
_REPAIR_TOKEN_ESTIMATES = {
    "input_tokens_per_lesson": 1600,
    "output_tokens_per_lesson": 2500,
}

# Pricing per 1K tokens (input, output) by model — subset of openai_service pricing
_REPAIR_MODEL_PRICING = {
    "gpt-4.1-nano":              {"input": 0.0001,   "output": 0.0004,  "label": "GPT-4.1 Nano",   "free_tier": False},
    "gpt-4.1-mini":              {"input": 0.0004,   "output": 0.0016,  "label": "GPT-4.1 Mini",   "free_tier": False},
    "gpt-4.1":                   {"input": 0.002,    "output": 0.008,   "label": "GPT-4.1",        "free_tier": False},
    "llama-3.3-70b-versatile":   {"input": 0.00059,  "output": 0.00079, "label": "Llama 3.3 70B (Groq)", "free_tier": True},
    "gemini-2.5-flash":          {"input": 0.000075, "output": 0.0003,  "label": "Gemini 2.5 Flash", "free_tier": True},
    "gpt-oss-120b":              {"input": 0.00059,  "output": 0.00079, "label": "GPT-OSS 120B (Cerebras)", "free_tier": True},
    "zai-glm-4.7":               {"input": 0.00005,  "output": 0.00008, "label": "ZAI GLM 4.7 (Cerebras)", "free_tier": True},
    "llama-3.3-70b":             {"input": 0.0003,   "output": 0.0007,  "label": "Llama 3.3 70B (Venice)", "free_tier": False},
    "Meta-Llama-3.3-70B-Instruct":{"input": 0.0006,  "output": 0.0012,  "label": "Llama 3.3 70B (SambaNova)", "free_tier": True},
}

_PROVIDER_DISPLAY_NAMES = {
    "openai":    "OpenAI",
    "groq":      "Groq",
    "cerebras":  "Cerebras",
    "gemini":    "Google Gemini",
    "sambanova": "SambaNova",
    "venice":    "Venice AI",
}


def _compute_cost_per_lesson(model: str) -> float:
    """Compute estimated USD cost per lesson repair based on token estimates."""
    pricing = _REPAIR_MODEL_PRICING.get(model)
    if not pricing:
        # Default fallback
        pricing = {"input": 0.0001, "output": 0.0004}
    inp = (_REPAIR_TOKEN_ESTIMATES["input_tokens_per_lesson"] / 1000) * pricing["input"]
    out = (_REPAIR_TOKEN_ESTIMATES["output_tokens_per_lesson"] / 1000) * pricing["output"]
    return round(inp + out, 6)


class RepairRunRequest(BaseModel):
    mode: str = "sample"          # sample | filtered | all
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    use_llm: bool = False
    # Session-only API key override — used for this repair job only.
    # NEVER logged, NEVER stored in DB.
    override_api_key: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_job(job_id: str) -> dict:
    """Get job from in-memory or DB. Raises 404 if not found."""
    job = _REPAIR_JOBS.get(job_id) or _db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Repair job not found.")
    return job


def _get_task(task_id: str) -> dict:
    """Get task from in-memory or DB. Raises 404 if not found."""
    task = _REPAIR_TASKS.get(task_id) or _db_get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Repair task not found.")
    return task


def _safe_job(job: dict) -> dict:
    """Strip sensitive fields from job before returning to frontend."""
    safe = {k: v for k, v in job.items() if k not in ("requested_by_admin_id",)}
    # Truncate large JSON blobs for list views
    safe.pop("report_json", None)
    return safe


def _safe_task(task: dict) -> dict:
    """Return task with all fields except any that could leak secrets."""
    return task  # tasks contain no secret material; safe as-is


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/lesson-repair/llm-info")
def get_repair_llm_info(admin=Depends(require_admin)):
    """
    Return the currently configured LLM provider, model, and cost estimates
    for lesson repair. Used by the admin UI to show before running repairs.

    Never exposes API keys — only provider name, model name, and cost figures.
    """
    from app.services.openai_service import get_effective_settings  # noqa: PLC0415

    settings = get_effective_settings()
    provider = settings.get("provider", "openai")

    # Determine active model based on provider
    model_map = {
        "openai":    settings.get("api_key") and "gpt-4.1-nano",  # default model
        "groq":      settings.get("groq_model") or "llama-3.3-70b-versatile",
        "cerebras":  settings.get("cerebras_model") or "gpt-oss-120b",
        "gemini":    settings.get("gemini_model") or "gemini-2.5-flash",
        "sambanova": settings.get("sambanova_model") or "Meta-Llama-3.3-70B-Instruct",
        "venice":    settings.get("venice_model") or "llama-3.3-70b",
    }
    model = model_map.get(provider) or "gpt-4.1-nano"
    if provider == "openai":
        model = "gpt-4.1-nano"  # default OpenAI model for repair

    pricing = _REPAIR_MODEL_PRICING.get(model, {"input": 0.0001, "output": 0.0004, "free_tier": False})
    cost_per_lesson = _compute_cost_per_lesson(model)
    provider_name = _PROVIDER_DISPLAY_NAMES.get(provider, provider.title())

    # Check if a key is configured (boolean only — never expose key value)
    has_key = bool(
        (provider == "openai" and settings.get("api_key")) or
        (provider == "groq" and settings.get("groq_api_key")) or
        (provider == "cerebras" and settings.get("cerebras_api_key")) or
        (provider == "gemini" and settings.get("gemini_api_key")) or
        (provider == "sambanova" and settings.get("sambanova_api_key")) or
        (provider == "venice" and settings.get("venice_api_key"))
    )

    return {
        "success": True,
        "provider": provider,
        "provider_name": provider_name,
        "model": model,
        "model_label": pricing.get("label", model),
        "free_tier_available": pricing.get("free_tier", False),
        "api_key_configured": has_key,
        "cost_per_lesson_usd": cost_per_lesson,
        "cost_10_lessons_usd": round(cost_per_lesson * 10, 4),
        "cost_50_lessons_usd": round(cost_per_lesson * 50, 4),
        "cost_100_lessons_usd": round(cost_per_lesson * 100, 4),
        "token_estimates": _REPAIR_TOKEN_ESTIMATES,
        "note": (
            "Free tier available — costs may be $0 within quota." if pricing.get("free_tier")
            else f"Paid API — estimated ${cost_per_lesson:.4f} per lesson."
        ),
    }


@router.get("/lesson-repair/latest")
def get_latest_repair_status(admin=Depends(require_admin)):
    """
    Return the latest repair job summary and the most recent audit report metadata.
    """
    # Most recent job
    all_jobs = sorted(
        list(_REPAIR_JOBS.values()) + (_db_list_jobs(1) or []),
        key=lambda j: j.get("created_at", ""),
        reverse=True,
    )
    # Deduplicate by id
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        jid = j.get("id")
        if jid and jid not in seen:
            seen.add(jid)
            unique_jobs.append(j)

    latest_job = _safe_job(unique_jobs[0]) if unique_jobs else None

    # Audit report metadata
    report = load_latest_audit_report()
    report_meta = None
    if report:
        summary = report.get("summary", {})
        report_meta = {
            "audited_at": report.get("audited_at"),
            "lessons_audited": summary.get("lessons_audited", 0),
            "critical_issues": summary.get("critical_issues", 0),
            "avg_overall_score": summary.get("avg_overall_score"),
            "overall": summary.get("overall"),
        }

    return {
        "success": True,
        "latest_job": latest_job,
        "audit_report_meta": report_meta,
    }


@router.get("/lesson-repair/history")
def get_repair_history(
    limit: int = Query(20, le=100),
    admin=Depends(require_admin),
):
    """Return recent repair job history."""
    db_jobs = _db_list_jobs(limit) or []
    mem_jobs = list(_REPAIR_JOBS.values())
    all_jobs = sorted(
        db_jobs + mem_jobs,
        key=lambda j: j.get("created_at", ""),
        reverse=True,
    )[:limit]
    seen = set()
    unique = []
    for j in all_jobs:
        jid = j.get("id")
        if jid and jid not in seen:
            seen.add(jid)
            unique.append(_safe_job(j))
    return {"success": True, "jobs": unique}


@router.post("/lesson-repair/run")
def run_repair(
    req: RepairRunRequest,
    admin=Depends(require_admin),
):
    """
    Start a lesson repair job. Returns job_id immediately; repair runs in background.

    mode: sample (10 random failures) | filtered (by grade/subject/chapter) | all
    use_llm: if True, LLM is called to generate repaired content.
             COSTS MONEY — admin must explicitly enable.
    """
    valid_modes = {"sample", "filtered", "all"}
    if req.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {sorted(valid_modes)}")

    # Validate audit report exists before queuing
    report = load_latest_audit_report()
    if not report:
        raise HTTPException(
            status_code=422,
            detail="No lesson_sections audit report found. "
                   "Run the lesson sections audit first (QA Center → Lesson Sections).",
        )

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "id": job_id,
        "requested_by_admin_id": admin_id,
        "status": "queued",
        "mode": req.mode,
        "grade": req.grade,
        "subject": req.subject,
        "chapter": req.chapter,
        "use_llm": req.use_llm,
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "approved_tasks": 0,
        "published_tasks": 0,
        "created_at": now,
        "updated_at": now,
    }

    _REPAIR_JOBS[job_id] = job
    _db_insert_job(job)

    # Run in background thread
    # override_api_key is passed in memory only — never stored in DB
    t = threading.Thread(
        target=run_repair_job,
        kwargs={
            "job_id": job_id,
            "admin_id": admin_id,
            "mode": req.mode,
            "use_llm": req.use_llm,
            "grade": req.grade,
            "subject": req.subject,
            "chapter": req.chapter,
            "override_api_key": req.override_api_key,
            "in_memory_jobs": _REPAIR_JOBS,
            "in_memory_tasks": _REPAIR_TASKS,
        },
        daemon=True,
    )
    t.start()

    llm_note = " LLM repair enabled — this will incur AI token costs." if req.use_llm else ""
    return {
        "success": True,
        "job_id": job_id,
        "message": f"Repair job {job_id} started ({req.mode} mode).{llm_note}",
    }


@router.get("/lesson-repair/status/{job_id}")
def get_repair_status(job_id: str, admin=Depends(require_admin)):
    """Poll the status of a repair job."""
    job = _get_job(job_id)
    return {"success": True, "job": _safe_job(job)}


@router.get("/lesson-repair/tasks/{job_id}")
def get_repair_tasks(
    job_id: str,
    status: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    admin=Depends(require_admin),
):
    """List all repair tasks for a job with optional filters."""
    _get_job(job_id)  # validate job exists

    # Collect from in-memory + DB
    mem_tasks = [t for t in _REPAIR_TASKS.values() if t.get("job_id") == job_id]
    db_tasks = _db_get_tasks(job_id, status=status)

    all_tasks = sorted(
        mem_tasks + db_tasks,
        key=lambda t: t.get("created_at", ""),
    )
    seen = set()
    unique = []
    for t in all_tasks:
        tid = t.get("id")
        if tid and tid not in seen:
            seen.add(tid)
            if status and t.get("status") != status:
                continue
            if grade and t.get("grade") != grade:
                continue
            if subject and t.get("subject", "").lower() != (subject or "").lower():
                continue
            unique.append(_safe_task(t))

    return {"success": True, "tasks": unique[:limit], "total": len(unique)}


@router.get("/lesson-repair/task/{task_id}")
def get_repair_task(task_id: str, admin=Depends(require_admin)):
    """Get full detail of a single repair task including before/after content."""
    task = _get_task(task_id)
    return {"success": True, "task": _safe_task(task)}


@router.post("/lesson-repair/task/{task_id}/approve")
def approve_repair_task(task_id: str, admin=Depends(require_admin)):
    """
    Approve a repaired task draft for publishing.
    Task must be in 'ready_for_review' status.
    """
    task = _get_task(task_id)
    if task.get("status") not in ("ready_for_review",):
        raise HTTPException(
            status_code=422,
            detail=f"Task must be in 'ready_for_review' status to approve. Current: {task.get('status')}",
        )

    if not task.get("repaired_content_json"):
        raise HTTPException(
            status_code=422,
            detail="No repaired content to approve. Task requires LLM repair first.",
        )

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    updates = {
        "status": "approved",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if task_id in _REPAIR_TASKS:
        _REPAIR_TASKS[task_id].update(updates)
    _db_update_task(task_id, updates)

    # Increment approved_tasks counter on job
    job_id = task.get("job_id")
    if job_id:
        job = _REPAIR_JOBS.get(job_id) or {}
        new_approved = (job.get("approved_tasks") or 0) + 1
        job_updates = {"approved_tasks": new_approved}
        if job_id in _REPAIR_JOBS:
            _REPAIR_JOBS[job_id].update(job_updates)
        _db_update_job(job_id, job_updates)

    _log.info("Task %s approved by admin %s", task_id, admin_id)
    return {"success": True, "message": "Task approved. Use /publish to write to lesson_cache."}


@router.post("/lesson-repair/task/{task_id}/publish")
def publish_repair_task(task_id: str, admin=Depends(require_admin)):
    """
    Publish an approved task — writes repaired content back to lesson_cache.
    Task must be in 'approved' status.
    Preserves original_content_json for rollback.
    """
    task = _get_task(task_id)

    result = publish_repaired_task(task)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["message"])

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    updates = {
        "status": "published",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if task_id in _REPAIR_TASKS:
        _REPAIR_TASKS[task_id].update(updates)
    _db_update_task(task_id, updates)

    # Increment published_tasks on job
    job_id = task.get("job_id")
    if job_id:
        job = _REPAIR_JOBS.get(job_id) or {}
        new_pub = (job.get("published_tasks") or 0) + 1
        job_updates = {"published_tasks": new_pub}
        if job_id in _REPAIR_JOBS:
            _REPAIR_JOBS[job_id].update(job_updates)
        _db_update_job(job_id, job_updates)

    _log.info("Task %s published by admin %s", task_id, admin_id)
    return {"success": True, "message": result["message"]}


@router.post("/lesson-repair/task/{task_id}/rerun")
def rerun_repair_task(task_id: str, admin=Depends(require_admin)):
    """
    Re-run LLM repair for a single task that failed or had validation errors.
    """
    task = _get_task(task_id)
    if task.get("status") not in ("failed", "validation_failed"):
        raise HTTPException(
            status_code=422,
            detail=f"Only 'failed' or 'validation_failed' tasks can be re-run. Current: {task.get('status')}",
        )

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"

    # Re-run LLM in background
    def _rerun():
        issues_data = task.get("issues_json") or []
        lesson_stub = {
            "grade": task.get("grade", ""),
            "subject": task.get("subject", ""),
            "chapter": task.get("chapter", ""),
            "step_title": task.get("step_title", ""),
            "all_issues": issues_data,
        }
        upd = {"status": "running", "updated_at": datetime.now(timezone.utc).isoformat()}
        if task_id in _REPAIR_TASKS:
            _REPAIR_TASKS[task_id].update(upd)
        _db_update_task(task_id, upd)

        result = run_llm_repair(lesson_stub, admin_username=f"admin:{admin_id}")
        if not result["success"]:
            fail_upd = {"status": "failed", "error_message": result["error"],
                        "updated_at": datetime.now(timezone.utc).isoformat()}
            if task_id in _REPAIR_TASKS:
                _REPAIR_TASKS[task_id].update(fail_upd)
            _db_update_task(task_id, fail_upd)
            return

        draft = result["draft"]
        validation = validate_repaired_draft(draft)
        new_status = "ready_for_review" if validation["valid"] else "validation_failed"
        ok_upd = {
            "status": new_status,
            "repaired_content_json": draft,
            "validation_result_json": validation,
            "audit_after_score": validation.get("overall_score", 0),
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if task_id in _REPAIR_TASKS:
            _REPAIR_TASKS[task_id].update(ok_upd)
        _db_update_task(task_id, ok_upd)

    threading.Thread(target=_rerun, daemon=True).start()
    return {"success": True, "message": "Re-run started. Poll /task/{task_id} for status."}


@router.post("/lesson-repair/job/{job_id}/cancel")
def cancel_repair_job(job_id: str, admin=Depends(require_admin)):
    """Cancel a queued or running repair job."""
    job = _get_job(job_id)
    if job.get("status") not in ("queued", "running"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot cancel job in '{job.get('status')}' state.",
        )
    updates = {
        "status": "cancelled",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if job_id in _REPAIR_JOBS:
        _REPAIR_JOBS[job_id].update(updates)
    _db_update_job(job_id, updates)
    return {"success": True, "message": f"Job {job_id} cancelled."}


@router.get("/lesson-repair/report")
def download_repair_report(
    job_id: Optional[str] = Query(None),
    format: str = Query("json", pattern="^(json|csv|md)$"),
    admin=Depends(require_admin),
):
    """Download a repair job report in JSON, CSV, or Markdown."""
    # Get tasks for the job (or latest job if no job_id given)
    if not job_id:
        all_jobs = sorted(
            list(_REPAIR_JOBS.values()) + (_db_list_jobs(1) or []),
            key=lambda j: j.get("created_at", ""),
            reverse=True,
        )
        if not all_jobs:
            raise HTTPException(status_code=404, detail="No repair jobs found.")
        job_id = all_jobs[0]["id"]

    job = _get_job(job_id)
    tasks = _db_get_tasks(job_id) or [
        t for t in _REPAIR_TASKS.values() if t.get("job_id") == job_id
    ]

    if format == "json":
        payload = {"job": _safe_job(job), "tasks": tasks}
        return PlainTextResponse(
            json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=repair_report_{job_id[:8]}.json"},
        )

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "grade", "subject", "chapter", "step_title",
            "status", "audit_before_score", "audit_after_score", "error_message",
        ])
        writer.writeheader()
        for t in tasks:
            writer.writerow({
                "id": t.get("id", ""),
                "grade": t.get("grade", ""),
                "subject": t.get("subject", ""),
                "chapter": t.get("chapter", ""),
                "step_title": t.get("step_title", ""),
                "status": t.get("status", ""),
                "audit_before_score": t.get("audit_before_score", ""),
                "audit_after_score": t.get("audit_after_score", ""),
                "error_message": (t.get("error_message") or "")[:200],
            })
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=repair_report_{job_id[:8]}.csv"},
        )

    # Markdown
    lines = [
        f"# Lesson Repair Report\n",
        f"**Job:** {job_id}  ",
        f"**Mode:** {job.get('mode')}  ",
        f"**Status:** {job.get('status')}  ",
        f"**Tasks:** {job.get('total_tasks', 0)} total, "
        f"{job.get('completed_tasks', 0)} repaired, "
        f"{job.get('failed_tasks', 0)} failed, "
        f"{job.get('published_tasks', 0)} published\n",
        "---\n",
    ]
    for t in tasks:
        lines.append(
            f"## {t.get('grade')} | {t.get('subject')} | {t.get('chapter')} | {t.get('step_title')}\n"
            f"- **Status:** {t.get('status')}\n"
            f"- **Before score:** {t.get('audit_before_score', 'N/A')}\n"
            f"- **After score:** {t.get('audit_after_score', 'N/A')}\n"
        )
        if t.get("error_message"):
            lines.append(f"- **Error:** {t.get('error_message', '')[:200]}\n")
        lines.append("")

    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=repair_report_{job_id[:8]}.md"},
    )
