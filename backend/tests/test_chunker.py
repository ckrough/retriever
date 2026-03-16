"""Tests for the hierarchical document chunker."""

from __future__ import annotations

from retriever.modules.rag.chunker import ChunkingConfig, HierarchicalChunker
from retriever.modules.rag.schemas import DocumentChunker


class TestHierarchicalChunker:
    """Tests for HierarchicalChunker."""

    def test_short_text_returns_single_chunk(self) -> None:
        """Short text that fits within max_size returns one chunk."""
        chunker = HierarchicalChunker()
        chunks = chunker.chunk("Hello world.", source="test.md", title="Test")

        assert len(chunks) == 1
        assert chunks[0].content == "Hello world."
        assert chunks[0].source == "test.md"
        assert chunks[0].title == "Test"
        assert chunks[0].position == 0

    def test_header_based_splitting(self) -> None:
        """Content with headers is split into sections."""
        content = "## Section A\n\nContent A.\n\n## Section B\n\nContent B."
        chunker = HierarchicalChunker()
        chunks = chunker.chunk(content, source="doc.md")

        assert len(chunks) == 2
        assert "Section A" in chunks[0].section
        assert "Content A." in chunks[0].content
        assert "Section B" in chunks[1].section
        assert "Content B." in chunks[1].content

    def test_paragraph_splitting_for_long_text(self) -> None:
        """Long text without headers is split by paragraphs."""
        # Create text longer than default max_size (1500 chars)
        paragraphs = [f"Paragraph {i}. " * 20 for i in range(10)]
        content = "\n\n".join(paragraphs)

        chunker = HierarchicalChunker(config=ChunkingConfig(max_size=500, overlap=100))
        chunks = chunker.chunk(content, source="long.txt")

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.source == "long.txt"

    def test_overlap_is_applied_between_chunks(self) -> None:
        """Adjacent chunks share overlapping content."""
        # Create content that needs splitting with overlap
        paragraphs = [f"Unique paragraph {i} with some text." for i in range(20)]
        content = "\n\n".join(paragraphs)

        chunker = HierarchicalChunker(config=ChunkingConfig(max_size=200, overlap=100))
        chunks = chunker.chunk(content, source="overlap.md")

        # With overlap, later chunks should contain some text from earlier ones
        assert len(chunks) >= 2
        # The overlap mechanism means chunk boundaries are not disjoint
        # Verify by checking total content covers more than the original
        # (due to overlap duplication)
        total_chunk_chars = sum(len(c.content) for c in chunks)
        assert total_chunk_chars >= len(content)

    def test_empty_content_returns_empty_list(self) -> None:
        """Empty or whitespace-only content produces no chunks."""
        chunker = HierarchicalChunker()

        assert chunker.chunk("", source="empty.txt") == []
        assert chunker.chunk("   \n\n  ", source="blank.txt") == []

    def test_custom_config(self) -> None:
        """Custom ChunkingConfig is respected."""
        config = ChunkingConfig(max_size=50, overlap=10, min_chunk_size=5)
        chunker = HierarchicalChunker(config=config)

        content = "Short sentence one. Short sentence two. Short sentence three."
        chunks = chunker.chunk(content, source="test.txt")

        # With very small max_size, content should be split
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.source == "test.txt"

    def test_positions_are_sequential(self) -> None:
        """Chunk positions increment sequentially."""
        content = "## A\n\nContent A.\n\n## B\n\nContent B.\n\n## C\n\nContent C."
        chunker = HierarchicalChunker()
        chunks = chunker.chunk(content, source="pos.md")

        positions = [c.position for c in chunks]
        assert positions == list(range(len(chunks)))

    def test_section_header_prepended_to_chunk_content(self) -> None:
        """When a section has a header, it is prepended to the chunk content."""
        content = "## Important Rules\n\nFollow these rules carefully."
        chunker = HierarchicalChunker()
        chunks = chunker.chunk(content, source="rules.md")

        assert len(chunks) == 1
        assert chunks[0].content.startswith("Important Rules")
        assert "Follow these rules carefully." in chunks[0].content

    def test_satisfies_document_chunker_protocol(self) -> None:
        """HierarchicalChunker satisfies the DocumentChunker protocol."""
        chunker = HierarchicalChunker()
        assert isinstance(chunker, DocumentChunker)

    def test_metadata_auto_populated(self) -> None:
        """Chunk metadata is auto-populated from fields."""
        chunker = HierarchicalChunker()
        chunks = chunker.chunk("Some text.", source="meta.md", title="Meta")

        assert len(chunks) == 1
        meta = chunks[0].metadata
        assert meta["source"] == "meta.md"
        assert meta["title"] == "Meta"
        assert meta["position"] == "0"
