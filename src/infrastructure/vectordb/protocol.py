"""Protocol definition for vector store providers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class DocumentChunk:
    """A chunk of a document for storage in the vector store."""

    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, str]


@dataclass
class RetrievalResult:
    """Result from a vector similarity search."""

    id: str
    content: str
    metadata: dict[str, str]
    score: float  # Similarity score (higher is better for cosine similarity)


class VectorStore(Protocol):
    """Protocol for vector store implementations.

    This allows swapping between different vector database backends
    without changing business logic.
    """

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Add document chunks with embeddings to the store.

        Args:
            chunks: List of chunks with embeddings and metadata.

        Raises:
            VectorStoreError: If addition fails.
        """
        ...

    async def query(
        self,
        embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Query for similar chunks.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of retrieval results with similarity scores.

        Raises:
            VectorStoreError: If query fails.
        """
        ...

    async def clear(self) -> None:
        """Clear all data from the store.

        Raises:
            VectorStoreError: If clearing fails.
        """
        ...

    def count(self) -> int:
        """Return the number of chunks in the store."""
        ...
