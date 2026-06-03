def build_study_recommendations(history: list[dict]):
    """
    Build actionable study recommendations from test-history trends.

    The logic looks for weak subjects, strong subjects, latest low scores, and
    recent decline patterns, then returns a short prioritized list for the UI.
    """
    if not history:
        return [
            {
                "type": "start",
                "title": "Start with one mock test",
                "message": "Take one mock test so your AI tutor can identify strengths and weak areas.",
                "priority": "medium",
            }
        ]

    recommendations = []

    subject_map = {}

    for item in history:
        subject = item.get("subject") or "Unknown"
        score = float(item.get("percentage") or 0)

        if subject not in subject_map:
            subject_map[subject] = {
                "total": 0,
                "count": 0,
            }

        subject_map[subject]["total"] += score
        subject_map[subject]["count"] += 1

    subject_averages = {
        subject: round(data["total"] / data["count"], 2)
        for subject, data in subject_map.items()
    }

    weakest_subject = min(
        subject_averages,
        key=subject_averages.get,
    )

    strongest_subject = max(
        subject_averages,
        key=subject_averages.get,
    )

    weakest_score = subject_averages[weakest_subject]
    strongest_score = subject_averages[strongest_subject]

    if weakest_score < 60:
        recommendations.append({
            "type": "weak_subject",
            "title": f"Revise {weakest_subject}",
            "message": f"Your average score in {weakest_subject} is {weakest_score}%. Start with lesson review, then attempt a quiz.",
            "priority": "high",
        })
    elif weakest_score < 75:
        recommendations.append({
            "type": "practice_subject",
            "title": f"Practice more {weakest_subject}",
            "message": f"{weakest_subject} is your current improvement area. Try one focused quiz before the next mock test.",
            "priority": "medium",
        })

    if strongest_score >= 85:
        recommendations.append({
            "type": "strength",
            "title": f"Strong in {strongest_subject}",
            "message": f"You are performing well in {strongest_subject}. Try Olympiad-level questions to stretch your thinking.",
            "priority": "low",
        })

    latest = history[-1]
    latest_score = float(latest.get("percentage") or 0)

    if latest_score < 60:
        recommendations.append({
            "type": "latest_low",
            "title": "Review before next test",
            "message": "Your latest mock test score was low. Revise the chapter summary and solve 5 practice questions before retesting.",
            "priority": "high",
        })
    elif latest_score >= 90:
        recommendations.append({
            "type": "latest_high",
            "title": "Ready for harder practice",
            "message": "Excellent latest score. Move to Olympiad HOTS questions for this chapter.",
            "priority": "low",
        })

    if len(history) >= 3:
        recent_scores = [
            float(item.get("percentage") or 0)
            for item in history[-3:]
        ]

        if recent_scores[-1] < recent_scores[0]:
            recommendations.append({
                "type": "decline",
                "title": "Performance dipped recently",
                "message": "Your recent score trend is going down. Review mistakes from the last two tests.",
                "priority": "medium",
            })

    if not recommendations:
        recommendations.append({
            "type": "steady",
            "title": "Keep a steady routine",
            "message": "Continue one lesson, one quiz, and one mock test cycle each week.",
            "priority": "low",
        })

    return recommendations[:4]
