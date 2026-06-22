import threading
import time

from openai import OpenAI
from app.services.logger_service import get_logger, PlatformError

_log = get_logger("openai_service")

from app.config import settings
from app.services.ssl_service import enable_system_truststore
from app.services.usage_service import log_ai_usage

enable_system_truststore()

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
# Only gpt-4.1-nano is available on this OpenAI project.
# GPT_MINI_TEXT_MODEL and GPT_FULL_TEXT_MODEL intentionally alias to nano
# so routing upgrades degrade gracefully instead of returning 403.

DEFAULT_TEXT_MODEL = "gpt-4.1-nano"
GPT_MINI_TEXT_MODEL = "gpt-4.1-nano"   # gpt-4.1-mini not available on this project
GPT_FULL_TEXT_MODEL = "gpt-4.1-nano"   # gpt-4.1 not available on this project
PREWARM_TEXT_MODEL = "gpt-4.1-nano"
# Legacy aliases kept for backward compatibility with model_routing_service
GPT5_TEXT_MODEL = GPT_MINI_TEXT_MODEL
GPT5_MINI_TEXT_MODEL = DEFAULT_TEXT_MODEL

VENICE_BASE_URL = "https://api.venice.ai/api/v1"

_MODEL_PRICING = {
    # OpenAI models
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004},
    "gpt-4.1":      {"input": 0.002,  "output": 0.008},
    # Venice models (prices as of June 2026 — update when Venice pricing changes)
    "llama-3.3-70b":          {"input": 0.0003, "output": 0.0007},
    "llama-3.2-3b":           {"input": 0.00003,"output": 0.00006},
    "mistral-31-24b":         {"input": 0.00012,"output": 0.00024},
    "qwen-2.5-72b":           {"input": 0.0003, "output": 0.0006},
    "deepseek-r1-671b":       {"input": 0.0008, "output": 0.0024},
}

INPUT_COST_PER_1K = 0.0001
OUTPUT_COST_PER_1K = 0.0004

# ---------------------------------------------------------------------------
# Dynamic client — key and enabled/disabled state are loaded from Supabase
# admin_settings and cached for 60 s so every LLM call does not hit the DB.
# ---------------------------------------------------------------------------

_client_lock = threading.Lock()
_active_client: OpenAI | None = None
_active_key: str | None = None

_settings_cache: dict = {
    "api_key": None,
    "api_enabled": True,
    "provider": "openai",       # "openai" | "venice"
    "venice_api_key": None,
    "venice_model": "llama-3.3-70b",
    "loaded_at": 0.0,
}
_SETTINGS_TTL = 60.0  # seconds

# ── Venice client cache (separate from OpenAI client) ────────────────────────
_venice_client: OpenAI | None = None
_venice_key: str | None = None


def _load_db_settings() -> dict | None:
    """
    Load the ai_settings row from the admin_settings Supabase table.

    Uses admin_client (service_role key) because the admin_settings table
    has RLS enabled — the publishable anon key cannot read it.
    Lazy import avoids circular imports at module level.
    """
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
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


def force_refresh_settings() -> None:
    """Immediately expire the settings cache so the next call reloads from DB."""
    _settings_cache["loaded_at"] = 0.0


def get_effective_settings() -> dict:
    """
    Return {api_key, api_enabled} using DB settings when available.

    Falls back to the OPENAI_API_KEY environment variable when the DB row is
    absent or the stored key is blank.  The result is cached for 60 seconds.
    """
    now = time.time()
    if now - _settings_cache["loaded_at"] > _SETTINGS_TTL:
        db = _load_db_settings()
        if db:
            db_key = (db.get("openai_api_key") or "").strip()
            _settings_cache["api_key"] = db_key if db_key else settings.OPENAI_API_KEY
            _settings_cache["api_enabled"] = db.get("api_enabled", True)
            _settings_cache["provider"] = db.get("provider", "openai") or "openai"
            _settings_cache["venice_api_key"] = db.get("venice_api_key") or settings.VENICE_API_KEY
            _settings_cache["venice_model"] = db.get("venice_model") or "llama-3.3-70b"
        else:
            _settings_cache["api_key"] = settings.OPENAI_API_KEY
            _settings_cache["api_enabled"] = True
            _settings_cache["provider"] = "openai"
            _settings_cache["venice_api_key"] = settings.VENICE_API_KEY
            _settings_cache["venice_model"] = "llama-3.3-70b"
        _settings_cache["loaded_at"] = now

    return _settings_cache


def get_openai_client() -> OpenAI:
    """
    Return an OpenAI client initialised with the current effective API key.

    The client is recreated only when the active key changes so connection
    pools are reused across requests.
    """
    global _active_client, _active_key

    effective_key = (
        get_effective_settings()["api_key"] or settings.OPENAI_API_KEY or ""
    )

    if _active_client is None or effective_key != _active_key:
        with _client_lock:
            if _active_client is None or effective_key != _active_key:
                _active_client = OpenAI(api_key=effective_key, timeout=60.0)
                _active_key = effective_key

    return _active_client


def get_venice_client() -> OpenAI:
    """
    Return an OpenAI-compatible client pointed at Venice AI.

    Venice uses the OpenAI Chat Completions API format so the same
    openai Python SDK works — just with a different base_url and API key.
    """
    global _venice_client, _venice_key

    current_settings = get_effective_settings()
    venice_key = (
        current_settings.get("venice_api_key")
        or settings.VENICE_API_KEY
        or ""
    )

    if _venice_client is None or venice_key != _venice_key:
        with _client_lock:
            if _venice_client is None or venice_key != _venice_key:
                _venice_client = OpenAI(
                    api_key=venice_key,
                    base_url=VENICE_BASE_URL,
                    timeout=90.0,  # Venice can be slower on larger models
                )
                _venice_key = venice_key

    return _venice_client


def get_chat_client() -> OpenAI:
    """
    Return the active LLM client based on the admin-configured provider.

    Returns Venice client when provider == 'venice', OpenAI client otherwise.
    This is the function that ask_llm() should use.
    """
    current = get_effective_settings()
    if current.get("provider") == "venice":
        return get_venice_client()
    return get_openai_client()


# Backward-compat alias used by rag_service and any other direct importers.
# Code that imports `client` directly still works; prefer get_openai_client()
# in new code so key changes propagate without a server restart.
@property
def _client_property():
    return get_openai_client()


# Module-level `client` — initialised once with env key; stays in sync because
# rag_service now calls get_openai_client() directly.
client = get_openai_client()


# ---------------------------------------------------------------------------
# Cost helpers
# ---------------------------------------------------------------------------

def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = DEFAULT_TEXT_MODEL,
) -> float:
    """
    Estimate one OpenAI call's cost from token counts.

    Looks up per-model pricing so the admin usage dashboard accurately
    reflects nano (pre-generation) vs mini (live requests) costs.
    """
    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING[DEFAULT_TEXT_MODEL])
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


# ---------------------------------------------------------------------------
# Core LLM helper
# ---------------------------------------------------------------------------

def ask_llm(
    system_prompt: str,
    user_prompt: str,
    username: str = "unknown",
    feature: str = "lesson",
    model: str = DEFAULT_TEXT_MODEL,
) -> str:
    """
    Send a prompt to the configured LLM and log usage metrics.

    Raises HTTP 503 when the admin has disabled the AI API from the console.
    All high-level tutor features call through this helper so token accounting
    and cost tracking stay consistent across lessons, doubts, and mock tests.
    """
    from fastapi import HTTPException  # noqa: PLC0415 — avoid circular at module level

    current = get_effective_settings()
    if not current.get("api_enabled", True):
        raise HTTPException(
            status_code=503,
            detail="AI API is currently disabled. The admin can re-enable it from the Admin Control page.",
        )

    current = get_effective_settings()
    provider = current.get("provider", "openai")

    # When Venice is active, override the model with the configured Venice model
    # unless the caller already specified a Venice model name explicitly.
    active_model = model
    if provider == "venice":
        active_model = current.get("venice_model") or "llama-3.3-70b"

    # Use OpenAI Chat Completions API format — compatible with OpenAI AND Venice.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    t_start = time.perf_counter()
    try:
        response = get_chat_client().chat.completions.create(
            model=active_model,
            messages=messages,
            temperature=0.4,
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - t_start) * 1000)
        err_str = str(exc).lower()
        if "timeout" in err_str:
            error_code = PlatformError.LLM_TIMEOUT
        elif "rate" in err_str or "429" in err_str:
            error_code = PlatformError.LLM_RATE_LIMIT
        elif "quota" in err_str:
            error_code = PlatformError.LLM_QUOTA_EXCEEDED
        elif "context" in err_str or "token" in err_str:
            error_code = PlatformError.LLM_CONTEXT_TOO_LONG
        else:
            error_code = PlatformError.SYS_EXTERNAL_API_FAILED
        _log.error(
            "llm.call_failed",
            error_code=error_code,
            provider=provider,
            model=active_model,
            feature=feature,
            username=username,
            duration_ms=duration_ms,
            error=str(exc),
            exc_info=True,
        )
        raise

    duration_ms = round((time.perf_counter() - t_start) * 1000)
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
    total_tokens = prompt_tokens + completion_tokens

    estimated_cost = estimate_cost(prompt_tokens, completion_tokens, model=active_model)

    _log.info(
        "llm.call_success",
        provider=provider,
        model=active_model,
        feature=feature,
        username=username,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost,
        duration_ms=duration_ms,
    )

    log_ai_usage(
        username=username,
        feature=feature,
        model=active_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )

    return response.choices[0].message.content
