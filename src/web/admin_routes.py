"""Admin routes for document management."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from src.config import Settings, get_settings
from src.infrastructure.cache import ChromaSemanticCache
from src.infrastructure.database import get_database
from src.infrastructure.embeddings import (
    EmbeddingProviderError,
    OpenAIEmbeddingProvider,
)
from src.infrastructure.llm import OpenRouterProvider
from src.infrastructure.vectordb import ChromaVectorStore
from src.modules.documents import (
    DocumentAlreadyExistsError,
    DocumentIndexingError,
    DocumentNotFoundError,
    DocumentRepository,
    DocumentService,
    DocumentValidationError,
)
from src.modules.rag import HybridRetriever, RAGService, list_documents, load_document
from src.modules.rag.loader import DocumentLoadError
from src.web.dependencies import require_admin
from src.web.routes import (
    get_hybrid_retriever,
    get_llm_provider,
    get_semantic_cache,
    get_vector_store,
)
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
    hybrid_retriever: Annotated[HybridRetriever | None, Depends(get_hybrid_retriever)],
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
        hybrid_retriever=hybrid_retriever,
        top_k=settings.rag_top_k,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )


def get_document_service(
    settings: Annotated[Settings, Depends(get_settings)],
    rag_service: Annotated[RAGService | None, Depends(get_admin_rag_service)],
) -> DocumentService | None:
    """Get the document service for document management operations.

    Returns None if RAG is not configured.
    """
    if rag_service is None:
        return None

    database = get_database()
    repository = DocumentRepository(database)

    return DocumentService(
        repository=repository,
        rag_service=rag_service,
        uploads_path=Path(settings.uploads_path),
        documents_path=Path(settings.documents_path),
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
    hybrid_retriever: Annotated[HybridRetriever | None, Depends(get_hybrid_retriever)],
    doc_service: Annotated[DocumentService | None, Depends(get_document_service)],
    _admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)],
) -> Response:
    """Render the admin dashboard.

    Requires admin authentication when enabled.
    """
    # Static documents from ./documents/
    documents_path = Path(settings.documents_path)
    document_paths = list_documents(documents_path)
    static_documents = [_load_document_info(doc_path) for doc_path in document_paths]

    # Uploaded documents from database
    uploaded_documents = []
    if doc_service is not None:
        uploaded_documents = await doc_service.list_documents()

    # Check configuration status
    llm_configured = settings.openrouter_api_key is not None
    embeddings_configured = settings.embedding_api_key is not None

    # Cache stats
    cache_enabled = settings.cache_enabled and semantic_cache is not None
    cache_count = semantic_cache.count() if semantic_cache else 0

    # Hybrid retrieval stats
    hybrid_enabled = settings.hybrid_retrieval_enabled and hybrid_retriever is not None
    keyword_index_count = (
        hybrid_retriever.get_keyword_index_count() if hybrid_retriever else 0
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "static_documents": static_documents,
            "uploaded_documents": uploaded_documents,
            "chunk_count": vector_store.count(),
            "documents_path": str(documents_path),
            "uploads_path": str(settings.uploads_path),
            "llm_configured": llm_configured,
            "embeddings_configured": embeddings_configured,
            "cache_enabled": cache_enabled,
            "cache_count": cache_count,
            "hybrid_enabled": hybrid_enabled,
            "keyword_index_count": keyword_index_count,
        },
    )


@router.post("/index", response_class=HTMLResponse)
async def index_documents(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    rag_service: Annotated[RAGService | None, Depends(get_admin_rag_service)],
    _admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)],
) -> Response:
    """Index all documents from both static and uploads directories.

    Requires admin authentication when enabled.
    """
    if rag_service is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/index_error.html",
            context={
                "error_message": "RAG not configured. Please set OPENROUTER_API_KEY and EMBEDDING_API_KEY."
            },
        )

    try:
        # Clear existing index
        await rag_service.clear_index()

        results = []

        # Index static documents
        documents_path = Path(settings.documents_path)
        if documents_path.exists():
            static_results = await rag_service.index_all_documents(documents_path)
            results.extend(static_results)

        # Index uploaded documents
        uploads_path = Path(settings.uploads_path)
        if uploads_path.exists():
            upload_results = await rag_service.index_all_documents(uploads_path)
            results.extend(upload_results)

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
    _admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)],
) -> Response:
    """Clear the semantic cache without affecting indexed documents.

    Requires admin authentication when enabled.
    """
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


# Document Management Routes


@router.post("/documents/upload", response_class=HTMLResponse)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form()] = None,
    doc_service: Annotated[
        DocumentService | None, Depends(get_document_service)
    ] = None,
    admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)] = None,
) -> Response:
    """Upload and index a new document.

    Requires admin authentication when enabled.
    """
    if doc_service is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={
                "error_message": "RAG not configured. Please set OPENROUTER_API_KEY and EMBEDDING_API_KEY."
            },
        )

    if not file.filename:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": "No file selected."},
        )

    # Sanitize filename early for safe logging
    safe_filename = Path(file.filename).name.strip() if file.filename else "unknown"

    # Validate file size before reading into memory (defense against memory exhaustion)
    max_size_bytes = 1 * 1024 * 1024  # 1 MB
    if file.size is not None and file.size > max_size_bytes:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": "File too large. Maximum size: 1 MB"},
        )

    try:
        # Read file content
        file_content = await file.read()

        # Double-check size after reading (in case file.size was unavailable)
        if len(file_content) > max_size_bytes:
            return templates.TemplateResponse(
                request=request,
                name="admin/partials/upload_error.html",
                context={"error_message": "File too large. Maximum size: 1 MB"},
            )

        # Get user ID if authenticated
        uploaded_by = None
        if admin_user:
            uploaded_by = UUID(admin_user["user_id"])

        # Upload and index document
        doc = await doc_service.upload_document(
            file_content=file_content,
            filename=file.filename,
            description=description,
            uploaded_by=uploaded_by,
        )

        logger.info(
            "admin_document_uploaded",
            filename=doc.filename,
            title=doc.title,
            uploaded_by=str(uploaded_by) if uploaded_by else "anonymous",
        )

        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_success.html",
            context={
                "document": doc,
            },
        )

    except DocumentAlreadyExistsError as e:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": f"Document '{e.filename}' already exists."},
        )

    except DocumentValidationError as e:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": str(e)},
        )

    except DocumentIndexingError as e:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": f"Indexing failed: {e.reason}"},
        )

    except Exception as e:
        logger.error(
            "admin_document_upload_error",
            error=str(e),
            error_type=type(e).__name__,
            filename=safe_filename,  # Use sanitized filename for safe logging
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/upload_error.html",
            context={"error_message": f"Upload failed: {e}"},
        )


@router.delete("/documents/{doc_id}", response_class=HTMLResponse)
async def delete_document(
    request: Request,
    doc_id: UUID,
    doc_service: Annotated[
        DocumentService | None, Depends(get_document_service)
    ] = None,
    _admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)] = None,
) -> Response:
    """Delete a document and rebuild the index.

    Due to ChromaDB limitations, this clears and rebuilds the entire index.
    Requires admin authentication when enabled.
    """
    if doc_service is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/delete_error.html",
            context={
                "error_message": "RAG not configured. Please set OPENROUTER_API_KEY and EMBEDDING_API_KEY."
            },
        )

    try:
        # Get document info before deletion for logging
        doc = await doc_service.get_document(doc_id)
        filename = doc.filename

        # Delete document (includes reindexing)
        await doc_service.delete_document(doc_id)

        logger.info("admin_document_deleted", doc_id=str(doc_id), filename=filename)

        return templates.TemplateResponse(
            request=request,
            name="admin/partials/delete_success.html",
            context={"filename": filename},
        )

    except DocumentNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/delete_error.html",
            context={"error_message": "Document not found."},
        )

    except Exception as e:
        logger.error(
            "admin_document_delete_error",
            error=str(e),
            error_type=type(e).__name__,
            doc_id=str(doc_id),
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/delete_error.html",
            context={"error_message": f"Delete failed: {e}"},
        )


@router.get("/documents", response_class=HTMLResponse)
async def list_uploaded_documents(
    request: Request,
    doc_service: Annotated[
        DocumentService | None, Depends(get_document_service)
    ] = None,
    _admin_user: Annotated[dict[str, Any] | None, Depends(require_admin)] = None,
) -> Response:
    """List all uploaded documents.

    Requires admin authentication when enabled.
    Returns an HTMX partial for the documents list.
    """
    documents = []
    if doc_service is not None:
        documents = await doc_service.list_documents()

    return templates.TemplateResponse(
        request=request,
        name="admin/partials/documents_list.html",
        context={"documents": documents},
    )
