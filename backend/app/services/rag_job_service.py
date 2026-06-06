import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from app.services.auth_service import admin_client


RAG_JOB_WORKERS = max(1, int(os.getenv("RAG_JOB_WORKERS", "2")))
_executor = ThreadPoolExecutor(max_workers=RAG_JOB_WORKERS)


def clamp_percent(value: int) -> int:
    """Keep persisted progress percentages inside the UI-safe 0-100 range."""
    return max(0, min(100, int(value)))


def create_rag_job(
    *,
    job_type: str,
    filename: str = "",
    file_size: int = 0,
    created_by: str | None = None,
    message: str = "",
) -> dict[str, Any]:
    """Create a durable progress row before background RAG work starts."""
    response = (
        admin_client
        .table("rag_upload_jobs")
        .insert({
            "job_type": job_type,
            "status": "queued",
            "phase": "queued",
            "filename": filename or "",
            "file_size": file_size or 0,
            "percent": 0,
            "message": message or "Waiting for a worker.",
            "created_by": created_by,
        })
        .execute()
    )

    return response.data[0]


def update_rag_job(job_id: str, **fields) -> dict[str, Any] | None:
    """Patch a RAG job row with progress, result, or failure details."""
    if "percent" in fields:
        fields["percent"] = clamp_percent(fields["percent"])

    response = (
        admin_client
        .table("rag_upload_jobs")
        .update(fields)
        .eq("id", job_id)
        .execute()
    )

    return response.data[0] if response.data else None


def get_rag_job(job_id: str) -> dict[str, Any] | None:
    """Return one RAG job row for frontend polling."""
    response = (
        admin_client
        .table("rag_upload_jobs")
        .select("*")
        .eq("id", job_id)
        .execute()
    )

    return response.data[0] if response.data else None


def list_recent_rag_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent RAG jobs so admins can track parallel batches."""
    response = (
        admin_client
        .table("rag_upload_jobs")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def submit_rag_job(worker: Callable[..., None], *args, **kwargs):
    """Run one RAG job in the shared worker pool."""
    return _executor.submit(worker, *args, **kwargs)
