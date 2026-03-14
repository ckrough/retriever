"""Schemas for the RAG module.

Pydantic models and Protocol definitions for document parsing, chunking,
and retrieval-augmented generation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from retriever.infrastructure.vectordb.protocol import SearchResult


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol for document parsers.

    Allows swapping in Docling or other parsers later.
    """

    def parse(self, content: str, source: str) -> ParsedDocument:
        """Parse raw document content into a structured representation.

        Args:
            content: Raw document text.
            source: Source filename or identifier.

        Returns:
            Parsed document with extracted metadata.
        """
        ...


@runtime_checkable
class DocumentChunker(Protocol):
    """Protocol for document chunkers.

    Allows swapping in Docling's HybridChunker later.
    """

    def chunk(self, content: str, source: str, *, title: str = "") -> list[Chunk]:
        """Split document content into chunks for embedding.

        Args:
            content: Document text to chunk.
            source: Source filename or identifier.
            title: Document title.

        Returns:
            List of document chunks.
        """
        ...


class ParsedDocument(BaseModel, frozen=True):
    """A parsed document with extracted metadata."""

    content: str
    source: str
    title: str
    document_type: str


class Chunk(BaseModel, frozen=True):
    """A chunk of text from a document.

    Represents a segment of a document that can be embedded and stored
    in the vector database for retrieval.
    """

    content: str
    source: str
    section: str
    position: int
    title: str = ""
    metadata: dict[str, str] = {}

    def model_post_init(self, __context: Any) -> None:
        """Populate metadata from fields if not provided."""
        if not self.metadata:
            # Use object.__setattr__ since the model is frozen
            object.__setattr__(
                self,
                "metadata",
                {
                    "source": self.source,
                    "section": self.section,
                    "position": str(self.position),
                    "title": self.title,
                },
            )


class ChunkWithScore(BaseModel, frozen=True):
    """A retrieved chunk with its similarity score."""

    content: str
    source: str
    section: str
    score: float
    title: str = ""

    @classmethod
    def from_search_result(cls, result: SearchResult) -> ChunkWithScore:
        """Create from a vectordb SearchResult.

        Args:
            result: Search result from the vector store.

        Returns:
            ChunkWithScore with fields extracted from the result.
        """
        return cls(
            content=result["content"],
            source=result["source"],
            section="",
            score=result["score"],
            title=result.get("title", ""),
        )


class IndexingResult(BaseModel, frozen=True):
    """Result of indexing a document."""

    source: str
    chunks_created: int
    success: bool
    error_message: str | None = None


class RAGResponse(BaseModel, frozen=True):
    """Response from the RAG pipeline."""

    answer: str
    chunks_used: list[ChunkWithScore]
    question: str
    confidence_level: str = "medium"
    confidence_score: float = 0.5
    blocked: bool = False
    blocked_reason: str | None = None
