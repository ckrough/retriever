"""Tests for LLM fallback provider."""

import pytest

from src.infrastructure.llm import FallbackLLMProvider, LLMProviderError


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(
        self,
        *,
        should_fail: bool = False,
        fail_on_models: list[str] | None = None,
    ) -> None:
        """Initialize the mock provider.

        Args:
            should_fail: If True, always raises LLMProviderError.
            fail_on_models: List of model names that should fail.
        """
        self._should_fail = should_fail
        self._fail_on_models = fail_on_models or []
        self.calls: list[dict[str, str | None]] = []

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        model: str | None = None,
    ) -> str:
        """Mock completion method."""
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "model": model,
            }
        )

        if self._should_fail:
            raise LLMProviderError("Mock failure", provider="mock")

        if model and model in self._fail_on_models:
            raise LLMProviderError(f"Model {model} failed", provider="mock")

        return f"Response from {model or 'default'}"


class TestFallbackLLMProvider:
    """Tests for the fallback LLM provider."""

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self) -> None:
        """Should use primary model when it succeeds."""
        mock = MockLLMProvider()
        fallback = FallbackLLMProvider(mock, fallback_model="haiku")

        result = await fallback.complete(
            system_prompt="system",
            user_message="hello",
        )

        assert "Response from" in result
        assert len(mock.calls) == 1

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self) -> None:
        """Should fall back to secondary model when primary fails."""
        mock = MockLLMProvider(fail_on_models=["primary-model"])
        fallback = FallbackLLMProvider(mock, fallback_model="fallback-model")

        result = await fallback.complete(
            system_prompt="system",
            user_message="hello",
            model="primary-model",
        )

        assert "fallback-model" in result
        assert len(mock.calls) == 2
        assert mock.calls[0]["model"] == "primary-model"
        assert mock.calls[1]["model"] == "fallback-model"

    @pytest.mark.asyncio
    async def test_raises_when_both_fail(self) -> None:
        """Should raise when both primary and fallback fail."""
        mock = MockLLMProvider(should_fail=True)
        fallback = FallbackLLMProvider(mock, fallback_model="fallback-model")

        with pytest.raises(LLMProviderError):
            await fallback.complete(
                system_prompt="system",
                user_message="hello",
            )

        # Should have tried both
        assert len(mock.calls) == 2

    @pytest.mark.asyncio
    async def test_model_override_passed_to_primary(self) -> None:
        """Model override should be used for primary attempt."""
        mock = MockLLMProvider()
        fallback = FallbackLLMProvider(mock, fallback_model="fallback-model")

        await fallback.complete(
            system_prompt="system",
            user_message="hello",
            model="custom-model",
        )

        assert mock.calls[0]["model"] == "custom-model"
