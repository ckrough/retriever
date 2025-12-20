"""Protocol definition for semantic caching."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


def _now_utc() -> datetime:
    """Return current UTC time (for dataclass default)."""
    return datetime.now(UTC)


@dataclass
class CacheEntry:
    """A cached RAG response.

    Stores the original question, answer, and metadata for cache retrieval.
    The similarity_score is populated during retrieval to indicate how
    closely the cached question matched the query.
    """

    question: str
    answer: str
    chunks_json: str  # JSON-serialized list of ChunkWithScore
    created_at: datetime = field(default_factory=_now_utc)
    similarity_score: float = 0.0  # Set during retrieval


class SemanticCache(Protocol):
    """Protocol for semantic caching implementations.

    Semantic caching stores question-answer pairs and retrieves them
    based on question similarity rather than exact matching. This allows
    "Where do I sign in?" to match "sign in location".
    """

    async def get(self, question: str) -> CacheEntry | None:
        """Retrieve a cached answer for a similar question.

        Args:
            question: The user's question to look up.

        Returns:
            CacheEntry if a similar question was found above the
            similarity threshold, None otherwise.
        """
        ...

    async def set(
        self,
        question: str,
        answer: str,
        chunks_json: str,
    ) -> None:
        """Store a question-answer pair in the cache.

        Args:
            question: The original question asked.
            answer: The generated answer.
            chunks_json: JSON-serialized list of ChunkWithScore used.
        """
        ...

    async def clear(self) -> None:
        """Clear all cached entries.

        Called when documents are reindexed to invalidate stale answers.
        """
        ...

    def count(self) -> int:
        """Return the number of cached entries."""
        ...
