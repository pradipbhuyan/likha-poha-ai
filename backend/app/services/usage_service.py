from datetime import datetime, timezone

from app.services.supabase_client import supabase


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


def get_user_limits(username: str):
    response = (
        supabase
        .table("profiles")
        .select("username, role, daily_token_limit, monthly_token_limit, account_status")
        .eq("username", username)
        .single()
        .execute()
    )

    return response.data


def get_token_usage(username: str):
    now = datetime.now(timezone.utc)

    today_start = now.date().isoformat()
    month_start = now.replace(day=1).date().isoformat()

    daily_response = (
        supabase
        .table("ai_usage_logs")
        .select("total_tokens")
        .eq("username", username)
        .gte("created_at", f"{today_start}T00:00:00Z")
        .execute()
    )

    monthly_response = (
        supabase
        .table("ai_usage_logs")
        .select("total_tokens")
        .eq("username", username)
        .gte("created_at", f"{month_start}T00:00:00Z")
        .execute()
    )

    daily_logs = daily_response.data or []
    monthly_logs = monthly_response.data or []

    daily_tokens = sum(int(item.get("total_tokens") or 0) for item in daily_logs)
    monthly_tokens = sum(int(item.get("total_tokens") or 0) for item in monthly_logs)

    return {
        "daily_tokens": daily_tokens,
        "monthly_tokens": monthly_tokens,
    }


def enforce_token_limits(username: str):
    profile = get_user_limits(username)

    if not profile:
        return {
            "allowed": False,
            "message": "User profile not found.",
        }

    if profile.get("role") == "admin":
        return {
            "allowed": True,
            "message": "Admin allowed.",
        }

    if profile.get("account_status") not in [None, "active", "trial"]:
        return {
            "allowed": False,
            "message": "Account is not active.",
        }

    usage = get_token_usage(username)

    daily_limit = int(profile.get("daily_token_limit") or 0)
    monthly_limit = int(profile.get("monthly_token_limit") or 0)

    if daily_limit > 0 and usage["daily_tokens"] >= daily_limit:
        return {
            "allowed": False,
            "message": "Daily AI token limit reached. Please try again tomorrow or upgrade your plan.",
            "usage": usage,
        }

    if monthly_limit > 0 and usage["monthly_tokens"] >= monthly_limit:
        return {
            "allowed": False,
            "message": "Monthly AI token limit reached. Please upgrade your plan.",
            "usage": usage,
        }

    return {
        "allowed": True,
        "message": "Allowed",
        "usage": usage,
    }


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
        "total_tokens": sum(int(item.get("total_tokens") or 0) for item in logs),
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