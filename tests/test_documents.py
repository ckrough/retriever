"""Tests for document management module."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.infrastructure.database import Database
from src.modules.documents import (
    Document,
    DocumentAlreadyExistsError,
    DocumentIndexingError,
    DocumentNotFoundError,
    DocumentRepository,
    DocumentService,
    DocumentValidationError,
)
from src.modules.rag import RAGService
from src.modules.rag.schemas import IndexingResult


@pytest.fixture
async def database() -> Database:
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        await db.connect()
        yield db
        await db.disconnect()


@pytest.fixture
async def repository(database: Database) -> DocumentRepository:
    """Create a document repository with test database."""
    return DocumentRepository(database)


@pytest.fixture
def mock_rag_service() -> MagicMock:
    """Create a mock RAG service."""
    mock = MagicMock(spec=RAGService)
    mock.index_document = AsyncMock(
        return_value=IndexingResult(
            source="test.md",
            success=True,
            chunks_created=5,
            error_message=None,
        )
    )
    mock.clear_index = AsyncMock()
    mock.index_all_documents = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def temp_dirs() -> tuple[Path, Path]:
    """Create temporary upload and documents directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        uploads = Path(tmpdir) / "uploads"
        documents = Path(tmpdir) / "documents"
        uploads.mkdir()
        documents.mkdir()
        yield uploads, documents


class TestDocumentModel:
    """Tests for Document model."""

    def test_document_creation(self) -> None:
        """Should create a document with all fields."""
        now = datetime.now(UTC)
        doc = Document(
            id=uuid4(),
            filename="test.md",
            title="Test Document",
            description="A test document",
            file_path=Path("/tmp/test.md"),
            file_type="markdown",
            file_size_bytes=1024,
            uploaded_by=uuid4(),
            is_indexed=True,
            created_at=now,
            updated_at=now,
        )
        assert doc.filename == "test.md"
        assert doc.title == "Test Document"
        assert doc.is_indexed

    def test_document_from_row(self) -> None:
        """Should create document from database row."""
        now = datetime.now(UTC).isoformat()
        doc_id = str(uuid4())
        user_id = str(uuid4())
        row = {
            "id": doc_id,
            "filename": "test.md",
            "title": "Test Document",
            "description": "A test",
            "file_path": "/tmp/test.md",
            "file_type": "markdown",
            "file_size_bytes": 1024,
            "uploaded_by": user_id,
            "is_indexed": 1,
            "created_at": now,
            "updated_at": now,
        }
        doc = Document.from_row(row)
        assert doc.filename == "test.md"
        assert doc.is_indexed
        assert doc.uploaded_by is not None

    def test_document_from_row_without_uploaded_by(self) -> None:
        """Should handle null uploaded_by."""
        now = datetime.now(UTC).isoformat()
        row = {
            "id": str(uuid4()),
            "filename": "test.md",
            "title": "Test",
            "description": None,
            "file_path": "/tmp/test.md",
            "file_type": "text",
            "file_size_bytes": 512,
            "uploaded_by": None,
            "is_indexed": 0,
            "created_at": now,
            "updated_at": now,
        }
        doc = Document.from_row(row)
        assert doc.uploaded_by is None
        assert not doc.is_indexed


class TestDocumentRepository:
    """Tests for DocumentRepository."""

    @pytest.mark.asyncio
    async def test_create_document(self, repository: DocumentRepository) -> None:
        """Should create a document in the database."""
        doc = await repository.create(
            filename="test.md",
            title="Test Document",
            file_path=Path("/tmp/test.md"),
            file_type="markdown",
            file_size_bytes=1024,
        )
        assert doc.filename == "test.md"
        assert doc.title == "Test Document"
        assert doc.id is not None

    @pytest.mark.asyncio
    async def test_create_document_with_description(
        self, repository: DocumentRepository
    ) -> None:
        """Should create document with optional description."""
        doc = await repository.create(
            filename="test.txt",
            title="Full Doc",
            file_path=Path("/tmp/test.txt"),
            file_type="text",
            file_size_bytes=512,
            description="A full document",
        )
        assert doc.description == "A full document"
        assert doc.uploaded_by is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: DocumentRepository) -> None:
        """Should retrieve document by ID."""
        doc = await repository.create(
            filename="test.md",
            title="Test",
            file_path=Path("/tmp/test.md"),
            file_type="markdown",
            file_size_bytes=100,
        )
        retrieved = await repository.get_by_id(doc.id)
        assert retrieved is not None
        assert retrieved.id == doc.id
        assert retrieved.filename == "test.md"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: DocumentRepository) -> None:
        """Should return None for non-existent ID."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_filename(self, repository: DocumentRepository) -> None:
        """Should retrieve document by filename."""
        await repository.create(
            filename="unique.md",
            title="Unique",
            file_path=Path("/tmp/unique.md"),
            file_type="markdown",
            file_size_bytes=200,
        )
        result = await repository.get_by_filename("unique.md")
        assert result is not None
        assert result.filename == "unique.md"

    @pytest.mark.asyncio
    async def test_get_by_filename_not_found(
        self, repository: DocumentRepository
    ) -> None:
        """Should return None for non-existent filename."""
        result = await repository.get_by_filename("nonexistent.md")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, repository: DocumentRepository) -> None:
        """Should list all documents ordered by created_at desc."""
        await repository.create(
            filename="first.md",
            title="First",
            file_path=Path("/tmp/first.md"),
            file_type="markdown",
            file_size_bytes=100,
        )
        await repository.create(
            filename="second.md",
            title="Second",
            file_path=Path("/tmp/second.md"),
            file_type="markdown",
            file_size_bytes=200,
        )
        docs = await repository.list_all()
        assert len(docs) == 2
        # Newest first
        assert docs[0].filename == "second.md"
        assert docs[1].filename == "first.md"

    @pytest.mark.asyncio
    async def test_update_index_status(self, repository: DocumentRepository) -> None:
        """Should update document index status."""
        doc = await repository.create(
            filename="test.md",
            title="Test",
            file_path=Path("/tmp/test.md"),
            file_type="markdown",
            file_size_bytes=100,
        )
        assert not doc.is_indexed

        await repository.update_index_status(doc.id, is_indexed=True)
        updated = await repository.get_by_id(doc.id)
        assert updated is not None
        assert updated.is_indexed

    @pytest.mark.asyncio
    async def test_delete(self, repository: DocumentRepository) -> None:
        """Should delete a document."""
        doc = await repository.create(
            filename="delete-me.md",
            title="Delete Me",
            file_path=Path("/tmp/delete-me.md"),
            file_type="markdown",
            file_size_bytes=50,
        )
        await repository.delete(doc.id)
        result = await repository.get_by_id(doc.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_count(self, repository: DocumentRepository) -> None:
        """Should count documents."""
        assert await repository.count() == 0

        await repository.create(
            filename="one.md",
            title="One",
            file_path=Path("/tmp/one.md"),
            file_type="markdown",
            file_size_bytes=100,
        )
        assert await repository.count() == 1

        await repository.create(
            filename="two.md",
            title="Two",
            file_path=Path("/tmp/two.md"),
            file_type="markdown",
            file_size_bytes=100,
        )
        assert await repository.count() == 2


class TestDocumentService:
    """Tests for DocumentService."""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should upload and index a document."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        content = b"# Test Document\n\nThis is a test."
        doc = await service.upload_document(
            file_content=content,
            filename="test.md",
            description="A test document",
        )

        assert doc.filename == "test.md"
        assert doc.title == "Test Document"
        assert (uploads / "test.md").exists()
        mock_rag_service.index_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_validates_extension(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject unsupported file types."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentValidationError, match="Unsupported file type"):
            await service.upload_document(
                file_content=b"test",
                filename="test.pdf",
            )

    @pytest.mark.asyncio
    async def test_upload_document_validates_size(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject files that are too large."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        # 2 MB content (exceeds 1 MB limit)
        large_content = b"x" * (2 * 1024 * 1024)
        with pytest.raises(DocumentValidationError, match="File too large"):
            await service.upload_document(
                file_content=large_content,
                filename="large.md",
            )

    @pytest.mark.asyncio
    async def test_upload_document_validates_empty(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject empty files."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentValidationError, match="File is empty"):
            await service.upload_document(
                file_content=b"",
                filename="empty.md",
            )

    @pytest.mark.asyncio
    async def test_upload_document_rejects_duplicate(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject duplicate filenames."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        content = b"# Test\n\nContent"
        await service.upload_document(file_content=content, filename="dup.md")

        with pytest.raises(DocumentAlreadyExistsError):
            await service.upload_document(file_content=content, filename="dup.md")

    @pytest.mark.asyncio
    async def test_upload_document_validates_filename(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject invalid filenames."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentValidationError, match="Hidden files"):
            await service.upload_document(
                file_content=b"test",
                filename=".hidden.md",
            )

    @pytest.mark.asyncio
    async def test_upload_document_enforces_limit(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should reject uploads when at document limit."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        # Create 20 documents to hit limit
        for i in range(20):
            content = f"# Doc {i}\n\nContent".encode()
            await service.upload_document(file_content=content, filename=f"doc{i}.md")

        with pytest.raises(DocumentValidationError, match="Maximum document limit"):
            await service.upload_document(
                file_content=b"# Too many\n\nContent",
                filename="toomany.md",
            )

    @pytest.mark.asyncio
    async def test_upload_document_handles_indexing_failure(
        self,
        database: Database,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should clean up on indexing failure."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)

        mock_rag = MagicMock(spec=RAGService)
        mock_rag.index_document = AsyncMock(
            return_value=IndexingResult(
                source="fail.md",
                success=False,
                chunks_created=0,
                error_message="Embedding failed",
            )
        )

        service = DocumentService(
            repository=repo,
            rag_service=mock_rag,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentIndexingError):
            await service.upload_document(
                file_content=b"# Fail\n\nContent",
                filename="fail.md",
            )

        # File should be cleaned up
        assert not (uploads / "fail.md").exists()
        # DB record should be cleaned up
        assert await repo.count() == 0

    @pytest.mark.asyncio
    async def test_delete_document(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should delete document and trigger reindex."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        content = b"# Delete Me\n\nContent"
        doc = await service.upload_document(file_content=content, filename="delete.md")

        await service.delete_document(doc.id)

        assert not (uploads / "delete.md").exists()
        assert await repo.get_by_id(doc.id) is None
        mock_rag_service.clear_index.assert_called()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should raise error for non-existent document."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentNotFoundError):
            await service.delete_document(uuid4())

    @pytest.mark.asyncio
    async def test_list_documents(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should list all documents."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        await service.upload_document(
            file_content=b"# One\n\nContent", filename="one.md"
        )
        await service.upload_document(
            file_content=b"# Two\n\nContent", filename="two.md"
        )

        docs = await service.list_documents()
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_get_document(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should get document by ID."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        created = await service.upload_document(
            file_content=b"# Get Me\n\nContent", filename="get.md"
        )
        doc = await service.get_document(created.id)
        assert doc.filename == "get.md"

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should raise error for non-existent document."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        with pytest.raises(DocumentNotFoundError):
            await service.get_document(uuid4())

    @pytest.mark.asyncio
    async def test_get_document_count(
        self,
        database: Database,
        mock_rag_service: MagicMock,
        temp_dirs: tuple[Path, Path],
    ) -> None:
        """Should count documents."""
        uploads, documents = temp_dirs
        repo = DocumentRepository(database)
        service = DocumentService(
            repository=repo,
            rag_service=mock_rag_service,
            uploads_path=uploads,
            documents_path=documents,
        )

        assert await service.get_document_count() == 0

        await service.upload_document(
            file_content=b"# Count\n\nContent", filename="count.md"
        )
        assert await service.get_document_count() == 1


class TestDocumentExceptions:
    """Tests for document exceptions."""

    def test_document_not_found_error(self) -> None:
        """Should create DocumentNotFoundError with identifier."""
        error = DocumentNotFoundError("abc123")
        assert "abc123" in str(error)

    def test_document_already_exists_error(self) -> None:
        """Should create DocumentAlreadyExistsError with filename."""
        error = DocumentAlreadyExistsError("test.md")
        assert error.filename == "test.md"
        assert "test.md" in str(error)

    def test_document_validation_error(self) -> None:
        """Should create DocumentValidationError with message."""
        error = DocumentValidationError("Invalid format")
        assert "Invalid format" in str(error)

    def test_document_indexing_error(self) -> None:
        """Should create DocumentIndexingError with details."""
        error = DocumentIndexingError("test.md", "Embedding failed")
        assert error.filename == "test.md"
        assert error.reason == "Embedding failed"
        assert "test.md" in str(error)
