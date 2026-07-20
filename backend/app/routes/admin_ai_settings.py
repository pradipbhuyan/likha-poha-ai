"""
admin_ai_settings.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Master AI switch and per-provider API key/model management.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client
from app.config import settings

router = APIRouter()


class UpdateAiSettingsRequest(BaseModel):
    api_enabled: bool
    openai_api_key: str | None = None
    provider: str = "openai"    # "openai"|"venice"|"groq"|"cerebras"|"gemini"|"sambanova"
    venice_api_key: str | None = None
    venice_model: str = "llama-3.3-70b"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str | None = None
    cerebras_model: str = "llama3.3-70b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash-lite"
    sambanova_api_key: str | None = None
    sambanova_model: str = "Meta-Llama-3.3-70B-Instruct"
    nvidia_api_key: str | None = None
    nvidia_model: str = "meta/llama-4-scout-17b-16e-instruct"
    ollama_cloud_api_key: str | None = None
    ollama_cloud_model: str = "gemma3:4b"


def _load_ai_settings_row() -> dict | None:
    """Read the ai_settings row from admin_settings. Returns value dict or None."""
    try:
        response = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", "ai_settings")
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["value"]
    except Exception:
        pass
    return None


@router.get("/ai-settings")
def get_ai_settings(admin=Depends(require_admin)):
    """
    Return current AI settings for the admin console.

    The full API key is never returned — only the first 8 characters so the
    admin can confirm which key is active without exposing the secret.
    """
    row = _load_ai_settings_row()

    if row:
        stored_key = (row.get("openai_api_key") or "").strip()
        effective_key = stored_key if stored_key else (settings.OPENAI_API_KEY or "")
        stored_venice_key = (row.get("venice_api_key") or "").strip()
        stored_groq_key = (row.get("groq_api_key") or "").strip()
        stored_cerebras_key = (row.get("cerebras_api_key") or "").strip()
        stored_gemini_key = (row.get("gemini_api_key") or "").strip()
        stored_sambanova_key = (row.get("sambanova_api_key") or "").strip()
        stored_nvidia_key = (row.get("nvidia_api_key") or "").strip()
        stored_ollama_cloud_key = (row.get("ollama_cloud_api_key") or "").strip()
        return {
            "success": True,
            "api_enabled": row.get("api_enabled", True),
            "api_key_prefix": effective_key[:12] if effective_key else "",
            "key_source": "database" if stored_key else "environment",
            "provider": row.get("provider", "openai") or "openai",
            "venice_key_prefix": stored_venice_key[:12] if stored_venice_key else "",
            "venice_model": row.get("venice_model") or "llama-3.3-70b",
            "groq_key_prefix": stored_groq_key[:12] if stored_groq_key else "",
            "groq_model": row.get("groq_model") or "llama-3.3-70b-versatile",
            "cerebras_key_prefix": stored_cerebras_key[:12] if stored_cerebras_key else "",
            "cerebras_model": row.get("cerebras_model") or "llama3.3-70b",
            "gemini_key_prefix": stored_gemini_key[:12] if stored_gemini_key else "",
            "gemini_model": row.get("gemini_model") or "gemini-2.0-flash-lite",
            "sambanova_key_prefix": stored_sambanova_key[:12] if stored_sambanova_key else "",
            "sambanova_model": row.get("sambanova_model") or "Meta-Llama-3.3-70B-Instruct",
            "nvidia_key_prefix": stored_nvidia_key[:12] if stored_nvidia_key else "",
            "nvidia_model": row.get("nvidia_model") or "meta/llama-4-scout-17b-16e-instruct",
            "ollama_cloud_key_prefix": stored_ollama_cloud_key[:12] if stored_ollama_cloud_key else "",
            "ollama_cloud_model": row.get("ollama_cloud_model") or "gemma3:4b",
        }

    # Table exists but no row yet — fall back to env key
    env_key = settings.OPENAI_API_KEY or ""
    env_groq_key = settings.GROQ_API_KEY or ""
    env_cerebras_key = settings.CEREBRAS_API_KEY or ""
    return {
        "success": True,
        "api_enabled": True,
        "api_key_prefix": env_key[:12] if env_key else "",
        "key_source": "environment",
        "provider": "openai",
        "venice_key_prefix": "",
        "venice_model": "llama-3.3-70b",
        "groq_key_prefix": env_groq_key[:12] if env_groq_key else "",
        "groq_model": "llama-3.3-70b-versatile",
        "cerebras_key_prefix": env_cerebras_key[:12] if env_cerebras_key else "",
        "cerebras_model": "llama3.3-70b",
        "gemini_key_prefix": "",
        "gemini_model": "gemini-2.0-flash-lite",
        "sambanova_key_prefix": "",
        "sambanova_model": "Meta-Llama-3.3-70B-Instruct",
        "nvidia_key_prefix": "",
        "nvidia_model": "meta/llama-4-scout-17b-16e-instruct",
        "ollama_cloud_key_prefix": "",
        "ollama_cloud_model": "gemma3:4b",
    }


@router.put("/ai-settings")
def update_ai_settings(
    data: UpdateAiSettingsRequest,
    admin=Depends(require_admin),
):
    """
    Persist the master API switch and (optionally) a new OpenAI API key.

    When openai_api_key is omitted or blank the existing stored key is kept.
    After saving, the in-memory settings cache is force-expired so the next
    LLM call picks up the change without a server restart.
    """
    # Preserve existing key when the admin only toggles the switch
    existing_key = ""
    row = _load_ai_settings_row()
    if row:
        existing_key = (row.get("openai_api_key") or "").strip()

    new_key = (data.openai_api_key or "").strip()
    effective_key = new_key if new_key else existing_key

    # Venice key — preserve existing if blank
    existing_venice_key = (row.get("venice_api_key") or "").strip() if row else ""
    new_venice_key = (data.venice_api_key or "").strip()
    effective_venice_key = new_venice_key if new_venice_key else existing_venice_key

    # Groq key — preserve existing if blank
    existing_groq_key = (row.get("groq_api_key") or "").strip() if row else ""
    new_groq_key = (data.groq_api_key or "").strip()
    effective_groq_key = new_groq_key if new_groq_key else existing_groq_key

    # Cerebras key — preserve existing if blank
    existing_cerebras_key = (row.get("cerebras_api_key") or "").strip() if row else ""
    new_cerebras_key = (data.cerebras_api_key or "").strip()
    effective_cerebras_key = new_cerebras_key if new_cerebras_key else existing_cerebras_key

    # Gemini key — preserve existing if blank
    existing_gemini_key = (row.get("gemini_api_key") or "").strip() if row else ""
    new_gemini_key = (data.gemini_api_key or "").strip()
    effective_gemini_key = new_gemini_key if new_gemini_key else existing_gemini_key

    # SambaNova key — preserve existing if blank
    existing_sambanova_key = (row.get("sambanova_api_key") or "").strip() if row else ""
    new_sambanova_key = (data.sambanova_api_key or "").strip()
    effective_sambanova_key = new_sambanova_key if new_sambanova_key else existing_sambanova_key

    # NVIDIA key — preserve existing if blank
    existing_nvidia_key = (row.get("nvidia_api_key") or "").strip() if row else ""
    new_nvidia_key = (data.nvidia_api_key or "").strip()
    effective_nvidia_key = new_nvidia_key if new_nvidia_key else existing_nvidia_key

    # Ollama Cloud key — preserve existing if blank
    existing_ollama_cloud_key = (row.get("ollama_cloud_api_key") or "").strip() if row else ""
    new_ollama_cloud_key = (data.ollama_cloud_api_key or "").strip()
    effective_ollama_cloud_key = new_ollama_cloud_key if new_ollama_cloud_key else existing_ollama_cloud_key

    value = {
        "api_enabled": data.api_enabled,
        "openai_api_key": effective_key,
        "provider": data.provider or "openai",
        "venice_api_key": effective_venice_key,
        "venice_model": (data.venice_model or "llama-3.3-70b").strip(),
        "groq_api_key": effective_groq_key,
        "groq_model": (data.groq_model or "llama-3.3-70b-versatile").strip(),
        "cerebras_api_key": effective_cerebras_key,
        "cerebras_model": (data.cerebras_model or "llama3.3-70b").strip(),
        "gemini_api_key": effective_gemini_key,
        "gemini_model": (data.gemini_model or "gemini-2.0-flash-lite").strip(),
        "sambanova_api_key": effective_sambanova_key,
        "sambanova_model": (data.sambanova_model or "Meta-Llama-3.3-70B-Instruct").strip(),
        "nvidia_api_key": effective_nvidia_key,
        "nvidia_model": (data.nvidia_model or "meta/llama-4-scout-17b-16e-instruct").strip(),
        "ollama_cloud_api_key": effective_ollama_cloud_key,
        "ollama_cloud_model": (data.ollama_cloud_model or "gemma3:4b").strip(),
    }

    try:
        admin_client.table("admin_settings").upsert(
            {
                "key": "ai_settings",
                "value": value,
                "updated_at": "now()",
            },
            on_conflict="key",
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save AI settings. Run backend/sql/add_admin_settings.sql "
                f"in Supabase first. Original error: {str(exc)}"
            ),
        )

    # Immediately expire the in-memory cache in this process
    from app.services.openai_service import force_refresh_settings
    force_refresh_settings()

    display_key = effective_key if effective_key else (settings.OPENAI_API_KEY or "")
    return {
        "success": True,
        "api_enabled": data.api_enabled,
        "api_key_prefix": display_key[:12] if display_key else "",
        "key_source": "database" if effective_key else "environment",
        "provider": data.provider or "openai",
        "venice_key_prefix": effective_venice_key[:12] if effective_venice_key else "",
        "venice_model": value["venice_model"],
        "groq_key_prefix": effective_groq_key[:12] if effective_groq_key else "",
        "groq_model": value["groq_model"],
        "cerebras_key_prefix": effective_cerebras_key[:12] if effective_cerebras_key else "",
        "cerebras_model": value["cerebras_model"],
        "gemini_key_prefix": effective_gemini_key[:12] if effective_gemini_key else "",
        "gemini_model": value["gemini_model"],
        "sambanova_key_prefix": effective_sambanova_key[:12] if effective_sambanova_key else "",
        "sambanova_model": value["sambanova_model"],
        "nvidia_key_prefix": effective_nvidia_key[:12] if effective_nvidia_key else "",
        "nvidia_model": value["nvidia_model"],
        "ollama_cloud_key_prefix": effective_ollama_cloud_key[:12] if effective_ollama_cloud_key else "",
        "ollama_cloud_model": value["ollama_cloud_model"],
        "message": "AI settings saved successfully.",
    }
