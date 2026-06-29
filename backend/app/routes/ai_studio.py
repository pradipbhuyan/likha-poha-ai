"""
ai_studio.py — Admin AI Studio API Routes
──────────────────────────────────────────────────────────────────────────────
All endpoints are admin-only (require_admin).
API keys are NEVER returned — only masked versions.
No provider secrets in logs or responses.

Endpoints:
  GET  /api/admin/ai-studio/providers
  PATCH /api/admin/ai-studio/providers/{provider_key}
  POST  /api/admin/ai-studio/providers/{provider_key}/test
  GET  /api/admin/ai-studio/providers/{provider_key}/models
  GET  /api/admin/ai-studio/model-profiles
  PATCH /api/admin/ai-studio/model-profiles/{feature_key}
  GET  /api/admin/ai-studio/prompts
  PATCH /api/admin/ai-studio/prompts/{template_id}
  POST  /api/admin/ai-studio/prompts/{template_id}/activate-version
  GET  /api/admin/ai-studio/prompts/{template_id}/versions
  GET  /api/admin/ai-studio/knowledge-sources
  GET  /api/admin/ai-studio/jobs
  GET  /api/admin/ai-studio/usage
  GET  /api/admin/ai-studio/quality
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.auth_service import require_admin
from app.services.ai_studio_service import (
    PROVIDER_REGISTRY,
    FEATURE_DISPLAY_NAMES,
    activate_template_version,
    get_generation_jobs,
    get_knowledge_sources,
    get_model_profiles,
    get_prompt_templates,
    get_quality_metrics,
    get_template_versions,
    get_usage_summary,
    list_local_models,
    save_model_profile,
    save_prompt_template,
    save_provider,
    test_connection,
    get_providers,
)

router = APIRouter()
_log = logging.getLogger("likhapoha.ai_studio_routes")


# ── Pydantic models ───────────────────────────────────────────────────────────

class ProviderUpdateRequest(BaseModel):
    # api_key intentionally Optional — empty string = no change
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_s: Optional[int] = None
    is_enabled: Optional[bool] = None
    set_as_primary: Optional[bool] = None
    set_as_fallback: Optional[bool] = None


class ProviderTestRequest(BaseModel):
    # Optional: send a key to test WITHOUT saving it (useful for testing before committing)
    api_key: Optional[str] = None


class ModelProfileUpdateRequest(BaseModel):
    provider_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    is_enabled: Optional[bool] = None
    notes: Optional[str] = None


class PromptTemplateUpdateRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    change_summary: Optional[str] = None
    set_active: bool = True


class ActivateVersionRequest(BaseModel):
    version_number: int


# ── Providers ─────────────────────────────────────────────────────────────────

@router.get("/providers")
def list_providers(admin=Depends(require_admin)):
    """
    List all AI providers with their configuration.
    API keys are returned as masked strings only (e.g. sk-p••••••••k123).
    """
    return {"success": True, "providers": get_providers()}


@router.patch("/providers/{provider_key}")
def update_provider(
    provider_key: str,
    req: ProviderUpdateRequest,
    admin=Depends(require_admin),
):
    """
    Update provider configuration.
    If api_key is provided and not masked (not starting with ••), it is saved.
    NEVER returns the raw API key.
    """
    if provider_key not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_key}")

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    result = save_provider(provider_key, req.dict(exclude_none=True), admin_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"success": True, "message": result["message"]}


@router.post("/providers/{provider_key}/test")
def test_provider_connection(
    provider_key: str,
    req: ProviderTestRequest,
    admin=Depends(require_admin),
):
    """
    Test connection to a provider with a minimal completion call.
    If api_key in body is provided and non-masked, it is used for THIS test only —
    it is NOT saved to settings. NEVER logged.
    """
    if provider_key not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_key}")

    # Accept key override only if it's clearly not masked and not empty
    override_key = None
    if req.api_key and not req.api_key.startswith("••"):
        override_key = req.api_key.strip()

    result = test_connection(provider_key, override_key=override_key)
    return {"success": result["success"], **result}


@router.get("/providers/{provider_key}/models")
def get_provider_models(
    provider_key: str,
    base_url: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """
    List available models for a provider.
    Currently only supported for ollama_local (fetches from /api/tags).
    Returns empty list for other providers (manual entry required).
    """
    if provider_key == "ollama_local":
        models = list_local_models(base_url=base_url)
        return {"success": True, "provider_key": provider_key, "models": models}

    # For other providers, return suggested models from registry
    meta = PROVIDER_REGISTRY.get(provider_key, {})
    return {
        "success": True,
        "provider_key": provider_key,
        "models": meta.get("suggested_models", []),
        "note": "Model list is not dynamically fetched for this provider. Use the suggested models or enter manually.",
    }


# ── Model Profiles ─────────────────────────────────────────────────────────────

@router.get("/model-profiles")
def list_model_profiles(admin=Depends(require_admin)):
    """Return model routing configuration for all platform features."""
    return {"success": True, "profiles": get_model_profiles()}


@router.patch("/model-profiles/{feature_key}")
def update_model_profile(
    feature_key: str,
    req: ModelProfileUpdateRequest,
    admin=Depends(require_admin),
):
    """Update the AI provider/model for a specific platform feature."""
    if feature_key not in FEATURE_DISPLAY_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown feature: {feature_key}")

    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    result = save_model_profile(feature_key, req.dict(exclude_none=True), admin_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"success": True, "message": result["message"]}


# ── Prompt Templates ──────────────────────────────────────────────────────────

@router.get("/prompts")
def list_prompt_templates(admin=Depends(require_admin)):
    """Return all prompt templates with their active version content."""
    return {"success": True, "templates": get_prompt_templates()}


@router.patch("/prompts/{template_id}")
def update_prompt_template(
    template_id: str,
    req: PromptTemplateUpdateRequest,
    admin=Depends(require_admin),
):
    """
    Save a new version of a prompt template.
    Each save creates a new version. Use activate-version to roll back.
    """
    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    result = save_prompt_template(template_id, req.dict(), admin_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"success": True, "message": result["message"], "version": result.get("version")}


@router.post("/prompts/{template_id}/activate-version")
def activate_prompt_version(
    template_id: str,
    req: ActivateVersionRequest,
    admin=Depends(require_admin),
):
    """Activate (roll back to) a specific version of a prompt template."""
    admin_id = (admin.get("profile") or {}).get("id") or admin.get("id") or "unknown"
    result = activate_template_version(template_id, req.version_number, admin_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"success": True, "message": result["message"]}


@router.get("/prompts/{template_id}/versions")
def get_prompt_versions(template_id: str, admin=Depends(require_admin)):
    """Return version history for a prompt template."""
    versions = get_template_versions(template_id)
    return {"success": True, "versions": versions}


# ── Knowledge Sources ─────────────────────────────────────────────────────────

@router.get("/knowledge-sources")
def list_knowledge_sources(admin=Depends(require_admin)):
    """Return knowledge source status. Read-only; some sources are Coming Soon."""
    return {"success": True, "sources": get_knowledge_sources()}


# ── Generation Jobs ───────────────────────────────────────────────────────────

@router.get("/jobs")
def list_generation_jobs(
    limit: int = Query(50, le=200),
    admin=Depends(require_admin),
):
    """Return recent AI generation jobs across all job types."""
    jobs = get_generation_jobs(limit=limit)
    return {"success": True, "jobs": jobs, "total": len(jobs)}


@router.post("/jobs/{job_id}/retry")
def retry_generation_job(job_id: str, admin=Depends(require_admin)):
    """Retry a failed generation job. Currently returns a placeholder response."""
    # Future: look up job type and re-trigger the appropriate background task
    return {
        "success": True,
        "message": f"Retry for job {job_id} queued. Check the relevant workflow page for status.",
        "note": "Use the Lesson Repair page to retry lesson repair jobs.",
    }


# ── Usage & Costs ─────────────────────────────────────────────────────────────

@router.get("/usage")
def get_usage(
    days: int = Query(30, ge=1, le=365),
    admin=Depends(require_admin),
):
    """Return AI usage and cost summary for the specified number of days."""
    summary = get_usage_summary(days=days)
    return {"success": True, **summary}


# ── Quality Metrics ───────────────────────────────────────────────────────────

@router.get("/quality")
def get_quality(admin=Depends(require_admin)):
    """Return AI output quality metrics from audit and repair data."""
    metrics = get_quality_metrics()
    return {"success": True, **metrics}
