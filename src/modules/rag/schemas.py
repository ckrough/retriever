"""Pydantic schemas for the RAG module."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

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
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate metadata from fields if not provided."""
        if not self.metadata:
            self.metadata = {
                "source": self.source,
                "section": self.section,
                "position": str(self.position),
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


@dataclass
class ChunkWithScore:
    """A retrieved chunk with its similarity score."""

    content: str
    source: str
    section: str
    score: float

    @classmethod
    def from_retrieval_result(cls, result: "RetrievalResult") -> "ChunkWithScore":
        """Create from a RetrievalResult."""

        return cls(
            content=result.content,
            source=result.metadata.get("source", "unknown"),
            section=result.metadata.get("section", ""),
            score=result.score,
        )
