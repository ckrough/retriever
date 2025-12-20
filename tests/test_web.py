"""Tests for web routes."""

from collections.abc import Generator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.llm import LLMProviderError, OpenRouterProvider
from src.main import app
from src.web.dependencies import require_auth
from src.web.routes import MAX_QUESTION_LENGTH, get_llm_provider

# Mock user for authenticated tests
MOCK_USER = {
    "user_id": str(uuid4()),
    "email": "test@example.com",
    "is_admin": False,
}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client fixture with mocked authentication."""
    # Clear any existing overrides
    app.dependency_overrides.clear()
    # Mock authentication to return test user (simulates logged-in user)
    app.dependency_overrides[require_auth] = lambda: MOCK_USER
    yield TestClient(app)
    # Clean up after test
    app.dependency_overrides.clear()


class TestIndexPage:
    """Tests for the index page."""

    def test_index_page_loads(self, client: TestClient) -> None:
        """Main page should load successfully."""
        response = client.get("/")

        assert response.status_code == 200
        assert "Retriever" in response.text
        assert "Volunteer Assistant" in response.text


class TestAskEndpointValidation:
    """Tests for ask endpoint input validation."""

    @pytest.fixture(autouse=True)
    def use_fallback_llm(self) -> Generator[None, None, None]:
        """Use fallback LLM for all validation tests (faster)."""
        app.dependency_overrides[get_llm_provider] = lambda: None
        yield
        app.dependency_overrides.clear()

    def test_ask_endpoint_requires_question(self, client: TestClient) -> None:
        """Ask endpoint should require a question."""
        response = client.post("/ask", data={})

        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_rejects_empty_question(self, client: TestClient) -> None:
        """Ask endpoint should reject empty string questions."""
        response = client.post("/ask", data={"question": ""})

        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_rejects_oversized_question(self, client: TestClient) -> None:
        """Ask endpoint should reject questions exceeding max length."""
        huge_question = "x" * (MAX_QUESTION_LENGTH + 1)
        response = client.post("/ask", data={"question": huge_question})

        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_escapes_html(self, client: TestClient) -> None:
        """Ask endpoint should escape HTML in user input (XSS prevention)."""
        malicious_input = "<script>alert('xss')</script>"
        response = client.post("/ask", data={"question": malicious_input})

        assert response.status_code == 200
        # Jinja2 auto-escapes by default - script tag should be escaped
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text


class TestAskEndpointFallback:
    """Tests for ask endpoint without LLM configured."""

    def test_returns_fallback_when_no_api_key(self, client: TestClient) -> None:
        """Ask endpoint should return fallback response when LLM not configured."""
        # Override dependency to return None (simulating no API key)
        app.dependency_overrides[get_llm_provider] = lambda: None

        response = client.post("/ask", data={"question": "Hello"})

        assert response.status_code == 200
        assert "Hello" in response.text  # Question echoed back
        assert "Retriever" in response.text  # Answer contains app name
        assert "LLM not configured" in response.text


class TestAskEndpointWithLLM:
    """Tests for ask endpoint with LLM provider."""

    def test_returns_llm_response_when_configured(self, client: TestClient) -> None:
        """Ask endpoint should return LLM response when configured."""
        # Create a mock provider
        mock_provider = AsyncMock(spec=OpenRouterProvider)
        mock_provider.complete = AsyncMock(
            return_value="The capital of France is Paris."
        )

        # Override dependency to return our mock
        app.dependency_overrides[get_llm_provider] = lambda: mock_provider

        response = client.post(
            "/ask", data={"question": "What is the capital of France?"}
        )

        assert response.status_code == 200
        assert "What is the capital of France?" in response.text
        assert "capital of France is Paris" in response.text

    def test_shows_error_message_on_llm_failure(self, client: TestClient) -> None:
        """Ask endpoint should show error message when LLM fails."""
        # Create a mock provider that raises an error
        mock_provider = AsyncMock(spec=OpenRouterProvider)
        mock_provider.complete = AsyncMock(
            side_effect=LLMProviderError("API error", provider="openrouter")
        )

        # Override dependency to return our mock
        app.dependency_overrides[get_llm_provider] = lambda: mock_provider

        response = client.post("/ask", data={"question": "Test question"})

        assert response.status_code == 200
        # Should show the question
        assert "Test question" in response.text
        # Should show error message
        assert "trouble connecting" in response.text


class TestRateLimiting:
    """Tests for rate limiting.

    These tests use a fresh limiter storage to avoid state from other tests.
    """

    @pytest.fixture
    def fresh_rate_limit_client(self) -> Generator[TestClient, None, None]:
        """Client with fresh rate limit storage."""
        from src.api.rate_limit import limiter

        # Clear rate limit storage, use fallback LLM, and mock auth
        limiter.reset()
        app.dependency_overrides[get_llm_provider] = lambda: None
        app.dependency_overrides[require_auth] = lambda: MOCK_USER
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_rate_limit_exceeded_returns_429(
        self, fresh_rate_limit_client: TestClient
    ) -> None:
        """Should return 429 after exceeding rate limit (10/minute)."""
        # Make 11 requests to exceed the 10/minute limit
        for i in range(11):
            response = fresh_rate_limit_client.post("/ask", data={"question": f"Q{i}"})
            if response.status_code == 429:
                break

        assert response.status_code == 429
        assert "Too many requests" in response.text

    def test_rate_limit_error_includes_friendly_message(
        self, fresh_rate_limit_client: TestClient
    ) -> None:
        """Rate limit error should include user-friendly message."""
        # Make 11 requests to exceed the 10/minute limit
        for i in range(11):
            response = fresh_rate_limit_client.post("/ask", data={"question": f"Q{i}"})
            if response.status_code == 429:
                break

        assert "Please wait" in response.text
