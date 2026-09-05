from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS


def save_test_result(result):
    """Persist one mock-test result row for analytics and leaderboard features."""
    payload = {
        "profile_id": result.get("profile_id"),
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
        # time_taken_seconds column does not exist in the test_history table — omit it
        "submitted_at": result.get("submittedAt"),
    }

    response = (
        supabase
        .table("test_history")
        .insert(payload)
        .execute()
    )

    return response.data[0] if response.data else payload


def get_user_history(username, profile_id=None):
    """Return all stored test results for one username in chronological order."""
    query = (
        supabase
        .table("test_history")
        .select("*")
    )
    query = query.eq("profile_id", profile_id) if profile_id else query.eq("username", username)
    response = query.order("submitted_at", desc=False).execute()

    return response.data or []


def get_all_history():
    """Return all stored test-history rows for platform analytics."""
    response = (
        supabase
        .table("test_history")
        .select("*")
        .order("submitted_at", desc=False)
        .execute()
    )

    return response.data or []


def clear_test_history():
    """Delete all test-history rows."""
    response = (
        supabase
        .table("test_history")
        .delete()
        .neq("id", 0)
        .execute()
    )

    return response.data


def clear_user_test_history(username, profile_id=None):
    """Delete all test-history rows for one username."""
    query = (
        supabase
        .table("test_history")
        .delete()
    )
    query = query.eq("profile_id", profile_id) if profile_id else query.eq("username", username)
    response = query.execute()

    return response.data


# Minimum test count a student's average needs before the leaderboard trusts
# it at face value. Below this, ranking blends the student's own average
# with the platform-wide mean (weighted by how few tests they've taken) —
# a standard Bayesian/"IMDb-style" adjustment. Without it, one lucky test at
# 100% outranks fifty consistent tests at 85%, which is exactly the "trust"
# problem this exists to fix. `average_score` shown to students is always
# their real, unadjusted average — only the sort order is weighted.
_LEADERBOARD_CONFIDENCE_TESTS = 5


def get_leaderboard():
    """Build leaderboard rows from each student's best and average scores."""
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

    total_tests = sum(data["tests"] for data in scores.values())
    platform_mean = (
        sum(data["total_score"] for data in scores.values()) / total_tests
        if total_tests
        else 0
    )

    def weighted_score(data):
        tests = data["tests"]
        return (
            data["total_score"] + platform_mean * _LEADERBOARD_CONFIDENCE_TESTS
        ) / (tests + _LEADERBOARD_CONFIDENCE_TESTS)

    ranked_usernames = sorted(
        scores.keys(),
        key=lambda u: weighted_score(scores[u]),
        reverse=True,
    )

    return [
        {
            "username": username,
            "tests": scores[username]["tests"],
            "best_score": scores[username]["best_score"],
            "average_score": round(
                scores[username]["total_score"] / scores[username]["tests"],
                2,
            ),
        }
        for username in ranked_usernames
    ]
