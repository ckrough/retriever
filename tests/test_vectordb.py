"""Tests for vector store infrastructure."""

from pathlib import Path

import pytest

from src.infrastructure.vectordb import (
    ChromaVectorStore,
    DocumentChunk,
)


class TestChromaVectorStoreInit:
    """Tests for ChromaVectorStore initialization."""

    def test_init_creates_collection(self, tmp_path: Path):
        """Store should create collection on init."""
        store = ChromaVectorStore(
            persist_path=tmp_path / "chroma",
            collection_name="test_collection",
        )

        assert store.count() == 0

    def test_init_creates_persist_directory(self, tmp_path: Path):
        """Store should create persist directory if it doesn't exist."""
        persist_path = tmp_path / "new_dir" / "chroma"

        ChromaVectorStore(persist_path=persist_path)

        assert persist_path.exists()


class TestChromaVectorStoreAddChunks:
    """Tests for ChromaVectorStore.add_chunks() method."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> ChromaVectorStore:
        """Create a test store."""
        return ChromaVectorStore(
            persist_path=tmp_path / "chroma",
            collection_name="test_collection",
        )

    @pytest.fixture
    def sample_chunks(self) -> list[DocumentChunk]:
        """Create sample chunks for testing."""
        return [
            DocumentChunk(
                id="chunk1",
                content="This is the first chunk about dogs.",
                embedding=[0.1] * 1536,
                metadata={"source": "test.md", "section": "Dogs"},
            ),
            DocumentChunk(
                id="chunk2",
                content="This is the second chunk about cats.",
                embedding=[0.2] * 1536,
                metadata={"source": "test.md", "section": "Cats"},
            ),
        ]

    async def test_add_chunks_stores_documents(self, store, sample_chunks):
        """Add chunks should store documents in the collection."""
        await store.add_chunks(sample_chunks)

        assert store.count() == 2

    async def test_add_empty_list_does_nothing(self, store):
        """Add empty list should not fail."""
        await store.add_chunks([])

        assert store.count() == 0


class TestChromaVectorStoreQuery:
    """Tests for ChromaVectorStore.query() method."""

    @pytest.fixture
    def store_with_data(self, tmp_path: Path) -> ChromaVectorStore:
        """Create a store with test data."""
        store = ChromaVectorStore(
            persist_path=tmp_path / "chroma",
            collection_name="test_collection",
        )

        # Add test chunks directly using sync method for fixture
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="Dogs are great pets.",
                embedding=[0.9, 0.1] + [0.0] * 1534,  # High first dimension
                metadata={"source": "pets.md", "section": "Dogs"},
            ),
            DocumentChunk(
                id="chunk2",
                content="Cats are independent.",
                embedding=[0.1, 0.9] + [0.0] * 1534,  # High second dimension
                metadata={"source": "pets.md", "section": "Cats"},
            ),
            DocumentChunk(
                id="chunk3",
                content="Birds can fly.",
                embedding=[0.5, 0.5] + [0.0] * 1534,  # Balanced
                metadata={"source": "pets.md", "section": "Birds"},
            ),
        ]

        # Use the sync method for adding in fixture
        store._collection.add(
            ids=[c.id for c in chunks],
            documents=[c.content for c in chunks],
            embeddings=[c.embedding for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

        return store

    async def test_query_returns_results(self, store_with_data):
        """Query should return results."""
        # Query with embedding similar to "dogs" chunk
        query_embedding = [0.9, 0.1] + [0.0] * 1534

        results = await store_with_data.query(query_embedding, top_k=2)

        assert len(results) == 2

    async def test_query_returns_most_similar_first(self, store_with_data):
        """Query should return most similar chunks first."""
        # Query with embedding similar to "dogs" chunk
        query_embedding = [0.9, 0.1] + [0.0] * 1534

        results = await store_with_data.query(query_embedding, top_k=1)

        assert len(results) == 1
        assert "Dogs" in results[0].content

    async def test_query_includes_metadata(self, store_with_data):
        """Query results should include metadata."""
        query_embedding = [0.9, 0.1] + [0.0] * 1534

        results = await store_with_data.query(query_embedding, top_k=1)

        assert results[0].metadata["source"] == "pets.md"
        assert results[0].metadata["section"] == "Dogs"

    async def test_query_includes_score(self, store_with_data):
        """Query results should include similarity score."""
        query_embedding = [0.9, 0.1] + [0.0] * 1534

        results = await store_with_data.query(query_embedding, top_k=1)

        # Score should be between 0 and 1 for cosine similarity
        assert 0 <= results[0].score <= 1


class TestChromaVectorStoreClear:
    """Tests for ChromaVectorStore.clear() method."""

    @pytest.fixture
    def store_with_data(self, tmp_path: Path) -> ChromaVectorStore:
        """Create a store with test data."""
        store = ChromaVectorStore(
            persist_path=tmp_path / "chroma",
            collection_name="test_collection",
        )

        store._collection.add(
            ids=["chunk1"],
            documents=["Test content"],
            embeddings=[[0.1] * 1536],
            metadatas=[{"source": "test.md"}],
        )

        return store

    async def test_clear_removes_all_chunks(self, store_with_data):
        """Clear should remove all chunks from the store."""
        assert store_with_data.count() == 1

        await store_with_data.clear()

        assert store_with_data.count() == 0


class TestChromaVectorStoreCount:
    """Tests for ChromaVectorStore.count() method."""

    def test_count_empty_store(self, tmp_path: Path):
        """Count should return 0 for empty store."""
        store = ChromaVectorStore(persist_path=tmp_path / "chroma")

        assert store.count() == 0

    def test_count_with_data(self, tmp_path: Path):
        """Count should return correct number of chunks."""
        store = ChromaVectorStore(persist_path=tmp_path / "chroma")

        store._collection.add(
            ids=["chunk1", "chunk2", "chunk3"],
            documents=["A", "B", "C"],
            embeddings=[[0.1] * 1536, [0.2] * 1536, [0.3] * 1536],
            metadatas=[{"source": "test.md"}] * 3,
        )

        assert store.count() == 3
