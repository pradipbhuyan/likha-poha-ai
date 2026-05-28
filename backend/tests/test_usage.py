from fastapi.testclient import TestClient

from app.main import app
import app.routes.usage as usage_route

client = TestClient(app)


class FakeUsageResult:
    """
    Small fake object that behaves like the Supabase response object.

    The real Supabase response has a .data attribute.
    Our route reads result.data, so this fake object gives the route
    the same shape without calling the real database.
    """

    def __init__(self, data):
        self.data = data


class FakeUsageQuery:
    """
    Fake Supabase query chain for usage summary tests.

    The real route calls:
    supabase.table(...).select(...).order(...).eq(...).execute()

    This fake class supports those same method names and returns itself
    until execute() returns fake data.
    """

    def __init__(self, data):
        self.data = data
        self.filtered_username = None

    def select(self, value):
        return self

    def order(self, column, desc=False):
        return self

    def eq(self, column, value):
        if column == "username":
            self.filtered_username = value
        return self

    def execute(self):
        if self.filtered_username:
            filtered_data = [
                item
                for item in self.data
                if item.get("username") == self.filtered_username
            ]
            return FakeUsageResult(filtered_data)

        return FakeUsageResult(self.data)


class FakeUsageSupabase:
    """
    Fake Supabase client for usage route tests.

    It returns FakeUsageQuery whenever the route asks for a table.
    """

    def __init__(self, data):
        self.data = data

    def table(self, table_name):
        assert table_name == "ai_usage_logs"
        return FakeUsageQuery(self.data)


def test_usage_summary_returns_totals_with_mocked_supabase(monkeypatch):
    """
    Test that the usage summary endpoint calculates total usage correctly.

    This test mocks Supabase so it does not read from the real database.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - totals should include combined cost, tokens, images, and request count.
    """
    fake_logs = [
        {
            "username": "test_user",
            "feature": "lesson",
            "estimated_cost": 1.25,
            "total_tokens": 1000,
            "image_count": 0,
            "tts_chars": 0,
        },
        {
            "username": "test_user",
            "feature": "doubt",
            "estimated_cost": 0.75,
            "total_tokens": 500,
            "image_count": 1,
            "tts_chars": 100,
        },
    ]

    monkeypatch.setattr(
        usage_route,
        "supabase",
        FakeUsageSupabase(fake_logs),
    )

    response = client.get("/api/usage/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["totals"]["total_cost"] == 2.0
    assert data["totals"]["total_tokens"] == 1500
    assert data["totals"]["total_images"] == 1
    assert data["totals"]["total_tts_chars"] == 100
    assert data["totals"]["requests"] == 2


def test_usage_summary_filters_by_username_with_mocked_supabase(monkeypatch):
    """
    Test that the usage summary endpoint can filter logs by username.

    This checks the optional query parameter:
    /api/usage/summary?username=test_user

    Expected result:
    - Only logs for the requested username should be included.
    - Totals should be calculated from the filtered logs.
    """
    fake_logs = [
        {
            "username": "test_user",
            "feature": "lesson",
            "estimated_cost": 1.0,
            "total_tokens": 1000,
            "image_count": 0,
            "tts_chars": 0,
        },
        {
            "username": "other_user",
            "feature": "lesson",
            "estimated_cost": 9.0,
            "total_tokens": 9000,
            "image_count": 5,
            "tts_chars": 500,
        },
    ]

    monkeypatch.setattr(
        usage_route,
        "supabase",
        FakeUsageSupabase(fake_logs),
    )

    response = client.get("/api/usage/summary?username=test_user")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["totals"]["total_cost"] == 1.0
    assert data["totals"]["total_tokens"] == 1000
    assert data["totals"]["requests"] == 1
    assert data["by_user"][0]["username"] == "test_user"


def test_usage_summary_creates_alerts_when_usage_is_high(monkeypatch):
    """
    Test that the usage summary endpoint creates alerts for high usage.

    The route should create alerts when:
    - total cost is at least $5
    - image count is at least 25
    - token usage is at least 100,000

    Expected result:
    - The response should contain three alerts.
    """
    fake_logs = [
        {
            "username": "test_user",
            "feature": "lesson",
            "estimated_cost": 5.5,
            "total_tokens": 100000,
            "image_count": 25,
            "tts_chars": 0,
        },
    ]

    monkeypatch.setattr(
        usage_route,
        "supabase",
        FakeUsageSupabase(fake_logs),
    )

    response = client.get("/api/usage/summary")

    assert response.status_code == 200

    data = response.json()

    assert len(data["alerts"]) == 3
    assert data["alerts"][0]["level"] == "high"
    assert data["alerts"][1]["level"] == "medium"
    assert data["alerts"][2]["level"] == "medium"