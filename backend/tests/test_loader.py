"""Tests for the document loader and file validation."""

from __future__ import annotations

import pytest

from retriever.modules.rag.loader import (
    MAX_FILE_SIZE,
    FileValidationError,
    TextDocumentParser,
    validate_file,
)
from retriever.modules.rag.schemas import DocumentParser


class TestTextDocumentParser:
    """Tests for TextDocumentParser."""

    def test_markdown_title_extraction(self) -> None:
        """Extracts title from the first H1 heading in markdown."""
        parser = TextDocumentParser()
        result = parser.parse("# My Title\n\nSome content.", source="doc.md")

        assert result.title == "My Title"
        assert result.document_type == "markdown"
        assert result.source == "doc.md"
        assert result.content == "# My Title\n\nSome content."

    def test_markdown_without_heading_uses_source(self) -> None:
        """Markdown without an H1 heading falls back to source filename stem."""
        parser = TextDocumentParser()
        result = parser.parse("No heading here.", source="readme.md")

        assert result.title == "readme"
        assert result.document_type == "markdown"

    def test_plain_text_uses_source_as_title(self) -> None:
        """Plain text files use the source filename stem as title."""
        parser = TextDocumentParser()
        result = parser.parse("Just plain text.", source="notes.txt")

        assert result.title == "notes"
        assert result.document_type == "text"

    def test_source_without_extension(self) -> None:
        """Source without extension is used as-is for title."""
        parser = TextDocumentParser()
        result = parser.parse("Content.", source="noext")

        assert result.title == "noext"
        assert result.document_type == "text"

    def test_satisfies_document_parser_protocol(self) -> None:
        """TextDocumentParser satisfies the DocumentParser protocol."""
        parser = TextDocumentParser()
        assert isinstance(parser, DocumentParser)

    def test_content_preserved(self) -> None:
        """Parsed document preserves original content."""
        content = "# Title\n\nParagraph 1.\n\nParagraph 2."
        parser = TextDocumentParser()
        result = parser.parse(content, source="preserve.md")

        assert result.content == content


class TestValidateFile:
    """Tests for validate_file."""

    def test_valid_markdown_file(self) -> None:
        """Valid markdown file passes validation."""
        validate_file("document.md", 1000)  # Should not raise

    def test_valid_text_file(self) -> None:
        """Valid text file passes validation."""
        validate_file("notes.txt", 500)  # Should not raise

    def test_invalid_extension_raises(self) -> None:
        """Unsupported extension raises FileValidationError."""
        with pytest.raises(FileValidationError, match="Unsupported file format"):
            validate_file("image.png", 1000)

    def test_no_extension_raises(self) -> None:
        """File without extension raises FileValidationError."""
        with pytest.raises(FileValidationError, match="no extension"):
            validate_file("noext", 1000)

    def test_too_large_raises(self) -> None:
        """File exceeding max size raises FileValidationError."""
        with pytest.raises(FileValidationError, match="too large"):
            validate_file("big.md", MAX_FILE_SIZE + 1)

    def test_hidden_file_raises(self) -> None:
        """Hidden files (starting with .) raise FileValidationError."""
        with pytest.raises(FileValidationError, match="Hidden files"):
            validate_file(".hidden.md", 100)

    def test_empty_file_raises(self) -> None:
        """Empty file raises FileValidationError."""
        with pytest.raises(FileValidationError, match="empty"):
            validate_file("empty.md", 0)

    def test_exactly_max_size_passes(self) -> None:
        """File at exactly max size passes validation."""
        validate_file("exact.md", MAX_FILE_SIZE)  # Should not raise
