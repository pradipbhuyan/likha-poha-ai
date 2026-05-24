from datetime import date, timedelta
from app.services.supabase_client import supabase


def get_student_profile(username: str):
    result = (
        supabase.table("student_profiles")
        .select("*")
        .eq("username", username)
        .execute()
    )

    if result.data:
        return result.data[0]

    profile = {
        "username": username,
        "study_streak_days": 0,
        "lessons_completed": 0,
        "quizzes_attempted": 0,
        "mock_tests_taken": 0,
        "visuals_generated": 0,
        "achievement_count": 0,
        "last_active_date": None,
    }

    supabase.table("student_profiles").insert(profile).execute()

    return profile


def update_student_activity(username: str, activity_type: str):
    profile = get_student_profile(username)

    today = date.today()
    last_active = profile.get("last_active_date")

    current_streak = int(profile.get("study_streak_days") or 0)

    if last_active:
        last_active_date = date.fromisoformat(last_active)

        if last_active_date == today:
            new_streak = current_streak
        elif last_active_date == today - timedelta(days=1):
            new_streak = current_streak + 1
        else:
            new_streak = 1
    else:
        new_streak = 1

    updates = {
        "study_streak_days": new_streak,
        "last_active_date": today.isoformat(),
    }

    if activity_type == "lesson_completed":
        updates["lessons_completed"] = int(profile.get("lessons_completed") or 0) + 1

    if activity_type == "quiz_attempted":
        updates["quizzes_attempted"] = int(profile.get("quizzes_attempted") or 0) + 1

    if activity_type == "mock_test_taken":
        updates["mock_tests_taken"] = int(profile.get("mock_tests_taken") or 0) + 1

    if activity_type == "visual_generated":
        updates["visuals_generated"] = int(profile.get("visuals_generated") or 0) + 1

    result = (
        supabase.table("student_profiles")
        .update(updates)
        .eq("username", username)
        .execute()
    )

    return result.data[0] if result.data else get_student_profile(username)