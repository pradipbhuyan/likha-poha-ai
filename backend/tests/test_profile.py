from fastapi.testclient import TestClient

from app.main import app
import app.routes.profile as profile_route

client = TestClient(app)


def test_get_profile_api_with_mocked_service(monkeypatch):
    """
    Test that the profile GET endpoint returns a student profile.

    This test uses monkeypatch to replace get_student_profile with a fake
    function. That means the test does not call Supabase and does not create
    or update real database records.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - profile should contain the mocked username and XP details.
    """

    def fake_get_student_profile(username):
        return {
            "username": username,
            "xp_points": 100,
            "student_level": 2,
            "rank_title": "Beginner",
        }

    monkeypatch.setattr(
        profile_route,
        "get_student_profile",
        fake_get_student_profile,
    )

    response = client.get("/api/profile/test_user")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["profile"]["username"] == "test_user"
    assert data["profile"]["xp_points"] == 100
    assert data["profile"]["student_level"] == 2
    assert data["profile"]["rank_title"] == "Beginner"


def test_log_activity_api_with_mocked_service(monkeypatch):
    """
    Test that the profile activity endpoint logs student activity.

    This test uses monkeypatch to replace update_student_activity with a fake
    function. That keeps the test safe because it avoids writing activity data
    to Supabase.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - profile should include the mocked updated activity values.
    """

    def fake_update_student_activity(username, activity_type):
        return {
            "username": username,
            "activity_type": activity_type,
            "xp_points": 25,
            "student_level": 1,
            "rank_title": "Beginner",
            "lessons_completed": 1,
        }

    monkeypatch.setattr(
        profile_route,
        "update_student_activity",
        fake_update_student_activity,
    )

    payload = {
        "username": "test_user",
        "activity_type": "lesson_completed",
    }

    response = client.post("/api/profile/activity", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["profile"]["username"] == "test_user"
    assert data["profile"]["activity_type"] == "lesson_completed"
    assert data["profile"]["xp_points"] == 25
    assert data["profile"]["lessons_completed"] == 1


def test_log_activity_missing_username():
    """
    Test that the profile activity endpoint rejects a missing username.

    Activity must belong to a specific student, so username is required.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 422 because the required field is missing.
    """
    payload = {
        "activity_type": "lesson_completed",
    }

    response = client.post("/api/profile/activity", json=payload)

    assert response.status_code == 422


def test_log_activity_missing_activity_type():
    """
    Test that the profile activity endpoint rejects a missing activity_type.

    The backend needs activity_type to know what kind of student activity
    was completed, such as lesson_completed or quiz_attempted.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 422 because the required field is missing.
    """
    payload = {
        "username": "test_user",
    }

    response = client.post("/api/profile/activity", json=payload)

    assert response.status_code == 422