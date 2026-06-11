from openai import OpenAI

from app.config import settings
from app.services.ssl_service import enable_system_truststore
from app.services.usage_service import log_ai_usage

enable_system_truststore()

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
# All features use gpt-4.1-mini to keep token costs low.
# To upgrade premium features (SOF mock tests, complex doubts, RAG analysis)
# to a stronger model when budget allows, change GPT5_TEXT_MODEL to "gpt-4.1"
# or "gpt-4o" — no other files need to change.
# ---------------------------------------------------------------------------

DEFAULT_TEXT_MODEL = "gpt-4.1-mini"

# Premium-feature model — set to mini until token budget improves.
# Future upgrade path: change to "gpt-4.1" for richer SOF Olympiad output.
GPT5_TEXT_MODEL = "gpt-4.1-mini"

# Admin per-student override model — same as default.
GPT5_MINI_TEXT_MODEL = "gpt-4.1-mini"

# Pre-generation model — gpt-4.1-nano for offline lesson cache building.
# 75% cheaper than mini ($0.10/$0.40 per 1M vs $0.40/$1.60 per 1M).
# Quality is reviewed before going live; cache misses still use DEFAULT_TEXT_MODEL.
PREWARM_TEXT_MODEL = "gpt-4.1-nano"

# Pricing per 1K tokens by model (used by estimate_cost).
_MODEL_PRICING = {
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004},
    "gpt-4.1":      {"input": 0.002,  "output": 0.008},
}

# Approximate GPT-4.1-mini pricing (per 1K tokens) — kept for backward compat
INPUT_COST_PER_1K = 0.0004
OUTPUT_COST_PER_1K = 0.0016


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str = DEFAULT_TEXT_MODEL) -> float:
    """
    Estimate one OpenAI call's cost from token counts.

    Looks up per-model pricing so the admin usage dashboard accurately
    reflects nano (pre-generation) vs mini (live requests) costs.
    The values are used for admin usage reporting only.
    """
    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING[DEFAULT_TEXT_MODEL])
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]

    return round(input_cost + output_cost, 6)


def ask_llm(
    system_prompt: str,
    user_prompt: str,
    username: str = "unknown",
    feature: str = "lesson",
    model: str = DEFAULT_TEXT_MODEL,
) -> str:
    """
    Send a prompt to the configured LLM and log usage metrics.

    All high-level tutor features call through this helper so token accounting
    and estimated-cost tracking stay consistent across lessons, doubts, mock
    tests, practice, and image-related explanations.
    """
    request_payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    request_payload["temperature"] = 0.4

    response = client.responses.create(**request_payload)

    usage = getattr(response, "usage", None)

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    if usage:
        prompt_tokens = getattr(usage, "input_tokens", 0)
        completion_tokens = getattr(usage, "output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

    estimated_cost = estimate_cost(
        prompt_tokens,
        completion_tokens,
        model=model,
    )

    log_ai_usage(
        username=username,
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )

    return response.output_text
