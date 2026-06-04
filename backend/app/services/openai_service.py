from openai import OpenAI

from app.config import settings
from app.services.ssl_service import enable_system_truststore
from app.services.usage_service import log_ai_usage

enable_system_truststore()

client = OpenAI(api_key=settings.OPENAI_API_KEY)

DEFAULT_TEXT_MODEL = "gpt-4.1-mini"
GPT5_TEXT_MODEL = "gpt-5"
GPT5_MINI_TEXT_MODEL = "gpt-5-mini"

# Approximate GPT-4.1-mini pricing
INPUT_COST_PER_1K = 0.0003
OUTPUT_COST_PER_1K = 0.0012


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate one OpenAI call's cost from token counts.

    The values are used for admin usage reporting, not for billing parents
    directly, so a rounded approximate cost is sufficient.
    """
    input_cost = (prompt_tokens / 1000) * INPUT_COST_PER_1K
    output_cost = (completion_tokens / 1000) * OUTPUT_COST_PER_1K

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

    if model.startswith("gpt-5"):
        request_payload["reasoning"] = {"effort": "low"}
        request_payload["max_output_tokens"] = 6000
    else:
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
