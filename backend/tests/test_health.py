"""Tests for the health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from retriever.main import app


@pytest.mark.asyncio
async def test_health_returns_200() -> None:
    """Health endpoint returns 200 with healthy status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
