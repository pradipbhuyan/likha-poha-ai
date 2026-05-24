from fastapi import APIRouter, Query
from app.services.supabase_client import supabase

router = APIRouter()


@router.get("/summary")
def get_usage_summary(username: str | None = Query(default=None)):
    query = supabase.table("ai_usage_logs").select("*").order(
        "created_at",
        desc=True,
    )

    if username:
        query = query.eq("username", username)

    result = query.execute()
    logs = result.data or []

    total_cost = sum(float(item.get("estimated_cost") or 0) for item in logs)
    total_tokens = sum(int(item.get("total_tokens") or 0) for item in logs)
    total_images = sum(int(item.get("image_count") or 0) for item in logs)
    total_tts_chars = sum(int(item.get("tts_chars") or 0) for item in logs)

    by_user = {}
    by_feature = {}

    for item in logs:
        user = item.get("username") or "unknown"
        feature = item.get("feature") or "unknown"
        cost = float(item.get("estimated_cost") or 0)
        tokens = int(item.get("total_tokens") or 0)

        if user not in by_user:
            by_user[user] = {
                "username": user,
                "total_cost": 0,
                "total_tokens": 0,
                "requests": 0,
            }

        by_user[user]["total_cost"] += cost
        by_user[user]["total_tokens"] += tokens
        by_user[user]["requests"] += 1

        if feature not in by_feature:
            by_feature[feature] = {
                "feature": feature,
                "total_cost": 0,
                "total_tokens": 0,
                "requests": 0,
            }

        by_feature[feature]["total_cost"] += cost
        by_feature[feature]["total_tokens"] += tokens
        by_feature[feature]["requests"] += 1

    return {
        "success": True,
        "totals": {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "total_images": total_images,
            "total_tts_chars": total_tts_chars,
            "requests": len(logs),
        },
        "by_user": list(by_user.values()),
        "by_feature": list(by_feature.values()),
        "recent_logs": logs[:50],
    }