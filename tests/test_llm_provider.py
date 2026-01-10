"""Tests for LLM provider infrastructure."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from src.infrastructure.llm import (
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    OpenRouterProvider,
)


class TestOpenRouterProviderInit:
    """Tests for OpenRouterProvider initialization."""

    def test_init_with_valid_api_key(self):
        """Provider should initialize with valid API key."""
        provider = OpenRouterProvider(api_key="test-key")

        assert provider._default_model == "anthropic/claude-sonnet-4"
        assert provider._timeout == 30.0

    def test_init_with_custom_model(self):
        """Provider should accept custom default model."""
        provider = OpenRouterProvider(
            api_key="test-key",
            default_model="anthropic/claude-haiku",
        )

        assert provider._default_model == "anthropic/claude-haiku"

    def test_init_with_empty_api_key_raises(self):
        """Provider should raise error with empty API key."""
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenRouterProvider(api_key="")

        assert "API key is required" in str(exc_info.value)
        assert exc_info.value.provider == "openrouter"

    def test_init_with_custom_circuit_breaker_settings(self):
        """Provider should accept custom circuit breaker settings."""
        provider = OpenRouterProvider(
            api_key="test-key",
            circuit_breaker_fail_max=3,
            circuit_breaker_timeout=30.0,
        )

        assert provider._breaker._fail_max == 3

    def test_init_with_prompt_caching_enabled_by_default(self):
        """Provider should enable prompt caching by default."""
        provider = OpenRouterProvider(api_key="test-key")

        assert provider._enable_prompt_caching is True

    def test_init_with_prompt_caching_disabled(self):
        """Provider should accept disabled prompt caching."""
        provider = OpenRouterProvider(
            api_key="test-key",
            enable_prompt_caching=False,
        )

        assert provider._enable_prompt_caching is False


class TestOpenRouterProviderComplete:
    """Tests for OpenRouterProvider.complete() method."""

    @pytest.fixture
    def provider(self):
        """Create a provider with a mocked client."""
        provider = OpenRouterProvider(api_key="test-key")
        return provider

    @pytest.fixture
    def mock_response(self):
        """Create a mock API response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Test response"
        # Mock usage with no cache activity
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 0
        type(usage).cache_creation_input_tokens = 0
        response.usage = usage
        return response

    async def test_complete_returns_content(self, provider, mock_response):
        """Complete should return the message content."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        assert result == "Test response"

    async def test_complete_uses_default_model(self, provider, mock_response):
        """Complete should use default model when not specified."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "anthropic/claude-sonnet-4"

    async def test_complete_with_custom_model(self, provider, mock_response):
        """Complete should use specified model."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
            model="anthropic/claude-haiku",
        )

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "anthropic/claude-haiku"

    async def test_complete_includes_cache_control_when_enabled(
        self, provider, mock_response
    ):
        """Complete should include cache_control in system message when enabled."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        system_msg = messages[0]

        # Verify cache control structure
        assert system_msg["role"] == "system"
        assert isinstance(system_msg["content"], list)
        assert len(system_msg["content"]) == 1
        assert system_msg["content"][0]["type"] == "text"
        assert system_msg["content"][0]["text"] == "You are helpful."
        assert system_msg["content"][0]["cache_control"] == {"type": "ephemeral"}

    async def test_complete_excludes_cache_control_when_disabled(self, mock_response):
        """Complete should use plain string content when caching disabled."""
        provider = OpenRouterProvider(api_key="test-key", enable_prompt_caching=False)
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        system_msg = messages[0]

        # Verify plain string format
        assert system_msg["role"] == "system"
        assert system_msg["content"] == "You are helpful."

    async def test_complete_with_history_includes_cache_control(
        self, provider, mock_response
    ):
        """Complete with history should include cache_control in system message."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.complete_with_history(
            system_prompt="You are helpful.",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        system_msg = messages[0]

        # Verify cache control structure
        assert system_msg["role"] == "system"
        assert isinstance(system_msg["content"], list)
        assert system_msg["content"][0]["cache_control"] == {"type": "ephemeral"}

    async def test_complete_timeout_raises_llm_timeout_error(self, provider):
        """Complete should raise LLMTimeoutError on timeout."""
        provider._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(LLMTimeoutError) as exc_info:
            await provider.complete(
                system_prompt="You are helpful.",
                user_message="Hello",
            )

        assert "timed out" in str(exc_info.value)
        assert exc_info.value.provider == "openrouter"

    async def test_complete_rate_limit_raises_llm_rate_limit_error(self, provider):
        """Complete should raise LLMRateLimitError when rate limited."""
        provider._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )

        with pytest.raises(LLMRateLimitError) as exc_info:
            await provider.complete(
                system_prompt="You are helpful.",
                user_message="Hello",
            )

        assert "Rate limited" in str(exc_info.value)

    async def test_complete_connection_error_raises_llm_provider_error(self, provider):
        """Complete should raise LLMProviderError on connection error."""
        provider._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(
                system_prompt="You are helpful.",
                user_message="Hello",
            )

        assert "Unable to connect" in str(exc_info.value)

    async def test_complete_handles_empty_response_content(self, provider):
        """Complete should handle None content gracefully."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        # Mock usage with no cache activity
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 0
        type(usage).cache_creation_input_tokens = 0
        response.usage = usage

        provider._client.chat.completions.create = AsyncMock(return_value=response)

        result = await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        assert result == ""


class TestOpenRouterProviderResilience:
    """Tests for retry and circuit breaker behavior."""

    async def test_retries_on_connection_error(self):
        """Provider should retry on connection errors."""
        provider = OpenRouterProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"
        # Mock usage with no cache activity
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 0
        type(usage).cache_creation_input_tokens = 0
        mock_response.usage = usage

        # Fail once, then succeed
        provider._client.chat.completions.create = AsyncMock(
            side_effect=[
                APIConnectionError(request=MagicMock()),
                mock_response,
            ]
        )

        result = await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        assert result == "Success after retry"
        assert provider._client.chat.completions.create.call_count == 2

    async def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker should open after repeated failures.

        aiobreaker opens the circuit and raises CircuitBreakerError when the
        failure count reaches fail_max. With fail_max=3:
        - Call 1: fails, count=1, raises original error
        - Call 2: fails, count=2, raises original error
        - Call 3: fails, count=3, circuit opens, raises CircuitBreakerError
        """
        provider = OpenRouterProvider(
            api_key="test-key",
            circuit_breaker_fail_max=3,  # Opens on 3rd failure
            circuit_breaker_timeout=60.0,
        )

        provider._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )

        # First two failures - circuit still closed
        for _ in range(2):
            with pytest.raises(LLMRateLimitError):
                await provider.complete(
                    system_prompt="You are helpful.",
                    user_message="Hello",
                )

        # Third failure - circuit opens and raises CircuitBreakerError
        # which gets converted to LLMProviderError
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(
                system_prompt="You are helpful.",
                user_message="Hello",
            )

        # Verify it's the circuit breaker error, not the rate limit error
        assert "temporarily unavailable" in str(exc_info.value)
        # Also verify it's not LLMRateLimitError (more specific)
        assert not isinstance(exc_info.value, LLMRateLimitError)


class TestOpenRouterProviderCacheMetrics:
    """Tests for cache metrics logging."""

    @pytest.fixture
    def provider(self):
        """Create a provider with caching enabled."""
        return OpenRouterProvider(api_key="test-key", enable_prompt_caching=True)

    @pytest.fixture
    def mock_response_with_cache_hit(self):
        """Create a mock response with cache hit metrics."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Cached response"
        # Use PropertyMock to return proper integers
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 500
        type(usage).cache_creation_input_tokens = 0
        response.usage = usage
        return response

    @pytest.fixture
    def mock_response_with_cache_write(self):
        """Create a mock response with cache write metrics."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "New response"
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 0
        type(usage).cache_creation_input_tokens = 1200
        response.usage = usage
        return response

    @pytest.fixture
    def mock_response_without_cache(self):
        """Create a mock response without cache metrics."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Regular response"
        usage = MagicMock()
        type(usage).cache_read_input_tokens = 0
        type(usage).cache_creation_input_tokens = 0
        response.usage = usage
        return response

    async def test_logs_cache_hit_metrics(
        self, provider, mock_response_with_cache_hit, capsys
    ):
        """Provider should log cache hit metrics."""
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response_with_cache_hit
        )

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        captured = capsys.readouterr()
        assert "llm_cache_metrics" in captured.out
        assert "cache_read_tokens" in captured.out

    async def test_logs_cache_write_metrics(
        self, provider, mock_response_with_cache_write, capsys
    ):
        """Provider should log cache write metrics."""
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response_with_cache_write
        )

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        captured = capsys.readouterr()
        assert "llm_cache_metrics" in captured.out
        assert "cache_creation_tokens" in captured.out

    async def test_no_log_when_no_cache_activity(
        self, provider, mock_response_without_cache, capsys
    ):
        """Provider should not log when no cache activity."""
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response_without_cache
        )

        await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        captured = capsys.readouterr()
        assert "llm_cache_metrics" not in captured.out

    async def test_handles_missing_usage_gracefully(self, provider):
        """Provider should handle responses without usage object."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Response without usage"
        response.usage = None  # No usage data

        provider._client.chat.completions.create = AsyncMock(return_value=response)

        result = await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        # Should complete without error
        assert result == "Response without usage"

    async def test_handles_non_numeric_cache_tokens(self, provider, capsys):
        """Provider should handle non-numeric cache token values gracefully."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Response with invalid usage"
        # Create usage with non-convertible values (TypeError on int())
        response.usage = MagicMock()
        response.usage.cache_read_input_tokens = "not_a_number"
        response.usage.cache_creation_input_tokens = None

        provider._client.chat.completions.create = AsyncMock(return_value=response)

        result = await provider.complete(
            system_prompt="You are helpful.",
            user_message="Hello",
        )

        # Should complete without error and not log cache metrics
        assert result == "Response with invalid usage"
        captured = capsys.readouterr()
        assert "llm_cache_metrics" not in captured.out
