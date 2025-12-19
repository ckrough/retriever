"""RAG (Retrieval-Augmented Generation) module.

This module provides the core RAG functionality for GoodPuppy:
- Document loading and chunking
- Question answering with retrieved context
- Document indexing
"""

from src.modules.rag.chunker import ChunkingConfig, chunk_document
from src.modules.rag.loader import (
    DocumentLoadError,
    LoadedDocument,
    list_documents,
    load_document,
)
from src.modules.rag.schemas import (
    Chunk,
    ChunkWithScore,
    IndexingResult,
    RAGResponse,
)
from src.modules.rag.service import RAGService

__all__ = [
    "Chunk",
    "ChunkWithScore",
    "ChunkingConfig",
    "DocumentLoadError",
    "IndexingResult",
    "LoadedDocument",
    "RAGResponse",
    "RAGService",
    "chunk_document",
    "list_documents",
    "load_document",
]
