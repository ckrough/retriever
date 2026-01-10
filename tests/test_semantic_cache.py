"""Tests for semantic cache."""

import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.cache import CacheEntry, ChromaSemanticCache
from src.infrastructure.vectordb import RetrievalResult
from src.modules.rag import RAGService


class TestChromeSemanticCacheGet:
    """Tests for ChromaSemanticCache.get() method."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def cache(self, mock_embeddings: MagicMock) -> ChromaSemanticCache:
        """Create a semantic cache with a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ChromaSemanticCache(
                embedding_provider=mock_embeddings,
                persist_path=Path(tmpdir),
                similarity_threshold=0.95,
                ttl_hours=24,
            )
            yield cache

    async def test_get_returns_none_when_empty(
        self, cache: ChromaSemanticCache
    ) -> None:
        """Get should return None when cache is empty."""
        result = await cache.get("What is the policy?")
        assert result is None

    async def test_get_returns_none_below_threshold(
        self, cache: ChromaSemanticCache
    ) -> None:
        """Get should return None when similarity is below threshold."""
        # Store an entry
        await cache.set(
            question="What is the check-in policy?",
            answer="Check in at the front desk.",
            chunks_json="[]",
        )

        # Query with different embedding (simulating low similarity)
        # The mock always returns the same embedding, so this would be a hit
        # We need to mock Chroma's response to simulate low similarity
        with patch.object(
            cache._collection,
            "query",
            return_value={
                "ids": [["cache:test"]],
                "documents": [["Check in at the front desk."]],
                "metadatas": [
                    [
                        {
                            "question": "What is the check-in policy?",
                            "chunks_json": "[]",
                            "created_at": datetime.now(UTC).isoformat(),
                        }
                    ]
                ],
                "distances": [[0.2]],  # Low similarity (1 - 0.2 = 0.8 < 0.95)
            },
        ):
            result = await cache.get("Something completely different")
            assert result is None


class TestChromeSemanticCacheSet:
    """Tests for ChromaSemanticCache.set() method."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def cache(self, mock_embeddings: MagicMock) -> ChromaSemanticCache:
        """Create a semantic cache with a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ChromaSemanticCache(
                embedding_provider=mock_embeddings,
                persist_path=Path(tmpdir),
                similarity_threshold=0.95,
                ttl_hours=24,
            )
            yield cache

    async def test_set_stores_entry(self, cache: ChromaSemanticCache) -> None:
        """Set should store a cache entry."""
        await cache.set(
            question="Where do volunteers sign in?",
            answer="At the front desk.",
            chunks_json='[{"content": "Sign in at front desk."}]',
        )

        assert cache.count() == 1

    async def test_set_embeds_question(
        self, cache: ChromaSemanticCache, mock_embeddings: MagicMock
    ) -> None:
        """Set should embed the question."""
        await cache.set(
            question="Where do volunteers sign in?",
            answer="At the front desk.",
            chunks_json="[]",
        )

        mock_embeddings.embed.assert_called_with("Where do volunteers sign in?")


class TestChromeSemanticCacheClear:
    """Tests for ChromaSemanticCache.clear() method."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def cache(self, mock_embeddings: MagicMock) -> ChromaSemanticCache:
        """Create a semantic cache with a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ChromaSemanticCache(
                embedding_provider=mock_embeddings,
                persist_path=Path(tmpdir),
                similarity_threshold=0.95,
                ttl_hours=24,
            )
            yield cache

    async def test_clear_removes_all_entries(self, cache: ChromaSemanticCache) -> None:
        """Clear should remove all cache entries."""
        # Add some entries
        await cache.set("Q1", "A1", "[]")
        await cache.set("Q2", "A2", "[]")
        assert cache.count() == 2

        # Clear
        await cache.clear()
        assert cache.count() == 0


class TestChromaSemanticCacheIntegration:
    """Integration tests for ChromaSemanticCache with real Chroma."""

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        # Return consistent embeddings for same questions
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def cache(self, mock_embeddings: MagicMock) -> ChromaSemanticCache:
        """Create a semantic cache with a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ChromaSemanticCache(
                embedding_provider=mock_embeddings,
                persist_path=Path(tmpdir),
                similarity_threshold=0.95,
                ttl_hours=24,
            )
            yield cache

    async def test_cache_hit_with_similar_question(
        self, cache: ChromaSemanticCache
    ) -> None:
        """Cache should return entry when question embedding matches."""
        # Store an entry
        await cache.set(
            question="Where do volunteers sign in?",
            answer="At the front desk.",
            chunks_json='[{"content": "Sign in at front desk."}]',
        )

        # Query - will use same embedding (mock returns constant)
        # so distance will be 0 (similarity = 1.0)
        result = await cache.get("Where do volunteers sign in?")

        assert result is not None
        assert result.answer == "At the front desk."
        assert result.similarity_score > 0.95

    async def test_count_returns_correct_value(
        self, cache: ChromaSemanticCache
    ) -> None:
        """Count should return number of cached entries."""
        assert cache.count() == 0

        await cache.set("Q1", "A1", "[]")
        assert cache.count() == 1

        await cache.set("Q2", "A2", "[]")
        assert cache.count() == 2


class TestRAGServiceWithCache:
    """Tests for RAGService with semantic cache integration."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create a mock LLM provider."""
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="This is the answer.")
        return llm

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
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
            ]
        )
        store.clear = AsyncMock()
        return store

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock semantic cache."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)  # Default: cache miss
        cache.set = AsyncMock()
        cache.clear = AsyncMock()
        cache.count = MagicMock(return_value=0)
        return cache

    @pytest.fixture
    def rag_service_with_cache(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
        mock_cache: MagicMock,
    ) -> RAGService:
        """Create a RAG service with mocked dependencies including cache."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_cache=mock_cache,
        )

    async def test_ask_checks_cache_first(
        self,
        rag_service_with_cache: RAGService,
        mock_cache: MagicMock,
    ) -> None:
        """Ask should check cache before doing RAG."""
        await rag_service_with_cache.ask("What pets are good?")

        mock_cache.get.assert_called_once_with("What pets are good?")

    async def test_ask_returns_cached_answer_on_hit(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Ask should return cached answer without calling LLM."""
        # Configure cache hit
        mock_cache.get = AsyncMock(
            return_value=CacheEntry(
                question="What pets are good?",
                answer="Cached answer about pets.",
                chunks_json='[{"content": "Dogs are pets", "source": "pets.md", "section": "Dogs", "score": 0.9, "title": "Pets"}]',
                created_at=datetime.now(UTC),
                similarity_score=0.98,
            )
        )

        rag_service = RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_cache=mock_cache,
        )

        response = await rag_service.ask("What pets are good?")

        # Should return cached answer
        assert response.answer == "Cached answer about pets."
        # LLM should NOT be called
        mock_llm.complete.assert_not_called()
        # Embedding for query should NOT be called (we skip RAG)
        mock_embeddings.embed.assert_not_called()

    async def test_ask_stores_answer_in_cache_on_miss(
        self,
        rag_service_with_cache: RAGService,
        mock_cache: MagicMock,
    ) -> None:
        """Ask should store answer in cache after generation."""
        await rag_service_with_cache.ask("What pets are good?")

        # Should store in cache
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args.kwargs["question"] == "What pets are good?"
        assert call_args.kwargs["answer"] == "This is the answer."

    async def test_ask_does_not_cache_when_no_documents(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Ask should not cache fallback responses (no documents indexed)."""
        # Create vector store with no documents
        empty_store = MagicMock()
        empty_store.count = MagicMock(return_value=0)

        rag_service = RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=empty_store,
            semantic_cache=mock_cache,
        )

        await rag_service.ask("What is the policy?")

        # Should NOT store in cache (fallback response)
        mock_cache.set.assert_not_called()

    async def test_clear_index_also_clears_cache(
        self,
        rag_service_with_cache: RAGService,
        mock_cache: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Clearing index should also clear the cache."""
        await rag_service_with_cache.clear_index()

        mock_vector_store.clear.assert_called_once()
        mock_cache.clear.assert_called_once()

    async def test_clear_cache_only_clears_cache(
        self,
        rag_service_with_cache: RAGService,
        mock_cache: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Clear cache should only clear cache, not index."""
        await rag_service_with_cache.clear_cache()

        mock_cache.clear.assert_called_once()
        mock_vector_store.clear.assert_not_called()

    def test_get_cache_count_returns_count(
        self,
        rag_service_with_cache: RAGService,
        mock_cache: MagicMock,
    ) -> None:
        """Get cache count should return cache count."""
        mock_cache.count = MagicMock(return_value=42)
        assert rag_service_with_cache.get_cache_count() == 42


class TestRAGServiceWithoutCache:
    """Tests for RAGService when cache is disabled (None)."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create a mock LLM provider."""
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="This is the answer.")
        return llm

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider."""
        embeddings = MagicMock()
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
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
            ]
        )
        store.clear = AsyncMock()
        return store

    @pytest.fixture
    def rag_service_no_cache(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
    ) -> RAGService:
        """Create a RAG service without cache."""
        return RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_cache=None,  # Explicitly no cache
        )

    async def test_ask_works_without_cache(
        self,
        rag_service_no_cache: RAGService,
    ) -> None:
        """Ask should work when cache is None."""
        response = await rag_service_no_cache.ask("What pets are good?")
        assert response.answer == "This is the answer."

    def test_get_cache_count_returns_zero_without_cache(
        self,
        rag_service_no_cache: RAGService,
    ) -> None:
        """Get cache count should return 0 when cache is None."""
        assert rag_service_no_cache.get_cache_count() == 0

    async def test_clear_cache_is_noop_without_cache(
        self,
        rag_service_no_cache: RAGService,
    ) -> None:
        """Clear cache should be a no-op when cache is None."""
        # Should not raise
        await rag_service_no_cache.clear_cache()


class TestCacheEndToEndFlow:
    """End-to-end tests verifying the complete cache flow."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create a mock LLM provider."""
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="Dogs make great pets for volunteers.")
        return llm

    @pytest.fixture
    def mock_embeddings(self) -> MagicMock:
        """Create a mock embedding provider that returns consistent embeddings."""
        embeddings = MagicMock()
        # Return same embedding for similar questions to simulate cache hit
        embeddings.embed = AsyncMock(return_value=[0.1] * 1536)
        embeddings.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        embeddings.dimensions = 1536
        return embeddings

    @pytest.fixture
    def real_cache(self, mock_embeddings: MagicMock) -> ChromaSemanticCache:
        """Create a real semantic cache for end-to-end testing."""
        tmpdir = tempfile.mkdtemp()
        cache = ChromaSemanticCache(
            embedding_provider=mock_embeddings,
            persist_path=Path(tmpdir),
            similarity_threshold=0.95,
            ttl_hours=24,
        )
        yield cache
        # Cleanup after tests complete
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create a mock vector store with indexed documents."""
        store = MagicMock()
        store.count = MagicMock(return_value=5)  # Simulate indexed documents
        store.query = AsyncMock(
            return_value=[
                RetrievalResult(
                    id="chunk1",
                    content="Dogs are wonderful companions for shelter volunteers.",
                    metadata={"source": "volunteer-guide.md", "section": "Pets"},
                    score=0.92,  # High enough for medium/high confidence
                ),
                RetrievalResult(
                    id="chunk2",
                    content="Volunteers should always be gentle with animals.",
                    metadata={"source": "volunteer-guide.md", "section": "Guidelines"},
                    score=0.88,
                ),
            ]
        )
        store.clear = AsyncMock()
        return store

    async def test_full_cache_flow_miss_then_hit(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        mock_vector_store: MagicMock,
        real_cache: ChromaSemanticCache,
    ) -> None:
        """Test complete cache flow: miss on first query, hit on second."""
        # Create RAG service with real cache
        rag_service = RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=mock_vector_store,
            semantic_cache=real_cache,
        )

        # Verify cache starts empty
        assert real_cache.count() == 0

        # First query - should be a cache miss, LLM called
        question = "What pets are good for volunteers?"
        response1 = await rag_service.ask(question)

        assert response1.answer == "Dogs make great pets for volunteers."
        mock_llm.complete.assert_called_once()  # LLM was called

        # Verify answer was cached
        assert real_cache.count() == 1

        # Reset LLM mock to verify it's not called on cache hit
        mock_llm.complete.reset_mock()

        # Second query with same question - should be a cache hit
        response2 = await rag_service.ask(question)

        assert response2.answer == "Dogs make great pets for volunteers."
        mock_llm.complete.assert_not_called()  # LLM was NOT called (cache hit)

        # Cache count should still be 1 (no duplicate)
        assert real_cache.count() == 1

    async def test_cache_not_stored_when_no_chunks(
        self,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        real_cache: ChromaSemanticCache,
    ) -> None:
        """Test that cache is not populated when no documents are indexed."""
        # Create vector store with no documents
        empty_store = MagicMock()
        empty_store.count = MagicMock(return_value=0)

        rag_service = RAGService(
            llm_provider=mock_llm,
            embedding_provider=mock_embeddings,
            vector_store=empty_store,
            semantic_cache=real_cache,
        )

        # Query should work but not cache (no indexed documents)
        await rag_service.ask("What pets are good?")

        # Cache should remain empty (fallback responses not cached)
        assert real_cache.count() == 0
