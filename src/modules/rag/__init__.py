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
from src.modules.rag.quality import (
    AnswerMetrics,
    EvaluationResult,
    EvaluationSummary,
    GoldenExample,
    RetrievalMetrics,
    assess_example,
    calculate_answer_metrics,
    calculate_retrieval_metrics,
    load_golden_dataset,
    summarize_assessment,
)
from src.modules.rag.retriever import HybridRetriever, IndexedDocument
from src.modules.rag.schemas import (
    Chunk,
    ChunkWithScore,
    IndexingResult,
    RAGResponse,
)
from src.modules.rag.service import RAGService

__all__ = [
    "AnswerMetrics",
    "Chunk",
    "ChunkWithScore",
    "ChunkingConfig",
    "DocumentLoadError",
    "EvaluationResult",
    "EvaluationSummary",
    "GoldenExample",
    "HybridRetriever",
    "IndexedDocument",
    "IndexingResult",
    "LoadedDocument",
    "RAGResponse",
    "RAGService",
    "RetrievalMetrics",
    "assess_example",
    "calculate_answer_metrics",
    "calculate_retrieval_metrics",
    "chunk_document",
    "list_documents",
    "load_document",
    "load_golden_dataset",
    "summarize_assessment",
]
