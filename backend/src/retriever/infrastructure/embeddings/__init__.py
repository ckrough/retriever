"""Embedding provider infrastructure."""

from retriever.infrastructure.embeddings.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
)
from retriever.infrastructure.embeddings.openai import OpenAIEmbeddingProvider
from retriever.infrastructure.embeddings.protocol import EmbeddingProvider

__all__ = [
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingRateLimitError",
    "EmbeddingTimeoutError",
    "OpenAIEmbeddingProvider",
]
