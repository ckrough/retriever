"""Tests for hybrid retriever combining semantic and keyword search."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.vectordb import RetrievalResult
from src.modules.rag.retriever import HybridRetriever, IndexedDocument


class TestHybridRetrieverKeywordIndex:
    """Tests for HybridRetriever keyword index management."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=0)
        store.query = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def retriever(
        self,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
    ) -> HybridRetriever:
        """Create a hybrid retriever with mocks."""
        return HybridRetriever(
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_weight=0.5,
            keyword_weight=0.5,
        )

    def test_keyword_index_starts_empty(self, retriever: HybridRetriever) -> None:
        """Keyword index should start empty."""
        assert retriever.get_keyword_index_count() == 0

    def test_build_keyword_index_populates_index(
        self, retriever: HybridRetriever
    ) -> None:
        """Building keyword index should populate the BM25 index."""
        docs = [
            IndexedDocument(
                id="doc1",
                content="Dogs are great pets for families.",
                metadata={"source": "pets.md"},
            ),
            IndexedDocument(
                id="doc2",
                content="Cats require less maintenance than dogs.",
                metadata={"source": "pets.md"},
            ),
        ]

        retriever.build_keyword_index(docs)

        assert retriever.get_keyword_index_count() == 2

    def test_clear_keyword_index_empties_index(
        self, retriever: HybridRetriever
    ) -> None:
        """Clearing keyword index should empty it."""
        docs = [
            IndexedDocument(
                id="doc1",
                content="Test content",
                metadata={"source": "test.md"},
            ),
        ]

        retriever.build_keyword_index(docs)
        assert retriever.get_keyword_index_count() == 1

        retriever.clear_keyword_index()
        assert retriever.get_keyword_index_count() == 0

    def test_build_keyword_index_with_empty_list(
        self, retriever: HybridRetriever
    ) -> None:
        """Building keyword index with empty list should work."""
        retriever.build_keyword_index([])
        assert retriever.get_keyword_index_count() == 0


class TestHybridRetrieverKeywordSearch:
    """Tests for HybridRetriever keyword search."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=0)
        store.query = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def retriever_with_docs(
        self,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
    ) -> HybridRetriever:
        """Create a hybrid retriever with pre-indexed documents."""
        retriever = HybridRetriever(
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_weight=0.5,
            keyword_weight=0.5,
        )

        docs = [
            IndexedDocument(
                id="doc1",
                content="Dogs are loyal and friendly pets for families.",
                metadata={"source": "pets.md", "section": "Dogs"},
            ),
            IndexedDocument(
                id="doc2",
                content="Cats are independent and low maintenance.",
                metadata={"source": "pets.md", "section": "Cats"},
            ),
            IndexedDocument(
                id="doc3",
                content="COVID-19 vaccination protocols for shelter animals.",
                metadata={"source": "health.md", "section": "Vaccines"},
            ),
        ]

        retriever.build_keyword_index(docs)
        return retriever

    def test_keyword_search_finds_matching_documents(
        self, retriever_with_docs: HybridRetriever
    ) -> None:
        """Keyword search should find documents with matching terms."""
        results = retriever_with_docs._keyword_search("dogs", top_k=5)

        assert len(results) >= 1
        # The document about dogs should be in results
        doc_ids = [r.id for r in results]
        assert "doc1" in doc_ids

    def test_keyword_search_respects_top_k(
        self, retriever_with_docs: HybridRetriever
    ) -> None:
        """Keyword search should return at most top_k results."""
        results = retriever_with_docs._keyword_search("pets", top_k=1)

        assert len(results) <= 1

    def test_keyword_search_returns_empty_for_no_matches(
        self, retriever_with_docs: HybridRetriever
    ) -> None:
        """Keyword search should return empty for queries with no matches."""
        # Use a term that doesn't appear in any document
        results = retriever_with_docs._keyword_search("xyznonexistent", top_k=5)

        assert len(results) == 0

    def test_keyword_search_handles_exact_terms(
        self, retriever_with_docs: HybridRetriever
    ) -> None:
        """Keyword search should handle exact technical terms like COVID-19."""
        results = retriever_with_docs._keyword_search("COVID-19", top_k=5)

        assert len(results) >= 1
        doc_ids = [r.id for r in results]
        assert "doc3" in doc_ids


class TestHybridRetrieverRRF:
    """Tests for Reciprocal Rank Fusion merging."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=3)
        store.query = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def retriever(
        self,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
    ) -> HybridRetriever:
        """Create a hybrid retriever with mocks."""
        return HybridRetriever(
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_weight=0.5,
            keyword_weight=0.5,
            rrf_k=60,
        )

    def test_rrf_merges_both_result_sets(self, retriever: HybridRetriever) -> None:
        """RRF should include results from both semantic and keyword search."""
        semantic_results = [
            RetrievalResult(id="doc1", content="Content 1", metadata={}, score=0.9),
            RetrievalResult(id="doc2", content="Content 2", metadata={}, score=0.8),
        ]
        keyword_results = [
            RetrievalResult(id="doc2", content="Content 2", metadata={}, score=5.0),
            RetrievalResult(id="doc3", content="Content 3", metadata={}, score=3.0),
        ]

        merged = retriever._reciprocal_rank_fusion(semantic_results, keyword_results)

        # Should have all 3 unique documents
        merged_ids = [r.id for r in merged]
        assert "doc1" in merged_ids
        assert "doc2" in merged_ids
        assert "doc3" in merged_ids

    def test_rrf_ranks_shared_results_higher(self, retriever: HybridRetriever) -> None:
        """Documents appearing in both lists should rank higher."""
        semantic_results = [
            RetrievalResult(id="doc1", content="Content 1", metadata={}, score=0.9),
            RetrievalResult(id="doc2", content="Content 2", metadata={}, score=0.8),
        ]
        keyword_results = [
            RetrievalResult(id="doc2", content="Content 2", metadata={}, score=5.0),
            RetrievalResult(id="doc3", content="Content 3", metadata={}, score=3.0),
        ]

        merged = retriever._reciprocal_rank_fusion(semantic_results, keyword_results)

        # doc2 appears in both, so it should be ranked highest
        assert merged[0].id == "doc2"

    def test_rrf_handles_empty_keyword_results(
        self, retriever: HybridRetriever
    ) -> None:
        """RRF should handle empty keyword results gracefully."""
        semantic_results = [
            RetrievalResult(id="doc1", content="Content 1", metadata={}, score=0.9),
        ]
        keyword_results: list[RetrievalResult] = []

        merged = retriever._reciprocal_rank_fusion(semantic_results, keyword_results)

        assert len(merged) == 1
        assert merged[0].id == "doc1"

    def test_rrf_handles_empty_semantic_results(
        self, retriever: HybridRetriever
    ) -> None:
        """RRF should handle empty semantic results gracefully."""
        semantic_results: list[RetrievalResult] = []
        keyword_results = [
            RetrievalResult(id="doc1", content="Content 1", metadata={}, score=5.0),
        ]

        merged = retriever._reciprocal_rank_fusion(semantic_results, keyword_results)

        assert len(merged) == 1
        assert merged[0].id == "doc1"


class TestHybridRetrieverRetrieve:
    """Tests for the full hybrid retrieve method."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create a mock vector store."""
        store = MagicMock()
        store.count = MagicMock(return_value=3)
        store.query = AsyncMock(
            return_value=[
                RetrievalResult(
                    id="doc1",
                    content="Dogs are great pets.",
                    metadata={"source": "pets.md"},
                    score=0.95,
                ),
            ]
        )
        return store

    @pytest.fixture
    def retriever_with_docs(
        self,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
    ) -> HybridRetriever:
        """Create a hybrid retriever with pre-indexed documents."""
        retriever = HybridRetriever(
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_weight=0.5,
            keyword_weight=0.5,
        )

        docs = [
            IndexedDocument(
                id="doc1",
                content="Dogs are great pets for families.",
                metadata={"source": "pets.md"},
            ),
            IndexedDocument(
                id="doc2",
                content="Cats are independent animals.",
                metadata={"source": "pets.md"},
            ),
        ]

        retriever.build_keyword_index(docs)
        return retriever

    async def test_retrieve_combines_semantic_and_keyword(
        self,
        retriever_with_docs: HybridRetriever,
        mock_embeddings: MagicMock,
    ) -> None:
        """Retrieve should use both semantic and keyword search."""
        results = await retriever_with_docs.retrieve("dogs", top_k=5)

        # Should call embedding for semantic search
        mock_embeddings.embed.assert_called_once_with("dogs")

        # Should return results
        assert len(results) >= 1

    async def test_retrieve_returns_empty_when_no_documents(
        self,
        mock_embeddings: MagicMock,
    ) -> None:
        """Retrieve should return empty when no documents indexed."""
        empty_store = MagicMock()
        empty_store.count = MagicMock(return_value=0)

        retriever = HybridRetriever(
            embedding_provider=mock_embeddings,
            vector_store=empty_store,
        )

        results = await retriever.retrieve("test query", top_k=5)

        assert results == []

    async def test_retrieve_respects_top_k(
        self,
        retriever_with_docs: HybridRetriever,
        mock_vector_store: MagicMock,
    ) -> None:
        """Retrieve should return at most top_k results."""
        # Configure store to return multiple results
        mock_vector_store.query = AsyncMock(
            return_value=[
                RetrievalResult(
                    id="doc1",
                    content="Content 1",
                    metadata={"source": "test.md"},
                    score=0.9,
                ),
                RetrievalResult(
                    id="doc2",
                    content="Content 2",
                    metadata={"source": "test.md"},
                    score=0.8,
                ),
                RetrievalResult(
                    id="doc3",
                    content="Content 3",
                    metadata={"source": "test.md"},
                    score=0.7,
                ),
            ]
        )

        results = await retriever_with_docs.retrieve("test", top_k=2)

        assert len(results) <= 2


class TestTokenization:
    """Tests for the tokenization helper."""

    def test_tokenize_lowercase(self) -> None:
        """Tokenization should convert to lowercase."""
        tokens = HybridRetriever._tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_tokenize_removes_punctuation(self) -> None:
        """Tokenization should remove punctuation."""
        tokens = HybridRetriever._tokenize("Hello, World! How are you?")
        assert tokens == ["hello", "world", "how", "are", "you"]

    def test_tokenize_handles_numbers(self) -> None:
        """Tokenization should handle numbers."""
        tokens = HybridRetriever._tokenize("COVID-19 vaccine protocol")
        assert "covid" in tokens
        assert "19" in tokens
        assert "vaccine" in tokens

    def test_tokenize_handles_empty_string(self) -> None:
        """Tokenization should handle empty strings."""
        tokens = HybridRetriever._tokenize("")
        assert tokens == []
