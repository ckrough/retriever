"""Tests for content moderation using OpenAI Moderation API."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.infrastructure.safety.moderation import NoOpModerator, OpenAIModerator
from src.infrastructure.safety.schemas import ModerationResult


class TestOpenAIModeratorInit:
    """Tests for OpenAIModerator initialization."""

    def test_init_with_valid_api_key(self):
        """Test initialization with a valid API key."""
        moderator = OpenAIModerator(api_key="test-key-123")
        assert moderator._api_key == "test-key-123"
        assert moderator._timeout == 10.0

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        moderator = OpenAIModerator(api_key="test-key", timeout_seconds=5.0)
        assert moderator._timeout == 5.0


class TestOpenAIModeratorCheck:
    """Tests for OpenAIModerator.check method."""

    @pytest.mark.asyncio
    async def test_check_returns_safe_result_for_safe_content(self):
        """Test check returns safe result for non-flagged content."""
        moderator = OpenAIModerator(api_key="test-key")

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "flagged": False,
                    "categories": {"hate": False, "violence": False},
                    "category_scores": {"hate": 0.1, "violence": 0.05},
                }
            ]
        }
        moderator._client.post = AsyncMock(return_value=mock_response)

        result = await moderator.check("This is safe content")

        assert isinstance(result, ModerationResult)
        assert result.flagged is False
        assert result.categories == {"hate": False, "violence": False}

        await moderator.close()

    @pytest.mark.asyncio
    async def test_check_returns_flagged_result_for_unsafe_content(self):
        """Test check returns flagged result for unsafe content."""
        moderator = OpenAIModerator(api_key="test-key")

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "flagged": True,
                    "categories": {"hate": True, "violence": False},
                    "category_scores": {"hate": 0.9, "violence": 0.1},
                }
            ]
        }
        moderator._client.post = AsyncMock(return_value=mock_response)

        result = await moderator.check("Unsafe content")

        assert isinstance(result, ModerationResult)
        assert result.flagged is True
        assert result.categories["hate"] is True

        await moderator.close()

    @pytest.mark.asyncio
    async def test_check_handles_timeout_gracefully(self):
        """Test check returns safe result on timeout (fail open)."""
        moderator = OpenAIModerator(api_key="test-key")

        # Mock timeout exception
        moderator._client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        result = await moderator.check("Some text")

        # Should fail open (return safe result)
        assert isinstance(result, ModerationResult)
        assert result.flagged is False
        assert result.categories == {}

        await moderator.close()

    @pytest.mark.asyncio
    async def test_check_handles_http_error_gracefully(self):
        """Test check returns safe result on HTTP error (fail open)."""
        moderator = OpenAIModerator(api_key="test-key")

        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )
        moderator._client.post = AsyncMock(side_effect=error)

        result = await moderator.check("Some text")

        # Should fail open (return safe result)
        assert isinstance(result, ModerationResult)
        assert result.flagged is False
        assert result.categories == {}

        await moderator.close()

    @pytest.mark.asyncio
    async def test_check_handles_unexpected_error_gracefully(self):
        """Test check returns safe result on unexpected error (fail open)."""
        moderator = OpenAIModerator(api_key="test-key")

        # Mock unexpected exception
        moderator._client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        result = await moderator.check("Some text")

        # Should fail open (return safe result)
        assert isinstance(result, ModerationResult)
        assert result.flagged is False
        assert result.categories == {}

        await moderator.close()

    @pytest.mark.asyncio
    async def test_close_closes_http_client(self):
        """Test close method closes the HTTP client."""
        moderator = OpenAIModerator(api_key="test-key")
        moderator._client.aclose = AsyncMock()

        await moderator.close()

        moderator._client.aclose.assert_called_once()


class TestNoOpModerator:
    """Tests for NoOpModerator."""

    @pytest.mark.asyncio
    async def test_check_always_returns_safe(self):
        """Test NoOpModerator always returns safe result."""
        moderator = NoOpModerator()

        result = await moderator.check("Any text at all")

        assert isinstance(result, ModerationResult)
        assert result.flagged is False
        assert result.categories == {}

    @pytest.mark.asyncio
    async def test_close_does_nothing(self):
        """Test NoOpModerator close method is a no-op."""
        moderator = NoOpModerator()

        # Should not raise any exception
        await moderator.close()
