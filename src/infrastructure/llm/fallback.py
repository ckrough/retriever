"""Fallback LLM provider with model degradation."""

import structlog

from src.infrastructure.llm.exceptions import LLMProviderError
from src.infrastructure.llm.protocol import LLMProvider

logger = structlog.get_logger()


class FallbackLLMProvider:
    """LLM provider that falls back to a secondary model on failure.

    This provides graceful degradation when the primary model is unavailable
    or overloaded. The fallback model is typically smaller/faster/cheaper.
    """

    def __init__(
        self,
        primary_provider: LLMProvider,
        *,
        fallback_model: str,
    ) -> None:
        """Initialize the fallback provider.

        Args:
            primary_provider: The primary LLM provider to use.
            fallback_model: Model identifier to use when primary fails.
        """
        self._provider = primary_provider
        self._fallback_model = fallback_model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        model: str | None = None,
    ) -> str:
        """Generate a completion with automatic fallback.

        Tries the primary model first. On failure, automatically retries
        with the fallback model.

        Args:
            system_prompt: The system message setting context/behavior.
            user_message: The user's message to respond to.
            model: Optional model override for primary attempt.

        Returns:
            The generated completion text.

        Raises:
            LLMProviderError: If both primary and fallback fail.
        """
        # Try primary model first
        try:
            return await self._provider.complete(
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
            )
        except LLMProviderError as primary_error:
            logger.warning(
                "llm_primary_failed_trying_fallback",
                primary_error=str(primary_error),
                fallback_model=self._fallback_model,
            )

            # Try fallback model
            try:
                result = await self._provider.complete(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    model=self._fallback_model,
                )
                logger.info(
                    "llm_fallback_success",
                    fallback_model=self._fallback_model,
                )
                return result

            except LLMProviderError as fallback_error:
                logger.error(
                    "llm_fallback_also_failed",
                    primary_error=str(primary_error),
                    fallback_error=str(fallback_error),
                    fallback_model=self._fallback_model,
                )
                # Re-raise the original error
                raise primary_error from fallback_error
