"""Tests for root and health endpoints."""

from app import __version__


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Every Ball Wins!"
    assert "docs" in body


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def test_openapi_schema_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Every Ball Wins"
    assert "/api/v1/balls" in schema["paths"]
