"""Embedding provider infrastructure.

This module provides a Protocol-based abstraction for embedding providers,
allowing easy swapping between different embedding backends.
"""

from src.infrastructure.embeddings.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
)
from src.infrastructure.embeddings.openai import OpenAIEmbeddingProvider
from src.infrastructure.embeddings.protocol import EmbeddingProvider

__all__ = [
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingRateLimitError",
    "EmbeddingTimeoutError",
    "OpenAIEmbeddingProvider",
]
