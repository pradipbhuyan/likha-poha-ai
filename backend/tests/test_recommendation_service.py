from app.services.recommendation_service import build_study_recommendations


def test_recommendations_for_empty_history():
    """
    Test recommendations when a student has no test history.

    If there is no history, the platform should encourage the student
    to start with one mock test so the tutor can identify strengths and
    weak areas.

    Expected result:
    - One recommendation should be returned.
    - The recommendation type should be "start".
    - The priority should be "medium".
    """
    recommendations = build_study_recommendations([])

    assert len(recommendations) == 1
    assert recommendations[0]["type"] == "start"
    assert recommendations[0]["priority"] == "medium"


def test_recommendations_for_weak_subject():
    """
    Test recommendations when a student has a weak subject.

    A subject average below 60 should generate a high-priority
    recommendation to revise that subject.

    Expected result:
    - At least one recommendation should have type "weak_subject".
    - The recommendation should have high priority.
    """
    history = [
        {
            "subject": "Science",
            "percentage": 45,
        },
        {
            "subject": "Science",
            "percentage": 55,
        },
        {
            "subject": "Math",
            "percentage": 85,
        },
    ]

    recommendations = build_study_recommendations(history)

    weak_subject_recommendation = next(
        item for item in recommendations if item["type"] == "weak_subject"
    )

    assert weak_subject_recommendation["priority"] == "high"
    assert "Science" in weak_subject_recommendation["title"]


def test_recommendations_for_strong_subject():
    """
    Test recommendations when a student has a strong subject.

    A subject average of 85 or above should generate a low-priority
    recommendation encouraging harder practice.

    Expected result:
    - At least one recommendation should have type "strength".
    - The recommendation should have low priority.
    """
    history = [
        {
            "subject": "Science",
            "percentage": 88,
        },
        {
            "subject": "Science",
            "percentage": 92,
        },
        {
            "subject": "Math",
            "percentage": 70,
        },
    ]

    recommendations = build_study_recommendations(history)

    strength_recommendation = next(
        item for item in recommendations if item["type"] == "strength"
    )

    assert strength_recommendation["priority"] == "low"
    assert "Science" in strength_recommendation["title"]


def test_recommendations_for_latest_low_score():
    """
    Test recommendations when the latest mock test score is low.

    If the latest score is below 60, the platform should recommend
    reviewing before taking the next test.

    Expected result:
    - At least one recommendation should have type "latest_low".
    - The recommendation should have high priority.
    """
    history = [
        {
            "subject": "Science",
            "percentage": 80,
        },
        {
            "subject": "Science",
            "percentage": 50,
        },
    ]

    recommendations = build_study_recommendations(history)

    latest_low_recommendation = next(
        item for item in recommendations if item["type"] == "latest_low"
    )

    assert latest_low_recommendation["priority"] == "high"


def test_recommendations_for_declining_recent_scores():
    """
    Test recommendations when recent scores are going down.

    If the latest score is lower than the first score in the last three
    attempts, the platform should warn the student that performance has
    dipped recently.

    Expected result:
    - At least one recommendation should have type "decline".
    - The recommendation should have medium priority.
    """
    history = [
        {
            "subject": "Science",
            "percentage": 85,
        },
        {
            "subject": "Science",
            "percentage": 75,
        },
        {
            "subject": "Science",
            "percentage": 65,
        },
    ]

    recommendations = build_study_recommendations(history)

    decline_recommendation = next(
        item for item in recommendations if item["type"] == "decline"
    )

    assert decline_recommendation["priority"] == "medium"


def test_recommendations_returns_maximum_four_items():
    """
    Test that the recommendation list is limited to four items.

    This helps keep the frontend recommendation panel short and focused.

    Expected result:
    - The returned list should contain no more than four recommendations.
    """
    history = [
        {
            "subject": "Science",
            "percentage": 40,
        },
        {
            "subject": "Science",
            "percentage": 45,
        },
        {
            "subject": "Math",
            "percentage": 95,
        },
        {
            "subject": "English",
            "percentage": 55,
        },
        {
            "subject": "Social Science",
            "percentage": 92,
        },
    ]

    recommendations = build_study_recommendations(history)

    assert len(recommendations) <= 4
    
