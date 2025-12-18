"""Tests for web routes."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.web.routes import MAX_QUESTION_LENGTH


@pytest.fixture
def client() -> TestClient:
    """Create test client fixture."""
    return TestClient(app)


def test_index_page_loads(client: TestClient) -> None:
    """Main page should load successfully."""
    response = client.get("/")

    assert response.status_code == 200
    assert "GoodPuppy" in response.text
    assert "Volunteer Assistant" in response.text


def test_ask_endpoint_returns_answer(client: TestClient) -> None:
    """Ask endpoint should return hardcoded answer."""
    response = client.post("/ask", data={"question": "Hello"})

    assert response.status_code == 200
    assert "Hello" in response.text  # Question echoed back
    assert "GoodPuppy" in response.text  # Answer contains app name


def test_ask_endpoint_requires_question(client: TestClient) -> None:
    """Ask endpoint should require a question."""
    response = client.post("/ask", data={})

    assert response.status_code == 422  # Validation error


def test_ask_endpoint_rejects_empty_question(client: TestClient) -> None:
    """Ask endpoint should reject empty string questions."""
    response = client.post("/ask", data={"question": ""})

    assert response.status_code == 422  # Validation error


def test_ask_endpoint_rejects_oversized_question(client: TestClient) -> None:
    """Ask endpoint should reject questions exceeding max length."""
    huge_question = "x" * (MAX_QUESTION_LENGTH + 1)
    response = client.post("/ask", data={"question": huge_question})

    assert response.status_code == 422  # Validation error


def test_ask_endpoint_escapes_html(client: TestClient) -> None:
    """Ask endpoint should escape HTML in user input (XSS prevention)."""
    malicious_input = "<script>alert('xss')</script>"
    response = client.post("/ask", data={"question": malicious_input})

    assert response.status_code == 200
    # Jinja2 auto-escapes by default - script tag should be escaped
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
