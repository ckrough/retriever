"""OpenAI embedding provider implementation."""

from datetime import timedelta
from typing import ClassVar

import structlog
from aiobreaker import CircuitBreaker, CircuitBreakerError
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infrastructure.embeddings.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
)
from src.infrastructure.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class OpenAIEmbeddingProvider:
    """Embedding provider using OpenAI's embedding API.

    Includes resilience patterns:
    - Retries with exponential backoff for transient failures
    - Circuit breaker to fail fast after repeated failures
    - Configurable timeouts
    """

    PROVIDER_NAME = "openai"

    # Known dimensions for embedding models (via OpenRouter)
    MODEL_DIMENSIONS: ClassVar[dict[str, int]] = {
        "openai/text-embedding-3-small": 1536,
        "openai/text-embedding-3-large": 3072,
        "openai/text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "openai/text-embedding-3-small",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
        circuit_breaker_fail_max: int = 5,
        circuit_breaker_timeout: float = 60.0,
    ) -> None:
        """Initialize the embedding provider.

        Args:
            api_key: OpenRouter API key.
            model: Embedding model to use.
            base_url: Base URL for API.
            timeout_seconds: Request timeout in seconds.
            circuit_breaker_fail_max: Open circuit after this many failures.
            circuit_breaker_timeout: Time in seconds before attempting recovery.

        Raises:
            EmbeddingConfigurationError: If API key is missing.
        """
        if not api_key:
            raise EmbeddingConfigurationError(
                "API key is required", provider=self.PROVIDER_NAME
            )

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )
        self._model = model
        self._timeout = timeout_seconds

        # Circuit breaker: fail fast after repeated failures
        self._breaker = CircuitBreaker(
            fail_max=circuit_breaker_fail_max,
            timeout_duration=timedelta(seconds=circuit_breaker_timeout),
        )

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings produced by this provider."""
        return self.MODEL_DIMENSIONS.get(self._model, 1536)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as a list of floats.

        Raises:
            EmbeddingProviderError: If embedding generation fails.
            EmbeddingTimeoutError: If the request times out.
            EmbeddingRateLimitError: If rate limited.
        """
        with tracer.start_as_current_span("embeddings.embed") as span:
            span.set_attribute("embeddings.provider", self.PROVIDER_NAME)
            span.set_attribute("embeddings.model", self._model)
            span.set_attribute("embeddings.input_length", len(text))

            try:
                result = await self._embed_with_resilience([text])
                span.set_attribute("embeddings.dimensions", len(result[0]))
                return result[0]

            except CircuitBreakerError as e:
                span.record_exception(e)
                logger.warning(
                    "circuit_breaker_open",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                )
                raise EmbeddingProviderError(
                    "Service temporarily unavailable. Please try again in a moment.",
                    provider=self.PROVIDER_NAME,
                ) from e

            except APITimeoutError as e:
                span.record_exception(e)
                logger.warning(
                    "embedding_timeout",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    timeout_seconds=self._timeout,
                )
                raise EmbeddingTimeoutError(
                    f"Request timed out after {self._timeout}s",
                    provider=self.PROVIDER_NAME,
                ) from e

            except APIConnectionError as e:
                span.record_exception(e)
                logger.error(
                    "embedding_connection_error",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    error=str(e),
                )
                raise EmbeddingProviderError(
                    "Unable to connect to embedding service",
                    provider=self.PROVIDER_NAME,
                ) from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingProviderError: If embedding generation fails.
            EmbeddingTimeoutError: If the request times out.
            EmbeddingRateLimitError: If rate limited.
        """
        if not texts:
            return []

        with tracer.start_as_current_span("embeddings.embed_batch") as span:
            span.set_attribute("embeddings.provider", self.PROVIDER_NAME)
            span.set_attribute("embeddings.model", self._model)
            span.set_attribute("embeddings.batch_size", len(texts))

            try:
                result = await self._embed_with_resilience(texts)
                if result:
                    span.set_attribute("embeddings.dimensions", len(result[0]))
                return result

            except CircuitBreakerError as e:
                span.record_exception(e)
                logger.warning(
                    "circuit_breaker_open",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                )
                raise EmbeddingProviderError(
                    "Service temporarily unavailable. Please try again in a moment.",
                    provider=self.PROVIDER_NAME,
                ) from e

            except APITimeoutError as e:
                span.record_exception(e)
                logger.warning(
                    "embedding_timeout",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    timeout_seconds=self._timeout,
                    batch_size=len(texts),
                )
                raise EmbeddingTimeoutError(
                    f"Request timed out after {self._timeout}s",
                    provider=self.PROVIDER_NAME,
                ) from e

            except APIConnectionError as e:
                span.record_exception(e)
                logger.error(
                    "embedding_connection_error",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    error=str(e),
                )
                raise EmbeddingProviderError(
                    "Unable to connect to embedding service",
                    provider=self.PROVIDER_NAME,
                ) from e

    @retry(
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, max=5),
        reraise=True,
    )
    async def _embed_with_resilience(self, texts: list[str]) -> list[list[float]]:
        """Internal method with retry and circuit breaker logic."""
        return await self._breaker.call_async(  # type: ignore[no-any-return]
            self._do_embed, texts
        )

    async def _do_embed(self, texts: list[str]) -> list[list[float]]:
        """Execute the actual API call.

        Note: APIConnectionError and APITimeoutError are intentionally NOT caught
        here - they bubble up to allow retry logic in _embed_with_resilience.
        """
        logger.debug(
            "embedding_request_start",
            provider=self.PROVIDER_NAME,
            model=self._model,
            batch_size=len(texts),
        )

        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
            )

            # Sort by index to ensure correct ordering
            embeddings = [
                item.embedding for item in sorted(response.data, key=lambda x: x.index)
            ]

            logger.debug(
                "embedding_request_success",
                provider=self.PROVIDER_NAME,
                model=self._model,
                batch_size=len(texts),
                dimensions=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except RateLimitError as e:
            logger.warning(
                "embedding_rate_limited",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )
            raise EmbeddingRateLimitError(
                "Rate limited by OpenAI. Please try again shortly.",
                provider=self.PROVIDER_NAME,
            ) from e

        except (APIConnectionError, APITimeoutError):
            # Let these bubble up for retry logic
            raise

        except Exception as e:
            logger.error(
                "embedding_unexpected_error",
                provider=self.PROVIDER_NAME,
                model=self._model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise EmbeddingProviderError(
                "An unexpected error occurred",
                provider=self.PROVIDER_NAME,
            ) from e
