try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from openai import OpenAI

from app.config import settings
from app.services.usage_service import log_ai_usage

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Approximate GPT-4.1-mini pricing
INPUT_COST_PER_1K = 0.0003
OUTPUT_COST_PER_1K = 0.0012


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = (prompt_tokens / 1000) * INPUT_COST_PER_1K
    output_cost = (completion_tokens / 1000) * OUTPUT_COST_PER_1K

    return round(input_cost + output_cost, 6)


def ask_llm(
    system_prompt: str,
    user_prompt: str,
    username: str = "unknown",
    feature: str = "lesson",
) -> str:

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

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
        model="gpt-4.1-mini",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )

    return response.output_text