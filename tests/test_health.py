"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check_returns_healthy() -> None:
    """Health endpoint should return healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_check_includes_version() -> None:
    """Health endpoint should include app version."""
    response = client.get("/health")

    data = response.json()
    assert data["version"] == "0.1.0"
