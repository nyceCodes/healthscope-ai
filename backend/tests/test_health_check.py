from fastapi.testclient import TestClient

from main import app


def test_health_check_verifies_the_database_without_exposing_details():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert app.debug is False
