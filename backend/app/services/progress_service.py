from app.services.supabase_client import supabase


def get_chapter_progress(username, grade, mode, subject, chapter):
    """Return saved progress for one chapter, or an initial progress object."""
    response = (
        supabase
        .table("student_progress")
        .select("*")
        .eq("username", username)
        .eq("grade", grade)
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
        "last_lesson": last_lesson,
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

def get_user_progress(username):
    """Return all chapter-progress records for one username."""
    response = (
        supabase
        .table("student_progress")
        .select("*")
        .eq("username", username)
        .order("updated_at", desc=True)
        .execute()
    )

    return response.data or []
