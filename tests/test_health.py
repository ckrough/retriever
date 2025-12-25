"""Tests for health check endpoint."""

from src.config import get_settings
from src.main import app
from fastapi.testclient import TestClient


def test_health_check_returns_healthy() -> None:
    """Health endpoint should return healthy status."""
    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


def test_health_check_includes_version() -> None:
    """Health endpoint should include app version from settings."""
    with TestClient(app) as client:
        response = client.get("/health")

        data = response.json()
        assert data["version"] == get_settings().app_version
