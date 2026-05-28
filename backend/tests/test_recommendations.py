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