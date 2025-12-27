"""Document service for business logic."""

from pathlib import Path
from uuid import UUID

import structlog

from src.modules.documents.exceptions import (
    DocumentAlreadyExistsError,
    DocumentIndexingError,
    DocumentNotFoundError,
    DocumentValidationError,
)
from src.modules.documents.models import Document
from src.modules.documents.repository import DocumentRepository
from src.modules.rag import RAGService
from src.modules.rag.loader import DocumentLoadError, load_document

logger = structlog.get_logger()

# Supported file extensions
SUPPORTED_EXTENSIONS = {".md", ".txt"}

# Maximum file size in bytes (1 MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Maximum number of uploaded documents
MAX_DOCUMENTS = 20

# Characters not allowed in filenames
FORBIDDEN_FILENAME_CHARS = {"/", "\\", "\x00", "\n", "\r"}


class DocumentService:
    """Service for document management business logic.

    Orchestrates document upload, deletion, and indexing operations.
    Handles the coordination between file storage, database, and vector store.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        rag_service: RAGService,
        uploads_path: Path,
        documents_path: Path,
    ) -> None:
        """Initialize the document service.

        Args:
            repository: Document repository for database operations.
            rag_service: RAG service for document indexing.
            uploads_path: Path to the uploads directory.
            documents_path: Path to the static documents directory.
        """
        self._repo = repository
        self._rag = rag_service
        self._uploads_path = uploads_path
        self._documents_path = documents_path

        # Ensure uploads directory exists
        self._uploads_path.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        *,
        description: str | None = None,
        uploaded_by: UUID | None = None,
    ) -> Document:
        """Upload and index a new document.

        Steps:
        1. Validate filename, size, extension
        2. Check for duplicates
        3. Save file to uploads directory
        4. Extract title from content
        5. Create database record
        6. Index via RAG service
        7. Update index status
        8. Return Document

        Args:
            file_content: Raw file content as bytes.
            filename: Original filename.
            description: Optional document description.
            uploaded_by: ID of the user uploading the document.

        Returns:
            Created and indexed Document.

        Raises:
            DocumentValidationError: Invalid file format or size.
            DocumentAlreadyExistsError: Document with same filename exists.
            DocumentIndexingError: Indexing failed.
        """
        # Validate filename
        if not filename:
            raise DocumentValidationError("Filename is required")

        # Sanitize filename - only use the base name and strip whitespace
        safe_filename = Path(filename).name.strip()

        # Robust filename validation
        if not safe_filename or safe_filename in (".", ".."):
            raise DocumentValidationError("Invalid filename")

        # Reject hidden files (starting with .)
        if safe_filename.startswith("."):
            raise DocumentValidationError("Hidden files are not allowed")

        # Check for forbidden characters
        if any(char in safe_filename for char in FORBIDDEN_FILENAME_CHARS):
            raise DocumentValidationError("Filename contains invalid characters")

        # Validate extension
        suffix = Path(safe_filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise DocumentValidationError(
                f"Unsupported file type: {suffix}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # Validate size
        file_size = len(file_content)
        if file_size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            raise DocumentValidationError(
                f"File too large. Maximum size: {max_mb:.0f} MB"
            )

        if file_size == 0:
            raise DocumentValidationError("File is empty")

        # Check for duplicates
        existing = await self._repo.get_by_filename(safe_filename)
        if existing:
            raise DocumentAlreadyExistsError(safe_filename)

        # Check document count limit
        current_count = await self._repo.count()
        if current_count >= MAX_DOCUMENTS:
            raise DocumentValidationError(
                f"Maximum document limit reached ({MAX_DOCUMENTS}). "
                "Please delete existing documents before uploading new ones."
            )

        # Determine file path
        file_path = self._uploads_path / safe_filename

        try:
            # Save file
            file_path.write_bytes(file_content)
            logger.debug(
                "document_file_saved", filename=safe_filename, path=str(file_path)
            )

            # Extract title using existing loader
            loaded_doc = load_document(file_path)
            title = loaded_doc.title
            file_type = loaded_doc.document_type

            # Create database record
            doc = await self._repo.create(
                filename=safe_filename,
                title=title,
                file_path=file_path,
                file_type=file_type,
                file_size_bytes=file_size,
                description=description,
                uploaded_by=uploaded_by,
            )

            # Index the document
            result = await self._rag.index_document(file_path)

            if not result.success:
                # Indexing failed - clean up
                await self._repo.delete(doc.id)
                file_path.unlink(missing_ok=True)
                raise DocumentIndexingError(
                    safe_filename, result.error_message or "Unknown error"
                )

            # Update index status
            await self._repo.update_index_status(doc.id, is_indexed=True)

            logger.info(
                "document_uploaded",
                doc_id=str(doc.id),
                filename=safe_filename,
                title=title,
                chunks_created=result.chunks_created,
                uploaded_by=str(uploaded_by) if uploaded_by else None,
            )

            # Return updated document
            return await self._repo.get_by_id(doc.id) or doc

        except (
            DocumentAlreadyExistsError,
            DocumentValidationError,
            DocumentIndexingError,
        ):
            # Re-raise domain exceptions
            raise
        except DocumentLoadError as e:
            # Clean up on load error
            file_path.unlink(missing_ok=True)
            raise DocumentValidationError(f"Failed to parse document: {e}") from e
        except Exception as e:
            # Clean up on any other error
            file_path.unlink(missing_ok=True)
            logger.error(
                "document_upload_failed",
                filename=safe_filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DocumentValidationError(f"Upload failed: {e}") from e

    async def delete_document(self, doc_id: UUID) -> None:
        """Delete a document and reindex the vector store.

        Due to ChromaDB limitations, we cannot delete individual document
        chunks. Instead, we:
        1. Delete the database record
        2. Delete the file from filesystem
        3. Clear the entire vector store
        4. Reindex all remaining documents

        Args:
            doc_id: UUID of the document to delete.

        Raises:
            DocumentNotFoundError: Document doesn't exist.
        """
        # Get document
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise DocumentNotFoundError(str(doc_id))

        filename = doc.filename
        file_path = doc.file_path

        # Delete from database first
        await self._repo.delete(doc_id)

        # Delete file
        if file_path.exists():
            file_path.unlink()
            logger.debug("document_file_deleted", filename=filename)

        # Clear and reindex
        await self._reindex_all()

        logger.info(
            "document_deleted_and_reindexed",
            doc_id=str(doc_id),
            filename=filename,
        )

    async def _reindex_all(self) -> None:
        """Clear vector store and reindex all documents.

        Reindexes documents from both:
        - Uploaded documents (./uploads/)
        - Static documents (./documents/)

        Updates database records to reflect actual indexing status.
        """
        # Clear existing index
        await self._rag.clear_index()

        # Track successfully indexed filenames
        successfully_indexed: set[str] = set()

        # Reindex static documents
        if self._documents_path.exists():
            results = await self._rag.index_all_documents(self._documents_path)
            for r in results:
                if r.success:
                    successfully_indexed.add(r.source)
            success_count = sum(1 for r in results if r.success)
            logger.debug(
                "static_documents_reindexed",
                path=str(self._documents_path),
                success_count=success_count,
                total=len(results),
            )

        # Reindex uploaded documents
        if self._uploads_path.exists():
            results = await self._rag.index_all_documents(self._uploads_path)
            for r in results:
                if r.success:
                    successfully_indexed.add(r.source)
            success_count = sum(1 for r in results if r.success)
            logger.debug(
                "uploaded_documents_reindexed",
                path=str(self._uploads_path),
                success_count=success_count,
                total=len(results),
            )

        # Update index status based on actual indexing results
        docs = await self._repo.list_all()
        for doc in docs:
            is_indexed = doc.filename in successfully_indexed
            await self._repo.update_index_status(doc.id, is_indexed=is_indexed)
            if not is_indexed:
                logger.warning(
                    "document_reindex_failed",
                    doc_id=str(doc.id),
                    filename=doc.filename,
                )

    async def list_documents(self) -> list[Document]:
        """List all uploaded documents.

        Returns:
            List of documents ordered by creation date (newest first).
        """
        return await self._repo.list_all()

    async def get_document(self, doc_id: UUID) -> Document:
        """Get a document by ID.

        Args:
            doc_id: Document UUID.

        Returns:
            Document instance.

        Raises:
            DocumentNotFoundError: Document doesn't exist.
        """
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise DocumentNotFoundError(str(doc_id))
        return doc

    async def get_document_count(self) -> int:
        """Get the total number of uploaded documents.

        Returns:
            Number of documents.
        """
        return await self._repo.count()
