"""Document repository for database operations."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from src.infrastructure.database import Database
from src.modules.documents.exceptions import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
)
from src.modules.documents.models import Document

logger = structlog.get_logger()


class DocumentRepository:
    """Repository for document CRUD operations.

    Handles all database interactions for document metadata.
    File storage is handled by the service layer.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the repository.

        Args:
            database: Database connection instance.
        """
        self._db = database

    async def create(
        self,
        filename: str,
        title: str,
        file_path: Path,
        file_type: str,
        file_size_bytes: int,
        *,
        description: str | None = None,
        uploaded_by: UUID | None = None,
    ) -> Document:
        """Create a new document record.

        Args:
            filename: Original filename.
            title: Document title (extracted or provided).
            file_path: Path where file is stored.
            file_type: Type of document ('markdown' or 'text').
            file_size_bytes: Size of the file in bytes.
            description: Optional document description.
            uploaded_by: ID of the user who uploaded the document.

        Returns:
            Created Document instance.

        Raises:
            DocumentAlreadyExistsError: If a document with the same filename exists.
        """
        doc_id = uuid4()
        now = datetime.now(UTC).isoformat()

        try:
            await self._db.execute(
                """
                INSERT INTO documents (
                    id, filename, title, description, file_path, file_type,
                    file_size_bytes, uploaded_by, is_indexed, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    str(doc_id),
                    filename,
                    title,
                    description,
                    str(file_path),
                    file_type,
                    file_size_bytes,
                    str(uploaded_by) if uploaded_by else None,
                    now,
                    now,
                ),
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise DocumentAlreadyExistsError(filename) from e
            raise

        logger.info(
            "document_created",
            doc_id=str(doc_id),
            filename=filename,
            file_type=file_type,
        )

        return Document(
            id=doc_id,
            filename=filename,
            title=title,
            description=description,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            uploaded_by=uploaded_by,
            is_indexed=False,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    async def get_by_id(self, doc_id: UUID) -> Document | None:
        """Get a document by its ID.

        Args:
            doc_id: Document UUID.

        Returns:
            Document if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM documents WHERE id = ?",
            (str(doc_id),),
        )
        return Document.from_row(dict(row)) if row else None

    async def get_by_filename(self, filename: str) -> Document | None:
        """Get a document by its filename.

        Args:
            filename: Document filename.

        Returns:
            Document if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM documents WHERE filename = ?",
            (filename,),
        )
        return Document.from_row(dict(row)) if row else None

    async def list_all(self, *, include_unindexed: bool = True) -> list[Document]:
        """List all documents.

        Args:
            include_unindexed: Whether to include documents that are not indexed.

        Returns:
            List of documents ordered by creation date (newest first).
        """
        if include_unindexed:
            rows = await self._db.fetch_all(
                "SELECT * FROM documents ORDER BY created_at DESC"
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM documents WHERE is_indexed = 1 ORDER BY created_at DESC"
            )
        return [Document.from_row(dict(row)) for row in rows]

    async def update_index_status(self, doc_id: UUID, is_indexed: bool) -> None:
        """Update the indexing status of a document.

        Args:
            doc_id: Document UUID.
            is_indexed: New indexing status.

        Raises:
            DocumentNotFoundError: If document doesn't exist.
        """
        now = datetime.now(UTC).isoformat()
        cursor = await self._db.execute(
            "UPDATE documents SET is_indexed = ?, updated_at = ? WHERE id = ?",
            (1 if is_indexed else 0, now, str(doc_id)),
        )
        if cursor.rowcount == 0:
            raise DocumentNotFoundError(str(doc_id))

        logger.debug(
            "document_index_status_updated",
            doc_id=str(doc_id),
            is_indexed=is_indexed,
        )

    async def delete(self, doc_id: UUID) -> Document:
        """Delete a document record.

        Args:
            doc_id: Document UUID.

        Returns:
            The deleted Document.

        Raises:
            DocumentNotFoundError: If document doesn't exist.
        """
        # First get the document
        doc = await self.get_by_id(doc_id)
        if doc is None:
            raise DocumentNotFoundError(str(doc_id))

        await self._db.execute(
            "DELETE FROM documents WHERE id = ?",
            (str(doc_id),),
        )

        logger.info("document_deleted", doc_id=str(doc_id), filename=doc.filename)
        return doc

    async def count(self) -> int:
        """Get the total number of documents.

        Returns:
            Number of documents.
        """
        row = await self._db.fetch_one("SELECT COUNT(*) as count FROM documents")
        return int(row["count"]) if row else 0
