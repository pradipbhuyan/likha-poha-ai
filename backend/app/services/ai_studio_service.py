"""
ai_studio_service.py — Admin AI Studio Backend Service
────────────────────────────────────────────────────────────────────────────
Centralised AI provider management, model routing, prompt templates,
usage aggregation, and quality metrics.

Supports providers:
  openai | groq | cerebras | gemini | sambanova | venice |
  ollama_cloud | ollama_local | anthropic

Security rules:
  - API keys NEVER returned in responses — show masked value only
  - API keys read from admin_settings.ai_settings (existing secure storage)
  - No keys logged in any structured log field
  - All writes audit-logged
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

_log = logging.getLogger("likhapoha.ai_studio")

# ── Provider registry ─────────────────────────────────────────────────────────

PROVIDER_REGISTRY = {
    "openai": {
        "display_name": "OpenAI",
        "base_url": None,
        "key_prefix": "sk-",
        "key_env": "OPENAI_API_KEY",
        "settings_key": "openai_api_key",
        "supports_list_models": False,
        "free_tier": False,
        "docs_url": "https://platform.openai.com/docs",
        "suggested_models": ["gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1"],
    },
    "groq": {
        "display_name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "key_prefix": "gsk_",
        "key_env": "GROQ_API_KEY",
        "settings_key": "groq_api_key",
        "model_settings_key": "groq_model",
        "supports_list_models": False,
        "free_tier": True,
        "free_tier_notes": "14,400 req/day free",
        "docs_url": "https://console.groq.com/docs",
        "suggested_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    },
    "cerebras": {
        "display_name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "key_prefix": "csk-",
        "key_env": "CEREBRAS_API_KEY",
        "settings_key": "cerebras_api_key",
        "model_settings_key": "cerebras_model",
        "supports_list_models": False,
        "free_tier": True,
        "free_tier_notes": "No daily token cap",
        "docs_url": "https://inference-docs.cerebras.ai",
        "suggested_models": ["gpt-oss-120b", "zai-glm-4.7"],
    },
    "gemini": {
        "display_name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_prefix": "AIza",
        "key_env": "GEMINI_API_KEY",
        "settings_key": "gemini_api_key",
        "model_settings_key": "gemini_model",
        "supports_list_models": False,
        "free_tier": True,
        "free_tier_notes": "1M tokens/day free",
        "docs_url": "https://ai.google.dev/docs",
        "suggested_models": ["gemini-2.5-flash", "gemini-1.5-flash"],
    },
    "sambanova": {
        "display_name": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "key_prefix": "sn-",
        "key_env": "SAMBANOVA_API_KEY",
        "settings_key": "sambanova_api_key",
        "model_settings_key": "sambanova_model",
        "supports_list_models": False,
        "free_tier": True,
        "free_tier_notes": "Free tier with Llama models",
        "docs_url": "https://docs.sambanova.ai",
        "suggested_models": ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-4-Scout-17B-16E-Instruct"],
    },
    "venice": {
        "display_name": "Venice AI",
        "base_url": "https://api.venice.ai/api/v1",
        "key_prefix": "",
        "key_env": "VENICE_API_KEY",
        "settings_key": "venice_api_key",
        "model_settings_key": "venice_model",
        "supports_list_models": False,
        "free_tier": False,
        "docs_url": "https://docs.venice.ai",
        "suggested_models": ["llama-3.3-70b", "mistral-31-24b", "qwen-2.5-72b"],
    },
    "ollama_cloud": {
        "display_name": "Ollama Cloud",
        "base_url": "https://api.ollama.ai/v1",
        "key_prefix": "",
        "key_env": None,
        "settings_key": "ollama_cloud_api_key",
        "model_settings_key": "ollama_cloud_model",
        "supports_list_models": False,
        "free_tier": False,
        "docs_url": "https://ollama.com/docs",
        "suggested_models": ["glm-4-9b", "minimax-text-01", "qwen2.5-coder-7b", "moonshot-v1-8k"],
    },
    "ollama_local": {
        "display_name": "Local Ollama",
        "base_url": "http://localhost:11434/v1",
        "key_prefix": "",
        "key_env": None,
        "settings_key": None,  # No API key for local
        "model_settings_key": "ollama_local_model",
        "supports_list_models": True,
        "free_tier": True,
        "free_tier_notes": "Self-hosted, fully free",
        "docs_url": "https://ollama.com",
        "suggested_models": ["llama3.2", "mistral", "qwen2.5-coder"],
    },
    "anthropic": {
        "display_name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "key_prefix": "sk-ant-",
        "key_env": "ANTHROPIC_API_KEY",
        "settings_key": "anthropic_api_key",
        "model_settings_key": "anthropic_model",
        "supports_list_models": False,
        "free_tier": False,
        "docs_url": "https://docs.anthropic.com",
        "suggested_models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-opus-4-5"],
    },
}

FEATURE_KEYS = [
    "lesson_repair", "lesson_prewarm", "formula_generation", "formula_review",
    "mcq_generation", "lesson_quality_review", "ask_doubt", "ai_tutor",
    "summary_generation", "common_mistakes",
]

FEATURE_DISPLAY_NAMES = {
    "lesson_repair":          "Lesson Repair",
    "lesson_prewarm":         "Lesson Prewarming",
    "formula_generation":     "Formula Generation",
    "formula_review":         "Formula Review",
    "mcq_generation":         "MCQ Generation",
    "lesson_quality_review":  "Lesson Quality Review",
    "ask_doubt":              "Ask Doubt",
    "ai_tutor":               "AI Tutor",
    "summary_generation":     "Summary Generation",
    "common_mistakes":        "Common Mistakes",
}

# ── Key masking ───────────────────────────────────────────────────────────────

def _mask_key(key: Optional[str]) -> str:
    """Return a masked version of an API key. Never returns the real value."""
    if not key or not key.strip():
        return ""
    k = key.strip()
    if len(k) <= 8:
        return "••••••••"
    return k[:4] + "••••••••" + k[-4:]


# ── Settings access ───────────────────────────────────────────────────────────

def _get_ai_settings() -> dict:
    """Load the full ai_settings object from admin_settings."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = (admin_client.table("admin_settings")
                .select("value").eq("key", "ai_settings").limit(1).execute())
        if resp.data:
            return resp.data[0].get("value") or {}
    except Exception as e:
        _log.warning("Could not load ai_settings: %s", e)
    return {}


def _save_ai_settings(updates: dict) -> bool:
    """Merge updates into ai_settings and persist."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        current = _get_ai_settings()
        merged = {**current, **updates}
        resp = (admin_client.table("admin_settings")
                .upsert({"key": "ai_settings", "value": merged}, on_conflict="key")
                .execute())
        # Invalidate openai_service cache
        try:
            from app.services.openai_service import force_refresh_settings  # noqa: PLC0415
            force_refresh_settings()
        except Exception:
            pass
        return True
    except Exception as e:
        _log.error("Failed to save ai_settings: %s", e)
        return False


def _get_provider_key_value(settings: dict, provider_key: str) -> Optional[str]:
    """Get the raw API key for a provider from settings (for internal use only)."""
    meta = PROVIDER_REGISTRY.get(provider_key, {})
    sk = meta.get("settings_key")
    if not sk:
        return None
    val = settings.get(sk) or ""
    return val.strip() or None


# ── Provider listing ──────────────────────────────────────────────────────────

def get_providers() -> list[dict]:
    """
    Return all providers with their current configuration.
    API keys are ALWAYS masked — never return raw values.
    """
    from app.services.openai_service import get_effective_settings  # noqa: PLC0415
    eff = get_effective_settings()
    current_provider = eff.get("provider", "openai")
    fallback_provider = eff.get("fallback_provider")

    # Load DB configs for extra metadata
    db_configs: dict[str, dict] = {}
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = admin_client.table("ai_provider_configs").select("*").execute()
        for row in (resp.data or []):
            db_configs[row["provider_key"]] = row
    except Exception:
        pass

    result = []
    for pk, meta in PROVIDER_REGISTRY.items():
        raw_key = _get_provider_key_value(eff, pk)
        has_key = bool(raw_key)

        # Get model from effective settings
        model_sk = meta.get("model_settings_key")
        current_model = eff.get(model_sk, "") if model_sk else meta.get("suggested_models", [None])[0]

        db = db_configs.get(pk, {})

        result.append({
            "provider_key": pk,
            "display_name": meta["display_name"],
            "is_primary": pk == current_provider,
            "is_fallback": pk == fallback_provider,
            "is_enabled": db.get("is_enabled", True),
            "has_api_key": has_key,
            "masked_key": _mask_key(raw_key) if has_key else "",
            "base_url": db.get("base_url") or meta.get("base_url") or "",
            "current_model": current_model or "",
            "suggested_models": meta.get("suggested_models", []),
            "temperature": float(db.get("temperature") or 0.4),
            "max_tokens": int(db.get("max_tokens") or 4096),
            "timeout_s": int(db.get("timeout_s") or 60),
            "free_tier": meta.get("free_tier", False),
            "free_tier_notes": meta.get("free_tier_notes", ""),
            "key_prefix": meta.get("key_prefix", ""),
            "docs_url": meta.get("docs_url", ""),
            "supports_list_models": meta.get("supports_list_models", False),
        })

    return result


def save_provider(provider_key: str, data: dict, admin_id: str) -> dict:
    """
    Save provider configuration. API key update is optional.
    Returns {success, message}.
    Security: never log the API key value.
    """
    if provider_key not in PROVIDER_REGISTRY:
        return {"success": False, "message": f"Unknown provider: {provider_key}"}

    meta = PROVIDER_REGISTRY[provider_key]

    # Build settings updates (no key logging)
    settings_updates: dict[str, Any] = {}
    new_key = (data.get("api_key") or "").strip()
    if new_key and new_key != "••••••••" and not new_key.startswith("••"):
        sk = meta.get("settings_key")
        if sk:
            settings_updates[sk] = new_key  # key value never logged

    model_sk = meta.get("model_settings_key")
    if model_sk and data.get("model"):
        settings_updates[model_sk] = data["model"].strip()

    if data.get("base_url") and provider_key in ("ollama_cloud", "ollama_local"):
        settings_updates[f"{provider_key}_base_url"] = data["base_url"].strip()

    if settings_updates:
        _save_ai_settings(settings_updates)

    # Update DB config row
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        db_updates = {"provider_key": provider_key}
        if data.get("display_name"):
            db_updates["display_name"] = data["display_name"]
        if data.get("temperature") is not None:
            db_updates["temperature"] = float(data["temperature"])
        if data.get("max_tokens") is not None:
            db_updates["max_tokens"] = int(data["max_tokens"])
        if data.get("timeout_s") is not None:
            db_updates["timeout_s"] = int(data["timeout_s"])
        if data.get("base_url") is not None:
            db_updates["base_url"] = data["base_url"]
        if data.get("is_enabled") is not None:
            db_updates["is_enabled"] = bool(data["is_enabled"])
        db_updates.setdefault("display_name", meta["display_name"])
        (admin_client.table("ai_provider_configs")
         .upsert(db_updates, on_conflict="provider_key").execute())
    except Exception as db_err:
        _log.warning("Could not update ai_provider_configs for %s: %s", provider_key, db_err)

    # Handle primary/fallback switching
    if data.get("set_as_primary"):
        _save_ai_settings({"provider": provider_key})
    if data.get("set_as_fallback"):
        _save_ai_settings({"fallback_provider": provider_key})

    _log.info("[ai_studio] provider=%s saved by admin=%s", provider_key, admin_id)
    return {"success": True, "message": f"{meta['display_name']} configuration saved."}


def test_connection(provider_key: str, override_key: Optional[str] = None) -> dict:
    """
    Test connection to a provider with a minimal completion request.
    Returns {success, latency_ms, model, message}.
    NEVER logs the API key.
    """
    if provider_key not in PROVIDER_REGISTRY:
        return {"success": False, "latency_ms": 0, "model": "", "message": f"Unknown provider: {provider_key}"}

    meta = PROVIDER_REGISTRY[provider_key]
    from app.services.openai_service import get_effective_settings  # noqa: PLC0415

    eff = get_effective_settings()
    api_key = override_key or _get_provider_key_value(eff, provider_key) or ""
    model_sk = meta.get("model_settings_key")
    model = eff.get(model_sk, "") if model_sk else (meta.get("suggested_models", ["gpt-4.1-nano"])[0])
    base_url = eff.get(f"{provider_key}_base_url") or meta.get("base_url")
    timeout = 15.0

    # Local Ollama: check server reachability first
    if provider_key == "ollama_local":
        import requests as _req  # noqa: PLC0415
        server_url = base_url or "http://localhost:11434"
        try:
            r = _req.get(f"{server_url.rstrip('/')}/api/version", timeout=5)
            if r.status_code != 200:
                return {"success": False, "latency_ms": 0, "model": model,
                        "message": f"Local Ollama server returned {r.status_code}. Is it running?"}
        except Exception:
            return {"success": False, "latency_ms": 0, "model": model,
                    "message": "Local Ollama server not reachable. Start it with: ollama serve"}

    # Anthropic uses its own API format
    if provider_key == "anthropic":
        return _test_anthropic(api_key, model, timeout)

    if not api_key and provider_key != "ollama_local":
        return {"success": False, "latency_ms": 0, "model": model,
                "message": f"No API key configured for {meta['display_name']}."}

    try:
        from openai import OpenAI  # noqa: PLC0415
        client_kwargs: dict[str, Any] = {"api_key": api_key or "ollama", "timeout": timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with one word: OK"}],
            max_tokens=5,
            temperature=0,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)
        text = resp.choices[0].message.content or ""
        return {"success": True, "latency_ms": latency_ms, "model": model,
                "message": f"Connected. Response: {text[:40]!r}"}
    except Exception as exc:
        err = str(exc)
        if "401" in err or "unauthorized" in err.lower() or "incorrect api" in err.lower():
            msg = "Authentication failed — check your API key."
        elif "404" in err:
            msg = f"Model '{model}' not found. Try a different model."
        elif "timeout" in err.lower():
            msg = "Connection timed out. Check the server URL and try again."
        elif "connection" in err.lower() or "refused" in err.lower():
            msg = "Connection refused. Is the server running at the configured URL?"
        else:
            msg = f"Connection failed: {err[:120]}"
        return {"success": False, "latency_ms": 0, "model": model, "message": msg}


def _test_anthropic(api_key: str, model: str, timeout: float) -> dict:
    """Test Anthropic connection using the messages API."""
    if not api_key:
        return {"success": False, "latency_ms": 0, "model": model,
                "message": "No API key configured for Anthropic."}
    try:
        import requests as _req  # noqa: PLC0415
        t0 = time.perf_counter()
        r = _req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,  # key value goes to provider only — not logged
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": 5,
                  "messages": [{"role": "user", "content": "Reply with: OK"}]},
            timeout=timeout,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            text = (r.json().get("content") or [{}])[0].get("text", "")
            return {"success": True, "latency_ms": latency_ms, "model": model,
                    "message": f"Connected. Response: {text[:40]!r}"}
        elif r.status_code == 401:
            return {"success": False, "latency_ms": latency_ms, "model": model,
                    "message": "Authentication failed — check your Anthropic API key."}
        else:
            return {"success": False, "latency_ms": latency_ms, "model": model,
                    "message": f"Anthropic returned status {r.status_code}."}
    except Exception as exc:
        return {"success": False, "latency_ms": 0, "model": model,
                "message": f"Anthropic connection failed: {str(exc)[:120]}"}


def list_local_models(base_url: Optional[str] = None) -> list[str]:
    """List models available in a local Ollama server."""
    url = (base_url or "http://localhost:11434").rstrip("/")
    try:
        import requests as _req  # noqa: PLC0415
        r = _req.get(f"{url}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models") or []
            return [m.get("name", "") for m in models if m.get("name")]
    except Exception:
        pass
    return []


# ── Model Profiles ────────────────────────────────────────────────────────────

def get_model_profiles() -> list[dict]:
    """Return model routing profiles for all features."""
    db_profiles: dict[str, dict] = {}
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = admin_client.table("ai_model_profiles").select("*").execute()
        for row in (resp.data or []):
            db_profiles[row["feature_key"]] = row
    except Exception:
        pass

    result = []
    for fk in FEATURE_KEYS:
        db = db_profiles.get(fk, {})
        result.append({
            "feature_key": fk,
            "display_name": FEATURE_DISPLAY_NAMES.get(fk, fk),
            "provider_key": db.get("provider_key", "openai"),
            "model": db.get("model", "gpt-4.1-nano"),
            "temperature": float(db.get("temperature") or 0.4),
            "max_tokens": int(db.get("max_tokens") or 4096),
            "fallback_provider": db.get("fallback_provider") or "",
            "fallback_model": db.get("fallback_model") or "",
            "is_enabled": db.get("is_enabled", True),
            "notes": db.get("notes") or "",
        })
    return result


def save_model_profile(feature_key: str, data: dict, admin_id: str) -> dict:
    """Update the model routing profile for a feature."""
    if feature_key not in FEATURE_DISPLAY_NAMES:
        return {"success": False, "message": f"Unknown feature: {feature_key}"}
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        updates = {
            "feature_key": feature_key,
            "display_name": FEATURE_DISPLAY_NAMES[feature_key],
        }
        for field in ("provider_key", "model", "temperature", "max_tokens",
                      "fallback_provider", "fallback_model", "is_enabled", "notes"):
            if data.get(field) is not None:
                updates[field] = data[field]
        (admin_client.table("ai_model_profiles")
         .upsert(updates, on_conflict="feature_key").execute())
        _log.info("[ai_studio] model_profile=%s updated by admin=%s", feature_key, admin_id)
        return {"success": True, "message": f"Model profile for '{FEATURE_DISPLAY_NAMES[feature_key]}' saved."}
    except Exception as e:
        return {"success": False, "message": f"Failed to save model profile: {str(e)[:200]}"}


# ── Prompt Templates ──────────────────────────────────────────────────────────

def get_prompt_templates() -> list[dict]:
    """Return all prompt templates with their active version content."""
    result = []
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        templates = (admin_client.table("ai_prompt_templates")
                     .select("*").order("feature_key").execute().data or [])
        for tmpl in templates:
            tid = tmpl["id"]
            active_v = tmpl.get("active_version", 1)
            # Fetch active version content
            ver_resp = (admin_client.table("ai_prompt_template_versions")
                        .select("*")
                        .eq("template_id", tid)
                        .eq("version_number", active_v)
                        .limit(1).execute())
            ver = (ver_resp.data or [{}])[0]
            # Fetch version count
            count_resp = (admin_client.table("ai_prompt_template_versions")
                          .select("version_number")
                          .eq("template_id", tid)
                          .order("version_number", desc=True)
                          .limit(1).execute())
            latest_v = (count_resp.data or [{"version_number": 1}])[0].get("version_number", 1)
            result.append({
                "id": tid,
                "feature_key": tmpl["feature_key"],
                "display_name": tmpl["display_name"],
                "description": tmpl.get("description") or "",
                "active_version": active_v,
                "latest_version": latest_v,
                "system_prompt": ver.get("system_prompt", ""),
                "user_prompt": ver.get("user_prompt", ""),
                "updated_at": tmpl.get("updated_at", ""),
            })
    except Exception as e:
        _log.warning("Could not load prompt templates: %s", e)
    return result


def save_prompt_template(template_id: str, data: dict, admin_id: str) -> dict:
    """Save a new version of a prompt template."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        # Get current latest version
        resp = (admin_client.table("ai_prompt_template_versions")
                .select("version_number")
                .eq("template_id", template_id)
                .order("version_number", desc=True)
                .limit(1).execute())
        latest = (resp.data or [{"version_number": 0}])[0].get("version_number", 0)
        new_version = latest + 1

        (admin_client.table("ai_prompt_template_versions").insert({
            "template_id": template_id,
            "version_number": new_version,
            "system_prompt": data.get("system_prompt", ""),
            "user_prompt": data.get("user_prompt", ""),
            "change_summary": data.get("change_summary", "")[:200],
            "created_by": admin_id,
        }).execute())

        if data.get("set_active", True):
            (admin_client.table("ai_prompt_templates")
             .update({"active_version": new_version})
             .eq("id", template_id).execute())

        _log.info("[ai_studio] prompt_template=%s v%d saved by admin=%s",
                  template_id, new_version, admin_id)
        return {"success": True, "message": f"Prompt saved as version {new_version}.", "version": new_version}
    except Exception as e:
        return {"success": False, "message": f"Failed to save prompt: {str(e)[:200]}"}


def activate_template_version(template_id: str, version_number: int, admin_id: str) -> dict:
    """Set a specific version as the active version."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        (admin_client.table("ai_prompt_templates")
         .update({"active_version": version_number})
         .eq("id", template_id).execute())
        _log.info("[ai_studio] template=%s activated v%d by admin=%s",
                  template_id, version_number, admin_id)
        return {"success": True, "message": f"Version {version_number} is now active."}
    except Exception as e:
        return {"success": False, "message": f"Failed to activate version: {str(e)[:200]}"}


def get_template_versions(template_id: str) -> list[dict]:
    """Return all versions of a prompt template."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = (admin_client.table("ai_prompt_template_versions")
                .select("version_number,change_summary,created_by,created_at")
                .eq("template_id", template_id)
                .order("version_number", desc=True).execute())
        return resp.data or []
    except Exception:
        return []


# ── Usage & Costs ─────────────────────────────────────────────────────────────

def get_usage_summary(days: int = 30) -> dict:
    """Return usage and cost summary from ai_usage_logs."""
    from app.services.openai_service import get_effective_settings  # noqa: PLC0415
    eff = get_effective_settings()
    summary = {
        "provider": eff.get("provider", "openai"),
        "model": eff.get("groq_model") or eff.get("gemini_model") or "gpt-4.1-nano",
        "total_requests": 0,
        "today_requests": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "avg_latency_ms": None,
        "success_rate": None,
        "last_error": None,
        "by_feature": [],
        "by_provider": [],
        "cost_note": "",
    }

    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        from datetime import date, timedelta  # noqa: PLC0415
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()

        # Try ai_usage_logs (existing table)
        resp = (admin_client.table("ai_usage_logs")
                .select("feature,model,total_tokens,estimated_cost,created_at")
                .gte("created_at", since).execute())
        rows = resp.data or []

        if rows:
            today_rows = [r for r in rows if r.get("created_at", "") >= today_start]
            summary["total_requests"] = len(rows)
            summary["today_requests"] = len(today_rows)
            summary["total_tokens"] = sum(int(r.get("total_tokens") or 0) for r in rows)
            summary["estimated_cost_usd"] = round(
                sum(float(r.get("estimated_cost") or 0) for r in rows), 6)

            # By feature
            feat_map: dict[str, dict] = {}
            for r in rows:
                fk = r.get("feature") or "unknown"
                if fk not in feat_map:
                    feat_map[fk] = {"feature_key": fk, "requests": 0,
                                    "tokens": 0, "cost": 0.0}
                feat_map[fk]["requests"] += 1
                feat_map[fk]["tokens"] += int(r.get("total_tokens") or 0)
                feat_map[fk]["cost"] += float(r.get("estimated_cost") or 0)
            summary["by_feature"] = sorted(
                feat_map.values(), key=lambda x: x["cost"], reverse=True)[:10]

    except Exception as e:
        _log.warning("Could not load usage summary: %s", e)

    # Cost note for free-tier providers
    provider = eff.get("provider", "openai")
    meta = PROVIDER_REGISTRY.get(provider, {})
    if meta.get("free_tier"):
        summary["cost_note"] = (
            f"{meta['display_name']} free tier — "
            f"{meta.get('free_tier_notes', 'costs may be $0 within quota')}."
        )

    return summary


def get_generation_jobs(limit: int = 50) -> list[dict]:
    """Return recent AI generation jobs."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = (admin_client.table("ai_generation_jobs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit).execute())
        return resp.data or []
    except Exception:
        return []


def get_quality_metrics() -> dict:
    """Return quality metrics from audit reports and validation data."""
    metrics: dict = {
        "llm_acceptance_rate": None,
        "repair_success_rate": None,
        "validation_failure_rate": None,
        "avg_before_score": None,
        "avg_after_score": None,
        "formula_validation_pass_rate": None,
        "mcq_validation_pass_rate": None,
        "common_failure_reasons": [],
        "note": "Metrics are computed from recent audit and repair job data.",
    }

    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        # Lesson repair tasks
        tasks = (admin_client.table("lesson_repair_tasks")
                 .select("status,audit_before_score,audit_after_score,validation_result_json")
                 .order("created_at", desc=True)
                 .limit(200).execute().data or [])
        if tasks:
            published = [t for t in tasks if t.get("status") == "published"]
            ready = [t for t in tasks if t.get("status") in ("ready_for_review", "approved", "published")]
            failed_val = [t for t in tasks if t.get("status") == "validation_failed"]
            total = len(tasks)
            if total > 0:
                metrics["repair_success_rate"] = round(len(ready) / total * 100, 1)
                metrics["validation_failure_rate"] = round(len(failed_val) / total * 100, 1)
            before_scores = [float(t["audit_before_score"]) for t in tasks
                             if t.get("audit_before_score") is not None]
            after_scores = [float(t["audit_after_score"]) for t in tasks
                            if t.get("audit_after_score") is not None]
            if before_scores:
                metrics["avg_before_score"] = round(sum(before_scores) / len(before_scores), 1)
            if after_scores:
                metrics["avg_after_score"] = round(sum(after_scores) / len(after_scores), 1)
    except Exception as e:
        _log.warning("Could not compute quality metrics: %s", e)

    return metrics


def get_knowledge_sources() -> list[dict]:
    """Return knowledge source status (read-only, future-ready)."""
    sources = [
        {
            "key": "dkb",
            "display_name": "DKB (Default Knowledge Base)",
            "description": "NCERT-aligned lesson content uploaded via RAG Upload",
            "status": "active",
            "action": None,
        },
        {
            "key": "formula_content",
            "display_name": "Formula Content Source",
            "description": "Formula sheets seeded via seed_formula_sheets.py",
            "status": "active",
            "action": None,
        },
        {
            "key": "lesson_cache",
            "display_name": "Lesson Cache",
            "description": "AI-generated lessons stored in lesson_cache table",
            "status": "active",
            "action": None,
        },
        {
            "key": "exemplar_content",
            "display_name": "NCERT Exemplar Content",
            "description": "Hard questions from NCERT Exemplar books",
            "status": "active",
            "action": None,
        },
        {
            "key": "vector_store",
            "display_name": "Vector Store / Embeddings",
            "description": "Semantic search index for lesson and formula content",
            "status": "coming_soon",
            "action": "coming_soon",
        },
        {
            "key": "custom_kb",
            "display_name": "Custom Knowledge Base",
            "description": "Upload custom PDFs or content for RAG",
            "status": "coming_soon",
            "action": "coming_soon",
        },
    ]
    # Check DKB document count
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        count_resp = admin_client.table("document_chunks").select("id", count="exact").limit(1).execute()
        count = getattr(count_resp, "count", None) or 0
        sources[0]["document_count"] = count
        sources[0]["status"] = "active" if count > 0 else "empty"
    except Exception:
        sources[0]["status"] = "unknown"
    return sources
