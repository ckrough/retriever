"""Admin routes for document management."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from src.config import Settings, get_settings
from src.infrastructure.cache import ChromaSemanticCache
from src.infrastructure.embeddings import (
    EmbeddingProviderError,
    OpenAIEmbeddingProvider,
)
from src.infrastructure.llm import OpenRouterProvider
from src.infrastructure.vectordb import ChromaVectorStore
from src.modules.rag import RAGService, list_documents, load_document
from src.modules.rag.loader import DocumentLoadError
from src.web.routes import get_llm_provider, get_semantic_cache, get_vector_store
from src.web.templates import templates

logger = structlog.get_logger()


@dataclass
class DocumentInfo:
    """Document metadata for admin display."""

    filename: str
    title: str
    document_type: str  # "markdown" or "text"


router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
    semantic_cache: Annotated[ChromaSemanticCache | None, Depends(get_semantic_cache)],
) -> RAGService | None:
    """Get the RAG service for admin operations.

    Similar to get_rag_service but specifically for admin routes.
    """
    if llm_provider is None:
        return None

    if settings.embedding_api_key is None:
        return None

    embedding_provider = OpenAIEmbeddingProvider(
        api_key=settings.embedding_api_key.get_secret_value(),
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        timeout_seconds=settings.embedding_timeout_seconds,
        circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
        circuit_breaker_timeout=settings.circuit_breaker_timeout,
    )

    return RAGService(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        semantic_cache=semantic_cache,
        top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )


def _load_document_info(doc_path: Path) -> DocumentInfo:
    """Load document metadata for admin display.

    Args:
        doc_path: Path to the document.

    Returns:
        DocumentInfo with extracted metadata.
    """
    try:
        doc = load_document(doc_path)
        return DocumentInfo(
            filename=doc.source,
            title=doc.title,
            document_type=doc.document_type,
        )
    except DocumentLoadError:
        # Fallback if document can't be loaded
        return DocumentInfo(
            filename=doc_path.name,
            title=doc_path.stem,
            document_type="unknown",
        )


@router.get("/", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
    semantic_cache: Annotated[ChromaSemanticCache | None, Depends(get_semantic_cache)],
) -> Response:
    """Render the admin dashboard."""
    documents_path = Path(settings.documents_path)
    document_paths = list_documents(documents_path)

    # Load document metadata for each document
    documents = [_load_document_info(doc_path) for doc_path in document_paths]

    # Check configuration status
    llm_configured = settings.openrouter_api_key is not None
    embeddings_configured = settings.embedding_api_key is not None

    # Cache stats
    cache_enabled = settings.cache_enabled and semantic_cache is not None
    cache_count = semantic_cache.count() if semantic_cache else 0

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "documents": documents,
            "chunk_count": vector_store.count(),
            "documents_path": str(documents_path),
            "llm_configured": llm_configured,
            "embeddings_configured": embeddings_configured,
            "cache_enabled": cache_enabled,
            "cache_count": cache_count,
        },
    )


@router.post("/index", response_class=HTMLResponse)
async def index_documents(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    rag_service: Annotated[RAGService | None, Depends(get_admin_rag_service)],
) -> Response:
    """Index all documents in the documents folder."""
    if rag_service is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/index_error.html",
            context={
                "error_message": "RAG not configured. Please set OPENROUTER_API_KEY and EMBEDDING_API_KEY."
            },
        )

    try:
        documents_path = Path(settings.documents_path)

        # Clear existing index
        await rag_service.clear_index()

        # Index all documents
        results = await rag_service.index_all_documents(documents_path)

        total_chunks = sum(r.chunks_created for r in results if r.success)
        success_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)

        logger.info(
            "admin_index_complete",
            documents_processed=len(results),
            documents_succeeded=success_count,
            documents_failed=failed_count,
            total_chunks=total_chunks,
        )

        return templates.TemplateResponse(
            request=request,
            name="admin/partials/index_result.html",
            context={
                "results": results,
                "total_chunks": total_chunks,
                "success_count": success_count,
                "failed_count": failed_count,
            },
        )

    except EmbeddingProviderError as e:
        logger.error("admin_index_embedding_error", error=str(e))
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/index_error.html",
            context={"error_message": f"Embedding error: {e}"},
        )

    except Exception as e:
        logger.error(
            "admin_index_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/index_error.html",
            context={"error_message": f"Indexing failed: {e}"},
        )


@router.post("/clear-cache", response_class=HTMLResponse)
async def clear_cache(
    request: Request,
    semantic_cache: Annotated[ChromaSemanticCache | None, Depends(get_semantic_cache)],
) -> Response:
    """Clear the semantic cache without affecting indexed documents."""
    if semantic_cache is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/cache_result.html",
            context={
                "success": False,
                "message": "Cache is not enabled.",
            },
        )

    try:
        await semantic_cache.clear()
        logger.info("admin_cache_cleared")

        return templates.TemplateResponse(
            request=request,
            name="admin/partials/cache_result.html",
            context={
                "success": True,
                "message": "Cache cleared successfully.",
            },
        )

    except Exception as e:
        logger.error("admin_cache_clear_error", error=str(e))
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/cache_result.html",
            context={
                "success": False,
                "message": f"Failed to clear cache: {e}",
            },
        )
