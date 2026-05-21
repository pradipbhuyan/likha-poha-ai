from app.services.supabase_client import supabase


def save_test_result(result):
    payload = {
        "username": result.get("username"),
        "grade": result.get("grade"),
        "mode": result.get("mode"),
        "subject": result.get("subject"),
        "chapter": result.get("chapter"),
        "mock_type": result.get("mockType"),
        "exam_type": result.get("examType"),
        "difficulty": result.get("difficulty"),
        "raw_score": result.get("rawScore"),
        "final_score": result.get("finalScore"),
        "max_score": result.get("maxScore"),
        "wrong_count": result.get("wrongCount"),
        "penalty": result.get("penalty"),
        "percentage": result.get("percentage"),
        "submitted_at": result.get("submittedAt"),
    }

    response = (
        supabase
        .table("test_history")
        .insert(payload)
        .execute()
    )

    return response.data[0] if response.data else payload


def get_user_history(username):
    response = (
        supabase
        .table("test_history")
        .select("*")
        .eq("username", username)
        .order("submitted_at", desc=False)
        .execute()
    )

    return response.data or []


def get_all_history():
    response = (
        supabase
        .table("test_history")
        .select("*")
        .order("submitted_at", desc=False)
        .execute()
    )

    return response.data or []


def clear_test_history():
    response = (
        supabase
        .table("test_history")
        .delete()
        .neq("id", 0)
        .execute()
    )

    return response.data


def clear_user_test_history(username):
    response = (
        supabase
        .table("test_history")
        .delete()
        .eq("username", username)
        .execute()
    )

    return response.data


def get_leaderboard():
    history = get_all_history()
    scores = {}

    for item in history:
        user = item.get("username")
        percent = float(item.get("percentage") or 0)

        if not user:
            continue

        if user not in scores:
            scores[user] = {
                "tests": 0,
                "best_score": 0,
                "total_score": 0,
            }

        scores[user]["tests"] += 1
        scores[user]["best_score"] = max(
            scores[user]["best_score"],
            percent,
        )
        scores[user]["total_score"] += percent

    leaderboard = []

    for username, data in scores.items():
        leaderboard.append({
            "username": username,
            "tests": data["tests"],
            "best_score": data["best_score"],
            "average_score": round(
                data["total_score"] / data["tests"],
                2,
            ),
        })

    return sorted(
        leaderboard,
        key=lambda x: x["average_score"],
        reverse=True,
    )