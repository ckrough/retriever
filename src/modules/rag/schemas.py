"""Schemas for the RAG module."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.infrastructure.vectordb import RetrievalResult


@dataclass
class Chunk:
    """A chunk of text from a document.

    Represents a segment of a document that can be embedded and stored
    in the vector database for retrieval.
    """

    content: str
    source: str  # Source document filename
    section: str  # Section header (if available)
    position: int  # Position in the document (for ordering)
    title: str = ""  # Document title (first # heading or filename)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate metadata from fields if not provided."""
        if not self.metadata:
            self.metadata = {
                "source": self.source,
                "section": self.section,
                "position": str(self.position),
                "title": self.title,
            }


@dataclass
class IndexingResult:
    """Result of indexing a document."""

    source: str
    chunks_created: int
    success: bool
    error_message: str | None = None


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""

    answer: str
    chunks_used: list["ChunkWithScore"]
    question: str
    confidence_level: str = "medium"  # high, medium, low
    confidence_score: float = 0.5
    blocked: bool = False  # True if blocked by safety checks
    blocked_reason: str | None = None


@dataclass
class ChunkWithScore:
    """A retrieved chunk with its similarity score."""

    content: str
    source: str
    section: str
    score: float
    title: str = ""

    @classmethod
    def from_retrieval_result(cls, result: "RetrievalResult") -> "ChunkWithScore":
        """Create from a RetrievalResult."""

        return cls(
            content=result.content,
            source=result.metadata.get("source", "unknown"),
            section=result.metadata.get("section", ""),
            score=result.score,
            title=result.metadata.get("title", ""),
        )


@dataclass
class Message:
    """A conversation message.

    Represents a single message in a conversation history,
    either from the user or the assistant.
    """

    id: UUID
    user_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "Message":
        """Create a Message from a database row.

        Args:
            row: Dictionary containing database row values.

        Returns:
            Message instance.
        """
        return cls(
            id=UUID(str(row["id"])),
            user_id=UUID(str(row["user_id"])),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
