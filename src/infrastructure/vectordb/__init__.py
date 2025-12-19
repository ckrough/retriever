"""Vector store infrastructure.

This module provides a Protocol-based abstraction for vector stores,
allowing easy swapping between different vector database backends.
"""

from src.infrastructure.vectordb.chroma import ChromaVectorStore
from src.infrastructure.vectordb.exceptions import (
    VectorStoreConfigurationError,
    VectorStoreConnectionError,
    VectorStoreError,
)
from src.infrastructure.vectordb.protocol import (
    DocumentChunk,
    RetrievalResult,
    VectorStore,
)

__all__ = [
    "ChromaVectorStore",
    "DocumentChunk",
    "RetrievalResult",
    "VectorStore",
    "VectorStoreConfigurationError",
    "VectorStoreConnectionError",
    "VectorStoreError",
]
