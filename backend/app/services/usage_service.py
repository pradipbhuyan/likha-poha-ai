from app.services.supabase_client import supabase
from datetime import datetime, timezone

def log_ai_usage(
    username: str,
    feature: str,
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    image_count: int = 0,
    tts_chars: int = 0,
    estimated_cost: float = 0.0,
    metadata: dict | None = None,
):
    try:
        supabase.table("ai_usage_logs").insert({
            "username": username or "unknown",
            "feature": feature,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "image_count": image_count,
            "tts_chars": tts_chars,
            "estimated_cost": estimated_cost,
            "metadata": metadata or {},
        }).execute()

    except Exception as e:
        print("Usage logging failed:", str(e))
        



def get_daily_usage(username: str, feature: str):
    today = datetime.now(timezone.utc).date().isoformat()

    result = (
        supabase.table("ai_usage_logs")
        .select("*")
        .eq("username", username)
        .eq("feature", feature)
        .gte("created_at", f"{today}T00:00:00Z")
        .execute()
    )

    logs = result.data or []

    return {
        "requests": len(logs),
        "total_cost": sum(float(item.get("estimated_cost") or 0) for item in logs),
    }


def enforce_daily_limit(username: str, feature: str, max_requests: int):
    usage = get_daily_usage(username, feature)

    if usage["requests"] >= max_requests:
        return {
            "allowed": False,
            "message": f"Daily limit reached for {feature}. Try again tomorrow.",
            "usage": usage,
        }

    return {
        "allowed": True,
        "message": "Allowed",
        "usage": usage,
    }