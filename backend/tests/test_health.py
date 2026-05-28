from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """
    Test that the backend health check endpoint is working.

    This endpoint is usually used to confirm that the FastAPI backend
    is running and able to respond to requests.

    Expected result:
    - The endpoint should return HTTP 200.
    """
    response = client.get("/api/health")

    assert response.status_code == 200


def test_openapi_schema_loads():
    """
    Test that the FastAPI OpenAPI schema can be loaded.

    FastAPI automatically provides an OpenAPI schema at /openapi.json.
    This schema is used by the API docs and can also help frontend/backend
    developers understand the available API routes.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain a "paths" section.
    - The "paths" section should not be empty.
    """
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert "paths" in data
    assert len(data["paths"]) > 0