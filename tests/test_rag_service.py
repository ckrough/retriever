"""Tests for RAG service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.vectordb import RetrievalResult
from src.modules.rag import RAGService


class TestRAGServiceAsk:
    """Tests for RAGService.ask() method."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="This is the answer.")
        return llm

    @pytest.fixture
    def mock_embeddings(self):
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=5)
        store.query = AsyncMock(
            return_value=[
                RetrievalResult(
                    id="chunk1",
                    content="Dogs are great pets.",
                    metadata={"source": "pets.md", "section": "Dogs"},
                    score=0.95,
                ),
                RetrievalResult(
                    id="chunk2",
                    content="Cats are independent.",
                    metadata={"source": "pets.md", "section": "Cats"},
                    score=0.85,
                ),
            ]
        )
        return store

    @pytest.fixture
    def rag_service(self, mock_llm, mock_embeddings, mock_vector_store):
        """Create a RAG service with mocked dependencies."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
        )

    async def test_ask_returns_answer(self, rag_service):
        """Ask should return an answer."""
        response = await rag_service.ask("What pets are good?")

        assert response.answer == "This is the answer."
        assert response.question == "What pets are good?"

    async def test_ask_embeds_question(self, rag_service, mock_embeddings):
        """Ask should embed the question."""
        await rag_service.ask("What pets are good?")

        mock_embeddings.embed.assert_called_once_with("What pets are good?")

    async def test_ask_queries_vector_store(self, rag_service, mock_vector_store):
        """Ask should query the vector store."""
        await rag_service.ask("What pets are good?")

        mock_vector_store.query.assert_called_once()

    async def test_ask_passes_context_to_llm(self, rag_service, mock_llm):
        """Ask should pass retrieved context to LLM."""
        await rag_service.ask("What pets are good?")

        mock_llm.complete.assert_called_once()
        call_kwargs = mock_llm.complete.call_args.kwargs
        # System prompt should contain the context
        assert "Dogs are great pets" in call_kwargs["system_prompt"]
        assert "Cats are independent" in call_kwargs["system_prompt"]

    async def test_ask_returns_chunks_used(self, rag_service):
        """Ask should return the chunks that were used."""
        response = await rag_service.ask("What pets are good?")

        assert len(response.chunks_used) == 2
        assert response.chunks_used[0].source == "pets.md"
        assert response.chunks_used[0].section == "Dogs"


class TestRAGServiceAskNoDocuments:
    """Tests for RAG service when no documents are indexed."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="I don't have any documents.")
        return llm

    @pytest.fixture
    def mock_embeddings(self):
        """Create a mock embedding provider."""
        return MagicMock()

    @pytest.fixture
    def empty_vector_store(self):
        """Create an empty mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=0)
        return store

    @pytest.fixture
    def rag_service(self, mock_llm, mock_embeddings, empty_vector_store):
        """Create a RAG service with empty vector store."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=empty_vector_store,
        )

    async def test_ask_with_no_documents_uses_fallback(self, rag_service, mock_llm):
        """Ask with no documents should use fallback prompt."""
        await rag_service.ask("What pets are good?")

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert "No shelter documents have been indexed" in call_kwargs["system_prompt"]

    async def test_ask_with_no_documents_returns_empty_chunks(self, rag_service):
        """Ask with no documents should return empty chunks list."""
        response = await rag_service.ask("What pets are good?")

        assert response.chunks_used == []


class TestRAGServiceIndexDocument:
    """Tests for RAGService.index_document() method."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        return MagicMock()

    @pytest.fixture
    def mock_embeddings(self):
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        # Return embedding for each input text
        embeddings.embed_batch = AsyncMock(
            side_effect=lambda texts: [[0.1] * 1536 for _ in texts]
        )
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=0)
        store.add_chunks = AsyncMock()
        store.clear = AsyncMock()
        return store

    @pytest.fixture
    def rag_service(self, mock_llm, mock_embeddings, mock_vector_store):
        """Create a RAG service with mocked dependencies."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
        )

    async def test_index_document_returns_result(self, rag_service, tmp_path: Path):
        """Index document should return result."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test\n\nThis is test content.")

        result = await rag_service.index_document(doc_path)

        assert result.success is True
        assert result.source == "test.md"
        assert result.chunks_created >= 1

    async def test_index_document_embeds_chunks(
        self, rag_service, mock_embeddings, tmp_path: Path
    ):
        """Index document should embed all chunks."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test\n\nThis is test content.")

        await rag_service.index_document(doc_path)

        mock_embeddings.embed_batch.assert_called_once()

    async def test_index_document_stores_chunks(
        self, rag_service, mock_vector_store, tmp_path: Path
    ):
        """Index document should store chunks in vector store."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test\n\nThis is test content.")

        await rag_service.index_document(doc_path)

        mock_vector_store.add_chunks.assert_called_once()

    async def test_index_nonexistent_file_returns_failure(
        self, rag_service, tmp_path: Path
    ):
        """Index nonexistent file should return failure result."""
        doc_path = tmp_path / "missing.md"

        result = await rag_service.index_document(doc_path)

        assert result.success is False
        assert "not found" in result.error_message.lower()


class TestRAGServiceIndexAllDocuments:
    """Tests for RAGService.index_all_documents() method."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        return MagicMock()

    @pytest.fixture
    def mock_embeddings(self):
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        # Return embedding for each input text
        embeddings.embed_batch = AsyncMock(
            side_effect=lambda texts: [[0.1] * 1536 for _ in texts]
        )
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=0)
        store.add_chunks = AsyncMock()
        store.clear = AsyncMock()
        return store

    @pytest.fixture
    def rag_service(self, mock_llm, mock_embeddings, mock_vector_store):
        """Create a RAG service with mocked dependencies."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
        )

    async def test_index_all_documents(self, rag_service, tmp_path: Path):
        """Index all documents should process all files."""
        (tmp_path / "doc1.md").write_text("# Doc 1\n\nContent 1")
        (tmp_path / "doc2.md").write_text("# Doc 2\n\nContent 2")

        results = await rag_service.index_all_documents(tmp_path)

        assert len(results) == 2
        assert all(r.success for r in results)

    async def test_index_all_empty_directory(self, rag_service, tmp_path: Path):
        """Index all in empty directory should return empty list."""
        results = await rag_service.index_all_documents(tmp_path)

        assert results == []


class TestRAGServiceClearIndex:
    """Tests for RAGService.clear_index() method."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.clear = AsyncMock()
        return store

    @pytest.fixture
    def rag_service(self, mock_vector_store):
        """Create a RAG service with mocked dependencies."""
        return RAGService(
            llm_provider=MagicMock(),
            embedding_provider=MagicMock(),
            vector_store=mock_vector_store,
        )

    async def test_clear_index_calls_store_clear(self, rag_service, mock_vector_store):
        """Clear index should call vector store clear."""
        await rag_service.clear_index()

        mock_vector_store.clear.assert_called_once()


class TestRAGServiceGetDocumentCount:
    """Tests for RAGService.get_document_count() method."""

    def test_get_document_count_returns_store_count(self):
        """Get document count should return vector store count."""
        store = MagicMock()
        store.count = MagicMock(return_value=42)

        service = RAGService(
            llm_provider=MagicMock(),
            embedding_provider=MagicMock(),
            vector_store=store,
        )

        assert service.get_document_count() == 42
