def save_doubt_history(
    client,
    profile_id: str,
    username: str,
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    question: str,
    prompt_question: str,
    answer: str,
    source_type: str,
    sources: list[dict],
    mentor_suggestions: list[str],
):
    """
    Persist the full Ask Doubt answer for student review history.

    This is intentionally separate from mentor_memory, which stores only a
    compact summary for future prompts. History is for the student's UI.
    """
    payload = {
        "profile_id": profile_id,
        "username": username,
        "grade": grade,
        "mode": mode,
        "subject": subject or "",
        "chapter": chapter or "",
        "question": question,
        "prompt_question": prompt_question or question,
        "answer": answer,
        "source_type": source_type or "LLM",
        "sources": sources or [],
        "mentor_suggestions": mentor_suggestions or [],
    }

    result = (
        client
        .table("doubt_history")
        .insert(payload)
        .execute()
    )

    return result.data[0] if result.data else payload


def list_doubt_history(
    client,
    profile_id: str,
    limit: int = 20,
):
    """Return recent Ask Doubt history rows for one authenticated student."""
    safe_limit = max(1, min(50, int(limit or 20)))

    result = (
        client
        .table("doubt_history")
        .select("*")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )

    return result.data or []
