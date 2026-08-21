from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS


def get_chapter_progress(username, grade, mode, subject, chapter, profile_id=None):
    """Return saved progress for one chapter, or an initial progress object."""
    query = (
        supabase
        .table("student_progress")
        .select("*")
    )
    query = query.eq("profile_id", profile_id) if profile_id else query.eq("username", username)
    response = (
        query.eq("grade", grade)
        .eq("mode", mode)
        .eq("subject", subject)
        .eq("chapter", chapter)
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
    """Upsert progress for one chapter and preserve per-step lesson cache."""
    username = data.get("username")
    profile_id = data.get("profile_id")
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
        profile_id=profile_id,
    )

    step_lessons = existing.get("step_lessons") or {}

    if last_lesson:
        step_lessons[str(step_index)] = last_lesson

    payload = {
        "username": username,
        "profile_id": profile_id,
        "grade": grade,
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "current_step_index": step_index,
        "completed": data.get("completed", False),
        "last_lesson": last_lesson,
        "step_lessons": step_lessons,
    }

    response = (
        supabase
        .table("student_progress")
        .upsert(
            payload,
            on_conflict=(
                "profile_id,grade,mode,subject,chapter"
                if profile_id else "username,grade,mode,subject,chapter"
            )
        )
        .execute()
    )

    return response.data[0] if response.data else payload

def get_user_progress(username, profile_id=None):
    """Return all chapter-progress records for one username."""
    query = (
        supabase
        .table("student_progress")
        .select("*")
    )
    query = query.eq("profile_id", profile_id) if profile_id else query.eq("username", username)
    response = query.order("updated_at", desc=True).execute()

    return response.data or []
