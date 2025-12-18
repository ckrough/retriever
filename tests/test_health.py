"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client fixture."""
    return TestClient(app)


def test_health_check_returns_healthy(client: TestClient) -> None:
    """Health endpoint should return healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_check_includes_version(client: TestClient) -> None:
    """Health endpoint should include app version from settings."""
    response = client.get("/health")

    data = response.json()
    assert data["version"] == get_settings().app_version
