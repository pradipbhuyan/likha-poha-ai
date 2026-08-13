from datetime import datetime, timezone

from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS


UNLIMITED_TOKEN_LIMIT = 0


def normalize_token_limit(value) -> int:
    """Normalize token caps so zero means unlimited and negatives never persist."""
    try:
        return max(UNLIMITED_TOKEN_LIMIT, int(value or 0))
    except (TypeError, ValueError):
        return UNLIMITED_TOKEN_LIMIT


def is_unlimited_token_limit(value) -> bool:
    """Return whether a stored token cap disables enforcement."""
    return normalize_token_limit(value) == UNLIMITED_TOKEN_LIMIT


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
    """
    Best-effort write of AI usage metrics for cost, token, image, and TTS views.

    Usage logging should never break the student workflow, so failures are
    printed and swallowed instead of raising back into lesson/doubt generation.
    """
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
    """Load role, account status, and configured AI token limits for a user."""
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
    """Aggregate daily and current-month token usage from usage logs."""
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
    """
    Decide whether a user can make another AI request based on plan limits.

    Admins bypass token ceilings; inactive/suspended students are blocked before
    expensive AI calls are made.
    """
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

    daily_limit = normalize_token_limit(profile.get("daily_token_limit"))
    monthly_limit = normalize_token_limit(profile.get("monthly_token_limit"))

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
        "limits": {
            "daily_token_limit": daily_limit,
            "monthly_token_limit": monthly_limit,
            "unlimited": (
                is_unlimited_token_limit(daily_limit)
                and is_unlimited_token_limit(monthly_limit)
            ),
        },
    }


def get_daily_usage(username: str, feature: str):
    """Summarize today's usage for one feature, such as TTS or image generation."""
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
    """Apply a simple per-day request limit for non-token-metered features."""
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


def get_daily_usage_multi(username: str, features: list[str]):
    """Summarize today's usage across SEVERAL feature keys combined.

    Used for caps that must count more than one ai_usage_logs feature value
    as a single quota -- e.g. paid-tier Ask Doubt calls can log under either
    'doubt_answer_live_synthesis' (strong RAG match) or
    'doubt_answer_weak_grounding' (weak RAG match), and both must count
    toward the same daily LLM-call cap.
    """
    today = datetime.now(timezone.utc).date().isoformat()

    result = (
        supabase.table("ai_usage_logs")
        .select("total_tokens, estimated_cost")
        .eq("username", username)
        .in_("feature", features)
        .gte("created_at", f"{today}T00:00:00Z")
        .execute()
    )

    logs = result.data or []

    return {
        "requests": len(logs),
        "total_cost": sum(float(item.get("estimated_cost") or 0) for item in logs),
        "total_tokens": sum(int(item.get("total_tokens") or 0) for item in logs),
    }


def enforce_daily_limit_multi(username: str, features: list[str], max_requests: int):
    """Same as enforce_daily_limit(), but the cap is checked across several
    feature keys combined (see get_daily_usage_multi's docstring)."""
    usage = get_daily_usage_multi(username, features)

    if usage["requests"] >= max_requests:
        return {
            "allowed": False,
            "message": f"Daily limit reached for {features}. Try again tomorrow.",
            "usage": usage,
        }

    return {
        "allowed": True,
        "message": "Allowed",
        "usage": usage,
    }
