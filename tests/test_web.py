"""Tests for web routes."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_index_page_loads() -> None:
    """Main page should load successfully."""
    response = client.get("/")

    assert response.status_code == 200
    assert "GoodPuppy" in response.text
    assert "Volunteer Assistant" in response.text


def test_ask_endpoint_returns_answer() -> None:
    """Ask endpoint should return hardcoded answer."""
    response = client.post("/ask", data={"question": "Hello"})

    assert response.status_code == 200
    assert "Hello" in response.text  # Question echoed back
    assert "GoodPuppy" in response.text  # Answer contains app name


def test_ask_endpoint_requires_question() -> None:
    """Ask endpoint should require a question."""
    response = client.post("/ask", data={})

    assert response.status_code == 422  # Validation error
