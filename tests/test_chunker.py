"""Tests for document chunking."""

from src.modules.rag.chunker import ChunkingConfig, chunk_document


class TestChunkDocument:
    """Tests for chunk_document function."""

    def test_chunk_empty_content_returns_empty(self):
        """Empty content should return empty list."""
        result = chunk_document("", source="test.md")

        assert result == []

    def test_chunk_whitespace_only_returns_empty(self):
        """Whitespace-only content should return empty list."""
        result = chunk_document("   \n\n   ", source="test.md")

        assert result == []

    def test_chunk_small_content_returns_single_chunk(self):
        """Content smaller than max_size should return single chunk."""
        content = "This is a short piece of content."

        result = chunk_document(content, source="test.md")

        assert len(result) == 1
        assert result[0].content == content
        assert result[0].source == "test.md"

    def test_chunk_preserves_source(self):
        """Chunks should preserve source filename."""
        result = chunk_document("Hello, world!", source="my-doc.md")

        assert result[0].source == "my-doc.md"


class TestChunkDocumentWithHeaders:
    """Tests for chunking documents with markdown headers."""

    def test_chunk_splits_on_headers(self):
        """Document should be split on markdown headers."""
        content = """# First Section

This is the first section content.

## Second Section

This is the second section content.
"""
        result = chunk_document(content, source="test.md")

        assert len(result) >= 2
        # Check that section headers are captured
        sections = [c.section for c in result]
        assert "First Section" in sections
        assert "Second Section" in sections

    def test_chunk_includes_header_in_content(self):
        """Section header should be included in chunk content."""
        content = """## My Section

This is the content.
"""
        result = chunk_document(content, source="test.md")

        assert len(result) == 1
        assert "My Section" in result[0].content
        assert "This is the content." in result[0].content

    def test_chunk_handles_nested_headers(self):
        """Document with nested headers should be chunked correctly."""
        content = """# Main

## Sub 1

Content 1

## Sub 2

Content 2
"""
        result = chunk_document(content, source="test.md")

        # Should have chunks for each section
        assert len(result) >= 2


class TestChunkDocumentSplitting:
    """Tests for splitting large sections."""

    def test_chunk_splits_large_content(self):
        """Content larger than max_size should be split."""
        # Create content larger than default chunk size (1500 chars)
        paragraph = "This is a sentence. " * 50  # ~1000 chars
        content = paragraph + "\n\n" + paragraph + "\n\n" + paragraph

        config = ChunkingConfig(max_size=500, overlap=100)
        result = chunk_document(content, source="test.md", config=config)

        assert len(result) > 1
        # Each chunk should be at or under max size (with some tolerance for header)
        for chunk in result:
            assert len(chunk.content) <= 600  # Some tolerance

    def test_chunk_creates_overlap(self):
        """Adjacent chunks should have overlapping content."""
        # Create content that will be split
        sentences = [f"Sentence number {i}." for i in range(50)]
        content = " ".join(sentences)

        config = ChunkingConfig(max_size=300, overlap=100)
        result = chunk_document(content, source="test.md", config=config)

        # Check that there's some overlap between consecutive chunks
        if len(result) > 1:
            # The end of first chunk should appear at start of second
            chunk1_words = set(result[0].content.split()[-10:])
            chunk2_words = set(result[1].content.split()[:20])
            # There should be some overlap
            overlap = chunk1_words & chunk2_words
            assert len(overlap) > 0


class TestChunkDocumentMetadata:
    """Tests for chunk metadata."""

    def test_chunk_sets_position(self):
        """Chunks should have incrementing position values."""
        content = """## Section 1

Content 1

## Section 2

Content 2

## Section 3

Content 3
"""
        result = chunk_document(content, source="test.md")

        positions = [c.position for c in result]
        # Positions should be unique and ordered
        assert positions == sorted(set(positions))

    def test_chunk_sets_metadata_dict(self):
        """Chunks should have metadata dict with source and section."""
        content = """## Test Section

Test content here.
"""
        result = chunk_document(content, source="doc.md")

        assert len(result) == 1
        assert result[0].metadata["source"] == "doc.md"
        assert result[0].metadata["section"] == "Test Section"


class TestChunkingConfig:
    """Tests for ChunkingConfig."""

    def test_default_config_values(self):
        """Default config should have expected values."""
        config = ChunkingConfig()

        assert config.max_size == 1500
        assert config.overlap == 800
        assert config.min_chunk_size == 100

    def test_custom_config_values(self):
        """Config should accept custom values."""
        config = ChunkingConfig(max_size=1000, overlap=500, min_chunk_size=50)

        assert config.max_size == 1000
        assert config.overlap == 500
        assert config.min_chunk_size == 50
