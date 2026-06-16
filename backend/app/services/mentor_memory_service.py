from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS


def get_recent_mentor_memory(
    username: str,
    subject: str | None = None,
    chapter: str | None = None,
    limit: int = 5,
):
    """Fetch recent mentor-memory rows for a student, optionally scoped by topic."""
    query = (
        supabase
        .table("mentor_memory")
        .select("*")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if subject:
        query = query.eq("subject", subject)

    if chapter:
        query = query.eq("chapter", chapter)

    result = query.execute()

    return result.data or []


def build_memory_context(memories: list[dict]) -> str:
    """Convert mentor-memory rows into compact prompt context for the tutor."""
    if not memories:
        return "No prior mentor memory is available for this student yet."

    lines = [
        "Recent student mentor memory:",
    ]

    for item in memories:
        question = item.get("question") or ""
        memory_note = item.get("memory_note") or ""
        weakness = item.get("weakness_detected") or ""
        style = item.get("preferred_style") or ""
        confidence = item.get("confidence_level") or ""

        lines.append(
            f"- Question: {question[:180]}"
        )

        if memory_note:
            lines.append(f"  Memory note: {memory_note}")

        if weakness:
            lines.append(f"  Weakness detected: {weakness}")

        if style:
            lines.append(f"  Preferred style: {style}")

        if confidence:
            lines.append(f"  Confidence level: {confidence}")

    return "\n".join(lines)


def save_mentor_memory(
    username: str,
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    question: str,
    answer: str,
):
    """
    Save one answered interaction as future mentor context.

    Lightweight derived fields capture confidence/style signals without storing
    or replaying a full chat transcript in every future prompt.
    """
    answer_summary = answer[:500] if answer else ""

    memory_note = "Student asked a doubt in this chapter. Use this as continuity for future explanations."

    weakness_detected = ""
    preferred_style = ""
    confidence_level = ""

    lower_question = question.lower()

    if any(word in lower_question for word in ["confused", "don't understand", "dont understand", "not clear", "stuck"]):
        confidence_level = "low"
        weakness_detected = "Student appears confused about this concept."

    if any(word in lower_question for word in ["example", "real life", "real-life"]):
        preferred_style = "Prefers examples and real-life explanations."

    if any(word in lower_question for word in ["step", "slow", "simple", "easier"]):
        preferred_style = "Prefers slow, step-by-step explanations."

    payload = {
        "username": username,
        "grade": grade,
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "question": question,
        "answer_summary": answer_summary,
        "memory_note": memory_note,
        "weakness_detected": weakness_detected,
        "preferred_style": preferred_style,
        "confidence_level": confidence_level,
    }

    result = (
        supabase
        .table("mentor_memory")
        .insert(payload)
        .execute()
    )

    return result.data[0] if result.data else payload
