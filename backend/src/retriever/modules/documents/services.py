"""Document service — orchestrates upload, indexing, and deletion."""

from __future__ import annotations

import uuid

import structlog

from retriever.infrastructure.cache.protocol import SemanticCache
from retriever.infrastructure.vectordb.protocol import VectorStore
from retriever.modules.documents.exceptions import (
    DocumentAlreadyExistsError,
    DocumentIndexingError,
    DocumentValidationError,
)
from retriever.modules.documents.repos import DocumentRepository
from retriever.modules.documents.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from retriever.modules.rag.loader import FileValidationError, validate_file
from retriever.modules.rag.service import RAGService

logger = structlog.get_logger(__name__)


def _mime_type_from_filename(filename: str) -> str:
    """Derive MIME type from filename extension.

    Args:
        filename: The filename to inspect.

    Returns:
        A MIME type string.
    """
    lower = filename.lower()
    if lower.endswith(".md"):
        return "text/markdown"
    if lower.endswith(".txt"):
        return "text/plain"
    return "application/octet-stream"


def _extract_title(content: str, filename: str) -> str:
    """Extract a title from content or fall back to filename.

    For markdown files, looks for the first H1 heading.
    Falls back to the filename without extension.

    Args:
        content: Document text content.
        filename: Original filename.

    Returns:
        Extracted or derived title.
    """
    import re

    if filename.lower().endswith(".md"):
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

    dot_pos = filename.rfind(".")
    if dot_pos > 0:
        return filename[:dot_pos]
    return filename


class DocumentService:
    """Orchestrates document upload, indexing, listing, and deletion.

    Coordinates between the document repository (DB metadata), the RAG
    service (chunking and embedding), the vector store (chunk deletion),
    and the semantic cache (invalidation on changes).
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        rag_service: RAGService,
        vector_store: VectorStore,
        semantic_cache: SemanticCache | None,
        *,
        max_documents: int = 20,
    ) -> None:
        """Initialize the document service.

        Args:
            document_repo: Repository for document metadata.
            rag_service: RAG service for indexing documents.
            vector_store: Vector store for chunk deletion.
            semantic_cache: Optional cache for invalidation on changes.
            max_documents: Maximum documents per tenant.
        """
        self._repo = document_repo
        self._rag = rag_service
        self._store = vector_store
        self._cache = semantic_cache
        self._max_documents = max_documents

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        tenant_id: uuid.UUID,
        uploaded_by: uuid.UUID,
    ) -> DocumentUploadResponse:
        """Upload, validate, index, and persist a document.

        Pipeline:
        1. Validate file (extension, size, hidden-file rules)
        2. Check document count < max_documents
        3. Check no duplicate filename
        4. Decode content as UTF-8
        5. Index via RAG service (chunk, embed, store)
        6. Create DB record
        7. Return response

        Args:
            file_content: Raw file bytes.
            filename: Original upload filename.
            tenant_id: Tenant scope.
            uploaded_by: UUID of the uploading user.

        Returns:
            Upload response with document ID and chunk count.

        Raises:
            DocumentValidationError: If the file fails validation.
            DocumentAlreadyExistsError: If a document with the same name exists.
            DocumentIndexingError: If indexing into the vector store fails.
        """
        # 1. Validate file
        try:
            validate_file(filename, len(file_content))
        except FileValidationError as exc:
            raise DocumentValidationError(str(exc)) from exc

        # 2. Check document count
        count = await self._repo.get_count(tenant_id)
        if count >= self._max_documents:
            raise DocumentValidationError(
                f"Maximum document limit reached ({self._max_documents}). "
                "Delete an existing document before uploading."
            )

        # 3. Check for duplicates
        if await self._repo.exists_by_filename(filename, tenant_id):
            raise DocumentAlreadyExistsError(
                f"A document named '{filename}' already exists. "
                "Delete it first or use a different filename."
            )

        # 4. Decode content
        try:
            content_str = file_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentValidationError("File must be valid UTF-8 text.") from exc

        # 5. Extract title and determine MIME type
        title = _extract_title(content_str, filename)
        file_type = _mime_type_from_filename(filename)

        # 6. Create DB record first to get the document ID
        document = await self._repo.create(
            filename=filename,
            title=title,
            file_path=f"ephemeral://{filename}",
            tenant_id=tenant_id,
            file_size_bytes=len(file_content),
            file_type=file_type,
            uploaded_by=uploaded_by,
            is_indexed=False,
        )

        # 7. Index via RAG service
        result = await self._rag.index_document(
            document_id=document.id,
            content=content_str,
            source=filename,
            title=title,
        )

        if not result.success:
            # Clean up the DB record on indexing failure
            await self._repo.delete(document.id, tenant_id)
            raise DocumentIndexingError(
                result.error_message or "Indexing failed with unknown error"
            )

        logger.info(
            "document.uploaded",
            document_id=str(document.id),
            filename=filename,
            chunks_created=result.chunks_created,
            tenant_id=str(tenant_id),
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=filename,
            title=title,
            chunks_created=result.chunks_created,
            message=f"Document '{filename}' uploaded and indexed "
            f"({result.chunks_created} chunks created).",
        )

    async def delete_document(
        self,
        document_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> DocumentDeleteResponse:
        """Delete a document, its vector chunks, and invalidate cache.

        Args:
            document_id: UUID of the document to delete.
            tenant_id: Tenant scope.

        Returns:
            Delete response with confirmation message.

        Raises:
            DocumentValidationError: If the document is not found.
        """
        # 1. Verify document exists
        document = await self._repo.get(document_id, tenant_id)
        if document is None:
            raise DocumentValidationError("Document not found.")

        filename = document.filename

        # 2. Delete chunks from vector store
        await self._store.delete_by_document(document_id, tenant_id)

        # 3. Invalidate cache
        if self._cache is not None:
            await self._cache.invalidate(tenant_id)

        # 4. Delete DB record
        await self._repo.delete(document_id, tenant_id)

        logger.info(
            "document.fully_deleted",
            document_id=str(document_id),
            filename=filename,
            tenant_id=str(tenant_id),
        )

        return DocumentDeleteResponse(
            message=f"Document '{filename}' and its indexed chunks deleted.",
        )

    async def list_documents(
        self,
        tenant_id: uuid.UUID,
    ) -> DocumentListResponse:
        """List all documents for a tenant.

        Args:
            tenant_id: Tenant scope.

        Returns:
            List response with document metadata and total count.
        """
        documents = await self._repo.list_all(tenant_id)
        return DocumentListResponse(
            documents=[
                DocumentResponse(
                    id=doc.id,
                    filename=doc.filename,
                    title=doc.title,
                    file_type=doc.file_type,
                    file_size_bytes=doc.file_size_bytes,
                    is_indexed=doc.is_indexed,
                    created_at=doc.created_at,
                    description=doc.description,
                )
                for doc in documents
            ],
            count=len(documents),
        )

    async def get_document(
        self,
        document_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> DocumentResponse:
        """Get a single document by ID.

        Args:
            document_id: UUID of the document.
            tenant_id: Tenant scope.

        Returns:
            Document metadata.

        Raises:
            DocumentValidationError: If the document is not found.
        """
        document = await self._repo.get(document_id, tenant_id)
        if document is None:
            raise DocumentValidationError("Document not found.")

        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            title=document.title,
            file_type=document.file_type,
            file_size_bytes=document.file_size_bytes,
            is_indexed=document.is_indexed,
            created_at=document.created_at,
            description=document.description,
        )

    async def get_document_count(
        self,
        tenant_id: uuid.UUID,
    ) -> int:
        """Return the number of documents for a tenant.

        Args:
            tenant_id: Tenant scope.

        Returns:
            Document count.
        """
        return await self._repo.get_count(tenant_id)
