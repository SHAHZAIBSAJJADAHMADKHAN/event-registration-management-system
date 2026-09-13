from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_application_starts_and_api_root_is_available() -> None:
    response = client.get("/api/")

    assert response.status_code == 200
    assert response.json()["service"] == "event-management-api"


def test_health_endpoint_returns_expected_contract() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "event-management-api",
    }
