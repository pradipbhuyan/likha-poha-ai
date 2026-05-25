from datetime import date, timedelta

from app.services.supabase_client import supabase


XP_REWARDS = {
    "lesson_completed": 25,
    "quiz_attempted": 10,
    "mock_test_taken": 40,
    "visual_generated": 15,
}


def calculate_level(xp_points: int) -> int:
    # Simple level curve: every 100 XP = 1 level
    return max(1, (xp_points // 100) + 1)


def calculate_rank_title(level: int) -> str:
    if level >= 20:
        return "AI Scholar"
    if level >= 15:
        return "Olympiad Master"
    if level >= 10:
        return "Concept Champion"
    if level >= 5:
        return "Active Learner"
    return "Beginner"


def get_student_profile(username: str):
    response = (
        supabase
        .table("student_profiles")
        .select("*")
        .eq("username", username)
        .execute()
    )

    if response.data:
        return response.data[0]

    profile = {
        "username": username,
        "study_streak_days": 0,
        "lessons_completed": 0,
        "quizzes_attempted": 0,
        "mock_tests_taken": 0,
        "visuals_generated": 0,
        "achievement_count": 0,
        "xp_points": 0,
        "student_level": 1,
        "rank_title": "Beginner",
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

    current_xp = int(profile.get("xp_points") or 0)
    earned_xp = XP_REWARDS.get(activity_type, 5)
    new_xp = current_xp + earned_xp
    new_level = calculate_level(new_xp)
    new_rank = calculate_rank_title(new_level)

    updates = {
        "study_streak_days": new_streak,
        "last_active_date": today.isoformat(),
        "xp_points": new_xp,
        "student_level": new_level,
        "rank_title": new_rank,
    }

    if activity_type == "lesson_completed":
        updates["lessons_completed"] = int(profile.get("lessons_completed") or 0) + 1

    if activity_type == "quiz_attempted":
        updates["quizzes_attempted"] = int(profile.get("quizzes_attempted") or 0) + 1

    if activity_type == "mock_test_taken":
        updates["mock_tests_taken"] = int(profile.get("mock_tests_taken") or 0) + 1

    if activity_type == "visual_generated":
        updates["visuals_generated"] = int(profile.get("visuals_generated") or 0) + 1

    response = (
        supabase
        .table("student_profiles")
        .update(updates)
        .eq("username", username)
        .execute()
    )

    return response.data[0] if response.data else get_student_profile(username)


def get_chapter_progress(username, grade, mode, subject, chapter):
    response = (
        supabase
        .table("student_progress")
        .select("*")
        .eq("username", username)
        .eq("grade", grade)
        .eq("mode", mode)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .limit(1)
        .execute()
    )

    if response.data:
        progress = response.data[0]

        step_index = int(progress.get("current_step_index") or 0)
        step_lessons = progress.get("step_lessons") or {}

        progress["last_lesson"] = (
            step_lessons.get(str(step_index))
            or progress.get("last_lesson")
            or ""
        )

        return progress

    return {
        "username": username,
        "grade": grade,
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "current_step_index": 0,
        "completed": False,
        "last_lesson": "",
        "step_lessons": {},
        "updated_at": None,
    }
    
    response = (
        supabase
        .table("student_progress")
        .select("*")
        .eq("username", username)
        .eq("grade", grade)
        .eq("mode", mode)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return {
        "username": username,
        "grade": grade,
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "current_step_index": 0,
        "completed": False,
        "last_lesson": "",
        "updated_at": None,
    }


def save_chapter_progress(data):
    username = data.get("username")
    grade = data.get("grade")
    mode = data.get("mode")
    subject = data.get("subject")
    chapter = data.get("chapter")
    step_index = int(data.get("current_step_index", 0))
    last_lesson = data.get("last_lesson", "")

    existing = get_chapter_progress(
        username=username,
        grade=grade,
        mode=mode,
        subject=subject,
        chapter=chapter,
    )

    step_lessons = existing.get("step_lessons") or {}

    if last_lesson:
        step_lessons[str(step_index)] = last_lesson

    payload = {
        "username": username,
        "grade": grade,
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "current_step_index": step_index,
        "completed": data.get("completed", False),
        "last_lesson": last_lesson or existing.get("last_lesson", ""),
        "step_lessons": step_lessons,
    }

    response = (
        supabase
        .table("student_progress")
        .upsert(
            payload,
            on_conflict="username,grade,mode,subject,chapter"
        )
        .execute()
    )

    return response.data[0] if response.data else payload
    payload = {
        "username": data.get("username"),
        "grade": data.get("grade"),
        "mode": data.get("mode"),
        "subject": data.get("subject"),
        "chapter": data.get("chapter"),
        "current_step_index": data.get("current_step_index", 0),
        "completed": data.get("completed", False),
        "last_lesson": data.get("last_lesson", ""),
    }

    response = (
        supabase
        .table("student_progress")
        .upsert(
            payload,
            on_conflict="username,grade,mode,subject,chapter"
        )
        .execute()
    )

    return response.data[0] if response.data else payload


def get_user_progress(username):
    response = (
        supabase
        .table("student_progress")
        .select("*")
        .eq("username", username)
        .order("updated_at", desc=True)
        .execute()
    )

    return response.data or []
