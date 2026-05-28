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
    
from fastapi.testclient import TestClient

from app.main import app
import app.routes.recommendations as recommendations_route

client = TestClient(app)


class FakeRecommendationResult:
    """
    Fake Supabase result object.

    The real Supabase execute() response has a .data attribute.
    This fake object gives the route the same shape without calling
    the real database.
    """

    def __init__(self, data):
        self.data = data


class FakeRecommendationQuery:
    """
    Fake Supabase query chain for recommendation route tests.

    The real route calls:
    supabase.table(...).select(...).eq(...).order(...).execute()

    This fake class supports the same method names and returns itself
    until execute() returns fake test history.
    """

    def __init__(self, data):
        self.data = data
        self.filtered_username = None

    def select(self, value):
        return self

    def eq(self, column, value):
        if column == "username":
            self.filtered_username = value
        return self

    def order(self, column):
        return self

    def execute(self):
        if self.filtered_username:
            filtered_data = [
                item
                for item in self.data
                if item.get("username") == self.filtered_username
            ]
            return FakeRecommendationResult(filtered_data)

        return FakeRecommendationResult(self.data)


class FakeRecommendationSupabase:
    """
    Fake Supabase client for recommendation route tests.

    It returns FakeRecommendationQuery whenever the route asks for
    the test_history table.
    """

    def __init__(self, data):
        self.data = data

    def table(self, table_name):
        assert table_name == "test_history"
        return FakeRecommendationQuery(self.data)


def test_get_recommendations_api_with_mocked_supabase(monkeypatch):
    """
    Test that the recommendations endpoint returns study recommendations.

    This test mocks Supabase so it does not read from the real database.
    It provides fake test history for one user and verifies that the route
    returns recommendations based on that history.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - recommendations should be a list.
    - At least one recommendation should be returned.
    """
    fake_history = [
        {
            "username": "test_user",
            "subject": "Science",
            "percentage": 50,
        },
        {
            "username": "test_user",
            "subject": "Math",
            "percentage": 90,
        },
        {
            "username": "other_user",
            "subject": "Science",
            "percentage": 10,
        },
    ]

    monkeypatch.setattr(
        recommendations_route,
        "supabase",
        FakeRecommendationSupabase(fake_history),
    )

    response = client.get("/api/recommendations/test_user")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0