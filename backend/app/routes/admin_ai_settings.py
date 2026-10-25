"""
admin_ai_settings.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Master AI switch and per-provider API key/model management.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, admin_client
from app.config import settings

router = APIRouter()

_CHEMICAL_FORMULA_ANSWER_RE = re.compile(
    r"(?:[A-Z][a-z]?(?:[0-9₀₁₂₃₄₅₆₇₈₉]+)?){2,}"
)


def _requires_missing_formula_correction(question: str, answer: str) -> bool:
    """Detect a formula request answered only with a related chemistry property."""
    asks_for_formula = bool(
        re.search(r"\b(?:chemical\s+)?formula\b", question, re.IGNORECASE)
    )
    return asks_for_formula and not _CHEMICAL_FORMULA_ANSWER_RE.search(answer)


# Models exposed in Admin → AI & Settings. Entries are limited to models with
# an available free tier, except for the requested GPT-4 and GPT-5 OpenAI
# families. OpenAI API usage is billable.
ALLOWED_AI_MODELS: dict[str, frozenset[str]] = {
    "openai": frozenset({
        # GPT-4 family
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # GPT-5 family
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
    }),
    "groq": frozenset({"llama-3.3-70b-versatile", "llama-3.1-8b-instant"}),
    "cerebras": frozenset({"gpt-oss-120b", "zai-glm-4.7"}),
    "gemini": frozenset({"gemini-2.5-flash"}),
    "sambanova": frozenset({
        "Meta-Llama-3.3-70B-Instruct",
        "DeepSeek-V3.2",
        "DeepSeek-V3.1",
        "gemma-4-31B-it",
        "gpt-oss-120b",
    }),
    "nvidia": frozenset({"meta/llama-4-scout-17b-16e-instruct"}),
    "ollama_cloud": frozenset({"gemma3:4b", "gemma3:12b", "gpt-oss:20b"}),
}


class AskDoubtModelTestRequest(BaseModel):
    question: str


class UpdateAiSettingsRequest(BaseModel):
    api_enabled: bool
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"
    provider: str = "openai"
    venice_api_key: str | None = None
    venice_model: str = ""
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str | None = None
    cerebras_model: str = "gpt-oss-120b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    sambanova_api_key: str | None = None
    sambanova_model: str = "Meta-Llama-3.3-70B-Instruct"
    nvidia_api_key: str | None = None
    nvidia_model: str = "meta/llama-4-scout-17b-16e-instruct"
    ollama_cloud_api_key: str | None = None
    ollama_cloud_model: str = "gemma3:4b"


def _validate_provider_models(data: UpdateAiSettingsRequest) -> None:
    """Reject providers and model IDs that are not in the reviewed catalog."""
    provider = (data.provider or "openai").strip()
    if provider not in ALLOWED_AI_MODELS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported AI provider: {provider}.",
        )

    models = {
        "openai": data.openai_model,
        "groq": data.groq_model,
        "cerebras": data.cerebras_model,
        "gemini": data.gemini_model,
        "sambanova": data.sambanova_model,
        "nvidia": data.nvidia_model,
        "ollama_cloud": data.ollama_cloud_model,
    }
    invalid = [
        f"{name}={model}"
        for name, model in models.items()
        if (model or "").strip() not in ALLOWED_AI_MODELS[name]
    ]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=(
                "Only reviewed free-tier models or approved OpenAI GPT-4/GPT-5 "
                "models may be saved: " + ", ".join(invalid)
            ),
        )


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
            "provider": (
                row.get("provider")
                if row.get("provider") in ALLOWED_AI_MODELS
                else "openai"
            ),
            "openai_model": (
                row.get("openai_model")
                if row.get("openai_model") in ALLOWED_AI_MODELS["openai"]
                else "gpt-5-nano"
            ),
            "venice_key_prefix": stored_venice_key[:12] if stored_venice_key else "",
            "venice_model": "",
            "groq_key_prefix": stored_groq_key[:12] if stored_groq_key else "",
            "groq_model": (
                row.get("groq_model")
                if row.get("groq_model") in ALLOWED_AI_MODELS["groq"]
                else "llama-3.3-70b-versatile"
            ),
            "cerebras_key_prefix": stored_cerebras_key[:12] if stored_cerebras_key else "",
            "cerebras_model": (
                row.get("cerebras_model")
                if row.get("cerebras_model") in ALLOWED_AI_MODELS["cerebras"]
                else "gpt-oss-120b"
            ),
            "gemini_key_prefix": stored_gemini_key[:12] if stored_gemini_key else "",
            "gemini_model": (
                row.get("gemini_model")
                if row.get("gemini_model") in ALLOWED_AI_MODELS["gemini"]
                else "gemini-2.5-flash"
            ),
            "sambanova_key_prefix": stored_sambanova_key[:12] if stored_sambanova_key else "",
            "sambanova_model": (
                row.get("sambanova_model")
                if row.get("sambanova_model") in ALLOWED_AI_MODELS["sambanova"]
                else "Meta-Llama-3.3-70B-Instruct"
            ),
            "nvidia_key_prefix": stored_nvidia_key[:12] if stored_nvidia_key else "",
            "nvidia_model": (
                row.get("nvidia_model")
                if row.get("nvidia_model") in ALLOWED_AI_MODELS["nvidia"]
                else "meta/llama-4-scout-17b-16e-instruct"
            ),
            "ollama_cloud_key_prefix": stored_ollama_cloud_key[:12] if stored_ollama_cloud_key else "",
            "ollama_cloud_model": (
                row.get("ollama_cloud_model")
                if row.get("ollama_cloud_model") in ALLOWED_AI_MODELS["ollama_cloud"]
                else "gemma3:4b"
            ),
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
        "openai_model": "gpt-5-nano",
        "venice_key_prefix": "",
        "venice_model": "",
        "groq_key_prefix": env_groq_key[:12] if env_groq_key else "",
        "groq_model": "llama-3.3-70b-versatile",
        "cerebras_key_prefix": env_cerebras_key[:12] if env_cerebras_key else "",
        "cerebras_model": "gpt-oss-120b",
        "gemini_key_prefix": "",
        "gemini_model": "gemini-2.5-flash",
        "sambanova_key_prefix": "",
        "sambanova_model": "Meta-Llama-3.3-70B-Instruct",
        "nvidia_key_prefix": "",
        "nvidia_model": "meta/llama-4-scout-17b-16e-instruct",
        "ollama_cloud_key_prefix": "",
        "ollama_cloud_model": "gemma3:4b",
    }


@router.post("/ai-settings/test-ask-doubt")
def test_ask_doubt_model(
    data: AskDoubtModelTestRequest,
    admin=Depends(require_admin),
):
    """
    Send one admin-only Ask Doubt test through the active platform provider/model.

    This deliberately calls ask_llm() rather than a provider-specific client so
    the test follows the same model selection, kill switch, retry, and fallback
    behavior used by the platform's normal AI features.
    """
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Enter a question to test.")
    if len(question) > 4_000:
        raise HTTPException(
            status_code=422,
            detail="Keep the test question to 4,000 characters or fewer.",
        )

    from app.services.openai_service import ask_llm, get_effective_settings

    active = get_effective_settings()
    provider = active.get("provider", "openai")
    model_fields = {
        "openai": "openai_model",
        "groq": "groq_model",
        "cerebras": "cerebras_model",
        "gemini": "gemini_model",
        "sambanova": "sambanova_model",
        "nvidia": "nvidia_model",
        "ollama_cloud": "ollama_cloud_model",
    }
    model = active.get(model_fields.get(provider, "openai_model"), "")

    try:
        answer = ask_llm(
            system_prompt=(
                "You are Likha Poha AI, a helpful CBSE tutor. Answer the "
                "student's doubt clearly and accurately. State the direct "
                "answer in the first sentence, then explain step by step where "
                "helpful. If asked for a chemical formula, explicitly write "
                "the formula using element symbols and subscripts or digits; "
                "do not answer only with a related property such as electron "
                "count or aromaticity. Use simple language and include a "
                "short example when it improves understanding."
            ),
            user_prompt=question,
            username="admin_model_test",
            feature="admin_ask_doubt_model_test",
        )
        if _requires_missing_formula_correction(question, answer):
            answer = ask_llm(
                system_prompt=(
                    "Rewrite the answer so it directly answers the student's "
                    "question. The earlier answer omitted the requested chemical "
                    "formula. Start with the formula in element symbols and "
                    "digits or subscripts, then add only a brief accurate "
                    "explanation. Do not discuss a related property instead."
                ),
                user_prompt=(
                    f"Student question: {question}\n\n"
                    f"Earlier incomplete answer: {answer}"
                ),
                username="admin_model_test",
                feature="admin_ask_doubt_model_test_formula_correction",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model test failed: {str(exc)[:500]}",
        ) from exc

    return {
        "success": True,
        "answer": answer,
        "provider": provider,
        "model": model,
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
    _validate_provider_models(data)

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
        "openai_model": (data.openai_model or "gpt-5-nano").strip(),
        "provider": data.provider or "openai",
        "venice_api_key": effective_venice_key,
        "venice_model": "",
        "groq_api_key": effective_groq_key,
        "groq_model": (data.groq_model or "llama-3.3-70b-versatile").strip(),
        "cerebras_api_key": effective_cerebras_key,
        "cerebras_model": (data.cerebras_model or "gpt-oss-120b").strip(),
        "gemini_api_key": effective_gemini_key,
        "gemini_model": (data.gemini_model or "gemini-2.5-flash").strip(),
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
        "openai_model": value["openai_model"],
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
