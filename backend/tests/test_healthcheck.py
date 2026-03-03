from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_contains_service_name_and_version() -> None:
    client = TestClient(app)
    response = client.get("/health")
    payload = response.json()

    assert "service_name" in payload
    assert "version" in payload
